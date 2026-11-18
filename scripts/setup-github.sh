#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Configure the GitHub side of this repository: description, topics, features, merge and Actions settings,
# security settings and labels. Needs the GitHub CLI (gh), signed in as a repository admin. It only prints
# what it would do unless you pass --apply, so you can read the plan first. Safe to run again.
#
# usage: scripts/setup-github.sh [--repo owner/name] [--apply] [--ruleset]
#   --repo     default: kdtix-open/sdlca-for-spawn
#   --apply    actually make the changes
#   --ruleset  also create (or update) the branch ruleset for main from .github/rulesets/main.json.
#              The ruleset needs pull requests, so push the first commit to main before using it.
#
# A dry run prints the same gh commands that --apply runs. With --apply, a step that GitHub refuses does not
# stop the steps after it: the script prints what failed, finishes the rest and exits with status 1. The
# security steps (secret scanning and push protection) come first, so a later refusal cannot skip them.
#
# What it does not do: create Discussions categories (we know of no API for them), set up code scanning
# (optional, after the first push) or create the Project (scripts/setup-project.sh does that).
# docs/maintainers/github-settings.md lists the manual steps.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."

REPO="kdtix-open/sdlca-for-spawn" APPLY=0 RULESET=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) [ -n "${2:-}" ] || { echo "--repo needs a value like owner/name" >&2; exit 2; }; REPO="$2"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    --ruleset) RULESET=1; shift ;;
    -h | --help) awk 'NR >= 3 { if ($0 ~ /^#/) { sub(/^# ?/, ""); print } else { exit } }' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[[ "$REPO" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || { echo "--repo must look like owner/name, got: $REPO" >&2; exit 2; }
command -v gh > /dev/null 2>&1 || { echo "the GitHub CLI (gh) is required" >&2; exit 1; }

DESCRIPTION="Unofficial starter kit for directing AI coding agents on Spawn from chat. Not affiliated with Spawn."
# Topics describe what exists today and contain no vendor name and no Spawn name (docs/compliance/trademarks-and-credits.md).
# A topic for the planned Slack bridge waits until it ships, and a maintainer decides then.
TOPICS=(ai-agents agentic developer-tools multiplayer-games starter-kit unofficial)

FAILED=() STEP=""
say() { STEP="$1"; printf '\n== %s\n' "$1"; }
# run <command ...>: print the command (dry run) or run it (--apply). With --apply a refused command is remembered
# and the script goes on, so one refusal cannot skip a later step. If FAIL_NOTE is set for the call, it is printed
# when that command fails.
run() {
  if [ "$APPLY" -eq 1 ]; then
    if ! "$@" > /dev/null; then
      FAILED+=("$STEP: $*")
      echo "FAILED: $*" >&2
      [ -z "${FAIL_NOTE:-}" ] || echo "  $FAIL_NOTE" >&2
    fi
  else
    printf '[dry-run] %s\n' "$*"
  fi
}

say "Repository: $REPO ($([ "$APPLY" -eq 1 ] && echo applying || echo dry run))"

# Secret scanning and push protection come first, so that a refusal further down cannot skip them. On an empty
# repository GitHub may refuse them: then turn them on by hand in Settings before the first push (see
# docs/maintainers/github-settings.md).
say "Security: secret scanning and push protection"
run gh api -X PATCH "repos/$REPO" \
  -f 'security_and_analysis[secret_scanning][status]=enabled' \
  -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'

say "Security: Dependabot alerts and security updates, private vulnerability reporting"
run gh api -X PUT "repos/$REPO/vulnerability-alerts"
run gh api -X PUT "repos/$REPO/automated-security-fixes"
run gh api -X PUT "repos/$REPO/private-vulnerability-reporting"

# Squash merge only, so the pull request title becomes the commit subject (see CONTRIBUTING.md) and the
# individual commit messages (with their sign-off and Assisted-by lines) are kept in the body.
# Auto-merge stays off: the AI policy says no agent merges, and a person can turn it on later if wanted.
# Web sign-off adds a Signed-off-by line to commits made in this repository's GitHub web editor, matching the DCO
# rule. (We have not verified that it reaches a contributor's own fork.)
# The repository's own Projects switch is left as GitHub has it: the Project is an organization Project that
# scripts/setup-project.sh links to this repository.
say "Description, features and merge settings"
run gh api -X PATCH "repos/$REPO" \
  -f description="$DESCRIPTION" \
  -F has_issues=true -F has_wiki=false \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -F allow_auto_merge=false -F delete_branch_on_merge=true \
  -F web_commit_signoff_required=true \
  -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=COMMIT_MESSAGES

# `gh repo edit` turns Discussions on. Creating the categories has no API that we know of, so that stays manual.
say "Discussions"
run gh repo edit "$REPO" --enable-discussions

# Workflows get a read-only token unless a workflow asks for more (ours do, explicitly), and Actions may not
# approve pull requests, so no automation can supply the human approval the ruleset asks for.
say "Actions: read-only default token, no approving pull requests"
run gh api -X PUT "repos/$REPO/actions/permissions/workflow" \
  -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false

# The AI policy promises that CI on a pull request from a project agent account waits for a person. This is the
# setting behind it. If GitHub refuses the call (for example, an organization policy sets it), set it by hand.
say "Actions: a person approves workflow runs for pull requests from all external contributors"
FAIL_NOTE="Set it by hand: Settings > Actions > General, the fork pull request workflows section, 'Require approval for all external contributors'." \
  run gh api -X PUT "repos/$REPO/actions/permissions/fork-pr-contributor-approval" \
  -f approval_policy=all_external_contributors

say "Topics"
topic_args=()
for t in "${TOPICS[@]}"; do topic_args+=(-f "names[]=$t"); done
run gh api -X PUT "repos/$REPO/topics" "${topic_args[@]}"

say "Labels (from .github/labels.tsv)"
while IFS=$'\t' read -r name color description; do
  case "$name" in '' | '#'*) continue ;; esac
  run gh label create "$name" --repo "$REPO" --color "$color" --description "$description" --force
done < .github/labels.tsv

if [ "$RULESET" -eq 1 ]; then
  say "Branch ruleset for main"
  # Update the ruleset if one with this name exists, so running the script again does not create a copy.
  ruleset_name="$(python3 -I -B -c 'import json, sys; print(json.load(open(sys.argv[1]))["name"])' .github/rulesets/main.json)"
  ruleset_id="" lookup_ok=1
  if [ "$APPLY" -eq 1 ]; then
    ruleset_id="$(gh api "repos/$REPO/rulesets" --jq "[.[] | select(.name == \"$ruleset_name\") | .id] | first // empty")" || lookup_ok=0
  else
    echo "(a dry run does not look for an existing ruleset; with --apply an existing one named \"$ruleset_name\" is updated)"
  fi
  if [ "$lookup_ok" -eq 0 ]; then
    # Do not guess: creating one now could make a copy of a ruleset that already exists.
    FAILED+=("$STEP: could not list the existing rulesets, so none was created or updated")
    echo "FAILED: could not list the existing rulesets; no ruleset was created or updated" >&2
  elif [ -n "$ruleset_id" ]; then
    run gh api -X PUT "repos/$REPO/rulesets/$ruleset_id" --input .github/rulesets/main.json
  else
    run gh api -X POST "repos/$REPO/rulesets" --input .github/rulesets/main.json
  fi
fi

say "Done"
if [ "$APPLY" -eq 0 ]; then
  echo "Nothing was changed. Run again with --apply to make these changes."
elif [ "${#FAILED[@]}" -gt 0 ]; then
  echo "${#FAILED[@]} step(s) were refused or failed:" >&2
  printf '  %s\n' "${FAILED[@]}" >&2
  echo "Fix the cause (see docs/maintainers/github-settings.md), then run the script again. It is safe to repeat." >&2
  exit 1
fi
