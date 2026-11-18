# Testing guide

This guide is for contributors and AI agents who run, read, write or extend the tests of the SDLCA agent kit. You will learn why the tests are built the way they are, how the fake programs (`curl`, `spawn`, `bun` and `systemctl`) work, how to write a Python test and a shell test, and what each existing test file covers.

## The philosophy

1. **No internet, no secrets, no real accounts.** Anyone can run the tests on a laptop, in CI (our automatic checks on GitHub) and on a train with no signal. A test that needs a token or a Spawn account is a bug. The few tests that need "a server" start one on your own machine (`127.0.0.1`, or a `file://` folder standing in for Spawn).
2. **Replace outside programs with shims.** The kit calls `curl`, `spawn`, `bun` and `systemctl`. The tests put fake programs with those names first on `PATH`. The fakes record what they were asked and answer from canned data.
3. **Never touch your real home.** Every test builds a temporary folder and deletes it afterwards. The shell tests point `HOME`, `XDG_CONFIG_HOME`, `GIT_CONFIG_GLOBAL` and `SDLCA_SPAWN_HOME` into it, so a run can never touch your real git or systemd files, even if your environment points at them (a test proves it). The Python tests pass a temporary `SDLCA_SPAWN_HOME` to the programs they run, and give them the system's temporary folder as `HOME`.
4. **The security promises have tests.** Fail-closed senders, chat text that cannot pick a world, tokens that never reach a command line or another host, the raw token kept out of the agent's environment, a cursor that never moves backward, a hung agent that frees its lock. If you change code near one of these, you change its test in the same pull request.
5. **Small and fast.** The whole suite takes about a minute on the machine we tested on (a few tests wait on locks and timeouts on purpose). Keep it that way so people run it.
6. **Never make a test pass by weakening it.** If a test fails, fix the code or explain in the pull request why the test was wrong. Do not delete or loosen it to get a green check.

## Run the tests

```bash
bash tests/run.sh                                                    # everything
python3 -I -B -m unittest discover -s tests -p 'test_route.py' -v       # one Python file
python3 -I -B -m unittest discover -s tests -p 'test_route.py' -k test_owner_is_allowed -v   # one test
bash tests/shell/test_on_chat.sh                                     # one shell test file
```

`tests/run.sh` runs all Python tests (`python3 -I -B -m unittest discover`), then each `tests/shell/test_*.sh`. It prints a line `Ran N tests` for the Python tests, and one line starting with `  ok` for every shell check that passed. `bash scripts/lint.sh` runs the tests as its last step. The `-B` keeps Python from leaving `__pycache__` folders in `lib/` and `tests/`; if you leave it out, git ignores the folders.

Each shell test group starts by clearing every `SDLCA_*`, `SPAWN_*` and `SHIM_*` variable, and `ACCOUNT` and `OWNER`, from your environment, so settings you exported in your shell, such as `SDLCA_AGENT_CMD` or `SPAWN_ORIGIN`, do not leak into the checks. The Python tests start their programs with a small, clean environment too.

## How the shims work

The four shims live in `tests/shims/` and are plain bash. They are chosen by `PATH` order, not by any flag in the code under test.

**`tests/shims/curl`** is the fake `curl`.

