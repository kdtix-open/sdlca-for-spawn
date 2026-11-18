#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# What the small tools refuse to do: send a local file, take an odd token, write a screenshot anywhere,
# or build a handler command a shell can misread.
# shellcheck disable=SC2016  # single quotes are deliberate in the test descriptions
set -u
# shellcheck source=lib.sh
. "$(dirname "$(readlink -f "$0")")/lib.sh"

api() { SPAWN_TOKEN_FILE="$ACC/token" "$ROOT/bin/sdlca-api" "$@"; }

echo "sdlca-api never lets curl read a local file"
setup
printf 'top secret file contents' > "$TMP/secret.txt"
api POST /api/agent/v1/x "@$TMP/secret.txt" > /dev/null 2> "$TMP/err"; rc=$?
check "a body that starts with @ is refused" test "$rc" -ne 0
check "the refusal says why" grep -q 'a leading @' "$TMP/err"
check "curl was never started" bash -c "! grep -q '^ARGV' '$SHIM_LOG'"
api GET /api/agent/v1/me '@/etc/passwd' > /dev/null 2>&1; check "also on GET" test $? -ne 0
api POST /api/agent/v1/x '{"mention":"@bob"}' > /dev/null 2>&1; check "an @ inside the JSON is fine" test $? -eq 0
check "that body reached curl as text" grep -q 'BODY: {"mention":"@bob"}' "$SHIM_LOG"
teardown

echo "curl ignores ~/.curlrc and does not expand [1-3] or {a,b} in a URL"
setup
api GET '/x[1-3]' > /dev/null 2>&1
check "-q is curl's first argument" grep -q '^ARGV: -q ' "$SHIM_LOG"
check "--globoff is set" grep -q -- ' --globoff ' "$SHIM_LOG"
teardown

echo "a token file with odd content is refused, and the error never prints it"
setup
for bad in 'sak_aaaa"bbbb' 'sak_aaaa\bbbb' 'sak_aaaa bbbb' $'sak_aaaa\nsak_bbbb' $'sak_caf\xc3\xa9_cccc'; do
  : > "$SHIM_LOG"
  printf '%s' "$bad" > "$ACC/token"
  api GET /api/agent/v1/me > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
  check "refused: $(printf '%q' "$bad")" test "$rc" -ne 0
  check "  no request was made" bash -c "! grep -q '^ARGV' '$SHIM_LOG'"
  check "  the error does not hold the token" bash -c "! grep -q 'sak_' '$TMP/stdout.txt' '$TMP/stderr.txt'"
  check "  the error says what to do" grep -q 'store it again with sdlca-token' "$TMP/stderr.txt"
done
printf 'sak_secret_token_value\n' > "$ACC/token"
api GET /api/agent/v1/me > /dev/null 2>&1; check "a normal token (with its newline) still works" test $? -eq 0
teardown

echo "sdlca-token refuses what a token never contains"
setup
for bad in 'sak_aaaaaaaaaaaaaaaaaaaa"b' 'sak_aaaaaaaaaaaaaaaaaaaa\b' 'sak_aaaaaaaa aaaaaaaaaaaa' 'sak_short'; do
  printf '%s\n' "$bad" | "$ROOT/bin/sdlca-token" add bob --owner bob --stdin > /dev/null 2> "$TMP/err"; rc=$?
  check "refused: $(printf '%q' "$bad")" test "$rc" -ne 0
  check "  no token file was stored" test ! -e "$SDLCA_SPAWN_HOME/accounts/bob/token"
done
teardown

