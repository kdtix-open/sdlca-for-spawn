#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# What the small tools refuse to do: send a local file, take an odd token, write a screenshot anywhere, join a world or an
# account they should not, leave a browser or a credential behind, or build a handler command a shell can misread.
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

# --- sdlca-look -------------------------------------------------------------------------------------------------------------------
# Helpers for its groups. No real client, browser or network is used: the spawn and bun shims stand in for them.

# look_setup: a runtime home, a kit folder of its own (so that a test can take things from it), a registry that serves a few worlds, and
# a second account.
look_setup() {
  setup
  KIT="$TMP/kit"
  mkdir -p "$KIT/node_modules/playwright-core"
  ln -s "$ROOT/bin" "$KIT/bin"; ln -s "$ROOT/lib" "$KIT/lib"
  cat > "$SDLCA_SPAWN_HOME/worlds.json" << JSON
{"worlds":{
"w-111":{"owner":"alice","slug":"game-1","address":"@alice/game-1","appId":"app-111","clone_path":"$TMP/clones/alice/game-1","aliases":[]},
"w-333":{"owner":"helper","slug":"game-1","address":"@@helper/game-1","appId":"app-333","clone_path":"$TMP/clones/helper/game-1","aliases":[],"accounts":["alice"]},
"w-444":{"owner":"alice","slug":"new-name","address":"@alice/new-name","appId":"app-444","clone_path":"$TMP/clones/alice/new-name","aliases":["@alice/old-name"],"accounts":["alice"]},
"w-555":{"owner":"bob","slug":"other","address":"@bob/other","appId":"app-555","clone_path":"$TMP/clones/bob/other","aliases":[],"accounts":["bob"]}}}
JSON
  mkdir -p "$SDLCA_SPAWN_HOME/accounts/bob"
  printf 'sak_bob_token_value\n' > "$SDLCA_SPAWN_HOME/accounts/bob/token"
  cat > "$SDLCA_SPAWN_HOME/accounts/bob/env" << ENV
OWNER=bob
SPAWN_USERNAME=bob_helper
SPAWN_TOKEN_FILE=$SDLCA_SPAWN_HOME/accounts/bob/token
: > "$TMP/bob-env-was-sourced"
ENV
  chmod 600 "$SDLCA_SPAWN_HOME/accounts/bob/token" "$SDLCA_SPAWN_HOME/accounts/bob/env"
}

# gone <pid>...: none of these processes is running (one that has ended but has not been collected yet does not count as running).
gone() {
  local p line
  for p in "$@"; do
    { read -r line < "/proc/$p/stat"; } 2> /dev/null || continue
    line="${line##*) }"
    [ "${line%% *}" = Z ] || return 1
  done
}

# start_foreign_listener: a program that was running before the look begins, with a socket that listens (what a debugging browser or
# a development server of the person would be). It sets FOREIGN_PID and FOREIGN_PORT.
start_foreign_listener() {
  python3 -I -B -c 'import socket, time
s = socket.socket()
s.bind(("127.0.0.1", 0))
s.listen(5)
print(s.getsockname()[1], flush=True)
time.sleep(120)' > "$TMP/foreign.port" &
  FOREIGN_PID=$!
  for _ in $(seq 100); do [ -s "$TMP/foreign.port" ] && break; sleep 0.05; done
  FOREIGN_PORT="$(cat "$TMP/foreign.port")"
  sleep 0.3 # a process start is timed in hundredths of a second: this puts it clearly before the look
}

# fresh_outputs: a look refuses an output name that is taken (it makes a NEW file), so every run starts with the names these tests use free.
fresh_outputs() {
  rm -f "$TMP/shot.png" "$TMP/shot2.png" "$SDLCA_SPAWN_HOME/shots/a.png" "$SDLCA_SPAWN_HOME/shots/shot.png"
  [ -z "${TMPDIR:-}" ] || rm -f "$TMPDIR/shot.png"
}

# placed_cwds: the folders that the client (join and leave) and bun were started in, one line each, from the shims' log.
placed_cwds() { sed -n -e 's/^SPAWN-CWD: //p' -e 's/^BUN-CWD: //p' "$SHIM_LOG"; }

