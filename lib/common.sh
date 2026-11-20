# shellcheck shell=bash
# SPDX-License-Identifier: Apache-2.0
#
# Shared helpers for the SDLCA agent kit. Source this file; do not execute it.
#
#   SDLCA_SPAWN_HOME  runtime home: accounts, tokens, logs, state (default ~/.sdlca/spawn)
#   SDLCA_CODE_DIR    where this kit's code lives (found automatically)

SDLCA_CODE_DIR="${SDLCA_CODE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"
SDLCA_SPAWN_HOME="${SDLCA_SPAWN_HOME:-$HOME/.sdlca/spawn}"
export SDLCA_CODE_DIR SDLCA_SPAWN_HOME

# Everything the kit writes is private to the user.
umask 077

# Make bun and user-installed CLIs (spawn, claude, ...) findable under systemd's minimal PATH.
for _d in "$HOME/.bun/bin" "$HOME/.local/bin"; do
  if [ -d "$_d" ]; then
    case ":$PATH:" in *":$_d:"*) ;; *) PATH="$_d:$PATH" ;; esac
  fi
done
unset _d
export PATH

die() {
  printf '%s: %s\n' "${0##*/}" "$*" >&2
  exit 1
}

# valid_account_name <name>
# An account is a folder under accounts/ holding an env file and a token. The name is one word, or two words
# joined by a slash to group accounts (sdlca-for-spawn/alice). A word is lowercase letters, digits, underscore
# or hyphen and starts with a letter or digit, so a name can never point outside accounts/.
valid_account_name() {
  [[ "${1:-}" =~ ^[a-z0-9][a-z0-9_-]{0,63}(/[a-z0-9][a-z0-9_-]{0,63})?$ ]]
}

# load_account <name>
# Validates the name, sources $SDLCA_SPAWN_HOME/accounts/<name>/env and checks the required variables.
# The env file is sourced as shell, so it must be owned by you and not writable by anyone else.
load_account() {
  ACCOUNT="${1:-}"
  valid_account_name "$ACCOUNT" ||
    die "invalid account name '$ACCOUNT' (words of lowercase letters, digits, underscore or hyphen, starting with a letter or digit; at most one slash, as in group/name)"
  ACC="$SDLCA_SPAWN_HOME/accounts/$ACCOUNT"
  [ -f "$ACC/env" ] || die "unknown account: $ACC/env not found (create one with sdlca-onboard for an agent, or sdlca-token init for a personal token)"
  if [ -n "$(find "$ACC/env" -perm /022 2>/dev/null)" ]; then
    die "$ACC/env is writable by group or others; run: chmod 600 '$ACC/env'"
  fi
  set -a
  # shellcheck disable=SC1091
  . "$ACC/env"
  set +a
  # Spawn's client reads SPAWN_TOKEN before it reads the token file (SPAWN_TOKEN_FILE). A SPAWN_TOKEN left in the caller's shell (a
  # personal token used for a test, say) would make every command run as this account act as somebody else, or fail with "this account
  # is a person's". The account's own token file is the only token, so it is removed here, and an env file cannot set it either.
  unset SPAWN_TOKEN
  : "${OWNER:?OWNER is not set in $ACC/env}" "${SPAWN_USERNAME:?SPAWN_USERNAME is not set in $ACC/env}" "${SPAWN_TOKEN_FILE:?SPAWN_TOKEN_FILE is not set in $ACC/env}"
  [ -r "$SPAWN_TOKEN_FILE" ] || die "token file is not readable: $SPAWN_TOKEN_FILE"
  export ACC ACCOUNT
}

# check_origin <origin>
# Prints the origin without a trailing slash, or stops. A token may only be sent to an https origin, to plain http
# on this machine, or to file:// when a test asks for it (SDLCA_ALLOW_FILE_ORIGIN=1); never to an origin with
# user information in it (https://www.spawn.co@elsewhere.example).
check_origin() {
  case "$1" in
    *@*) die "refusing to send a token to '$1' (an origin must not contain user information)" ;;
    https://?*) ;;
    http://127.0.0.1 | http://127.0.0.1[:/]* | http://localhost | http://localhost[:/]*) ;;
    file://?*) [ "${SDLCA_ALLOW_FILE_ORIGIN:-}" = 1 ] || die "refusing to send a token to '$1' (use an https origin)" ;;
    *) die "refusing to send a token to '$1' (use an https origin)" ;;
  esac
  printf '%s' "${1%/}"
}

# valid_token <text>
# A token is visible ASCII with no double quote and no backslash (and so no space or line break). Anything else
# would break the curl config line below or end up in an error message, so it is refused.
valid_token() {
  local LC_ALL=C t="${1:-}"
  [[ "$t" =~ ^[[:graph:]]{1,4096}$ ]] || return 1
  case "$t" in *'"'* | *\\*) return 1 ;; esac
  return 0
}

# spawn_curl <curl args...>
# Authenticated curl against Spawn. The token travels on curl's stdin config, never on the command
# line, so it does not show up in `ps` for other local users.
spawn_curl() {
  local tok
  tok="$(<"$SPAWN_TOKEN_FILE")"
  valid_token "$tok" || die "the token in $SPAWN_TOKEN_FILE has a character a token never has (a space, line break, quote or backslash); store it again with sdlca-token"
  printf 'header = "Authorization: Bearer %s"\n' "$tok" |
    curl -q -sS --fail --globoff --max-time "${SDLCA_HTTP_TIMEOUT:-30}" -K - "$@"
}

# cursor_advance <cursor>
# Remember the newest inbox event handled, so a restart resumes after it. Monotonic and atomic.
cursor_advance() {
  [ -n "${1:-}" ] && [ "$1" != "-" ] || return 0
  python3 -I -B "$SDLCA_CODE_DIR/lib/cursor.py" "$ACC/cursor" "$1"
}

# usage_header <file>
# Print a script's leading comment block (after the shebang and license line) as its --help text.
usage_header() {
  awk 'NR >= 3 { if ($0 ~ /^#/) { sub(/^# ?/, ""); print } else { exit } }' "$1"
}

# log_line <text...>
# One metadata line in the account's handler log. Never pass chat text or tokens here.
log_line() {
  printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" >> "$ACC/handler.log"
}
