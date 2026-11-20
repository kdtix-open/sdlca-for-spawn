#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -u
# shellcheck source=lib.sh
. "$(dirname "$(readlink -f "$0")")/lib.sh"

echo "listener refuses to start without an agent command"
setup
"$ROOT/bin/sdlca-listen" alice 2> "$TMP/err"; rc=$?
check "exit status 78 (do not restart-loop)" test "$rc" -eq 78
check "message says what to do" grep -q 'SDLCA_AGENT_CMD is not set' "$TMP/err"
teardown

echo "listener starts the event stream with the right kinds, the saved cursor and the handler"
setup
with_agent 'true'
printf 'CURSOR123' > "$ACC/cursor"
"$ROOT/bin/sdlca-listen" alice
check "watches the four kinds" grep -q 'SPAWN: events --kind chat_mention,friend_request,savi_finished,savi_needs_you' "$SHIM_LOG"
check "resumes from the cursor" grep -q -- '--since CURSOR123' "$SHIM_LOG"
check "hands events to sdlca-on-chat for this account" grep -q "sdlca-on-chat' 'alice'" "$SHIM_LOG"
teardown

echo "chat text printed by the client is not written to the log"
setup
with_agent 'true'
"$ROOT/bin/sdlca-listen" alice
check "status lines are logged" grep -q 'spawn events: listening' "$ACC/listener.log"
check "the event JSON with chat text is not" bash -c "! grep -q 'SECRET CHAT TEXT' '$ACC/listener.log'"
teardown

echo "account names and env files are validated"
setup
"$ROOT/bin/sdlca-as" '../etc' true 2> "$TMP/err"; check "path tricks in account names are rejected" test $? -ne 0
for bad in '-x' '.hidden' 'Upper' 'a b' '' 'a/b/c' '/abs' 'sdlca-for-spawn/../x' 'sdlca-for-spawn/' '/'; do
  "$ROOT/bin/sdlca-as" "$bad" true 2> /dev/null; check "account name '$bad' is rejected" test $? -ne 0
done
mkdir -p "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn"
cp "$ACC/env" "$ACC/token" "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn/"
"$ROOT/bin/sdlca-as" sdlca-for-spawn true; check "an account name may contain hyphens (for example a coordinator account)" test $? -eq 0
chmod 666 "$ACC/env"
"$ROOT/bin/sdlca-as" alice true 2> "$TMP/err"; check "a group- or world-writable env file is refused" grep -q 'writable by group or others' "$TMP/err"
chmod 600 "$ACC/env"
# shellcheck disable=SC2016  # the single quotes are deliberate: the inner shell expands its own variables
show_token='printf "%s|%s" "${SPAWN_TOKEN-unset}" "${SPAWN_TOKEN_FILE-none}"'
SPAWN_TOKEN=sak_stray_personal_token bash -c "$show_token" > "$TMP/control"
check "control: a command that does NOT go through sdlca-as sees the stray SPAWN_TOKEN, so the check below can fail" test "$(cut -d'|' -f1 "$TMP/control")" = sak_stray_personal_token
SPAWN_TOKEN=sak_stray_personal_token "$ROOT/bin/sdlca-as" alice bash -c "$show_token" > "$TMP/seen"
check "a SPAWN_TOKEN left in the caller's shell does not reach what sdlca-as runs: the client would read it before the account's token file" test "$(cut -d'|' -f1 "$TMP/seen")" = unset
check "  and the account's own token file is still named" test "$(cut -d'|' -f2 "$TMP/seen")" = "$ACC/token"
printf 'SPAWN_TOKEN=sak_set_by_the_env_file\n' >> "$ACC/env"
"$ROOT/bin/sdlca-as" alice bash -c "$show_token" > "$TMP/seen"
check "an env file cannot set SPAWN_TOKEN for what it runs either" test "$(cut -d'|' -f1 "$TMP/seen")" = unset
teardown

echo "sdlca-api only ever sends the token to the Spawn origin"
setup
SPAWN_TOKEN_FILE="$ACC/token" "$ROOT/bin/sdlca-api" GET https://evil.example/x 2> "$TMP/err"; check "foreign origin refused" grep -q 'refusing to send a token' "$TMP/err"
for origin in http://example.invalid ftp://www.spawn.co 'https://www.spawn.co@elsewhere.example' file:///tmp/x www.spawn.co; do
  SPAWN_ORIGIN="$origin" SPAWN_TOKEN_FILE="$ACC/token" "$ROOT/bin/sdlca-api" GET /api/agent/v1/me > /dev/null 2>&1; check "api refuses the origin '$origin'" test $? -ne 0
  SPAWN_ORIGIN="$origin" "$ROOT/bin/sdlca-friends" alice > /dev/null 2>&1; check "friends refuses the origin '$origin'" test $? -ne 0
done
SPAWN_ORIGIN="http://127.0.0.1:9" SPAWN_TOKEN_FILE="$ACC/token" "$ROOT/bin/sdlca-api" GET /x > /dev/null 2>&1; check "api accepts plain http to this machine" test $? -eq 0
SPAWN_TOKEN_FILE="$ACC/token" "$ROOT/bin/sdlca-api" GET /api/agent/v1/me > /dev/null
check "relative paths go to the Spawn origin" grep -q 'ARGV: .*https://www.spawn.co/api/agent/v1/me' "$SHIM_LOG"
teardown

finish