echo "sdlca-look checks its arguments before it joins anything"
look_setup
look() { fresh_outputs; SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" alice "$@"; }
for world in '--render=gpu' '-x' 'alice/game-1' '@alice' '@alice/' '@alice/a/b' '@alice/game 1' '@alice/game;id' '' $'@alice/game\nx'; do
  : > "$SHIM_LOG"
  look "$world" "$TMP/shot.png" 1 > /dev/null 2>&1; rc=$?
  check "world '$(printf '%q' "$world")' is refused" test "$rc" -ne 0
  check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
done
for out in "$HOME/.bashrc" /etc/passwd "$ACC/env" "$ACC/token" shot.png ./shot.png tmp/shot.png "$TMP/shot.txt" "$TMP/shot.png.sh" "$TMP/../x.png" '/tmp/../etc/x.png' ''; do
  : > "$SHIM_LOG"
  look @alice/game-1 "$out" 1 > /dev/null 2>&1; rc=$?
  check "output '$out' is refused" test "$rc" -ne 0
  check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
done
printf 'precious' > "$TMP/target"; ln -s "$TMP/target" "$TMP/link.png"
: > "$SHIM_LOG"
look @alice/game-1 "$TMP/link.png" 1 > /dev/null 2>&1; check "a link is not followed" test $? -ne 0
check "  and what it points to is untouched" test "$(cat "$TMP/target")" = precious
check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
ln -s "$TMP/nowhere" "$TMP/dangling.png"
look @alice/game-1 "$TMP/dangling.png" 1 > /dev/null 2>&1; check "a link to nothing is refused too" test $? -ne 0
check "  and nothing was made at its target" test ! -e "$TMP/nowhere"
printf 'mine' > "$TMP/taken.png"
: > "$SHIM_LOG"
look @alice/game-1 "$TMP/taken.png" 1 > /dev/null 2> "$TMP/stderr.txt"; check "a file that is there already is not replaced: the output must be new" test $? -ne 0
check "  it is untouched" test "$(cat "$TMP/taken.png")" = mine
check "  the message says to give a name that does not exist yet" grep -q 'give a name that does not exist yet' "$TMP/stderr.txt"
check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
mkdir "$TMP/dir.png"
look @alice/game-1 "$TMP/dir.png" 1 > /dev/null 2>&1; check "a folder is refused" test $? -ne 0
look @alice/game-1 "$TMP/no-such-folder/x.png" 1 > /dev/null 2>&1; check "a folder that does not exist is refused" test $? -ne 0
for wait in abc -1 1.5 ' 7' 10000; do
  : > "$SHIM_LOG"
  look @alice/game-1 "$TMP/shot.png" "$wait" > /dev/null 2>&1; rc=$?
  check "wait-seconds '$wait' is refused" test "$rc" -ne 0
  check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
done
: > "$SHIM_LOG"
: > "$SHIM_LOG"
look @alice/game-1 "$TMP/shot.png" > /dev/null 2>&1; check "with no wait given the screenshot waits 8 seconds" test $? -eq 0
check "  as the screenshot tool is told" grep -Eq "^BUN: .*/shot\.png 8 - - look[0-9]+ - -\$" "$SHIM_LOG"
for wait in 18446744073709551617 00000000000000000008 99999; do
  : > "$SHIM_LOG"
  look @alice/game-1 "$TMP/shot.png" "$wait" > /dev/null 2>&1; rc=$?
  check "a wait of more digits than a count of seconds needs ($wait) is refused, not read as another number" test "$rc" -ne 0
  check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
done
: > "$SHIM_LOG"
look @alice/game-1 "$TMP/shot.png" 3 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; check "a good call under /tmp works" test $? -eq 0
check "  the client joined the world with software rendering" grep -q 'client join @alice/game-1 --render cpu' "$SHIM_LOG"
check "  the screenshot tool got the page address, a file in a private folder of the look's own, and the wait" grep -Eq "^BUN: $KIT/lib/shot.mjs http://127.0.0.1:9222 ${TMPDIR:-/tmp}/sdlca-look\.[A-Za-z0-9]+/shot\.png 3 - - look[0-9]+ - -\$" "$SHIM_LOG"
check "  the picture it made is at the path that was asked for" grep -q 'stand-in picture' "$TMP/shot.png"
check "  and the tool says where it is" test "$(cat "$TMP/stdout.txt")" = "saved $TMP/shot.png"
check "  the client left again" grep -q 'client leave' "$SHIM_LOG"
JOINED_AS="$(sed -n 's/^SPAWN: client join .* --name \(look[0-9]*\) .*/\1/p' "$SHIM_LOG")"
check "  and it left the body it joined, by the same name" bash -c "test -n '$JOINED_AS' && grep -qx 'SPAWN: client leave --name $JOINED_AS' '$SHIM_LOG'"
look @@helper/game-1 "$SDLCA_SPAWN_HOME/shots/a.png" 1 > /dev/null 2>&1; check "a world an agent made, and the kit's own shots folder, work" test $? -eq 0
: > "$SHIM_LOG"
SHIM_JOIN_FAIL=sbk-fake-join-secret look @alice/game-1 "$TMP/shot2.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a failed join exits with an error" test "$rc" -ne 0
check "  and says how to see the client's own message" grep -q 'by hand to read the client' "$TMP/stderr.txt"
check "  and does not repeat what the client printed (it can hold join credentials)" bash -c "! grep -q 'sbk-fake-join-secret' '$TMP/stdout.txt' '$TMP/stderr.txt'"
check "  and still leaves the world" grep -q 'client leave' "$SHIM_LOG"
check "  the shots folder was made" test -d "$SDLCA_SPAWN_HOME/shots"
teardown

echo "sdlca-look starts the client and the screenshot tool in a private folder of its own, never in the caller's"
look_setup
CLONE="$TMP/clones/alice/game-1" # where an agent works: a world's clone, which other people can push to
printf 'preload = ["./pwn.js"]\n' > "$CLONE/bunfig.toml"
printf 'PLANTED_BY_THE_WORLD=%s\n' "$CLONE/dist" > "$CLONE/.env"
(cd "$CLONE" && spawn client leave --name control && bun /nonexistent/other.mjs)
check "control: a client and a bun that are started in that folder load both files, as the real ones do, so the checks below can fail" test "$(wc -l < "$SHIM_OUT/loaded-from-cwd")" -eq 4
# look_from_clone <NAME=value>...: a look that is started from the clone, with those settings for the stand-ins. The status is in $rc.
look_from_clone() {
  rm -f "$SHIM_OUT/loaded-from-cwd"; : > "$SHIM_LOG"; fresh_outputs
  (cd "$CLONE" && env "$@" SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" alice @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2>&1); rc=$?
}
# in_a_folder_of_its_own: everything the look started (the join, the screenshot tool, the leave) started in one folder, and the look made it.
in_a_folder_of_its_own() {
  local folders
  folders="$(placed_cwds | sort -u)"
  [ "$(printf '%s\n' "$folders" | wc -l)" -eq 1 ] && case "$folders" in "${TMPDIR:-/tmp}"/sdlca-look.*) true ;; *) false ;; esac
}
look_from_clone SHIM_NONE=1
check "a look that is started from that folder works" test "$rc" -eq 0
check "  nothing loaded the bunfig.toml or the .env of the caller's folder" test ! -e "$SHIM_OUT/loaded-from-cwd"
check "  the join, the screenshot tool and the leave all started in one folder, and the look made it" in_a_folder_of_its_own
check "  and there were three of them" test "$(placed_cwds | wc -l)" -eq 3
for scenario in "SHIM_JOIN_FAIL=x" "SHIM_JOIN_NO_PAGE=1" "SHIM_BUN_FAIL=1" "SHIM_JOIN_HANG=20 SDLCA_LOOK_TIMEOUT=2" "SHIM_BUN_HANG=20 SDLCA_LOOK_TIMEOUT=3"; do
  # shellcheck disable=SC2086  # a few NAME=value words
  look_from_clone $scenario
  check "a look that ends badly [$scenario]: it fails" test "$rc" -ne 0
  check "  nothing loaded a file of the caller's folder" test ! -e "$SHIM_OUT/loaded-from-cwd"
  check "  and what it started, the leave included, started in a folder of its own" in_a_folder_of_its_own
done
teardown

