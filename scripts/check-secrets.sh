#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Look for things that must never be committed: Spawn tokens and invite codes, Slack, GitHub and other
# provider tokens, cloud keys, passwords inside URLs and private keys. GitHub's own secret scanning does not
# know Spawn's token formats, so this covers them. It reads the files git would commit (tracked, or untracked
# and not ignored). The length limits for Spawn's formats are guesses: Spawn does not publish them.
# usage: scripts/check-secrets.sh
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")/.." || exit 1

PATTERNS=(
  'sak_[A-Za-z0-9_-]{24,}'                                   # Spawn agent or personal token
  'sbk_[A-Za-z0-9]{24,}'                                     # Spawn one-time invite code
  'xox[abprsced]-[0-9A-Za-z-]{10,}'                          # Slack tokens
  'xapp-[0-9A-Za-z-]{10,}'                                   # Slack app-level token
  'hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+' # Slack incoming webhook
  'gh[pousr]_[A-Za-z0-9]{30,}'                               # GitHub tokens
  'github_pat_[A-Za-z0-9_]{30,}'                             # GitHub fine-grained token
  'glpat-[A-Za-z0-9_-]{20,}'                                 # GitLab token
  'sk-ant-[A-Za-z0-9_-]{20,}'                                # Anthropic API key
  'sk-(proj|svcacct|admin)-[A-Za-z0-9_-]{20,}'               # OpenAI project and service keys
  'sk-[A-Za-z0-9]{40,}'                                      # other provider API keys
  '(sk|rk)_live_[A-Za-z0-9]{20,}'                            # Stripe live keys
  'AIza[0-9A-Za-z_-]{35}'                                    # Google API key
  '(AKIA|ASIA)[0-9A-Z]{16}'                                  # AWS access key id
  'hf_[A-Za-z0-9]{30,}'                                      # Hugging Face token
  'npm_[A-Za-z0-9]{36}'                                      # npm token
  'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.'           # a JSON Web Token
  'https?://[^/@[:space:]:]+:[^/@[:space:]]+@'               # a password inside a URL
  '(ANTHROPIC|OPENAI|GEMINI|GOOGLE)_API_KEY=["'"'"']?[A-Za-z0-9_-]{20,}' # a provider key assigned in a file
  '-----BEGIN [A-Z ]*PRIVATE KEY( BLOCK)?-----'              # private keys
)

# A line that must stay as it is (a deliberate test fixture) can carry the marker  check-secrets:allow  in a comment.

if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  mapfile -t files < <(git ls-files --cached --others --exclude-standard | while read -r f; do [ -f "$f" ] && printf '%s\n' "$f"; done)
else
  mapfile -t files < <(find . -type f -not -path './node_modules/*' -not -path './.git/*')
fi

found=0
tmpout="$(mktemp)"
trap 'rm -f "$tmpout"' EXIT
for pattern in "${PATTERNS[@]}"; do
  for f in "${files[@]}"; do
    case "$f" in bun.lock | LICENSE) continue ;; esac
    if grep -a -n -E -- "$pattern" "$f" 2> /dev/null | grep -v 'check-secrets:allow' > "$tmpout"; then
      while IFS= read -r line; do
        printf '%s:%s  (matches %s)\n' "$f" "${line%%:*}" "$pattern"
      done < "$tmpout"
      found=1
    fi
  done
done

if [ "$found" -eq 1 ]; then
  echo "possible secrets found: remove them, and if one was real, revoke it" >&2
  exit 1
fi
echo "no secrets found in ${#files[@]} files"