echo "sdlca-look checks its arguments before it joins anything"
setup
KIT="$TMP/kit"
mkdir -p "$KIT/node_modules/playwright-core"
ln -s "$ROOT/bin" "$KIT/bin"; ln -s "$ROOT/lib" "$KIT/lib"
look() { SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" alice "$@"; }
for world in '--render=gpu' '-x' 'alice/game-1' '@alice' '@alice/' '@alice/a/b' '@alice/game 1' '@alice/game;id' '' $'@alice/game\nx'; do
  : > "$SHIM_LOG"
  look "$world" "$TMP/shot.png" 1 > /dev/null 2>&1; rc=$?
  check "world '$(printf '%q' "$world")' is refused" test "$rc" -ne 0
  check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
done
for out in "$HOME/.bashrc" /etc/passwd "$ACC/env" "$ACC/token" shot.png ./shot.png "$TMP/shot.txt" "$TMP/shot.png.sh" "$TMP/../x.png" '/tmp/../etc/x.png' ''; do
  : > "$SHIM_LOG"
  look @alice/game-1 "$out" 1 > /dev/null 2>&1; rc=$?
  check "output '$out' is refused" test "$rc" -ne 0
  check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
done
printf 'precious' > "$TMP/target"; ln -s "$TMP/target" "$TMP/link.png"
look @alice/game-1 "$TMP/link.png" 1 > /dev/null 2>&1; check "a link is not followed" test $? -ne 0
check "  and what it points to is untouched" test "$(cat "$TMP/target")" = precious
mkdir "$TMP/dir.png"
look @alice/game-1 "$TMP/dir.png" 1 > /dev/null 2>&1; check "a folder is refused" test $? -ne 0
look @alice/game-1 "$TMP/no-such-folder/x.png" 1 > /dev/null 2>&1; check "a folder that does not exist is refused" test $? -ne 0
: > "$SHIM_LOG"
look @alice/game-1 "$TMP/shot.png" 3 > /dev/null 2>&1; check "a good call under /tmp works" test $? -eq 0
check "  the client joined the world with software rendering" grep -q 'client join @alice/game-1 --render cpu' "$SHIM_LOG"
check "  the screenshot tool got the page address, the file and the wait" grep -q "BUN: $KIT/lib/shot.mjs http://127.0.0.1:9222 $TMP/shot.png 3" "$SHIM_LOG"
check "  the client left again" grep -q 'client leave' "$SHIM_LOG"
look @@helper/game-1 "$SDLCA_SPAWN_HOME/shots/a.png" 1 > /dev/null 2>&1; check "a world an agent made, and the kit's own shots folder, work" test $? -eq 0
: > "$SHIM_LOG"
SHIM_JOIN_FAIL=sbk-fake-join-secret look @alice/game-1 "$TMP/shot2.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a failed join exits with an error" test "$rc" -ne 0
check "  and says how to see the client's own message" grep -q 'by hand to read the client' "$TMP/stderr.txt"
check "  and does not repeat what the client printed (it can hold join credentials)" bash -c "! grep -q 'sbk-fake-join-secret' '$TMP/stdout.txt' '$TMP/stderr.txt'"
check "  and still leaves the world" grep -q 'client leave' "$SHIM_LOG"
check "  the shots folder was made" test -d "$SDLCA_SPAWN_HOME/shots"
teardown

echo "sdlca-listen quotes the handler command for the shell that runs it"
setup
with_agent 'true'
for name in "it's a kit" "x';touch PWNED;'y" 'plain'; do
  ODD="$TMP/$name"
  mkdir -p "$ODD"
  ln -s "$ROOT/bin" "$ODD/bin"; ln -s "$ROOT/lib" "$ODD/lib"
  : > "$SHIM_LOG"
  SDLCA_CODE_DIR="$ODD" "$ROOT/bin/sdlca-listen" alice
  EXEC="$(sed -n 's/^SPAWN: events .*--exec //p' "$SHIM_LOG" | head -n 1)"
  rm -f "$TMP/PWNED"
  (cd "$TMP" && sh -c "for word in $EXEC; do printf '%s\n' \"\$word\"; done") > "$TMP/words" 2> /dev/null
  check "a shell reads '$name' as the handler path and the account, as two words" test "$(cat "$TMP/words")" = "$ODD/bin/sdlca-on-chat
alice"
  check "  and runs nothing else" test ! -e "$TMP/PWNED"
done
teardown

echo "install.sh refuses a folder name that would break the systemd unit"
setup
export SDLCA_SPAWN_HOME="$TMP/rt"
for name in "my kit" 'a&b' 'a#b' 'a%b' 'a$b'; do
  BAD="$TMP/$name"
  mkdir -p "$BAD"
  cp -r "$ROOT/bin" "$ROOT/lib" "$ROOT/scripts" "$ROOT/systemd" "$ROOT/templates" "$ROOT/package.json" "$BAD/"
  [ ! -e "$ROOT/bun.lock" ] || cp "$ROOT/bun.lock" "$BAD/"
  rm -rf "$HOME/.config"
  bash "$BAD/scripts/install.sh" > "$TMP/output.txt" 2> "$TMP/err"; rc=$?
  check "'$name': it stops" test "$rc" -ne 0
  check "  and says to move the kit to a plain path" grep -q 'Move the kit to a plain path' "$TMP/err"
  check "  and no unit was written" test ! -e "$HOME/.config/systemd/user/sdlca-listener@.service"
done
teardown

finish
