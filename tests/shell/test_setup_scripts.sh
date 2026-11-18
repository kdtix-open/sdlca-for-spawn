#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# The maintainer scripts that configure GitHub, run against a fake `gh`: they print a plan first, change
# nothing without --apply, keep going when GitHub refuses one step, and can finish a half-made Project.
# shellcheck disable=SC2016  # single quotes are deliberate in the test descriptions
set -u
# shellcheck source=lib.sh
. "$(dirname "$(readlink -f "$0")")/lib.sh"

project() { "$ROOT/scripts/setup-project.sh" "$@"; }
github() { "$ROOT/scripts/setup-github.sh" "$@"; }
calls() { grep -c "^GH: $1" "$SHIM_LOG"; }

echo "setup-project.sh: a dry run prints the plan and calls nothing"
setup
project > "$TMP/out.txt" 2>&1; rc=$?
check "it succeeds" test "$rc" -eq 0
check "it shows the six fields it would make" test "$(grep -c 'field-create' "$TMP/out.txt")" -eq 6
check "gh was never called" test ! -s "$SHIM_LOG"
teardown

echo "setup-project.sh --apply makes the Project, describes it, links it and adds the fields"
setup
project --apply > "$TMP/out.txt" 2>&1; rc=$?
check "it succeeds" test "$rc" -eq 0
check "it made one Project" test "$(calls 'project create')" -eq 1
check "it asked for public visibility" grep -q 'GH: project edit 18 --owner kdtix-open --visibility PUBLIC' "$SHIM_LOG"
check "it set the description, which says the project is unofficial" grep -q 'GH: project edit 18 .*--description .*Unofficial; not affiliated with Spawn' "$SHIM_LOG"
check "it linked the repository" grep -q 'GH: project link 18 --owner kdtix-open --repo kdtix-open/sdlca-for-spawn' "$SHIM_LOG"
check "it made all six fields" test "$(calls 'project field-create')" -eq 6
check "it tells how to finish the Project if a later step stops" grep -q -- '--number 18' "$TMP/out.txt"
teardown

echo "setup-project.sh: an owner-only step that is refused does not stop the rest"
setup
SHIM_GH_REFUSE_VISIBILITY=1 project --apply > "$TMP/out.txt" 2> "$TMP/err.txt"; rc=$?
check "it still succeeds" test "$rc" -eq 0
check "it says what a person with more rights must do" grep -q 'organization owner' "$TMP/err.txt"
check "the description, the link and the fields were still done" test "$(calls 'project link')" -eq 1 -a "$(calls 'project field-create')" -eq 6
check "the leftover is listed at the end" grep -q 'Left for a person with more rights' "$TMP/out.txt"
teardown

echo "setup-project.sh: it will not make a second Project with the same title"
setup
SHIM_GH_PROJECTS=$'other\nSDLCA agent kit: roadmap and triage' project --apply > "$TMP/out.txt" 2> "$TMP/err.txt"; rc=$?
check "it stops" test "$rc" -ne 0
check "it says how to finish the existing one" grep -q -- '--number' "$TMP/err.txt"
check "nothing was created" test "$(calls 'project create')" -eq 0
teardown

echo "setup-project.sh --number finishes a Project and skips fields that exist"
setup
SHIM_GH_FIELDS=$'Title\nStatus\nPriority\nArea' project --apply --number 7 > "$TMP/out.txt" 2>&1; rc=$?
check "it succeeds" test "$rc" -eq 0
check "it created nothing" test "$(calls 'project create')" -eq 0 -a "$(calls 'project list')" -eq 0
check "it worked on project 7" grep -q 'GH: project link 7 ' "$SHIM_LOG"
check "it made only the four missing fields" test "$(calls 'project field-create')" -eq 4
check "it said which it skipped" test "$(grep -c 'field exists, skipped' "$TMP/out.txt")" -eq 2
teardown

echo "setup-project.sh: it checks its inputs and the token scope first"
setup
SHIM_GH_NO_PROJECT_SCOPE=1 project --apply > /dev/null 2> "$TMP/err.txt"; rc=$?
check "without the project scope it stops and says how to get it" bash -c "[ $rc -ne 0 ] && grep -q 'gh auth refresh -s project' '$TMP/err.txt'"
check "and changed nothing" test "$(calls 'project create')" -eq 0
project --number abc > /dev/null 2>&1; check "a --number that is not a number is refused" test $? -eq 2
project --bogus > /dev/null 2>&1; check "an unknown option is refused" test $? -eq 2
teardown

echo "setup-github.sh: a dry run prints the plan and calls nothing"
setup
github > "$TMP/out.txt" 2>&1; rc=$?
check "it succeeds" test "$rc" -eq 0
check "it says nothing was changed" grep -q 'Nothing was changed' "$TMP/out.txt"
check "gh was never called" test ! -s "$SHIM_LOG"
check "secret scanning and push protection come first" bash -c "grep -m1 -n 'dry-run' '$TMP/out.txt' | grep -q 'security_and_analysis'"
teardown

echo "setup-github.sh --apply turns on the security settings first and makes every label"
setup
github --apply > "$TMP/out.txt" 2>&1; rc=$?
check "it succeeds" test "$rc" -eq 0
check "the first call is the secret scanning and push protection request" bash -c "head -n 1 '$SHIM_LOG' | grep -q 'security_and_analysis\[secret_scanning_push_protection\]'"
check "private vulnerability reporting is turned on" grep -q 'private-vulnerability-reporting' "$SHIM_LOG"
check "squash merge only, with web sign-off required" grep -q 'allow_merge_commit=false.*web_commit_signoff_required=true' "$SHIM_LOG"
check "Discussions are turned on" grep -q 'GH: repo edit kdtix-open/sdlca-for-spawn --enable-discussions' "$SHIM_LOG"
check "every label in the label file was made" test "$(calls 'label create')" -eq "$(grep -c -v -e '^#' -e '^$' "$ROOT/.github/labels.tsv")"
check "it sets topics" bash -c "grep -o 'names\[\]=[^ ]*' '$SHIM_LOG' | grep -q ."
check "no vendor name and no Spawn name in the topics" bash -c "! grep -o 'names\[\]=[^ ]*' '$SHIM_LOG' | grep -i -E 'claude|anthropic|openai|slack|spawn'"
check "the ruleset was not touched" bash -c "! grep -q rulesets '$SHIM_LOG'"
teardown

echo "setup-github.sh: a refused step is reported, and the steps after it still run"
setup
SHIM_GH_REFUSE=fork-pr-contributor-approval github --apply > "$TMP/out.txt" 2> "$TMP/err.txt"; rc=$?
check "the exit status is 1" test "$rc" -eq 1
check "the refused step is listed" grep -q 'fork-pr-contributor-approval' "$TMP/err.txt"
check "it says how to set it by hand" grep -q 'Require approval for all external contributors' "$TMP/err.txt"
check "the topics and the labels were still done" test "$(calls 'api -X PUT repos/kdtix-open/sdlca-for-spawn/topics')" -eq 1 -a "$(calls 'label create')" -gt 30
teardown

echo "setup-github.sh: it checks its inputs"
setup
github --repo no-slash > /dev/null 2>&1; check "a repository name without a slash is refused" test $? -eq 2
github --repo 'a/b c' > /dev/null 2>&1; check "a repository name with a space is refused" test $? -eq 2
github --bogus > /dev/null 2>&1; check "an unknown option is refused" test $? -eq 2
check "gh was never called" test ! -s "$SHIM_LOG"
teardown

finish
