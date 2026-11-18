#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# shellcheck disable=SC2016  # single quotes are deliberate in the test descriptions
set -u
# shellcheck source=lib.sh
. "$(dirname "$(readlink -f "$0")")/lib.sh"

# A throwaway "Spawn": a file:// origin that answers /api/agent/v1/me, and a local git repository as the world.
fixture() {
  git init -q --bare -b main "$TMP/remote.git"
  git init -q -b main "$TMP/seed"
  printf '# a world\n' > "$TMP/seed/AGENTS.md"
  git -C "$TMP/seed" add . > /dev/null
  git -C "$TMP/seed" -c user.name=t -c user.email=t@example.invalid commit -q -m born
  git -C "$TMP/seed" push -q "$TMP/remote.git" main 2> /dev/null
  mkdir -p "$TMP/origin/api/agent/v1"
  printf '{"worlds":[{"worldId":"w-1","appId":"a-1","address":"@alice/game-1","git":"file://%s","standing":"editor"}]}' "$TMP/remote.git" > "$TMP/origin/api/agent/v1/me"
  export SPAWN_ORIGIN="file://$TMP/origin" SDLCA_ALLOW_FILE_ORIGIN=1 SDLCA_REPOS="$TMP/repos"
}
# setup() creates a ready-made account; onboarding tests start from nothing.
fresh() {
  setup
  rm -rf "$SDLCA_SPAWN_HOME/accounts/alice" "$SDLCA_SPAWN_HOME/worlds.json"
  fixture
}
onboard() { "$ROOT/bin/sdlca-onboard" --owner alice --invite "${INVITE:-sbk_0123456789abcdef}" --username alice_helper "$@"; }
global_helper() { git config --global --get-all credential.https://git.spawn.co.helper; }

echo "onboarding creates the account and leaves the global git configuration exactly as it was"
fresh
git config --global --add credential.https://git.spawn.co.helper '!echo preexisting'
onboard --display-name sdlca > "$TMP/output.txt" 2>&1; rc=$?
check "it succeeds" test "$rc" -eq 0
check "the token file is private" test "$(stat -c %a "$SDLCA_SPAWN_HOME/accounts/alice/token")" = 600
check "the env file is private" test "$(stat -c %a "$SDLCA_SPAWN_HOME/accounts/alice/env")" = 600
check "the account folder is private" test "$(stat -c %a "$SDLCA_SPAWN_HOME/accounts/alice")" = 700
check "the global git helper is back to what it was" test "$(global_helper)" = '!echo preexisting'
check "the display name was set" grep -q 'BODY: {"name": "sdlca"}' "$SHIM_LOG"
check "the world was cloned" test -f "$TMP/repos/alice/game-1/AGENTS.md"
check "the world was registered for this account" grep -q '"accounts": \[' "$SDLCA_SPAWN_HOME/worlds.json"
check "it says what to do next" grep -q 'SDLCA_AGENT_CMD' "$TMP/output.txt"
check "the token never appears in the output" bash -c "! grep -q sak_fake_token_for_tests '$TMP/output.txt'"
check "the env file has no agent command yet (the listener will refuse to start)" bash -c "! grep -q '^SDLCA_AGENT_CMD=' '$SDLCA_SPAWN_HOME/accounts/alice/env'"
teardown

echo "with no helper configured before, none is left behind"
fresh
onboard > /dev/null 2>&1
check "no helper remains in the global git configuration" bash -c "! git config --global --get-all credential.https://git.spawn.co.helper"
teardown

echo "a refused invite fails cleanly"
fresh
git config --global --add credential.https://git.spawn.co.helper '!echo preexisting'
INVITE=sbk_badbadbad onboard > "$TMP/output.txt" 2>&1; rc=$?
check "it fails" test "$rc" -ne 0
check "it explains that invites work once" grep -q 'works once' "$TMP/output.txt"
check "no env file was written" test ! -e "$SDLCA_SPAWN_HOME/accounts/alice/env"
check "the global git helper is untouched" test "$(global_helper)" = '!echo preexisting'
teardown

echo "an odd token path is quoted, so sourcing the env file cannot run code"
fresh
mkdir -p "$TMP/odd dir"
weird="$TMP/odd dir/tok'en \$(touch PWNED1) ;touch PWNED2 \`touch PWNED3\`"
onboard --token-file "$weird" > /dev/null 2>&1; rc=$?
check "it still succeeds" test "$rc" -eq 0
"$ROOT/bin/sdlca-as" alice bash -c 'printf %s "$SPAWN_TOKEN_FILE"' > "$TMP/seen"
check "the env file reads back the exact path" test "$(cat "$TMP/seen")" = "$weird"
check "nothing was executed" test -z "$(find "$TMP" "$HOME" . -maxdepth 2 -name 'PWNED*' 2> /dev/null)"
teardown

echo "bad names are refused before anything happens"
fresh
"$ROOT/bin/sdlca-onboard" --owner 'Bad Owner' --invite sbk_0123456789abcdef --username alice_helper > /dev/null 2>&1; check "owner" test $? -ne 0
"$ROOT/bin/sdlca-onboard" --owner alice --invite sbk_0123456789abcdef --username '../x' > /dev/null 2>&1; check "username" test $? -ne 0
"$ROOT/bin/sdlca-onboard" --owner alice --invite 'not-an-invite' --username alice_helper > /dev/null 2>&1; check "invite" test $? -ne 0
check "nothing was created" test ! -e "$SDLCA_SPAWN_HOME/accounts/alice"
"$ROOT/bin/sdlca-onboard" --help > "$TMP/help" 2>&1
check "--help shows the usage and not the shebang or license lines" bash -c "grep -q 'usage: sdlca-onboard' '$TMP/help' && ! grep -q 'SPDX' '$TMP/help' && ! grep -q 'set -euo' '$TMP/help'"
teardown

echo "install.sh prepares the runtime home and the service unit, and can be run again"
setup
export SDLCA_SPAWN_HOME="$TMP/rt"
bash "$ROOT/scripts/install.sh" > "$TMP/output.txt" 2>&1; rc=$?
check "it succeeds" test "$rc" -eq 0
check "the home is private" test "$(stat -c %a "$TMP/rt")" = 700
check "starter files were copied" test -s "$TMP/rt/AGENTS.md" -a -s "$TMP/rt/WORK-TODO.md" -a -s "$TMP/rt/allowlist.json"
check "the unit points at this checkout" grep -q "ExecStart=$ROOT/bin/sdlca-listen" "$HOME/.config/systemd/user/sdlca-listener@.service"
check "no placeholder is left in the unit" bash -c "! grep -q '@CODE_DIR@' '$HOME/.config/systemd/user/sdlca-listener@.service'"
printf 'my own edits\n' > "$TMP/rt/AGENTS.md"
bash "$ROOT/scripts/install.sh" > /dev/null 2>&1
check "a second run keeps your edits" test "$(cat "$TMP/rt/AGENTS.md")" = 'my own edits'
teardown

echo "the tests never touch the real git or systemd configuration, even when the environment points at them"
CANARY="$(mktemp -d)"
mkdir -p "$CANARY/xdg/systemd/user"
printf '[credential "https://git.spawn.co"]\n\thelper = !echo the-real-helper\n' > "$CANARY/gitconfig"
printf 'the real unit\n' > "$CANARY/xdg/systemd/user/sdlca-listener@.service"
before="$(cat "$CANARY/gitconfig" "$CANARY/xdg/systemd/user/sdlca-listener@.service" | sha256sum)"
export XDG_CONFIG_HOME="$CANARY/xdg" GIT_CONFIG_GLOBAL="$CANARY/gitconfig" GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0='!echo from-the-environment'
fresh
onboard > /dev/null 2>&1
SDLCA_SPAWN_HOME="$TMP/rt" bash "$ROOT/scripts/install.sh" > /dev/null 2>&1
check "the real git configuration is byte for byte the same" test "$(cat "$CANARY/gitconfig" "$CANARY/xdg/systemd/user/sdlca-listener@.service" | sha256sum)" = "$before"
check "the test run used its own git configuration instead" test "$GIT_CONFIG_GLOBAL" = "$HOME/.gitconfig"
check "and its own folder for the service unit" test -f "$HOME/.config/systemd/user/sdlca-listener@.service"
teardown
rm -rf "$CANARY"
unset XDG_CONFIG_HOME GIT_CONFIG_GLOBAL GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 GIT_CONFIG_VALUE_0

finish