echo "sdlca-look places the picture as a new file, and never writes through a link that appears while it runs"
look_setup
export TMPDIR="$TMP/tmpdir"; mkdir -p "$TMPDIR"
look() { fresh_outputs; SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" alice "$@"; }
printf 'PRECIOUS' > "$TMP/victim.txt"
ln -s "$TMP/victim.txt" "$TMP/control.png"
bun "$ROOT/lib/shot.mjs" http://127.0.0.1:9222 "$TMP/control.png" 1
check "control: a screenshot tool that writes straight to the path it is given (what this tool used to do) writes through a link that is there" grep -q 'stand-in picture' "$TMP/victim.txt"
printf 'PRECIOUS' > "$TMP/victim.txt"
: > "$SHIM_LOG"
SHIM_PLANT_LINK="$TMP/pic.png=$TMP/victim.txt" look @alice/game-1 "$TMP/pic.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a link that appears at the output while the look runs is not written through: the look fails" test "$rc" -ne 0
check "  what the link points to is untouched" test "$(cat "$TMP/victim.txt")" = PRECIOUS
check "  the message says that the picture could not be saved there" grep -q 'could not save the picture' "$TMP/stderr.txt"
check "  the tool does not claim that it saved one" bash -c "! grep -q saved '$TMP/stdout.txt'"
check "  the client left" grep -q 'client leave' "$SHIM_LOG"
check "  and no working folder was left behind" test -z "$(find "$TMPDIR" -maxdepth 1 -name 'sdlca-look.*')"
SHIM_PLANT_FILE="$TMP/pic2.png=somebody else's file" look @alice/game-1 "$TMP/pic2.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "a file that appears there is not replaced either" test "$rc" -ne 0
check "  it is untouched" test "$(cat "$TMP/pic2.png")" = "somebody else's file"
mkdir "$TMP/place" "$TMP/elsewhere"
SHIM_PLANT_LINK="$TMP/place=$TMP/elsewhere" look @alice/game-1 "$TMP/place/pic3.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "a folder that is replaced by a link while the look runs is not followed" test "$rc" -ne 0
check "  and nothing was written where the link points" test -z "$(ls -A "$TMP/elsewhere")"
SHIM_BUN_NO_FILE=1 look @alice/game-1 "$TMP/nofile.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "a screenshot tool that succeeds and makes no picture is an error" test "$rc" -ne 0
check "  that says so" grep -q 'made no picture' "$TMP/stderr.txt"
check "  and nothing is at the output" test ! -e "$TMP/nofile.png"
look @alice/game-1 "$TMP/ok.png" 1 > "$TMP/stdout.txt" 2> /dev/null; rc=$?
check "control: without any of that the same look works" test "$rc" -eq 0
check "  and says where the picture is" test "$(cat "$TMP/stdout.txt")" = "saved $TMP/ok.png"
check "  the picture is private to the user (mode 600)" test "$(stat -c %a "$TMP/ok.png")" = 600
unset TMPDIR
teardown

echo "sdlca-look stops what the join started also when the join stays alive after its page line, and when the browser ignores SIGTERM"
look_setup
look() { fresh_outputs; SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" alice "$@"; }
still_running() { ! gone "$@"; }
: > "$SHIM_LOG"
SHIM_JOIN_BROWSER=1 SHIM_JOIN_LINGER=30 SDLCA_LOOK_TIMEOUT=3 look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
read -r main helper _ < "$SHIM_OUT/browser.pids"
check "a join that has shown its page line and stays alive is stopped at the time limit" test "$rc" -ne 0
check "  with the message about the time limit" grep -q 'did not finish within the time limit of 3 seconds' "$TMP/stderr.txt"
check "  and the browser it started is gone, with its helper (its page address was written down when the line came)" gone "$main" "$helper"
check "  and nothing warns that a browser is still running" bash -c "! grep -q 'still running' '$TMP/stderr.txt'"
SHIM_JOIN_BROWSER=1 SHIM_BROWSER_IGNORE_TERM=1 spawn client join x > /dev/null 2>&1
read -r main helper _ < "$SHIM_OUT/browser.pids"
kill -s TERM "$main" "$helper"; sleep 0.5
check "control: the stand-in browser ignores SIGTERM" still_running "$main" "$helper"
kill -s KILL "$main" "$helper"
: > "$SHIM_LOG"
SHIM_JOIN_BROWSER=1 SHIM_BROWSER_IGNORE_TERM=1 look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
read -r main helper _ < "$SHIM_OUT/browser.pids"
check "a browser that ignores SIGTERM: the look works" test "$rc" -eq 0
check "  and the browser is gone all the same, with its helper (it is killed after it was asked)" gone "$main" "$helper"
check "  and nothing warns" test ! -s "$TMP/stderr.txt"
teardown

echo "sdlca-look joins only a world this account serves"
look_setup
look() { fresh_outputs; SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" alice "$@"; }
for world in @bob/other @alice/never-heard-of @alice/game @alice/game-10 @alice/game-1. @Alice/game-1 @@alice/game-1 @alice/Game-1 @@helper/game; do
  : > "$SHIM_LOG"
  look "$world" "$TMP/shot.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
  check "'$world' is refused" test "$rc" -ne 0
  check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
  check "  and the message says what to run first" grep -q "sdlca-worlds --apply --only $world" "$TMP/stderr.txt"
done
: > "$SHIM_LOG"
fresh_outputs; SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" bob @bob/other "$TMP/shot.png" 1 > /dev/null 2>&1; check "the account that does serve @bob/other can look at it" test $? -eq 0
check "  and joined as that account" grep -q "SPAWN-JOIN-AS: $SDLCA_SPAWN_HOME/accounts/bob/token" "$SHIM_LOG"
: > "$SHIM_LOG"
look @alice/old-name "$TMP/shot.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "an old address of a renamed world works" test "$rc" -eq 0
check "  and the world is joined under its current address, never the old one" grep -q 'client join @alice/new-name --render cpu' "$SHIM_LOG"
check "  and nothing joined the old name" bash -c "! grep -q 'old-name' '$SHIM_LOG'"
check "  and the message says so" grep -q '@alice/old-name is an old address; joining it as @alice/new-name' "$TMP/stderr.txt"
: > "$SHIM_LOG"
look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2>&1; check "an entry with no list of accounts (an older one) is served to the owner's account" test $? -eq 0
cat > "$SDLCA_SPAWN_HOME/worlds.json" << JSON
{"worlds":{"w-666":{"owner":"alice","slug":"odd","address":"not an address","appId":"app-666","aliases":["@alice/odd"],"accounts":["alice"]}}}
JSON
: > "$SHIM_LOG"
look @alice/odd "$TMP/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "an entry whose address is not an address is not joined" test "$rc" -ne 0
check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
check "  and the message says to fix the entry" grep -q 'does not look like @owner/world' "$TMP/stderr.txt"
for registry in 'not json at all' '[]' '{"worlds":[]}' '{"worlds":{"w":"x"}}' ''; do
  printf '%s' "$registry" > "$SDLCA_SPAWN_HOME/worlds.json"
  : > "$SHIM_LOG"
  look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2>&1; rc=$?
  check "a registry that holds '$registry' serves nothing" test "$rc" -ne 0
  check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
done
rm -f "$SDLCA_SPAWN_HOME/worlds.json"
: > "$SHIM_LOG"
look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2>&1; rc=$?
check "no registry at all serves nothing" test "$rc" -ne 0
check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
# A lookup that cannot answer (route.py is missing, crashes, or says "usage error") is a refusal, never "served". The kit folder here has a
# route.py that exits with the status under test, and one that says yes as the control.
mkdir -p "$TMP/kit3/lib" "$TMP/kit3/node_modules/playwright-core"
ln -s "$ROOT/bin" "$TMP/kit3/bin"
: > "$TMP/kit3/lib/shot.mjs"
look3() { fresh_outputs; SDLCA_CODE_DIR="$TMP/kit3" "$ROOT/bin/sdlca-look" alice @bob/other "$TMP/shot.png" 1; }
for status in 2 3 127; do
  printf 'import sys\nsys.exit(%s)\n' "$status" > "$TMP/kit3/lib/route.py"
  : > "$SHIM_LOG"
  look3 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
  check "a lookup that fails with status $status is a refusal" test "$rc" -ne 0
  check "  that says that it could not look the world up" grep -q 'could not look @bob/other up' "$TMP/stderr.txt"
  check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
done
rm -f "$TMP/kit3/lib/route.py"
: > "$SHIM_LOG"
look3 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "no route.py at all is a refusal too" test "$rc" -ne 0
check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
printf 'import sys\nprint("@bob/other")\n' > "$TMP/kit3/lib/route.py"
: > "$SHIM_LOG"
look3 > /dev/null 2>&1; rc=$?
check "control: the same kit folder with a route.py that says yes lets the look through" test "$rc" -eq 0
check "  and the client joined" grep -q 'client join @bob/other' "$SHIM_LOG"
teardown

echo "sdlca-look inside an agent turn names only the turn's own account"
look_setup
turn_look() { fresh_outputs; SDLCA_TURN_ACCOUNT=alice SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" "$@"; }
rm -f "$TMP/bob-env-was-sourced"
: > "$SHIM_LOG"
turn_look bob @bob/other "$TMP/shot.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "naming another account is refused" test "$rc" -ne 0
check "  and the message names the turn's own account" grep -q "only the turn's own account (alice) may be named" "$TMP/stderr.txt"
check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
check "  and the other account's env file was not even read" test ! -e "$TMP/bob-env-was-sourced"
# An account that exists and whose name starts with the turn's own (the group/name layout): a guard that compared only a prefix would let it through.
mkdir -p "$SDLCA_SPAWN_HOME/accounts/alice/team"
printf 'sak_team_token_value\n' > "$SDLCA_SPAWN_HOME/accounts/alice/team/token"
printf 'OWNER=alice\nSPAWN_USERNAME=alice_team\nSPAWN_TOKEN_FILE=%s\n' "$SDLCA_SPAWN_HOME/accounts/alice/team/token" > "$SDLCA_SPAWN_HOME/accounts/alice/team/env"
chmod 600 "$SDLCA_SPAWN_HOME/accounts/alice/team/token" "$SDLCA_SPAWN_HOME/accounts/alice/team/env"
: > "$SHIM_LOG"
turn_look alice/team @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "an existing account whose name only starts with the turn's account (alice/team) is refused" test "$rc" -ne 0
check "  with the message that names the turn's own account" grep -q "only the turn's own account (alice) may be named" "$TMP/stderr.txt"
check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
fresh_outputs; SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" alice/team @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2>&1; rc=$?
check "control: with no turn that account can look, so the refusal above is the guard's" test "$rc" -eq 0
check "  and it joined as that account" grep -q "SPAWN-JOIN-AS: $SDLCA_SPAWN_HOME/accounts/alice/team/token" "$SHIM_LOG"
for other in '' alice/x ALICE 'alice ' ../accounts/alice; do
  turn_look "$other" @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2>&1; rc=$?
  check "the account '$other' is not the turn's account, so it is refused" test "$rc" -ne 0
done
: > "$SHIM_LOG"
turn_look alice @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2>&1; check "the turn's own account can look" test $? -eq 0
check "  and joined as that account" grep -q "SPAWN-JOIN-AS: $SDLCA_SPAWN_HOME/accounts/alice/token" "$SHIM_LOG"
: > "$SHIM_LOG"
fresh_outputs; SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" bob @bob/other "$TMP/shot.png" 1 > /dev/null 2>&1; check "control: with no turn (a person's own shell) any account may be named" test $? -eq 0
check "  and joined as that account" grep -q "SPAWN-JOIN-AS: $SDLCA_SPAWN_HOME/accounts/bob/token" "$SHIM_LOG"
: > "$SHIM_LOG"
turn_look_unset() { fresh_outputs; env -u SDLCA_TURN_ACCOUNT SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" "$@"; }
turn_look_unset bob @bob/other "$TMP/shot.png" 1 > /dev/null 2>&1; check "control: a command that unsets the variable is not stopped by it (the check keeps the allowed tool from being the way round; it is not a sandbox, and the agent tool's own rules must refuse such a command)" test $? -eq 0
: > "$SHIM_LOG"
fresh_outputs; SDLCA_TURN_ACCOUNT=alice env SDLCA_TURN_ACCOUNT=bob SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" bob @bob/other "$TMP/shot.png" 1 > /dev/null 2>&1; check "control: nor is one that sets it to another account" test $? -eq 0
: > "$SHIM_LOG"
turn_look --check bob > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "--check of another account is refused too" test "$rc" -ne 0
check "  with the same message" grep -q "only the turn's own account (alice) may be named" "$TMP/stderr.txt"
turn_look --check > "$TMP/stdout.txt" 2> /dev/null
check "--check with no account looks at the turn's own" grep -q 'the account alice loads' "$TMP/stdout.txt"
teardown

echo "sdlca-look waits for a real picture: the software renderer draws nothing until the world has loaded"
look_setup
look() { fresh_outputs; SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" alice "$@"; }
export SDLCA_LOOK_POLL=1 SDLCA_LOOK_SETTLE=1
fresh_calls() { rm -f "$SHIM_OUT/bun.calls"; : > "$SHIM_LOG"; }
calls() { cat "$SHIM_OUT/bun.calls" 2> /dev/null || echo 0; }
size_of() { wc -c < "$1" | tr -d ' '; }
fresh_calls
look @alice/game-1 "$TMP/w1.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a real picture at the first try is kept as it is, after one screenshot" bash -c "test '$rc' -eq 0 && test \"\$(cat '$SHIM_OUT/bun.calls')\" = 1"
check "  and nothing was said about waiting" bash -c "! grep -q 'no real picture yet' '$TMP/stderr.txt'"
fresh_calls
SHIM_BUN_SIZES="4354 4354 40000 50000" look @alice/game-1 "$TMP/w2.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "blank pictures are retried: the look succeeds when the world has loaded" test "$rc" -eq 0
check "  it took four pictures (two blank, the first real one, and one more after the scene had time to fill in)" test "$(calls)" -eq 4
check "  the picture that was kept is the last one" test "$(size_of "$TMP/w2.png")" -gt 50000
check "  it says once that it is waiting for the world" test "$(grep -c 'no real picture yet' "$TMP/stderr.txt")" -eq 1
check "  and it says where the picture is" test "$(cat "$TMP/stdout.txt")" = "saved $TMP/w2.png"
check "  the client left" grep -q 'client leave' "$SHIM_LOG"
fresh_calls
SHIM_BUN_SIZES="4354 40000" SHIM_BUN_FAIL_FROM=3 look @alice/game-1 "$TMP/w3.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "when the extra picture after the scene has settled fails, the first real picture is kept" test "$rc" -eq 0
check "  it was the picture before the failure (40000 bytes, not the 4 KB blank one)" bash -c "test \"\$(wc -c < '$TMP/w3.png' | tr -d ' ')\" -gt 40000 && test \"\$(wc -c < '$TMP/w3.png' | tr -d ' ')\" -lt 41000"
fresh_calls
SHIM_BUN_SIZES="4354" SDLCA_LOOK_TIMEOUT=5 look @alice/game-1 "$TMP/w4.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a world that never draws: the look fails at the time limit" test "$rc" -ne 0
check "  with a message that says every picture was blank" grep -q 'every picture was blank when the time limit of 5 seconds' "$TMP/stderr.txt"
check "  and what to do about it" grep -q 'larger SDLCA_LOOK_TIMEOUT' "$TMP/stderr.txt"
check "  nothing is at the output" test ! -e "$TMP/w4.png"
check "  it tried more than once" test "$(calls)" -ge 2
check "  and the client left" grep -q 'client leave' "$SHIM_LOG"
fresh_calls
SHIM_BUN_BUSY=2 SHIM_BUN_SIZES="30000 45000" look @alice/game-1 "$TMP/w9.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a page that is too busy to answer while the world loads is asked again, not given up on" test "$rc" -eq 0
check "  two busy answers, the first real picture, and one more after the scene settled: four calls" test "$(calls)" -eq 4
check "  the picture that was kept is the last one" test "$(size_of "$TMP/w9.png")" -gt 45000
check "  and no stack trace or crash is shown" bash -c "! grep -q -i -E 'TimeoutError|stack|at /' '$TMP/stderr.txt'"
fresh_calls
SHIM_BUN_BUSY=1000 SDLCA_LOOK_TIMEOUT=5 look @alice/game-1 "$TMP/w10.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a page that never answers: the look fails at the time limit" test "$rc" -ne 0
check "  with a message that says the page was too busy drawing" grep -q 'the page was too busy drawing to answer' "$TMP/stderr.txt"
check "  nothing is at the output, and the client left" bash -c "test ! -e '$TMP/w10.png' && grep -q 'client leave' '$SHIM_LOG'"
fresh_calls
SHIM_BUN_SIZES="4354 4354 30000" SDLCA_LOOK_SETTLE=0 look @alice/game-1 "$TMP/w5.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "SDLCA_LOOK_SETTLE=0 is allowed: the real picture is followed at once by one more" bash -c "test '$rc' -eq 0 && test \"\$(cat '$SHIM_OUT/bun.calls')\" = 4"
for bad in 0 301 abc -1 1.5; do
  fresh_calls
  SDLCA_LOOK_POLL="$bad" look @alice/game-1 "$TMP/w6.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
  check "SDLCA_LOOK_POLL='$bad' is refused" test "$rc" -ne 0
  check "  before anything joins" bash -c "! grep -q 'client join' '$SHIM_LOG'"
  check "  with a message that says what is allowed" grep -q 'SDLCA_LOOK_POLL must be a whole number of seconds from 1 to 300' "$TMP/stderr.txt"
done
for bad in 301 abc -1 1.5; do
  fresh_calls
  SDLCA_LOOK_SETTLE="$bad" look @alice/game-1 "$TMP/w7.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
  check "SDLCA_LOOK_SETTLE='$bad' is refused" test "$rc" -ne 0
  check "  before anything joins" bash -c "! grep -q 'client join' '$SHIM_LOG'"
  check "  with a message that says what is allowed" grep -q 'SDLCA_LOOK_SETTLE must be a whole number of seconds from 0 to 300' "$TMP/stderr.txt"
done
fresh_calls
SPAWN_TOKEN=sak_stray_personal_token look @alice/game-1 "$TMP/w8.png" 1 > /dev/null 2>&1; rc=$?
check "a SPAWN_TOKEN left in the caller's shell does not reach the client (it would read that before the account's token file)" bash -c "test '$rc' -eq 0 && grep -q '^SPAWN-TOKEN-ENV: unset\$' '$SHIM_LOG' && ! grep -q '^SPAWN-TOKEN-ENV: set\$' '$SHIM_LOG'"
unset SDLCA_LOOK_POLL SDLCA_LOOK_SETTLE
teardown

echo "sdlca-look --check reports what is missing, and joins nothing"
look_setup
BASH_BIN="$(command -v bash)"
# make_path <tool>...: a PATH that holds only what the tool needs (dirname, readlink and find) and the programs you name. spawn and
# bun are the shims.
make_path() {
  rm -rf "$TMP/p"; mkdir -p "$TMP/p"
  local t
  for t in dirname readlink find bash "$@"; do
    if [ -x "$ROOT/tests/shims/$t" ]; then ln -s "$ROOT/tests/shims/$t" "$TMP/p/$t"; else ln -s "$(command -v "$t")" "$TMP/p/$t"; fi
  done
}
# check_look <args>...: run the report with that PATH and the kit folder; the output goes to stdout.txt and the status is in $rc.
check_look() { PATH="$TMP/p" SDLCA_CODE_DIR="$KIT" "$BASH_BIN" "$ROOT/bin/sdlca-look" --check "$@" > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?; }
mkdir -p "$SDLCA_SPAWN_HOME/shots"
make_path python3 timeout spawn bun
: > "$SHIM_LOG"
PATH="$TMP/p" spawn client leave --name control > /dev/null 2>&1
check "control: under that PATH the stand-in client runs and logs its call, so an empty log below means that nothing was started" grep -q 'SPAWN: client leave --name control' "$SHIM_LOG"
PATH="$TMP/p" bun control.mjs > /dev/null 2>&1
check "control: and so does the stand-in bun" grep -q 'BUN: control.mjs' "$SHIM_LOG"
: > "$SHIM_LOG"
check_look alice
check "with everything in place the report says so and exits 0" test "$rc" -eq 0
check "  every line is ok" bash -c "! grep -q 'MISSING' '$TMP/stdout.txt' && grep -c '^  ok ' '$TMP/stdout.txt' | grep -qx 9"
check "  it says plainly that it cannot see the client's own browser, and what to do if a look fails at the join" bash -c "grep -q '^  note     the browser: the Spawn client starts its own' '$TMP/stdout.txt' && grep -q 'spawn client join <world> --render cpu' '$TMP/stdout.txt'"
check "  and it names none of the client's private details (Spawn publishes none)" bash -c "! grep -q -E 'install-browser|SPAWN_CLIENT|spawnco-client|Chromium build' '$TMP/stdout.txt'"
check "  it ends with a plain sentence" grep -q 'everything a look needs is in place' "$TMP/stdout.txt"
check "  it ran no program of the client and no bun (nothing was joined)" test ! -s "$SHIM_LOG"
check_look
check "with no account the account line is skipped, and the rest is still checked" bash -c "test '$rc' -eq 0 && grep -q 'skipped  the account' '$TMP/stdout.txt'"
check_look alice extra > /dev/null; check "more than one account is a usage error" test "$rc" -ne 0
check "  and nothing is reported" bash -c "! grep -q 'what a look needs' '$TMP/stdout.txt'"
"$ROOT/bin/sdlca-look" --help > "$TMP/stdout.txt" 2>&1; check "--help prints the usage and the options" bash -c "grep -q 'sdlca-look --check \[account\]' '$TMP/stdout.txt' && grep -q 'SDLCA_LOOK_TIMEOUT' '$TMP/stdout.txt'"
# one thing missing at a time: it is reported with its fix, the status is 1, and the rest is still checked
missing() { # missing <description> <text of the MISSING line> <text of the fix>
  check "$1: exit 1" test "$rc" -eq 1
  check "  it says what is missing" grep -q "MISSING  $2" "$TMP/stdout.txt"
  check "  and what to do" grep -q -- "-> .*$3" "$TMP/stdout.txt"
  check "  and ends by saying so" grep -q 'something is missing' "$TMP/stdout.txt"
  check "  and nothing was run" test ! -s "$SHIM_LOG"
}
make_path python3 timeout bun; check_look alice; missing "no spawn client" 'the spawn client' 'bun add -g @spawnco/client'
make_path python3 timeout spawn; check_look alice; missing "no bun" 'bun' 'https://bun.sh'
make_path timeout spawn bun; check_look alice; missing "no python3" 'python3' 'install Python 3'
make_path python3 spawn bun; check_look alice; missing "no timeout" 'timeout' 'install GNU coreutils'
make_path python3 timeout spawn bun
mkdir -p "$TMP/kit2"; ln -s "$ROOT/bin" "$TMP/kit2/bin"; ln -s "$ROOT/lib" "$TMP/kit2/lib"
PATH="$TMP/p" SDLCA_CODE_DIR="$TMP/kit2" "$BASH_BIN" "$ROOT/bin/sdlca-look" --check alice > "$TMP/stdout.txt" 2>&1; rc=$?
missing "no playwright-core in the kit's folder" 'playwright-core in' 'bun install'
PLAYWRIGHT_BROWSERS_PATH="$TMP/nowhere" check_look alice
check "the report does not look for a browser: a browser setting changes nothing, and no browser folder is needed" test "$rc" -eq 0
if [ "$(id -u)" -ne 0 ]; then
  chmod 500 "$SDLCA_SPAWN_HOME/shots"
  check_look alice; missing "a shots folder that cannot be written" 'the shots folder .* is not writable' 'chmod u+w'
  chmod 700 "$SDLCA_SPAWN_HOME/shots"
fi
rmdir "$SDLCA_SPAWN_HOME/shots"; : > "$SDLCA_SPAWN_HOME/shots"
check_look alice; missing "a shots path that is a file" 'the shots folder .* is not a folder' 'mkdir -p'
rm -f "$SDLCA_SPAWN_HOME/shots"
check_look alice
check "no shots folder yet is fine: a look makes it" bash -c "test '$rc' -eq 0 && grep -q 'does not exist yet' '$TMP/stdout.txt'"
check_look nobody; missing "an account that does not exist" 'the account nobody' 'unknown account'
check_look 'Bad Name'; missing "an account name that is not a name" 'the account Bad Name' 'invalid account name'
chmod 666 "$ACC/env"; check_look alice; missing "an env file that others can write" 'the account alice' 'writable by group or others'
chmod 600 "$ACC/env"
for bad in 0 3601 abc -5 1.5 1e2; do
  SDLCA_LOOK_TIMEOUT="$bad" check_look alice
  missing "SDLCA_LOOK_TIMEOUT=$bad" 'a usable time limit' 'whole number of seconds from 1 to 3600'
done
printf 'SDLCA_LOOK_TIMEOUT=0\n' >> "$ACC/env"
check_look alice; missing "a bad SDLCA_LOOK_TIMEOUT in the account's env file" 'a usable time limit' 'whole number of seconds'
sed -i '/^SDLCA_LOOK_TIMEOUT=0$/d' "$ACC/env"
for bad in 0 301 abc -1 1.5; do
  SDLCA_LOOK_POLL="$bad" check_look alice
  missing "SDLCA_LOOK_POLL=$bad" 'usable waits between pictures' 'SDLCA_LOOK_POLL to a whole number of seconds from 1 to 300'
done
for bad in 301 abc -1 1.5; do
  SDLCA_LOOK_SETTLE="$bad" check_look alice
  missing "SDLCA_LOOK_SETTLE=$bad" 'usable waits between pictures' 'SDLCA_LOOK_SETTLE from 0 to 300'
done
SDLCA_LOOK_SETTLE=0 check_look alice
check "SDLCA_LOOK_SETTLE=0 is allowed (no waiting for the scene to fill in)" test "$rc" -eq 0
teardown

echo "sdlca-look gives the join and the screenshot a time limit, and leaves however it ends"
look_setup
look() { fresh_outputs; SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" alice "$@"; }
export TMPDIR="$TMP/tmpdir"; mkdir -p "$TMPDIR" # so that a working folder left behind would be seen
for bad in 0 00 3601 99999 abc -5 1.5 '7 ' 1e2; do
  : > "$SHIM_LOG"
  SDLCA_LOOK_TIMEOUT="$bad" look @alice/game-1 "$SDLCA_SPAWN_HOME/shots/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
  check "SDLCA_LOOK_TIMEOUT='$bad' is refused" test "$rc" -ne 0
  check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
  check "  and the message says what is allowed" grep -q 'whole number of seconds from 1 to 3600' "$TMP/stderr.txt"
done
: > "$SHIM_LOG"
look @alice/game-1 "$SDLCA_SPAWN_HOME/shots/shot.png" 240 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "a wait as long as the limit is refused (the join and the screenshot share it)" test "$rc" -ne 0
check "  with a message that says so" grep -q 'must be less than the time limit of 240 seconds' "$TMP/stderr.txt"
check "  and the client was never asked to join" bash -c "! grep -q 'client join' '$SHIM_LOG'"
SDLCA_LOOK_TIMEOUT=10 look @alice/game-1 "$SDLCA_SPAWN_HOME/shots/shot.png" 10 > /dev/null 2>&1; check "the same with a limit of 10 and a wait of 10" test $? -ne 0
: > "$SHIM_LOG"
look @alice/game-1 "$SDLCA_SPAWN_HOME/shots/shot.png" 239 > /dev/null 2>&1; check "a wait one second under the limit is fine" test $? -eq 0
check "  and the body is told to end by itself 30 seconds after the limit (--ttl 270)" grep -q 'client join @alice/game-1 --render cpu --name look[0-9]* --ttl 270$' "$SHIM_LOG"
: > "$SHIM_LOG"
SDLCA_LOOK_TIMEOUT=45 look @alice/game-1 "$SDLCA_SPAWN_HOME/shots/shot.png" 009 > /dev/null 2>&1; check "a wait written with a leading zero is a decimal number (009 is 9)" test $? -eq 0
check "  and the limit moves --ttl (45 + 30)" grep -q -- '--ttl 75$' "$SHIM_LOG"
printf 'SDLCA_LOOK_TIMEOUT=2\n' >> "$ACC/env"
: > "$SHIM_LOG"; rm -f "$SHIM_OUT/bun.pid"
start=$SECONDS
SHIM_JOIN_HANG=30 look @alice/game-1 "$SDLCA_SPAWN_HOME/shots/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
elapsed=$((SECONDS - start))
check "a join that hangs is stopped at the limit set in the account's env file" test "$rc" -ne 0
check "  well before the hang ends (it took $elapsed seconds; the limit was 2)" test "$elapsed" -le 10
check "  the message says it was the time limit" grep -q 'did not finish within the time limit of 2 seconds (SDLCA_LOOK_TIMEOUT)' "$TMP/stderr.txt"
check "  the client left anyway" grep -q 'client leave' "$SHIM_LOG"
check "  no screenshot was tried" test ! -e "$SHIM_OUT/bun.pid"
check "  and no working folder is left behind" test -z "$(find "$TMPDIR" -maxdepth 1 -name 'sdlca-look.*')"
sed -i '/^SDLCA_LOOK_TIMEOUT=/d' "$ACC/env" # the account's env file is read after the caller's environment, so it would win
: > "$SHIM_LOG"
start=$SECONDS
SDLCA_LOOK_TIMEOUT=8 SHIM_JOIN_DELAY=5 SHIM_BUN_HANG=60 look @alice/game-1 "$SDLCA_SPAWN_HOME/shots/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
elapsed=$((SECONDS - start))
check "a join that takes 5 of the 8 seconds leaves 3 for the screenshot: the two share one limit" test "$rc" -ne 0
check "  and the whole run ended at the limit (it took $elapsed seconds; with a screenshot that got the whole limit again it would take 13)" bash -c "test '$elapsed' -ge 7 && test '$elapsed' -le 11"
check "  and the message says it was the screenshot" grep -q 'screenshot did not finish within the time limit of 8 seconds' "$TMP/stderr.txt"
: > "$SHIM_LOG"; rm -f "$SHIM_OUT/bun.pid"
start=$SECONDS
SHIM_JOIN_BROWSER=1 SHIM_BUN_HANG=30 SDLCA_LOOK_TIMEOUT=3 look @alice/game-1 "$SDLCA_SPAWN_HOME/shots/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
elapsed=$((SECONDS - start))
check "a screenshot that hangs is stopped at the limit" test "$rc" -ne 0
check "  well before the hang ends (it took $elapsed seconds; the limit was 3)" test "$elapsed" -le 14
check "  the message says it was the time limit" grep -q 'screenshot did not finish within the time limit of 3 seconds' "$TMP/stderr.txt"
check "  the screenshot process is gone" gone "$(cat "$SHIM_OUT/bun.pid")"
check "  the client left" grep -q 'client leave' "$SHIM_LOG"
read -r main helper _ < "$SHIM_OUT/browser.pids"
check "  and the browser the join started is gone, with its helper" gone "$main" "$helper"
# DEFAULT_SIGNALS_PY: a program for `python3 -c` that runs its arguments as a command with SIGHUP, SIGINT and SIGTERM at their defaults, in the
# same process (so that $! is the look's own id). A program that is started with one of them ignored (a background job of a script ignores SIGINT;
# a suite that was started with `nohup` ignores SIGHUP) keeps it ignored, and a shell cannot trap a signal that was ignored when it started, so a
# look could not react to the signals below and the test would depend on how the suite was started.
DEFAULT_SIGNALS_PY='import os, signal, sys
for name in ("SIGHUP", "SIGINT", "SIGTERM"):
    signal.signal(getattr(signal, name), signal.SIG_DFL)
os.execvp(sys.argv[1], sys.argv[1:])'

for sig in TERM HUP INT; do
  fresh_outputs
  : > "$SHIM_LOG"
  SDLCA_LOOK_TIMEOUT=60 SHIM_JOIN_HANG=30 SDLCA_CODE_DIR="$KIT" python3 -I -B -c "$DEFAULT_SIGNALS_PY" "$ROOT/bin/sdlca-look" alice @alice/game-1 "$SDLCA_SPAWN_HOME/shots/shot.png" 1 > /dev/null 2>&1 &
  pid=$!
  for _ in $(seq 100); do grep -q 'client join' "$SHIM_LOG" && break; sleep 0.05; done
  start=$SECONDS
  kill -s "$sig" "$pid"
  wait "$pid"; rc=$?
  elapsed=$((SECONDS - start))
  check "SIG$sig during a hung join ends the look at once, with the signal's status" test "$rc" -eq "$(case "$sig" in TERM) echo 143 ;; HUP) echo 129 ;; INT) echo 130 ;; esac)"
  check "  within $elapsed seconds (not the 60 of the limit)" test "$elapsed" -le 8
  check "  and the client still left" grep -q 'client leave' "$SHIM_LOG"
done
: > "$SHIM_LOG"
start=$SECONDS
SHIM_JOIN_BROWSER=1 SHIM_LEAVE_HANG=60 look @alice/game-1 "$SDLCA_SPAWN_HOME/shots/shot.png" 1 > /dev/null 2>&1; rc=$?
elapsed=$((SECONDS - start))
check "a leave that hangs does not hold the run (it took $elapsed seconds, not 60)" test "$elapsed" -le 25
check "  the look itself had worked" test "$rc" -eq 0
read -r main helper _ < "$SHIM_OUT/browser.pids"
check "  and the browser that the hung leave left behind was still stopped" gone "$main" "$helper"
check "  and no working folder is left behind" test -z "$(find "$TMPDIR" -maxdepth 1 -name 'sdlca-look.*')"
unset TMPDIR
teardown

echo "sdlca-look leaves no browser behind, and attaches only to the one its own join started"
look_setup
look() { fresh_outputs; SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" alice "$@"; }
: > "$SHIM_LOG"
SHIM_JOIN_BROWSER=1 SHIM_LEAVE_STOPS_BROWSER=1 look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
read -r main helper port < "$SHIM_OUT/browser.pids"
check "a client whose leave closes its browser: the look works" test "$rc" -eq 0
check "  the screenshot tool was given the browser's own port" grep -q "BUN: $KIT/lib/shot.mjs http://127.0.0.1:$port " "$SHIM_LOG"
check "  and the browser is gone" gone "$main" "$helper"
check "  and there is nothing to warn about" test ! -s "$TMP/stderr.txt"
: > "$SHIM_LOG"
SHIM_JOIN_BROWSER=1 look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
read -r main helper port < "$SHIM_OUT/browser.pids"
check "a client whose leave leaves the browser running: the look works" test "$rc" -eq 0
check "  the browser, which sat in a session of its own, is gone" gone "$main"
check "  and so is the helper process it started" gone "$helper"
check "  and nothing is left to warn about" test ! -s "$TMP/stderr.txt"
: > "$SHIM_LOG"
SHIM_JOIN_BROWSER=1 SHIM_BUN_FAIL=1 look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
read -r main helper port < "$SHIM_OUT/browser.pids"
check "a screenshot that fails: the look fails with the tool's status" test "$rc" -eq 1
check "  and says why (the tool's own message)" grep -q 'the page is gone' "$TMP/stderr.txt"
check "  the browser is stopped all the same" gone "$main" "$helper"
check "  and the client left" grep -q 'client leave' "$SHIM_LOG"
start_foreign_listener
: > "$SHIM_LOG"; rm -f "$SHIM_OUT/bun.pid"
SHIM_JOIN_PORT="$FOREIGN_PORT" look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "a page address that names the port of a program that was already running is refused" test "$rc" -ne 0
check "  with a message that says why" grep -q 'already running before this look began' "$TMP/stderr.txt"
check "  the screenshot tool was never started" test ! -e "$SHIM_OUT/bun.pid"
check "  that program was not stopped" kill -0 "$FOREIGN_PID"
check "  the client left" grep -q 'client leave' "$SHIM_LOG"
check "  and nothing tells the person to stop that program by hand" bash -c "! grep -q 'stop it by hand' '$TMP/stderr.txt'"
: > "$SHIM_LOG"
SHIM_JOIN_DECOY="$FOREIGN_PORT" look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "an address in other text of the join output (a player's name, a chat line) is ignored" test "$rc" -eq 0
check "  the page is the one on the page line" grep -q "BUN: $KIT/lib/shot.mjs http://127.0.0.1:9222 " "$SHIM_LOG"
check "  and the program on the other port was neither used nor stopped" bash -c "! grep -q ':$FOREIGN_PORT' '$SHIM_LOG' && kill -0 $FOREIGN_PID"
: > "$SHIM_LOG"; rm -f "$SHIM_OUT/bun.pid"
SHIM_JOIN_SECOND_PORT="$FOREIGN_PORT" look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "two page lines that name different addresses are refused, not guessed between" test "$rc" -ne 0
check "  with a message that says so" grep -q 'more than one page address' "$TMP/stderr.txt"
check "  the screenshot tool was never started" test ! -e "$SHIM_OUT/bun.pid"
check "  and that program was left alone" kill -0 "$FOREIGN_PID"
: > "$SHIM_LOG"; rm -f "$SHIM_OUT/bun.pid"
SHIM_JOIN_NO_PAGE=1 look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2> "$TMP/stderr.txt"; rc=$?
check "a join that prints no page line is refused" test "$rc" -ne 0
check "  with a message that says so" grep -q 'did not print a page address' "$TMP/stderr.txt"
check "  the screenshot tool was never started, and the client left" bash -c "test ! -e '$SHIM_OUT/bun.pid' && grep -q 'client leave' '$SHIM_LOG'"
for host in evil.example 10.0.0.5 localhost 127.0.0.1.evil.example 127.0.0.2; do
  : > "$SHIM_LOG"; rm -f "$SHIM_OUT/bun.pid"
  SHIM_JOIN_PAGE_HOST="$host" look @alice/game-1 "$TMP/shot.png" 1 > /dev/null 2>&1; rc=$?
  check "a page line that names $host instead of 127.0.0.1 is refused" test "$rc" -ne 0
  check "  and the screenshot tool was never started" test ! -e "$SHIM_OUT/bun.pid"
done
check "  (the program on the other port is still running after all of it)" kill -0 "$FOREIGN_PID"
kill "$FOREIGN_PID" 2> /dev/null; wait "$FOREIGN_PID" 2> /dev/null
teardown

echo "sdlca-look never prints or keeps what the client printed (it can hold join credentials)"
look_setup
look() { fresh_outputs; SDLCA_CODE_DIR="$KIT" "$ROOT/bin/sdlca-look" alice "$@"; }
export TMPDIR="$TMP/tmpdir"; mkdir -p "$TMPDIR"
CREDENTIAL="sak_FAKEJOINCREDENTIAL0123456789abcdef" # check-secrets:allow (a made-up value for this test)
SHIM_JOIN_SECRET="$CREDENTIAL" spawn client join x > "$TMP/control.out" 2> "$TMP/control.err"
check "control: the stand-in client prints the credential on standard output" grep -q "$CREDENTIAL" "$TMP/control.out"
check "control: and on standard error" grep -q "$CREDENTIAL" "$TMP/control.err"
rm -f "$TMP/control.out" "$TMP/control.err" # they hold the credential on purpose; the checks below look for it everywhere else
leaks() { # leaks <label>: the credential is nowhere: not in what the look printed, not in the shim's log, not in any file that was made
  check "  $1: not on standard output or standard error" bash -c "! grep -q '$CREDENTIAL' '$TMP/stdout.txt' '$TMP/stderr.txt'"
  check "  $1: not in the client's call log" bash -c "! grep -q '$CREDENTIAL' '$SHIM_LOG'"
  check "  $1: not in any file under the test's temporary folder, nor in the working folder's place" bash -c "! grep -rqF '$CREDENTIAL' '$TMP'"
  check "  $1: and no working folder was left in \$TMPDIR" test -z "$(find "$TMPDIR" -maxdepth 1 -name 'sdlca-look.*')"
}
: > "$SHIM_LOG"
SHIM_JOIN_SECRET="$CREDENTIAL" look @alice/game-1 "$TMPDIR/shot.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a look that works" test "$rc" -eq 0
leaks "a look that works"
: > "$SHIM_LOG"
SHIM_JOIN_FAIL="$CREDENTIAL" look @alice/game-1 "$TMPDIR/shot.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a join that is refused fails" test "$rc" -ne 0
leaks "a join that is refused"
: > "$SHIM_LOG"
SDLCA_LOOK_TIMEOUT=2 SHIM_JOIN_SECRET="$CREDENTIAL" SHIM_JOIN_HANG=20 look @alice/game-1 "$TMPDIR/shot.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a join that runs out of time fails" test "$rc" -ne 0
leaks "a join that runs out of time"
: > "$SHIM_LOG"
SHIM_JOIN_SECRET="$CREDENTIAL" SHIM_JOIN_NO_PAGE=1 look @alice/game-1 "$TMPDIR/shot.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a join with no page line fails" test "$rc" -ne 0
leaks "a join with no page line"
: > "$SHIM_LOG"
SHIM_JOIN_SECRET="$CREDENTIAL" SHIM_JOIN_SECOND_PORT=9333 look @alice/game-1 "$TMPDIR/shot.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a join with two page lines fails" test "$rc" -ne 0
leaks "a join with two page lines"
: > "$SHIM_LOG"
SHIM_JOIN_SECRET="$CREDENTIAL" SHIM_BUN_FAIL=1 look @alice/game-1 "$TMPDIR/shot.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt"; rc=$?
check "a screenshot that fails fails" test "$rc" -ne 0
leaks "a screenshot that fails"
fresh_outputs
: > "$SHIM_LOG"
SDLCA_LOOK_TIMEOUT=60 SHIM_JOIN_SECRET="$CREDENTIAL" SHIM_JOIN_HANG=30 SDLCA_CODE_DIR="$KIT" python3 -I -B -c "$DEFAULT_SIGNALS_PY" "$ROOT/bin/sdlca-look" alice @alice/game-1 "$TMPDIR/shot.png" 1 > "$TMP/stdout.txt" 2> "$TMP/stderr.txt" &
pid=$!
for _ in $(seq 100); do grep -q 'client join' "$SHIM_LOG" && break; sleep 0.05; done
kill -s TERM "$pid"; wait "$pid"
leaks "a look that is stopped by a signal"
unset TMPDIR
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

echo "sdlca-look aims the camera only when asked, and checks the aim"
setup
KIT="$ROOT"
: > "$SHIM_LOG"
look @alice/game-1 "$TMP/aim.png" 2 --yaw 90 --pitch -10 > /dev/null 2>&1; check "an aimed look works" test $? -eq 0
check "  the screenshot tool got the aim and the session name" grep -Eq "^BUN: .*/shot\.png 2 90 -10 look[0-9]+ - -\$" "$SHIM_LOG"
: > "$SHIM_LOG"
look @alice/game-1 "$TMP/place.png" 2 --at 0.6,24,-1.5 --face 0.6,25.3,-0.4 > /dev/null 2>&1; check "a placed look works" test $? -eq 0
check "  the screenshot tool got the position and the point to face" grep -Eq "^BUN: .*/shot\.png 2 - - look[0-9]+ 0\.6,24,-1\.5 0\.6,25\.3,-0\.4\$" "$SHIM_LOG"
for bad in "--at 1,2" "--at 1,2,3,4" "--at a,b,c" "--at 1,2,1e9" "--at 1,2,1000" "--at 1, 2,3" "--face 1;2;3" "--face ,,," "--at" "--at 1,2,3 --at" "--face 1,2,3 --face"; do
  : > "$SHIM_LOG"
  # shellcheck disable=SC2086
  look @alice/game-1 "$TMP/place2.png" $bad > /dev/null 2>&1; rc=$?
  check "an odd place or face ($bad) is refused before anything joins" bash -c "test $rc -ne 0 && ! grep -q 'client join' '$SHIM_LOG'"
done
: > "$SHIM_LOG"
SDLCA_LOOK_RENDER=gpu SDLCA_LOOK_WIDTH=1280 SDLCA_LOOK_HEIGHT=720 look @alice/game-1 "$TMP/hd.png" 2 > /dev/null 2>&1; check "a look with a chosen renderer and frame size works" test $? -eq 0
check "  the join got them" grep -q 'client join @alice/game-1 --render gpu --width 1280 --height 720 --name look' "$SHIM_LOG"
for bad in "SDLCA_LOOK_RENDER=metal" "SDLCA_LOOK_WIDTH=100 SDLCA_LOOK_HEIGHT=720" "SDLCA_LOOK_WIDTH=99999 SDLCA_LOOK_HEIGHT=720" "SDLCA_LOOK_WIDTH=12x0 SDLCA_LOOK_HEIGHT=720" "SDLCA_LOOK_WIDTH=1280 SDLCA_LOOK_HEIGHT=5" "SDLCA_LOOK_HEIGHT=720"; do
  : > "$SHIM_LOG"
  # shellcheck disable=SC2086
  env $bad "$ROOT/bin/sdlca-look" alice @alice/game-1 "$TMP/hd2.png" 2 > /dev/null 2>&1; rc=$?
  check "an odd render setting ($bad) is refused before anything joins" bash -c "test $rc -ne 0 && ! grep -q 'client join' '$SHIM_LOG'"
done
for bad in "--yaw x" "--yaw 1000" "--pitch 90" "--pitch" "--turn 5" "--yaw 5 --yaw"; do
  : > "$SHIM_LOG"
  # shellcheck disable=SC2086
  look @alice/game-1 "$TMP/aim2.png" $bad > /dev/null 2>&1; rc=$?
  check "an odd aim ($bad) is refused before anything joins" bash -c "test $rc -ne 0 && ! grep -q 'client join' '$SHIM_LOG'"
done

teardown

finish
