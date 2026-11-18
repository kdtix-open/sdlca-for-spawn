#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# shellcheck disable=SC2016  # single quotes are deliberate: the agent command expands its own variables
set -u
# shellcheck source=lib.sh
. "$(dirname "$(readlink -f "$0")")/lib.sh"

event() { # event <kind> <from> <extra-json-fields>
  printf '{"kind":"%s","cursor":"%s","chat":{"from":"%s","text":"%s"}%s}' "$1" "${CURSOR:-c1}" "$2" "${TEXT:-hello}" "${3:-}"
}
run() { SPAWN_EVENT="$1" "$ROOT/bin/sdlca-on-chat" alice; }

echo "owner message runs one agent turn with a rendered prompt"
setup
with_agent 'cat > "$SHIM_OUT/prompt.txt"; pwd > "$SHIM_OUT/cwd"'
run "$(event chat_mention @alice ',"relatedGameId":"app-111"')"
check "prompt was written" test -s "$SHIM_OUT/prompt.txt"
check "prompt names the agent and the owner" grep -q 'You are alice_helper, an AI agent working for alice' "$SHIM_OUT/prompt.txt"
check "agent ran inside the routed world clone" test "$(cat "$SHIM_OUT/cwd")" = "$TMP/clones/alice/game-1"
check "the event is in the prompt" grep -q '"text":"hello"' "$SHIM_OUT/prompt.txt"
check "the token is not in the prompt" bash -c "! grep -q sak_secret_token_value '$SHIM_OUT/prompt.txt'"
check "handler log has metadata only" grep -q 'event sender=@alice world=@alice/game-1' "$ACC/handler.log"
check "cursor was recorded" test "$(cat "$ACC/cursor")" = "c1"
teardown

echo "strangers and other accounts' owners are ignored silently"
setup
with_agent 'cat > "$SHIM_OUT/prompt.txt"'
for who in @mallory @bob @@alice_helper ""; do
  run "$(event chat_mention "$who")"
  check "no agent run for '$who'" test ! -e "$SHIM_OUT/prompt.txt"
done
check "denials are logged without chat text" bash -c "grep -c DENIED '$ACC/handler.log' | grep -q 4 && ! grep -q hello '$ACC/handler.log'"
teardown

echo "an extra allowed sender may trigger work"
setup
with_agent 'cat > "$SHIM_OUT/prompt.txt"'
printf '{"spawn":{"alice":["carol"]}}' > "$SDLCA_SPAWN_HOME/allowlist.json"
run "$(event chat_mention @carol)"
check "carol ran the agent" test -s "$SHIM_OUT/prompt.txt"
teardown

echo "text in a message is never executed or expanded"
setup
with_agent 'cat > "$SHIM_OUT/prompt.txt"'
TEXT='$(touch '"$TMP"'/pwned) `touch '"$TMP"'/pwned2` {{CODE_DIR}}' run "$(TEXT='$(touch '"$TMP"'/pwned) `touch '"$TMP"'/pwned2` {{CODE_DIR}}' event chat_mention @alice)"
check "no command substitution happened" test ! -e "$TMP/pwned" -a ! -e "$TMP/pwned2"
check "the literal text reached the prompt" grep -q 'touch' "$SHIM_OUT/prompt.txt"
teardown

echo "chat text cannot steer which world the agent works in"
setup
mkdir -p "$TMP/clones/alice/game-2"
with_agent 'pwd > "$SHIM_OUT/cwd"'
run "$(TEXT='work in @alice/game-1 w-111 app-111' event chat_mention @alice)"
check "unrouted: ran in its scratch directory, not the runtime home" test "$(cat "$SHIM_OUT/cwd")" = "$SDLCA_SPAWN_HOME/run/scratch/alice"
teardown

