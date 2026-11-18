# Development guide

This guide is for anyone who wants to change the code or the tests of the SDLCA agent kit, from a first-time contributor to an AI agent working on the repository. You will set up a working copy, learn the layout, run the checks, add a command, and find your way when something breaks. If you only want to fix the docs, you can skip most of this: edit the file, run `bash scripts/lint.sh` if you can, and open a pull request as described in [CONTRIBUTING.md](../../CONTRIBUTING.md).

You do not need a Spawn account to work on the kit. The tests run entirely on your machine.

## What you need

| Tool | What for | Needed for |
|---|---|---|
| bash 4.4 or newer | every command and test | everything |
| python3 | commands, libraries and tests (standard library only) | everything |
| git | the tests build small local repositories | tests |
| curl, `flock`, `timeout` | the commands call them (tests replace `curl` with a shim; `flock` and `timeout` run for real) | tests |
| shellcheck, yamllint, actionlint | the static checks in `scripts/lint.sh` | lint (skipped locally if missing; required in CI, our automatic checks on GitHub) |
| bun | installs `playwright-core` for `sdlca-look`; CI checks the lockfile | only if you touch screenshots, `package.json` or `bun.lock` |
| the Spawn client | the real commands call `spawn` | only for runs against real Spawn; tests use a shim |

We have tested only on Ubuntu under WSL2. The CI job is set up to run the same checks on GitHub's Ubuntu runner. Our machine had Ubuntu 26.04, GNU bash 5.3, Python 3.14, git 2.53, curl 8.18, bun 1.4 and util-linux `flock` 2.41, and the CI job is set to use the `ubuntu-24.04` runner image with that image's Python (3.12). Those are "tested with" versions, not guaranteed minimums. The code does need bash 4.4 or newer, because it relies on how that version handles empty arrays. macOS and native Windows are untested; the stock macOS bash is too old and has no `flock`. If you try it, please tell us what happened (it is a useful contribution).

## Get the code

Fork `kdtix-open/sdlca-for-spawn` on GitHub, then clone your fork using the URL GitHub shows you. Optionally add the original repository as `upstream` so you can pull in new work:

```bash
git remote add upstream https://github.com/kdtix-open/sdlca-for-spawn.git
git switch -c fix/listener-typo      # a branch name in the type/slug style
```

You do not need `scripts/install.sh` to develop. It prepares a real runtime home (`~/.sdlca/spawn`), installs a systemd user unit and runs `bun install`, so it changes your home directory. The tests run it only inside a throwaway home, with shims standing in for `bun` and `systemctl`, never in yours.

## Run the checks

```bash
bash scripts/lint.sh    # everything CI runs: static checks, then the tests
bash tests/run.sh       # the tests alone
```

`bun run lint` and `bun run test` do the same two things (see `package.json`). `scripts/lint.sh` runs these nine steps in order:

1. `bash -n` on every shell script (a syntax check).
2. A compile check on every Python file.
3. `shellcheck` on the shell scripts.
4. `yamllint` on `slack/`, `.github/` and `.yamllint.yml`.
5. `actionlint` on the workflows in `.github/workflows/`.
6. `scripts/check-secrets.sh`, which looks in the files git would commit (tracked files, and untracked files that are not ignored) for Spawn tokens and invite codes, Slack, GitHub, GitLab, OpenAI, Anthropic, Google, AWS, Hugging Face, npm and Stripe keys, Slack webhooks, JSON Web Tokens, passwords inside URLs, provider keys assigned in a file, and private keys. It fails on a match and never prints the secret itself. A line that must stay as it is, such as a deliberate test fixture, can carry the comment `check-secrets:allow`. The length limits for Spawn's own token formats are guesses, because Spawn does not publish them.
7. A `LICENSE` check: the sha256 checksum of `LICENSE` must equal that of the unmodified Apache-2.0 text published at apache.org (it needs `sha256sum` or `shasum`). Never edit `LICENSE`.
8. `scripts/check-links.py`, which checks that every relative link and heading anchor in the Markdown files resolves. It does not use the network, so it does not check web addresses.
9. The tests (`tests/run.sh`).