- It appends `ARGV: <all arguments>` to the file named by `SHIM_LOG`.
- If it was called as `curl -K -` (the kit's way of passing the token on stdin), it appends `STDIN: <the config it read>`. That is how tests prove the token arrived on stdin.
- For the argument after `--data-binary` it appends `BODY: <that argument>`.
- It answers by the last argument, the URL. `.../api/social/friends` returns the JSON in `SHIM_FRIENDS` (default `{"incoming":[]}`). `.../api/social/relation` returns `{"ok":true,"friend":"friends"}`. `.../api/agent/v1/me` returns the JSON in `SHIM_ME` (by default a person's account, `actorClass` `human`, with two worlds). Anything else returns `{"ok":true}`.

**`tests/shims/spawn`** is the fake Spawn client. It appends `SPAWN: <all arguments>` to `SHIM_LOG`. The listener normally replaces itself with `spawn events ... --exec '<handler>'`, so the test only checks the recorded command line (which kinds, which cursor, which handler). The handler is not started by the shim. Like the real client, `spawn events` prints a status line on stderr and one event, with the chat text `SECRET CHAT TEXT`, as JSON on stdout (that is how a test proves the listener does not log chat text). `spawn login` writes a fake token file at `SPAWN_TOKEN_FILE` and, as the real client does, adds a credential helper to the global git configuration, so the onboarding test can prove the kit puts that configuration back. It refuses an invite that starts with `sbk_bad`.

**`tests/shims/bun`** and **`tests/shims/systemctl`** only record their call (`BUN: ...`, `SYSTEMCTL: ...`) in `SHIM_LOG` and succeed, so the `scripts/install.sh` test changes nothing on your machine.

`SHIM_LOG` and `SHIM_OUT` (a folder where a fake agent can write files) are set by the shell test setup below. A test may also set `SHIM_FRIENDS` and `SHIM_ME` to change the canned answers.

## How `tests/shell/lib.sh` works

Every shell test starts by sourcing `tests/shell/lib.sh`. It gives you these pieces:

| Piece | What it does |
|---|---|
| `ROOT` | The repository root, so you can call `"$ROOT/bin/sdlca-on-chat"`. |
| `setup` | Clears every `SDLCA_*`, `SPAWN_*` and `SHIM_*` variable, and `ACCOUNT` and `OWNER`, from the environment. Makes a temporary folder `$TMP`. Sets `HOME` to a folder inside it, so `~/.bun/bin` and `~/.local/bin` (which `lib/common.sh` would otherwise put ahead of the shims) do not exist. Clears the `GIT_CONFIG_*` variables and points `XDG_CONFIG_HOME` and `GIT_CONFIG_GLOBAL` into the same folder, so no test reads or writes your own git or systemd files. Sets `SDLCA_SPAWN_HOME`, `SHIM_LOG` and `SHIM_OUT`, and puts `tests/shims` first on `PATH`. Creates the account "alice" with a fake token (`sak_secret_token_value`, mode 0600) and an env file (mode 0600) naming her agent `alice_helper`. Writes a `worlds.json` with one world, `@alice/game-1`, whose clone folder `$TMP/clones/alice/game-1` exists. Sets `ACC` to alice's account folder. |
| `with_agent '<command>'` | Adds `SDLCA_AGENT_CMD` to alice's env. The command reads the prompt on stdin, just as a real agent command does. |
| `check "<what it proves>" <command...>` | Runs the command; prints `ok` or `FAIL` and counts failures. |
| `finish` | Call it last. Exits 1 if any check failed. |
| `teardown` | Deletes `$TMP`. |

Shell tests use `set -u` but not `set -e`, so one failed check does not hide the others.

## Write a Python test

Python tests are `tests/test_<thing>.py`, use the standard library's `unittest`, and are found automatically. `tests/helpers.py` gives you `ROOT`, puts `lib/` on `sys.path` (so `import route` works), and offers `run(args, env=None, stdin=None, cwd=None)`, which runs a command in a subprocess with only a minimal environment plus the variables you pass.

Test pure functions by importing them. Test a command by running it with `python3 -I -B`, as the kit does. Here is a small example:

```python
# SPDX-License-Identifier: Apache-2.0
import json
import os
import unittest

import helpers  # puts lib/ on sys.path
import route


class ExampleTests(unittest.TestCase):
    def test_a_stranger_is_denied(self):
        event = {"kind": "chat_mention", "chat": {"from": "@mallory", "text": "hi"}}
        self.assertEqual(route.decide(event, "alice", "alice_helper", []), "deny:not-allowed")

    def test_the_command_runs_without_touching_the_network(self):
        script = os.path.join(helpers.ROOT, "bin", "sdlca-allow")
        result = helpers.run(["python3", "-I", "-B", script, "list"], env={"SDLCA_SPAWN_HOME": "/nonexistent-dir"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("members", json.loads(result.stdout)["slack"])


if __name__ == "__main__":
    unittest.main()
```

Good habits, copied from the existing tests:

- Name the class after the thing (`RouteTests`) and each method after the behavior in words (`test_chat_text_can_never_choose_the_world`).
- Use `tempfile.TemporaryDirectory()` and clean it up in `tearDown`.
- Pass `SDLCA_SPAWN_HOME`, `SPAWN_TOKEN_FILE` and friends explicitly; never read the real ones.
- Use `alice`, `bob`, `carol` and `@alice/game-1`, and clearly fake tokens such as `sak_test_token`. `scripts/check-secrets.sh` scans the test files too and fails on a token-shaped string (it knows many formats: Spawn, Slack, GitHub, provider keys, JSON Web Tokens, passwords inside URLs and more), so keep a fake token short, or build it from two pieces as `tests/shell/test_token.sh` does (`TOKEN="sak_""0123..."`). A line that must keep a real-looking shape can carry the comment `check-secrets:allow`.
- Test the failure and the odd input, not only the happy path. Most of this kit's value is in what it refuses.
- When a test needs a "server", follow `tests/test_say.py` (a tiny `http.server` on `127.0.0.1`, port chosen by the system) or `tests/test_worlds.py` (a local bare git repository and a `file://` origin).

## Write a shell test

Shell tests are `tests/shell/test_<thing>.sh`. `tests/run.sh` finds every file with that pattern, and `scripts/lint.sh` checks it with shellcheck. A test file is a series of groups. Each group says in plain words what it proves, calls `setup`, does something, runs `check` lines, and calls `teardown`:

```bash
#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# shellcheck disable=SC2016  # single quotes are deliberate: the agent command expands its own variables
set -u
# shellcheck source=lib.sh
. "$(dirname "$(readlink -f "$0")")/lib.sh"

echo "the owner's message reaches the agent"
setup
with_agent 'cat > "$SHIM_OUT/prompt.txt"'
SPAWN_EVENT='{"kind":"chat_mention","cursor":"c1","chat":{"from":"@alice","text":"hello"}}' "$ROOT/bin/sdlca-on-chat" alice
check "the prompt was written" test -s "$SHIM_OUT/prompt.txt"
check "the event is in the prompt" grep -q '"text":"hello"' "$SHIM_OUT/prompt.txt"
teardown

finish
```

Tips:

- Assert both sides of a promise: that the good thing happened and that the bad thing did not (see "no agent run for ..." in `test_on_chat.sh`).
- To check that something is absent, wrap it: `check "token is absent" bash -c "! grep -q sak_secret_token_value '$SHIM_LOG'"`.
- To add a canned answer for a new URL, extend the `case` in `tests/shims/curl`, and keep the `ARGV:`, `STDIN:` and `BODY:` lines as they are because other tests read them. A new shim program goes in `tests/shims/` and must also be added to `SHELL_FILES` in `scripts/lint.sh`.
- When a test needs Spawn's answers or a git remote, follow `tests/shell/test_onboard.sh`: a folder used as a `file://` origin (`SPAWN_ORIGIN`, with `SDLCA_ALLOW_FILE_ORIGIN=1`, a setting that exists for tests) and a local bare git repository.
- Keep `SPDX-License-Identifier: Apache-2.0` near the top of new files.

## What each test file covers

Run `bash tests/run.sh` for the current numbers; they change as tests are added, so this page does not count them. There are Python test files in `tests/` and shell test files in `tests/shell/`.

| File | What it covers |
|---|---|
| `tests/test_route.py` | Who may trigger work: the owner is allowed; a stranger, another owner's account and the agent's own handle are denied; handles are compared as Spawn writes them (`@name` is a person, `@@name` an agent), ignoring case, and a line break after a handle is not part of the name; an extra allowed sender works (a person as `carol`, an agent only as `@@name`); a malformed allowlist entry never widens access; missing or odd senders fail closed. Which world: whole-token matches on world id, app id (with or without hyphens), address and old alias, so `@alice/game` never matches `@alice/game-2`; an exact id beats an address; only the worlds the account can reach (including a world an agent made, and grouped accounts); chat text never chooses the world; lock names are safe file names; a damaged registry entry is skipped and the other worlds still route. The command line: output format, with the event id only when it is safe; an unrouted event gets a scratch directory, never the runtime home; a broken allowlist or registry falls back safely; non-chat events are not gated; no tabs or newlines in fields, and no empty field that bash could shift. |
| `tests/test_say.py` | `sdlca-say` against a local fake server: replies are split, numbered, authenticated and sent to the right door; every call gets fresh nonces; a direct message has no `replyTo`, and `replyTo` must be ASCII digits or `-`; it retries after HTTP 429 (honoring `Retry-After` or `retry_after_ms`, and ignoring a value that is negative, not a number or infinite) and after server errors; a long reply is capped, and even a tiny cap leaves room for a line of text before the note that says how much was left out; `ok:false` is an error; a redirect is never followed, so the token cannot leave; a plain-http origin that is not this machine, and an origin with user information, are refused; a token file with a line break or other odd content is refused without printing it; empty input and bad usage fail without posting; a missing token variable gives a clear error. |
| `tests/test_worlds.py` | `sdlca-worlds` with a local git repository and a `file://` origin: dry run changes nothing; `--apply` clones, registers and sets the commit identity (`sdlca-agent`), and a local path gets no credential helper; the registry records which accounts reach each world, a grouped account under its full name; odd account names are refused, and it refuses to run without an account; a rename moves the clone and remembers the old address, and waits while an agent holds the world's lock; a second run changes nothing; unsafe addresses, names that start with `.` or `-`, and malformed server entries are skipped; a registry that is not a valid JSON object is never overwritten (the command stops and changes nothing); a failed clone is tried again on the next run; a world an agent made (`@@agent/world`) is cloned; an existing clone is never modified. |
| `tests/test_gitcred.py` | The git settings for a clone (`lib/gitcred.py`): the credential helper is attached to the git host of the clone's https address only, and a port is part of the scope; an address that is not plain https gets no helper; paths with spaces or quotes are quoted. With real git (`git credential fill`, no network): Spawn's git host gets the account and token, any other host gets nothing, and the proactive-auth setting is scoped the same way. |
| `tests/test_linesplit.py` | Splitting replies into chat lines of at most 200 characters: empty input, short text, exact fit, numbered long text, no words lost or reordered, one huge word, more than 100 lines. |
| `tests/test_cursor.py` | The inbox cursor moves forward only, breaks ties on id, accepts opaque values, and is written atomically with mode 0600 with no leftover temp file; a time with a zone and one without can be compared; many writers that finish together never rewind it (the lock); a cursor file with bad bytes is replaced, not a crash. |
| `tests/test_render_prompt.py` | Prompt rendering: placeholders replaced in one pass; event text never expanded again; the default template names the world, the worlds and the event; an unrouted event gets a dash for the world and the scratch directory as its working directory; the event is fenced and a closing tag cannot be forged; a runtime override template wins. |
| `tests/test_allow.py` | `sdlca-allow`: add and remove Slack members, per-owner extra Spawn senders (a person as `carol`, an agent with `@@name`), rejection of malformed ids and names (a trailing line break too), the file is mode 0600 and the folder it creates 0700, `list` on a fresh home. |
| `tests/test_check_links.py` | `scripts/check-links.py` on small throwaway Markdown trees: good links and anchors pass; missing files and anchors are reported; GitHub-style heading anchors; duplicate headings get numeric suffixes; code blocks, inline code, web addresses and `mailto:` links are ignored. |
| `tests/test_direct_run.py` | The three Python commands (`sdlca-say`, `sdlca-worlds`, `sdlca-allow`) start when run directly and print their usage; their first line is `#!/usr/bin/env -S python3 -I -B`; `sdlca-allow list` works when run directly. Add a new Python command to the list in this file. |
| `tests/test_state_files.py` | The small helpers that keep state or guard a token. `lib/dedupe.py`: an id is unseen until it is added; the file is private and holds each id once; only the newest 500 are kept; a damaged file is read leniently; a file that cannot be opened, a bad call or an odd id means "could not tell" (exit 2), never "unseen". `lib/ratelimit.py`: the cap holds inside the window; old runs fall out; a limit of 0 turns the cap off; damaged lines never count; a bad call or an unusable file means "could not tell", not a refusal. `safeurl.read_token`: a plain token is read without its newline; a space, line break, quote, backslash, non-ASCII byte, empty file or over-long value is refused, and the message never holds the token. |
| `tests/test_check_secrets.py` | `scripts/check-secrets.sh` in a throwaway git repository: a clean tree passes; every secret format it knows (Spawn tokens and invites, Slack tokens and webhooks, GitHub, GitLab, Anthropic, OpenAI and other provider keys, Stripe, Google, AWS, Hugging Face, npm, JSON Web Tokens, passwords inside URLs, assigned provider keys, private keys) is found and named; harmless look-alikes are left alone; the `check-secrets:allow` marker lets a deliberate fixture through; the report never prints the secret; files git ignores are skipped and untracked ones are scanned. The fake secrets are built from pieces at run time, so this file holds nothing the scanner would flag. |
| `tests/shell/test_on_chat.sh` | The handler end to end: one agent turn with the rendered prompt in the routed clone; strangers, other owners' accounts and the agent's own handle ignored silently and logged without chat text; an extra allowed sender; chat text never executed or expanded; chat text cannot steer the world (an unrouted event runs in its scratch directory); friend requests accepted only from the owner; the token travels on stdin, never argv; malformed events and a missing agent command; the cursor never moves backward; a hung agent is stopped (status 124) and the lock freed; a process the agent leaves running does not keep the lock; an event id never runs twice, and a failed turn is kept in `run/failed` and not marked handled; kept events older than `SDLCA_FAILED_KEEP_DAYS` are deleted, and `0` keeps them forever; an unreadable credentials file keeps the event and says so once; the agent never runs in the runtime home and does not get the raw `SPAWN_TOKEN` or an exported `EVENT`; the cap on runs per hour, and a cap that cannot be checked leaves the event unhandled; a turn that waits too long for the world's lock is skipped and kept; two copies of one event that arrive together run the agent once; an agent that exits with 74, 75 or 76 (the handler's own codes) still counts as a failed turn; a `handled.ids` file that cannot be read does not lose the event. |
| `tests/shell/test_listen.sh` | The listener and the origin checks: exits 78 without an agent command; starts the event stream with the four kinds, the saved cursor and the handler; the chat text the client prints is not written to `listener.log`, but its status lines are; account names (one word or `group/name`) and env files are validated; `sdlca-api` and `sdlca-friends` refuse an origin that is not https (or plain http to this machine) or that carries user information, and `sdlca-api` refuses to send the token to a foreign host. |
| `tests/shell/test_onboard.sh` | `sdlca-onboard` and `scripts/install.sh` with the fake client and a local git repository: onboarding makes a private account, clones and registers the world, sets the display name and never prints the token; the global git configuration ends exactly as it began, also when the invite is refused; a refused invite leaves no env file; an odd token path is quoted, so sourcing the env file cannot run code; bad names are refused before anything is created; `install.sh` prepares the runtime home and the service unit, and a second run keeps your edits; the test setup never touches your real git or systemd files, even when `XDG_CONFIG_HOME` or `GIT_CONFIG_GLOBAL` point at them. |
| `tests/shell/test_token.sh` | `sdlca-token`: `add` stores the token privately (mode 0600, folders 0700), never prints it and leaves no temporary file; a grouped account (`group/name`) works with `sdlca-as` and `path`; several tokens sit side by side in one group, and `list` shows them without any token; `init` makes an account without a token; adding again replaces the token and keeps the env file; an invite code, a short value and a value with spaces are refused without being echoed, and a bad account name or owner is refused too; an unusual prefix is stored with a note; `verify` shows who the token belongs to (never the token) and says plainly when it signs in as a person; `--help` prints the usage. |
| `tests/shell/test_tools.sh` | What the small tools refuse to do. `sdlca-api` never lets curl read a local file (a body that starts with `@`), and the kit's curl runs with `-q` and `--globoff`. A token file with odd content is refused and the error never prints it, and `sdlca-token add` refuses what a token never contains. `sdlca-look` checks its world and its output path before it joins anything (an option, a path or a world in the wrong shape; an output that is a link, a folder, not a `.png`, not under `/tmp`, `$TMPDIR` or `$SDLCA_SPAWN_HOME/shots`, or contains `..`), and a good call works. `sdlca-listen` quotes the handler command so a shell reads a kit folder name with a quote in it as one word and runs nothing else. `scripts/install.sh` refuses a kit folder name that would break the systemd unit. |
| `tests/shell/test_setup_scripts.sh` | The maintainer scripts that configure GitHub, run against a fake `gh` (`tests/shims/gh`) that records its calls. `setup-project.sh`: a dry run prints the plan and calls nothing; `--apply` makes the Project, describes it, links it and adds the six fields; a step that only an organization owner may do (making the Project public) is noted and does not stop the rest; it will not make a second Project with the same title; `--number` finishes a half-made Project and skips fields that exist; a missing `project` scope or a bad option is refused. `setup-github.sh`: a dry run calls nothing; `--apply` turns on secret scanning and push protection first, makes every label, sets no vendor or Spawn name as a topic and leaves the ruleset alone; a refused step is reported and the steps after it still run; a bad repository name is refused. What these tests cannot show is how the real GitHub answers. |

### Not covered yet

These parts have no automated tests of their own, so changes there need extra care and a note in the pull request on how you checked: the screenshot itself (`lib/shot.mjs`; `sdlca-look` is tested only up to its argument checks and the calls it makes to the fake client and `bun`), the systemd unit itself (the install test only checks that `scripts/install.sh` renders it), how the real GitHub answers the setup scripts (`tests/shell/test_setup_scripts.sh` uses a fake `gh`), and anything that needs the real Spawn service or a real agent. `lib/safeurl.py` is tested through `read_token` and through the commands that use it. Tests for these, without needing real accounts, are very welcome. The Slack bridge does not exist yet, so it has no tests.

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
