#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# shellcheck disable=SC2016  # single quotes are deliberate in the test descriptions
set -u
# shellcheck source=lib.sh
. "$(dirname "$(readlink -f "$0")")/lib.sh"

TOKEN="sak_""0123456789abcdef0123456789abcdef0123456789abcd"
tok() { "$ROOT/bin/sdlca-token" "$@"; }

echo "adding a token stores it privately and never prints it"
setup
printf '%s\n' "$TOKEN" | tok add sdlca-for-spawn/alice --owner alice --stdin > "$TMP/output.txt" 2>&1; rc=$?
A="$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn/alice"
check "it succeeds" test "$rc" -eq 0
check "the token file holds the token" test "$(cat "$A/token")" = "$TOKEN"
check "the token file is private" test "$(stat -c %a "$A/token")" = 600
check "the env file is private" test "$(stat -c %a "$A/env")" = 600
check "every folder on the way is private" test "$(stat -c %a "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn")" = 700 -a "$(stat -c %a "$A")" = 700
check "the env file names the owner and the token path" bash -c "grep -q '^OWNER=alice' '$A/env' && grep -q '^SPAWN_USERNAME=alice' '$A/env' && grep -q 'SPAWN_TOKEN_FILE=$A/token' '$A/env'"
check "the token is not in the output" bash -c "! grep -q '$TOKEN' '$TMP/output.txt'"
check "no temporary file is left behind" test -z "$(find "$A" -name '.token.*')"
teardown

echo "a nested account works with the other tools"
setup
printf '%s\n' "$TOKEN" | tok add sdlca-for-spawn/alice --owner alice --stdin > /dev/null 2>&1
"$ROOT/bin/sdlca-as" sdlca-for-spawn/alice bash -c 'printf "%s %s" "$OWNER" "$ACCOUNT"' > "$TMP/seen"
check "sdlca-as loads it" test "$(cat "$TMP/seen")" = "alice sdlca-for-spawn/alice"
check "path prints the token file" test "$(tok path sdlca-for-spawn/alice)" = "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn/alice/token"
check "path of an unknown account is an error" bash -c "! '$ROOT/bin/sdlca-token' path sdlca-for-spawn/nobody > /dev/null 2>&1"
teardown

echo "several tokens live side by side in one group"
setup
for who in alice bob carol; do printf '%s\n' "$TOKEN" | tok add "sdlca-for-spawn/$who" --owner "$who" --stdin > /dev/null 2>&1; done
tok list > "$TMP/list.txt"
for who in alice bob carol; do check "list shows $who" grep -q "^sdlca-for-spawn/$who .*owner=$who .*token=stored (mode 600)" "$TMP/list.txt"; done
check "list shows the ready-made account too" grep -q '^alice ' "$TMP/list.txt"
check "list never shows a token" bash -c "! grep -q '$TOKEN' '$TMP/list.txt'"
teardown

echo "init prepares an account without a token"
setup
tok init sdlca-for-spawn/dave --owner dave > /dev/null 2>&1
check "the env file exists" test -f "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn/dave/env"
check "there is no token yet" test ! -e "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn/dave/token"
tok list | grep -q '^sdlca-for-spawn/dave .*token=missing'; check "list says the token is missing" test $? -eq 0
teardown

echo "replacing a token keeps the env file"
setup
printf '%s\n' "$TOKEN" | tok add sdlca-for-spawn/alice --owner alice --stdin > /dev/null 2>&1
printf 'OWNER=alice\n# my own note\nSPAWN_USERNAME=alice\nSPAWN_TOKEN_FILE=%s\n' "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn/alice/token" > "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn/alice/env"
NEW="sak_""ffffffffffffffffffffffffffffffffffffffffffffff"
printf '%s\n' "$NEW" | tok add sdlca-for-spawn/alice --stdin > /dev/null 2>&1; check "adding again needs no --owner" test $? -eq 0
check "the token was replaced" test "$(cat "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn/alice/token")" = "$NEW"
check "the env file is untouched" grep -q '# my own note' "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn/alice/env"
teardown

echo "bad input is refused without echoing it"
setup
for bad in 'sbk_''0123456789abcdef0123456789abcdef' 'short' 'has a space in it 0123456789'; do
  printf '%s\n' "$bad" | tok add sdlca-for-spawn/eve --owner eve --stdin > "$TMP/output.txt" 2>&1
  check "refused: '${bad:0:12}...'" test $? -ne 0
  check "the refused value is not echoed" bash -c "! grep -qF '$bad' '$TMP/output.txt'"
done
check "no token file was written" test ! -e "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn/eve/token"
tok add sdlca-for-spawn/eve --owner eve < /dev/null > "$TMP/output.txt" 2>&1; check "without a terminal or --stdin it refuses" test $? -ne 0
for name in '../x' 'a/b/c' '/abs' 'Up' 'a b' '-lead'; do
  tok init "$name" --owner eve > /dev/null 2>&1; check "account name '$name' is refused" test $? -ne 0
done
tok init sdlca-for-spawn/eve --owner 'Bad Owner' > /dev/null 2>&1; check "a bad owner is refused" test $? -ne 0
teardown

echo "an unusual prefix is stored with a note"
setup
printf '%s\n' 'pat_''0123456789abcdef0123456789abcdef' | tok add sdlca-for-spawn/frank --owner frank --stdin > "$TMP/output.txt" 2>&1
check "it is stored" test -s "$SDLCA_SPAWN_HOME/accounts/sdlca-for-spawn/frank/token"
check "with a note" grep -q 'does not start with sak_' "$TMP/output.txt"
teardown

echo "verify asks Spawn and prints who the token is, not the token"
setup
printf '%s\n' "$TOKEN" | tok add sdlca-for-spawn/alice --owner alice --stdin > /dev/null 2>&1
tok verify sdlca-for-spawn/alice > "$TMP/output.txt" 2>&1; rc=$?
check "it succeeds" test "$rc" -eq 0
check "it prints the username and the number of worlds" grep -q 'username:    alice' "$TMP/output.txt"
check "a personal (human) token is called out as one" grep -q 'signs in AS A PERSON' "$TMP/output.txt"
SHIM_ME='{"username":"alice_helper","handle":"@@alice_helper","actorClass":"agent","linkedTo":"alice","worlds":[]}' tok verify sdlca-for-spawn/alice > "$TMP/output2.txt" 2>&1
check "an agent token is not called a person's" bash -c "! grep -q 'AS A PERSON' '$TMP/output2.txt' && grep -q 'linked to:   alice' '$TMP/output2.txt'"
check "the token is not printed" bash -c "! grep -q '$TOKEN' '$TMP/output.txt'"
check "the token went to curl on stdin only" bash -c "! grep '^ARGV' '$SHIM_LOG' | grep -q '$TOKEN'"
teardown

echo "--help prints the usage"
setup
tok --help > "$TMP/help.txt" 2>&1
check "--help shows the usage" grep -q 'usage: sdlca-token init' "$TMP/help.txt"
check "--help hides the shebang and license lines" bash -c "! grep -q 'SPDX' '$TMP/help.txt'"
teardown

finish