You can run steps 6 and 8 alone: `bash scripts/check-secrets.sh` and `python3 -I -B scripts/check-links.py [file-or-folder ...]`.

A linter that is not installed is skipped with a notice on your machine. In CI (`CI=true`) a missing linter is a failure. Run `CI=true bash scripts/lint.sh` to see what CI would say.

### Install the lint tools in a virtualenv

CI installs the linters from PyPI into a throwaway virtual environment. You can do the same, outside the repository so nothing gets committed:

```bash
python3 -m venv ~/.venvs/sdlca-lint
~/.venvs/sdlca-lint/bin/pip install yamllint==1.38.0 actionlint-py==1.7.12.25 shellcheck-py==0.11.0.1
export PATH="$HOME/.venvs/sdlca-lint/bin:$PATH"
CI=true bash scripts/lint.sh
```

Those version numbers are copied from [.github/workflows/ci.yml](../../.github/workflows/ci.yml). If CI changes them, copy the new ones; CI is the reference. Your package manager may also offer these tools, but a different version can give different results.

## Repository tour

| Path | What is there |
|---|---|
| `bin/` | The commands, all named `sdlca-*`. Most are bash; `sdlca-say`, `sdlca-worlds` and `sdlca-allow` are Python. Each has its usage in the header comment. `sdlca-token` stores and checks Spawn tokens in the account folders: `init`, `add`, `path`, `verify` and `list`. |
| `lib/` | Shared code. `common.sh` (account loading and the account-name rule, `die`, `valid_token`, `spawn_curl`, `check_origin`, `log_line`, cursor helper, `usage_header`), `route.py` (who may trigger work, which world), `render_prompt.py` (builds the agent prompt), `linesplit.py` (200-character chat lines), `cursor.py` (monotonic cursor, locked while it is read, compared and written), `dedupe.py` (remembers handled event ids), `ratelimit.py` (caps agent runs in a time window; the handler uses one hour), `safeurl.py` (origin check, token-file check and no redirects, for the Python commands), `gitcred.py` (per-clone git credential settings), `shot.mjs` (screenshot, run with bun). |
| `templates/` | Starter files. `scripts/install.sh` copies `AGENTS.md`, `WORK-TODO.md` and `allowlist.json` into a user's runtime home. The agent prompt `handler-prompt.md` is read from here unless the user keeps their own copy in the runtime home, and `account.env.example` is where `sdlca-onboard` takes the settings it writes into a new account's `env` file. |
| `systemd/` | The systemd user unit template that `scripts/install.sh` renders. |
| `slack/` | An example Slack app manifest and env example. The Slack bridge is planned and not built. |
| `scripts/` | `install.sh`, `lint.sh` (which runs `check-secrets.sh` and `check-links.py`), and the maintainer scripts `setup-github.sh`, `setup-project.sh` and `seed-starter-issues.py` (it posts the starter issues only when a person runs it with `--apply`). |
| `tests/` | `test_*.py` unit tests, `shell/` tests, `shims/` fake `curl`, `spawn`, `bun` and `systemctl`. See [testing](testing.md). |
| `docs/` | Documentation. Index: [docs/README.md](../README.md). |
| `.github/` | CI, issue forms, pull request template, labels, release notes config, ruleset. |

For how the pieces fit together, read [the architecture](../architecture.md). For who may trigger work and where tokens go, read [the security model](../security-model.md).

## Code conventions

