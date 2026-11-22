#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Static checks for the whole repository. CI runs exactly this. Tools that are not installed are
# skipped with a notice locally; in CI (CI=true) a missing tool is a failure.
# usage: scripts/lint.sh
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")/.." || exit 1
export PYTHONDONTWRITEBYTECODE=1
fail=0

have() {
  if command -v "$1" > /dev/null 2>&1; then return 0; fi
  if [ "${CI:-}" = "true" ]; then echo "MISSING TOOL (required in CI): $1"; fail=1; else echo "skipped (not installed): $1"; fi
  return 1
}
step() { printf '\n== %s\n' "$1"; }

SHELL_FILES=(bin/sdlca-token bin/sdlca-as bin/sdlca-api bin/sdlca-friends bin/sdlca-listen bin/sdlca-on-chat bin/sdlca-look bin/sdlca-onboard bin/sdlca-body bin/sdlca-ext bin/sdlca-asset
  lib/common.sh scripts/*.sh tests/run.sh tests/shell/*.sh tests/shims/curl tests/shims/spawn tests/shims/bun tests/shims/systemctl tests/shims/gh)
PY_FILES=(bin/sdlca-say bin/sdlca-worlds bin/sdlca-allow lib/*.py scripts/*.py tests/*.py)

step "bash -n"
for f in "${SHELL_FILES[@]}"; do bash -n "$f" || fail=1; done

step "python compile"
for f in "${PY_FILES[@]}"; do python3 -I -B -c 'import sys; compile(open(sys.argv[1]).read(), sys.argv[1], "exec")' "$f" || fail=1; done

step "shellcheck"
if have shellcheck; then shellcheck "${SHELL_FILES[@]}" || fail=1; fi

step "yamllint"
if have yamllint; then
  yamllint -c .yamllint.yml slack .github .yamllint.yml || fail=1
fi

step "actionlint"
if compgen -G ".github/workflows/*.y*ml" > /dev/null && have actionlint; then actionlint || fail=1; fi

step "secrets"
bash scripts/check-secrets.sh || fail=1

step "license"
# LICENSE must stay the unmodified Apache License 2.0 text: this is the sha256 of the file published at
# https://www.apache.org/licenses/LICENSE-2.0.txt (checked on 2026-11-17).
LICENSE_SHA256=cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30
if command -v sha256sum > /dev/null 2>&1; then
  actual="$(sha256sum LICENSE | cut -d' ' -f1)"
else
  actual="$(shasum -a 256 LICENSE 2> /dev/null | cut -d' ' -f1)"
fi
if [ "$actual" = "$LICENSE_SHA256" ]; then
  echo "LICENSE is the unmodified Apache-2.0 text"
else
  echo "LICENSE has changed (sha256 ${actual:-unknown}); it must stay the unmodified Apache License 2.0 text" >&2
  fail=1
fi

step "markdown links"
python3 -I -B scripts/check-links.py || fail=1

step "tests"
log="$(mktemp)"
if bash tests/run.sh > "$log" 2>&1; then echo "tests passed"; else tail -30 "$log"; fail=1; fi
rm -f "$log"

echo
if [ "$fail" -eq 0 ]; then echo "lint: all checks passed"; else echo "lint: FAILED"; fi
exit "$fail"