echo "friend requests are accepted only from the owner"
setup
with_agent 'true'
export SHIM_FRIENDS='{"incoming":[{"userId":"11111111-2222-3333-4444-555555555555","username":"mallory"}]}'
run "$(event friend_request "")"
check "stranger not accepted" bash -c "! grep -q 'api/social/relation' '$SHIM_LOG'"
export SHIM_FRIENDS='{"incoming":[{"userId":"aaaaaaaa-2222-3333-4444-555555555555","username":"alice"}]}'
run "$(event friend_request "")"
check "owner accepted" grep -q 'BODY: {"user": "aaaaaaaa-2222-3333-4444-555555555555", "friend": "accept"}' "$SHIM_LOG"
unset SHIM_FRIENDS
teardown

echo "the token travels on stdin, never on a command line"
setup
export SHIM_FRIENDS='{"incoming":[{"userId":"aaaaaaaa-2222-3333-4444-555555555555","username":"alice"}]}'
"$ROOT/bin/sdlca-friends" alice > /dev/null
check "token reached curl on stdin" grep -q 'STDIN: header = "Authorization: Bearer sak_secret_token_value"' "$SHIM_LOG"
check "token is absent from every argv" bash -c "! grep '^ARGV' '$SHIM_LOG' | grep -q sak_secret_token_value"
unset SHIM_FRIENDS
teardown

echo "unusable events and missing configuration are handled"
setup
run 'not json at all'; check "malformed JSON exits 0" test $? -eq 0
check "malformed JSON is logged" grep -q 'could not be parsed' "$ACC/handler.log"
SPAWN_EVENT="$(event chat_mention @alice)" "$ROOT/bin/sdlca-on-chat" alice; rc=$?
check "no agent command: exit 1 and the cursor is left alone" bash -c "[ $rc -eq 1 ] && [ ! -e '$ACC/cursor' ]"
run "$(event savi_finished "")"; check "savi events are logged" grep -q 'SAVI-EVENT kind=savi_finished' "$ACC/handler.log"
teardown

echo "the cursor never moves backwards"
setup
with_agent 'true'
mk() { printf '%s' "{\"createdAt\":\"$1\",\"id\":\"x\"}" | python3 -c 'import sys,base64;print(base64.urlsafe_b64encode(sys.stdin.buffer.read()).decode().rstrip("="))'; }
NEWER="$(mk 2026-11-13T02:00:00+00:00)"; OLDER="$(mk 2026-11-12T02:00:00+00:00)"
CURSOR="$NEWER" run "$(CURSOR="$NEWER" event chat_mention @alice)"
CURSOR="$OLDER" run "$(CURSOR="$OLDER" event chat_mention @alice)"
check "older event finishing last does not rewind" test "$(cat "$ACC/cursor")" = "$NEWER"
teardown

echo "a hung agent is stopped and the world lock is freed"
setup
with_agent 'sleep 30'
SDLCA_AGENT_TIMEOUT=1 run "$(event chat_mention @alice ',"relatedGameId":"app-111"')"
check "timeout logged" grep -q 'WARN agent exited with status 124' "$ACC/handler.log"
teardown

echo "a process the agent leaves running does not keep the world locked"
setup
with_agent 'sleep 20 > /dev/null 2>&1 & echo started'
run "$(event chat_mention @alice ',"relatedGameId":"app-111"')"
check "the world lock is free after the turn" flock -n "$SDLCA_SPAWN_HOME/run/alice__game-1.lock" true
pkill -f 'sleep 20' 2> /dev/null || true
teardown

