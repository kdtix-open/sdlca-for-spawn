#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Run every test. No network, no tokens: external programs are replaced by shims in tests/shims.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."
export PYTHONDONTWRITEBYTECODE=1
python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
for t in tests/shell/test_*.sh; do
  echo "== $t"
  bash "$t"
done
echo "all tests passed"
