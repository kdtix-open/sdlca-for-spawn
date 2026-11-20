# shellcheck shell=bash
# SPDX-License-Identifier: Apache-2.0
# Shared setup for the shell tests: a throwaway home, an account, and the shims first on PATH.
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../.." && pwd -P)"
FAILS=0

setup() {
  # Start from a clean slate: an exported SDLCA_AGENT_CMD or SPAWN_TOKEN_FILE must not leak into a test.
  while read -r var; do unset "$var"; done < <(compgen -v | grep -E '^(SDLCA_|SPAWN_|SHIM_|ACCOUNT$|OWNER$)')
  TMP="$(mktemp -d)"
  export HOME="$TMP/home"          # no ~/.bun/bin here, so the shims win on PATH
  mkdir -p "$HOME"
  # Nothing may reach the developer's real git or systemd files, whatever their environment says.
  while read -r var; do unset "$var"; done < <(compgen -v | grep -E '^GIT_CONFIG_(KEY|VALUE)_[0-9]+$')
  unset GIT_CONFIG_COUNT GIT_CONFIG_SYSTEM GIT_CONFIG_PARAMETERS
  # Nor may a repository the developer is in the middle of (git exports these to filter-branch and a few other tools) take the tests' git commands.
  unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CEILING_DIRECTORIES
  export XDG_CONFIG_HOME="$HOME/.config" GIT_CONFIG_GLOBAL="$HOME/.gitconfig" GIT_CONFIG_NOSYSTEM=1
  export SDLCA_SPAWN_HOME="$TMP/spawn"
  export SHIM_LOG="$TMP/shim.log"
  export SHIM_OUT="$TMP/out"
  mkdir -p "$SHIM_OUT" "$SDLCA_SPAWN_HOME/accounts/alice" "$TMP/clones/alice/game-1"
  : > "$SHIM_LOG"
  export PATH="$ROOT/tests/shims:$PATH"
  printf 'sak_secret_token_value\n' > "$SDLCA_SPAWN_HOME/accounts/alice/token"
  chmod 600 "$SDLCA_SPAWN_HOME/accounts/alice/token"
  cat > "$SDLCA_SPAWN_HOME/accounts/alice/env" << ENV
OWNER=alice
SPAWN_USERNAME=alice_helper
SPAWN_TOKEN_FILE=$SDLCA_SPAWN_HOME/accounts/alice/token
ENV
  chmod 600 "$SDLCA_SPAWN_HOME/accounts/alice/env"
  cat > "$SDLCA_SPAWN_HOME/worlds.json" << JSON
{"worlds":{"w-111":{"owner":"alice","slug":"game-1","address":"@alice/game-1","appId":"app-111","clone_path":"$TMP/clones/alice/game-1","aliases":[],"git":"https://git.spawn.co/@alice/game-1.git"}}}
JSON
  ACC="$SDLCA_SPAWN_HOME/accounts/alice"
}

teardown() { rm -rf "$TMP"; }

with_agent() { # with_agent '<command that reads the prompt on stdin>'
  printf 'SDLCA_AGENT_CMD=%q\n' "$1" >> "$ACC/env"
}

ok() { printf '  ok   %s\n' "$1"; }
bad() { printf '  FAIL %s\n' "$1"; FAILS=$((FAILS + 1)); }
check() { # check <description> <command...>
  local d="$1"; shift
  if "$@"; then ok "$d"; else bad "$d"; fi
}
finish() { [ "$FAILS" -eq 0 ] || { echo "$FAILS failure(s)"; exit 1; }; }