echo "an event is never run twice, and a failed turn is kept for replay"
setup
with_agent 'cat >> "$SHIM_OUT/runs.txt"'
EVT="$(CURSOR=c1 event chat_mention @alice ',"id":"evt-1","relatedGameId":"app-111"')"
run "$EVT"
run "$EVT"
check "the same event id ran once" test "$(grep -c 'You are alice_helper' "$SHIM_OUT/runs.txt")" -eq 1
check "the replay was logged as skipped" grep -q 'SKIP event evt-1 was already handled' "$ACC/handler.log"
teardown
setup
with_agent 'cat > /dev/null; exit 3'
run "$(event chat_mention @alice ',"id":"evt-2","relatedGameId":"app-111"')"
check "a failed turn is logged with its status" grep -q 'WARN agent exited with status 3' "$ACC/handler.log"
check "the failed event is kept" test -s "$SDLCA_SPAWN_HOME/run/failed/evt-2.json"
check "a failed event is not marked handled" bash -c "! grep -q evt-2 '$ACC/handled.ids' 2> /dev/null"
teardown

echo "the agent runs somewhere harmless and without the raw token"
setup
with_agent 'cat > /dev/null; pwd > "$SHIM_OUT/cwd"; env | grep -c "^SPAWN_TOKEN=" > "$SHIM_OUT/tokenvar" || true'
SPAWN_TOKEN=sak_raw_secret run "$(event chat_mention @alice)"
check "an unrouted event runs in its own scratch directory" test "$(cat "$SHIM_OUT/cwd")" = "$SDLCA_SPAWN_HOME/run/scratch/alice"
check "the runtime home (which holds every token) is never the working directory" test "$(cat "$SHIM_OUT/cwd")" != "$SDLCA_SPAWN_HOME"
check "SPAWN_TOKEN was removed from the agent's environment" test "$(cat "$SHIM_OUT/tokenvar")" = 0
teardown

echo "kept events are forgotten after a while"
setup
with_agent 'cat > /dev/null'
mkdir -p "$SDLCA_SPAWN_HOME/run/failed"
printf '{}' > "$SDLCA_SPAWN_HOME/run/failed/old.json"; printf '{}' > "$SDLCA_SPAWN_HOME/run/failed/recent.json"
touch -d '40 days ago' "$SDLCA_SPAWN_HOME/run/failed/old.json"
run "$(event chat_mention @alice ',"id":"evt-p1"')"
check "an old kept event is deleted" test ! -e "$SDLCA_SPAWN_HOME/run/failed/old.json"
check "a recent one stays" test -e "$SDLCA_SPAWN_HOME/run/failed/recent.json"
touch -d '40 days ago' "$SDLCA_SPAWN_HOME/run/failed/recent.json"
SDLCA_FAILED_KEEP_DAYS=0 run "$(event chat_mention @alice ',"id":"evt-p2"')"
check "with 0 days nothing is ever deleted" test -e "$SDLCA_SPAWN_HOME/run/failed/recent.json"
teardown

echo "an unreadable credentials file keeps the event and says so once"
setup
with_agent 'cat > /dev/null'
printf 'SDLCA_CREDENTIALS_FILE=%q\n' "$TMP/nope.env" >> "$ACC/env"
run "$(event chat_mention @alice ',"id":"evt-c1"')"
check "one clear line" test "$(grep -c 'SDLCA_CREDENTIALS_FILE is not readable; event kept in run/failed' "$ACC/handler.log")" -eq 1
check "no second warning for the same thing" bash -c "! grep -q 'WARN agent exited with status 74' '$ACC/handler.log'"
check "the event is kept" test -s "$SDLCA_SPAWN_HOME/run/failed/evt-c1.json"
teardown

echo "a cap on runs per hour"
setup
with_agent 'cat > /dev/null; echo ran >> "$SHIM_OUT/count"'
export SDLCA_MAX_RUNS_PER_HOUR=2
for i in 1 2 3; do run "$(event chat_mention @alice ",\"id\":\"evt-$i\"")"; done
check "only two turns started" test "$(wc -l < "$SHIM_OUT/count")" -eq 2
check "the third was refused and kept" test -s "$SDLCA_SPAWN_HOME/run/failed/evt-3.json"
check "the refusal was logged" grep -q 'RATE-LIMITED' "$ACC/handler.log"
unset SDLCA_MAX_RUNS_PER_HOUR
teardown