- Every source file starts with an `SPDX-License-Identifier: Apache-2.0` comment (after the shebang), a standard one-line license tag. Use `#` in bash and Python, and `//` in JavaScript, as `lib/shot.mjs` does. Python uses only the standard library; ask before adding a dependency.
- The kit's scripts and tests start Python files as `python3 -I -B` (isolated mode, and no `.pyc` files). Do the same in anything you add and in your own commands.
- Bash: `set -euo pipefail`, shellcheck-clean. Settings are in `.shellcheckrc`. If you must silence a warning, add a `# shellcheck disable=SCxxxx` line with a reason.
- Formatting comes from `.editorconfig`: UTF-8, LF line endings, final newline, two-space indent (four in Python).
- Errors: in bash, call `die "message"` from `lib/common.sh`. In Python, exit with a short message.
- Secrets: a token goes through `spawn_curl` (stdin) or an in-process header, never onto a command line, into a log or into a prompt. It goes only to a checked origin: `check_origin` in `lib/common.sh`, or `lib/safeurl.py` in Python, which also refuses to follow redirects.
- Account names: an account is one word or `group/name` (lowercase letters, digits, underscore or hyphen, starting with a letter or digit; at most one slash). Check a name with `valid_account_name` before you build a path from it, and prefer `$ACC`, which `load_account` already sets to the account's folder.
- Chat text is untrusted input. Never run it, expand it, or let it choose a path or a world.
- Commit and branch style, DCO and AI disclosure are in [CONTRIBUTING.md](../../CONTRIBUTING.md) and [AI-assisted contributions](ai-assisted-contributions.md).

## Add a new command

1. **Pick the language.** Use bash for thin glue that calls other programs. Use Python when there is parsing or logic. Put the logic in `lib/` (so tests can import it) and keep the `bin/` file thin.
2. **Create `bin/sdlca-<name>`** and make it executable (`chmod +x`). Start from this skeleton and fill in the header comment. The `usage:` line is the source of truth for the docs, so keep it accurate:

   ```bash
   #!/usr/bin/env bash
   # SPDX-License-Identifier: Apache-2.0
   # One sentence saying what the command does.
   # usage: sdlca-example <account>
   set -euo pipefail
   # shellcheck source=../lib/common.sh
   . "$(dirname "$(readlink -f "$0")")/../lib/common.sh"
   [ "$#" -eq 1 ] || die "usage: sdlca-example <account>"
   load_account "$1"
   # Now set: ACCOUNT, ACC (the account folder), OWNER, SPAWN_USERNAME and SPAWN_TOKEN_FILE.
   log_line "example ran"
   ```

   `load_account` validates the name (one word, or `group/name`), refuses an env file that others can write, and loads the account's environment. For `--help`, call `usage_header "$0"`, which prints the header comment; it must start on line 3, right after the license line (see `bin/sdlca-token`). For a Python command, follow `bin/sdlca-say`: start with `#!/usr/bin/env -S python3 -I -B` (isolated mode, no `.pyc` files), put `lib/` on `sys.path` as it does, and print the docstring as usage. Add the new command to the list in `tests/test_direct_run.py`, which checks the shebang and that the command starts and prints its usage.
3. **Register it with the linter.** `scripts/lint.sh` lists the files it checks. Add a bash command to `SHELL_FILES`, or a Python command to `PY_FILES`. Files matching `lib/*.py`, `scripts/*.py`, `tests/*.py`, `tests/shell/*.sh` and `scripts/*.sh` are found by pattern; anything else, including a new `lib/*.sh`, must be listed.
4. **Write tests first or alongside.** A Python test for the logic in `lib/`, and a shell test with shims if the command calls `curl`, `spawn`, `bun` or `systemctl`. See [testing](testing.md). A command that touches tokens, the allowlist or routing needs tests for the failure cases (wrong sender, odd input, missing file).
5. **Ask the security questions.** Does it send a token anywhere? (Only to the Spawn origin; use `sdlca-api`, `spawn_curl` or, in Python, `lib/safeurl.py`.) Does it log chat text? (Never.) Does it act on text a person typed? (Never directly.) Does it change who can trigger work? (Then it must go through `lib/route.py`.)
6. **Document it.** Add it where people will look for it, for example [configuration](../configuration.md) or [operations](../operations.md), and add a line under `[Unreleased]` in [CHANGELOG.md](../../CHANGELOG.md). Say "planned" for anything that is not working yet. A new file in `lib/` or `scripts/` also goes into the lists in this guide and in [AGENTS.md](../../AGENTS.md).
7. **Run `bash scripts/lint.sh`**, then open the pull request.

