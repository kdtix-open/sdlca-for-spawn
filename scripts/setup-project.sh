#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Create the public GitHub Project that tracks this repository's work, with the custom fields it uses.
# Needs the GitHub CLI signed in with the "project" scope (run: gh auth refresh -s project).
# It only prints what it would do unless you pass --apply. Safe to read first. It makes a new Project each
# time, so it stops if a Project with the same title already exists.
#
# usage: scripts/setup-project.sh [--owner kdtix-open] [--repo kdtix-open/sdlca-for-spawn] [--title "..."] [--apply]
#
# Not scripted, so these few steps stay manual: the Project's views and the Status options (GitHub may offer
# API calls for them, but this script does not use them yet), and the built-in workflows (auto-add, status on
# close), for which we know of no API. See docs/maintainers/github-settings.md and docs/community/project-board.md.
set -euo pipefail

OWNER="kdtix-open" REPO="kdtix-open/sdlca-for-spawn" TITLE="SDLCA agent kit: roadmap and triage" APPLY=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --owner) OWNER="${2:-}"; shift 2 ;;
    --repo) REPO="${2:-}"; shift 2 ;;
    --title) TITLE="${2:-}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    -h | --help) awk 'NR >= 3 { if ($0 ~ /^#/) { sub(/^# ?/, ""); print } else { exit } }' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
command -v gh > /dev/null 2>&1 || { echo "the GitHub CLI (gh) is required" >&2; exit 1; }

# Capture the output first, then test it. A pipe into `grep -q` can fail under pipefail when grep stops early.
if [ "$APPLY" -eq 1 ]; then
  auth_status="$(gh auth status 2>&1 || true)"
  case "$auth_status" in
    *"'project'"*) ;;
    *) echo "The GitHub CLI token needs the 'project' scope. Run:  gh auth refresh -s project" >&2; exit 1 ;;
  esac
fi

run() { if [ "$APPLY" -eq 1 ]; then "$@"; else printf '[dry-run] %s\n' "$*"; fi; }

# This script makes a new Project every time, so refuse to run twice with the same title.
# The list is read into a variable first, for the same reason as above. If gh cannot list the projects, the
# script stops here (set -e) instead of going on to create a second one.
if [ "$APPLY" -eq 1 ]; then
  existing_titles="$(gh project list --owner "$OWNER" --limit 200 --format json --jq '.projects[].title')"
  if grep -Fxq -- "$TITLE" <<< "$existing_titles"; then
    echo "A project titled '$TITLE' already exists for $OWNER. Edit it in the browser, or pass a different --title." >&2
    exit 1
  fi
fi

echo "Creating the project '$TITLE' for $OWNER"
if [ "$APPLY" -eq 1 ]; then
  NUMBER="$(gh project create --owner "$OWNER" --title "$TITLE" --format json --jq .number)"
else
  NUMBER="<number>"
  run gh project create --owner "$OWNER" --title "$TITLE" --format json
fi
run gh project edit "$NUMBER" --owner "$OWNER" --visibility PUBLIC
run gh project edit "$NUMBER" --owner "$OWNER" --description "Public roadmap and triage board for the SDLCA agent kit. Unofficial; not affiliated with Spawn."
run gh project link "$NUMBER" --owner "$OWNER" --repo "$REPO"

field() { # field <name> <comma-separated options>
  run gh project field-create "$NUMBER" --owner "$OWNER" --name "$1" --data-type SINGLE_SELECT --single-select-options "$2"
}
field "Priority" "P0,P1,P2,P3"
field "Area" "runtime,worlds,slack,providers,install,templates,docs,ci,tests"
field "Kind" "Bug,Feature,Docs,Compliance,Agent,Task"
field "Size" "XS,S,M,L,XL"
field "Upstream impact" "None,Spawn change,Spawn terms"
run gh project field-create "$NUMBER" --owner "$OWNER" --name "Target release" --data-type TEXT

echo
echo "Manual steps left (not scripted): create the views, set the Status options, turn on the built-in workflows."
echo "See docs/maintainers/github-settings.md."