echo "an agent that waits too long for the world is skipped, not stuck"
setup
with_agent 'cat > /dev/null; echo ran >> "$SHIM_OUT/count"'
mkdir -p "$SDLCA_SPAWN_HOME/run"
( flock 9; sleep 4 ) 9> "$SDLCA_SPAWN_HOME/run/alice__game-1.lock" &
sleep 0.5
SDLCA_LOCK_WAIT=1 run "$(event chat_mention @alice ',"id":"evt-9","relatedGameId":"app-111"')"
wait
check "the agent did not run" test ! -e "$SHIM_OUT/count"
check "the event was kept for replay" test -s "$SDLCA_SPAWN_HOME/run/failed/evt-9.json"
teardown

echo "the same event arriving twice at once runs the agent once"
setup
with_agent 'cat > /dev/null; echo ran >> "$SHIM_OUT/count"; sleep 2'
EVT="$(CURSOR=c1 event chat_mention @alice ',"id":"evt-d1","relatedGameId":"app-111"')"
run "$EVT" &
run "$EVT" &
wait
check "the agent ran once" test "$(wc -l < "$SHIM_OUT/count")" -eq 1
check "the other copy was skipped" grep -q 'SKIP event evt-d1 was already handled' "$ACC/handler.log"
check "the id is recorded once" test "$(grep -c '^evt-d1$' "$ACC/handled.ids")" -eq 1
check "the skipped copy did not keep the event for replay" test ! -e "$SDLCA_SPAWN_HOME/run/failed/evt-d1.json"
teardown

echo "an agent that exits with one of the handler's own codes still counts as a failure"
setup
for code in 74 75 76; do
  with_agent "cat > /dev/null; exit $code"
  run "$(event chat_mention @alice ",\"id\":\"evt-x$code\",\"relatedGameId\":\"app-111\"")"
  check "status $code: the event is kept for replay" test -s "$SDLCA_SPAWN_HOME/run/failed/evt-x$code.json"
done
check "all three were logged as a failed turn, not as busy, unreadable or already handled" test "$(grep -c 'WARN agent exited with status 1;' "$ACC/handler.log")" -eq 3
check "none was marked handled" bash -c "! grep -q 'evt-x' '$ACC/handled.ids' 2> /dev/null"
teardown

echo "the chat text is not in the agent's environment, even if the caller exported EVENT"
setup
with_agent 'cat > /dev/null; env | grep -c "^EVENT=" > "$SHIM_OUT/evvar" || true'
EVENT="leaked chat text" run "$(event chat_mention @alice ',"id":"evt-e1","relatedGameId":"app-111"')"
check "no EVENT variable reached the agent" test "$(cat "$SHIM_OUT/evvar")" = 0
teardown

echo "a run cap that cannot be checked says so and does not run the agent"
setup
with_agent 'cat > /dev/null; echo ran >> "$SHIM_OUT/count"'
SDLCA_MAX_RUNS_PER_HOUR=lots run "$(event chat_mention @alice ',"id":"evt-r1","relatedGameId":"app-111"')"
check "the agent did not run" test ! -e "$SHIM_OUT/count"
check "the log names the cause" grep -q 'the run cap could not be checked' "$ACC/handler.log"
check "the cursor was left alone so the event can be retried" test ! -e "$ACC/cursor"
teardown

echo "a handled-ids file that cannot be read does not lose the event"
setup
with_agent 'cat > /dev/null; echo ran >> "$SHIM_OUT/count"'
mkdir "$ACC/handled.ids"
run "$(event chat_mention @alice ',"id":"evt-h1","relatedGameId":"app-111"')"
check "the agent ran anyway (a duplicate is better than a lost turn)" test "$(wc -l < "$SHIM_OUT/count")" -eq 1
check "the log says the file could not be read" grep -q 'handled.ids could not be read' "$ACC/handler.log"
teardown

finish