## Change the agent prompt or the templates

`templates/handler-prompt.md` is rendered by `lib/render_prompt.py`. Placeholders look like `{{NAME}}` and the available names are `AGENT`, `OWNER`, `ACCOUNT`, `HOME`, `CODE_DIR`, `WORLD`, `CWD`, `WORLDS` and `EVENT`. `CWD` is the world's clone, or the scratch folder `run/scratch/<account>` for an event that names no known world. `EVENT` is the event JSON wrapped in `<untrusted_event>` tags, and every `<` inside it is written as `\u003c` (a backslash, then u003c), so nobody can forge the closing tag. Placeholders are replaced in one pass, so text inside the event is never expanded a second time. Some tests check exact phrases in the rendered prompt (for example "You are alice_helper, an AI agent working for alice"), so if you reword the template, update the tests too. Keep the `{{EVENT}}` placeholder, and keep the lines that tell the agent that chat text and everything it fetches later is untrusted data, and that it is not Spawn staff. A user may override the template with a file in their runtime home, so changes here must stay compatible with those placeholders.

## Debugging tips

| Symptom | Try this |
|---|---|
| One test fails | Run just that file: `python3 -I -B -m unittest discover -s tests -p 'test_route.py' -v`, or one test with `-k test_name`. For a shell test run `bash tests/shell/test_on_chat.sh`. |
| A shell test fails and you cannot see why | Add `cat "$SHIM_LOG"` before `teardown` (teardown deletes the temp folder), or temporarily remove the `teardown` line and `echo "$TMP"` to inspect the folder. `bash -x tests/shell/test_on_chat.sh` shows every command. |
| You want to see what the agent would receive, a routing decision, or how a reply is split | See "Look inside the pieces" below. |
| Lint passes locally but fails in CI | Run `CI=true bash scripts/lint.sh` with the pinned tool versions from the virtualenv section. |
| A command says "writable by group or others" | The account `env` file is sourced as shell, so it must not be writable by anyone but you: run `chmod 600` on it. |
| A command says "invalid account name" | An account name is one word or `group/name`: lowercase letters, digits, underscore or hyphen, starting with a letter or digit, with at most one slash. |
| The listener exits with status 78 | `SDLCA_AGENT_CMD` is not set in the account env. That is deliberate. Under systemd it is not restarted. |
| `sdlca-on-chat` exits 1 and the cursor does not move | Usually the same cause. It also happens when the hourly cap cannot be checked (see the `ERROR the run cap could not be checked` line). The event is left unhandled on purpose. |
| `WARN agent exited with status 124` in `handler.log` | The agent hit `SDLCA_AGENT_TIMEOUT`. The world lock was freed. Any other status means the agent command itself failed (an agent that exits with 74, 75 or 76, which are the handler's own codes, is logged as status 1). |
| An event you expected to run did not (`DENIED`, `WARN`, `RATE-LIMITED` or `SKIP` in `handler.log`) | `DENIED` means the sender is not the owner and not on that owner's allowlist; it is not kept. A turn that failed, timed out, waited longer than `SDLCA_LOCK_WAIT` for the world's lock, or was refused by `SDLCA_MAX_RUNS_PER_HOUR` is kept in `run/failed/<event-id>.json` in the runtime home, and the cursor moves past it. Replay it by hand: `SPAWN_EVENT="$(cat run/failed/<event-id>.json)" bin/sdlca-on-chat <account>`. The handler deletes kept events that are more than `SDLCA_FAILED_KEEP_DAYS` days old (default 30; `0` keeps them forever) when the next allowed event reaches it, so replay a turn before then or copy the file. `SKIP` means that event id already finished (the newest 500 are in `accounts/<account>/handled.ids`), or that another copy of the same event finished first. An `ERROR the run cap could not be checked` line means `SDLCA_MAX_RUNS_PER_HOUR` is not a number or `runs.log` cannot be written; the event is left unhandled. |
| Your `PYTHONPATH` or `PYTHONDONTWRITEBYTECODE` is ignored | The kit runs Python with `-I -B` (isolated mode, and no `.pyc` files). Isolated mode ignores `PYTHON*` variables and does not put the script's or current folder on the import path. The code and tests use `sys.path.insert` instead. If you run Python on the repository without `-B`, it leaves `__pycache__` folders in `lib/` and `tests/`; git ignores them. |
| You need the logs of a real run | `accounts/<account>/handler.log` and `listener.log` in the runtime home (default `~/.sdlca/spawn`; a grouped account lives in `accounts/<group>/<name>/`), and `journalctl --user -u sdlca-listener@<account>.service` under systemd. `listener.log` holds the Spawn client's status lines, not the events. `handler.log` holds the kit's metadata lines and the agent's own output, so keep it private. See [operations](../operations.md). |

### Look inside the pieces

Run these from the root of your clone. The routing decision is one tab-separated line: kind, cursor, event id, decision, sender, world address, working directory and lock name. An event that names no known world gets a folder under `run/scratch/` in the runtime home as its working directory, never the runtime home itself. The second command shows how a long reply is split into numbered chat lines.

```bash
echo '{"kind":"chat_mention","cursor":"c1","chat":{"from":"@alice","text":"hi"}}' \
  | OWNER=alice SPAWN_USERNAME=alice_helper SDLCA_SPAWN_HOME="$(mktemp -d)" python3 -I -B lib/route.py

python3 -I -B -c 'import sys; sys.path.insert(0, "lib"); from linesplit import chunk; print(chunk("word " * 100))'
```

To see the prompt an agent would get, use a throwaway runtime home, a fake token file and `cat` as the "agent", so it needs no network and no account. The prompt lands in that account's `handler.log`.

```bash
export SDLCA_SPAWN_HOME="$(mktemp -d)"
mkdir -p "$SDLCA_SPAWN_HOME/accounts/alice"
printf 'fake-token\n' > "$SDLCA_SPAWN_HOME/accounts/alice/token"
cat > "$SDLCA_SPAWN_HOME/accounts/alice/env" <<EOF
OWNER=alice
SPAWN_USERNAME=alice_helper
SPAWN_TOKEN_FILE=$SDLCA_SPAWN_HOME/accounts/alice/token
SDLCA_AGENT_CMD='cat'
EOF
chmod 600 "$SDLCA_SPAWN_HOME/accounts/alice/env" "$SDLCA_SPAWN_HOME/accounts/alice/token"
SPAWN_EVENT='{"kind":"chat_mention","cursor":"c1","chat":{"from":"@alice","text":"hello"}}' bin/sdlca-on-chat alice
cat "$SDLCA_SPAWN_HOME/accounts/alice/handler.log"
```

Delete the temporary folder when you are done.

## Staying safe while you develop

- Never paste a real token, invite code, browser cookie, env file, or any other session, join or login credential (including values printed by `spawn client join`) into code, tests, issues or chat. Tests use obviously fake values such as `sak_secret_token_value`. `scripts/check-secrets.sh` (part of lint) fails on anything shaped like a real token or key, so keep fake ones short, or build them from two pieces as `tests/shell/test_token.sh` does. A fixture that must keep a real-looking shape can carry the comment `check-secrets:allow` on its line.
- Do not point tests or experiments at real Spawn. If you want to try the kit for real, use your own account, follow [the rules we follow](../compliance/spawn-rules.md), and keep the agent command narrow (read [the security model](../security-model.md) first).
- Do not copy text, code or art from Spawn or other projects into the repository. Link instead.

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
