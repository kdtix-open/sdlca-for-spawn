#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Prepare this machine for the kit. Safe to run again.
#   - checks the tools the kit calls
#   - creates the runtime home (default ~/.sdlca/spawn, mode 0700) and copies the starter files if missing
#   - installs the Playwright client library used for screenshots
#   - renders the systemd user unit for the chat listeners
# usage: scripts/install.sh
set -euo pipefail
CODE_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd -P)"
# shellcheck source=../lib/common.sh
. "$CODE_DIR/lib/common.sh"

ok=1
need() {
  if command -v "$1" > /dev/null 2>&1; then
    printf '  ok       %s\n' "$1"
  else
    printf '  MISSING  %s  -> %s\n' "$1" "$2"
    ok=0
  fi
}
warn() {
  if command -v "$1" > /dev/null 2>&1; then
    printf '  ok       %s\n' "$1"
  else
    printf '  optional %s  -> %s\n' "$1" "$2"
  fi
}
echo "Checking tools"
need bash "bash 4.4 or newer"
need python3 "Python 3.9 or newer"
need git "install git"
need curl "install curl"
need flock "util-linux"
need bun "https://bun.sh (the Spawn client runs on Bun)"
need spawn "bun add -g @spawnco/client"
warn systemctl "systemd user services are how listeners stay running; see docs/operations.md for alternatives"
warn claude "or any agent CLI that reads a prompt on stdin (docs/configuration.md)"
[ "$ok" -eq 1 ] || {
  echo "Install the missing tools and run this again." >&2
  exit 1
}

echo "Preparing $SDLCA_SPAWN_HOME"
mkdir -p "$SDLCA_SPAWN_HOME/accounts" "$SDLCA_SPAWN_HOME/run" "$SDLCA_SPAWN_HOME/shots"
chmod 700 "$SDLCA_SPAWN_HOME" "$SDLCA_SPAWN_HOME/accounts" "$SDLCA_SPAWN_HOME/run" "$SDLCA_SPAWN_HOME/shots"
for f in AGENTS.md WORK-TODO.md allowlist.json; do
  if [ ! -e "$SDLCA_SPAWN_HOME/$f" ]; then
    cp "$CODE_DIR/templates/$f" "$SDLCA_SPAWN_HOME/$f"
    chmod 600 "$SDLCA_SPAWN_HOME/$f"
    echo "  created $f"
  fi
done

echo "Installing the Playwright client library"
if ! (cd "$CODE_DIR" && bun install --frozen-lockfile 2> /dev/null); then
  (cd "$CODE_DIR" && bun install)
fi

if command -v systemctl > /dev/null 2>&1; then
  case "$CODE_DIR" in
    *[!A-Za-z0-9_./+@:-]*)
      echo "  The kit's folder name has a space or a character that is special in a systemd unit or in sed: $CODE_DIR" >&2
      echo "  Move the kit to a plain path (letters, digits and . _ / + @ : -) and run this again." >&2
      exit 1
      ;;
  esac
  unit_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  mkdir -p "$unit_dir"
  sed "s#@CODE_DIR@#$CODE_DIR#g" "$CODE_DIR/systemd/sdlca-listener@.service.in" > "$unit_dir/sdlca-listener@.service"
  systemctl --user daemon-reload 2> /dev/null || echo "  note: could not reach the systemd user manager; run daemon-reload yourself"
  echo "Installed $unit_dir/sdlca-listener@.service"
fi

printf '\nDone. Next: create an account with\n'
printf '  %s/bin/sdlca-onboard --owner <spawn-username> --invite <sbk_...> --username <agent-username>\n' "$CODE_DIR"
