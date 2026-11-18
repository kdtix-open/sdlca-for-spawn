#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Create the public GitHub Project that tracks this repository's work, with the custom fields it uses.
# Needs the GitHub CLI signed in with the "project" scope (run: gh auth refresh -s project).
# It only prints what it would do unless you pass --apply. Safe to read first. It makes a new Project each
# time, so it stops if a Project with the same title already exists. If a run stops half way, finish the
# Project with --number instead: it creates nothing, and skips fields that already exist.
#
# usage: scripts/setup-project.sh [--owner kdtix-open] [--repo kdtix-open/sdlca-for-spawn] [--title "..."]
#                                 [--number N] [--apply]
#
# Only an organization owner can make a Project public. If the account running this script is not an owner,
# the Project stays private, the script says so and goes on, and an owner makes it public afterwards.
#
# Not scripted, so these few steps stay manual: the Project's views and the Status options (GitHub may offer
# API calls for them, but this script does not use them yet), and the built-in workflows (auto-add, status on
# close), for which we know of no API. See docs/maintainers/github-settings.md and docs/community/project-board.md.
set -euo pipefail

OWNER="kdtix-open" REPO="kdtix-open/sdlca-for-spawn" TITLE="SDLCA agent kit: roadmap and triage" APPLY=0 NUMBER=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --owner) OWNER="${2:-}"; shift 2 ;;
    --repo) REPO="${2:-}"; shift 2 ;;
    --title) TITLE="${2:-}"; shift 2 ;;
    --number) NUMBER="${2:-}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    -h | --help) awk 'NR >= 3 { if ($0 ~ /^#/) { sub(/^# ?/, ""); print } else { exit } }' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -z "$NUMBER" ] || [[ "$NUMBER" =~ ^[0-9]+$ ]] || { echo "--number must be the Project's number, for example 18" >&2; exit 2; }
command -v gh > /dev/null 2>&1 || { echo "the GitHub CLI (gh) is required" >&2; exit 1; }

# Capture the output first, then test it. A pipe into `grep -q` can fail under pipefail when grep stops early.
if [ "$APPLY" -eq 1 ]; then
  auth_status="$(gh auth status 2>&1 || true)"
  case "$auth_status" in
    *"'project'"*) ;;
    *) echo "The GitHub CLI token needs the 'project' scope. Run:  gh auth refresh -s project" >&2; exit 1 ;;
  esac
fi

LEFT=()
run() { if [ "$APPLY" -eq 1 ]; then "$@"; else printf '[dry-run] %s\n' "$*"; fi; }
# soft <what is left to do if it fails> <command ...>: a refused command is noted, and the script goes on.
soft() {
  local left="$1"
  shift
  if [ "$APPLY" -eq 1 ]; then
    if ! "$@" > /dev/null; then
      echo "note: $left" >&2
      LEFT+=("$left")
    fi
  else
    printf '[dry-run] %s\n' "$*"
  fi
}

if [ -n "$NUMBER" ]; then
  echo "Continuing with project number $NUMBER for $OWNER (nothing is created)"
else
  # This script makes a new Project every time, so refuse to run twice with the same title.
  # The list is read into a variable first, for the same reason as above. If gh cannot list the projects, the
  # script stops here (set -e) instead of going on to create a second one.
  if [ "$APPLY" -eq 1 ]; then
    existing_titles="$(gh project list --owner "$OWNER" --limit 200 --format json --jq '.projects[].title')"
    if grep -Fxq -- "$TITLE" <<< "$existing_titles"; then
      echo "A project titled '$TITLE' already exists for $OWNER. Finish it with --number <its number>, edit it in the browser, or pass a different --title." >&2
      exit 1
    fi
  fi
  echo "Creating the project '$TITLE' for $OWNER"
  if [ "$APPLY" -eq 1 ]; then
    NUMBER="$(gh project create --owner "$OWNER" --title "$TITLE" --format json --jq .number)"
    echo "Created project number $NUMBER. If this script stops before the end, finish it with:  $0 --apply --number $NUMBER"
  else
    NUMBER="<number>"
    run gh project create --owner "$OWNER" --title "$TITLE" --format json
  fi
fi

soft "Make the Project public: an organization owner opens the Project, Settings, Visibility, or runs  gh project edit $NUMBER --owner $OWNER --visibility PUBLIC" \
  gh project edit "$NUMBER" --owner "$OWNER" --visibility PUBLIC
soft "Set the Project's description in its settings." \
  gh project edit "$NUMBER" --owner "$OWNER" --description "Public roadmap and triage board for the SDLCA agent kit. Unofficial; not affiliated with Spawn."
soft "Link the Project to the repository: in the Project's settings, or  gh project link $NUMBER --owner $OWNER --repo $REPO" \
  gh project link "$NUMBER" --owner "$OWNER" --repo "$REPO"

# With --apply, a field that exists already is skipped, so the script can be run again to finish a Project.
existing_fields=""
if [ "$APPLY" -eq 1 ]; then
  existing_fields="$(gh project field-list "$NUMBER" --owner "$OWNER" --format json --jq '.fields[].name')"
fi
field() { # field <name> <data type> [<comma-separated options>]
  local name="$1" type="$2" options="${3:-}"
  if grep -Fxq -- "$name" <<< "$existing_fields"; then
    echo "field exists, skipped: $name"
    return
  fi
  if [ -n "$options" ]; then
    run gh project field-create "$NUMBER" --owner "$OWNER" --name "$name" --data-type "$type" --single-select-options "$options"
  else
    run gh project field-create "$NUMBER" --owner "$OWNER" --name "$name" --data-type "$type"
  fi
}
field "Priority" SINGLE_SELECT "P0,P1,P2,P3"
field "Area" SINGLE_SELECT "runtime,worlds,slack,providers,install,templates,docs,ci,tests"
field "Kind" SINGLE_SELECT "Bug,Feature,Docs,Compliance,Agent,Task"
field "Size" SINGLE_SELECT "XS,S,M,L,XL"
field "Upstream impact" SINGLE_SELECT "None,Spawn change,Spawn terms"
field "Target release" TEXT

echo
if [ "${#LEFT[@]}" -gt 0 ]; then
  echo "Left for a person with more rights than this account:"
  printf '  - %s\n' "${LEFT[@]}"
fi
echo "Manual steps left (not scripted): create the views, set the Status options, turn on the built-in workflows."
echo "See docs/maintainers/github-settings.md."
