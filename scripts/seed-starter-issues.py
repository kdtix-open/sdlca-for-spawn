#!/usr/bin/env -S python3 -I -B
# SPDX-License-Identifier: Apache-2.0
"""Post the starter issues for this repository, once, after the first push.

usage: scripts/seed-starter-issues.py [--repo owner/name] [--apply]

A dry run (the default) prints each title and its labels. Read the text below first: it is exactly what --apply
posts, under the account the GitHub CLI (gh) is signed in as. The project's AI policy says that an agent never
posts for a person, so a maintainer runs this and takes responsibility for the text. Every issue gets the
`ai-assisted` label, because the text was drafted with an AI tool and then read by a person.

It is safe to run again: an issue whose title already exists (open or closed) is skipped. The labels must exist
first (scripts/setup-github.sh creates them from .github/labels.tsv). There is one issue for each planned item on
docs/community/roadmap.md, plus a few small ones for newcomers.
"""
import json
import re
import subprocess
import sys

DEFAULT_REPO = "kdtix-open/sdlca-for-spawn"
COMMON_LABEL = "ai-assisted"

ISSUES = [
    {
        "title": "Slack bridge: a Socket Mode listener that hands allowed messages to the handler",
        "labels": ["enhancement", "area:slack", "priority:p2", "help wanted"],
        "body": """## Why
The kit can be directed from Spawn chat today. Many people live in Slack, so the plan is to let an allowed person direct the same agents from there. Only an example manifest and a design exist. See [the Slack bridge page](%(b)s/docs/slack-bridge.md) and the [roadmap](%(b)s/docs/community/roadmap.md).

## What done looks like
- [ ] One Socket Mode connection per Slack app, with the app-level and bot tokens read from a private file (never logged).
- [ ] Only members on the Slack allowlist (`sdlca-allow slack ...`) can start work; everyone else is ignored without a reply (fail closed, like the Spawn side).
- [ ] Events are de-duplicated by event id, and a replay does not run a finished turn again.
- [ ] A reply goes back in the same thread, split to fit.
- [ ] Tests use a fake Slack and no real tokens.
- [ ] The docs say what exists and what does not.

## Where to start
Read `docs/slack-bridge.md` and `bin/sdlca-on-chat`, then comment here with how you would shape it. A design discussion first is welcome: open an idea in Discussions if it is easier.

Not in scope here: slash commands, reactions, files and canvases (separate issues).
""",
    },
    {
        "title": "Slack bridge: show what the agent is doing with emoji reactions",
        "labels": ["enhancement", "area:slack", "priority:p3", "help wanted"],
        "body": """## Why
In Slack a reaction is the quickest status: building, playing, working, testing, or waiting for a person to confirm. This depends on the listener issue.

## What done looks like
- [ ] A small, documented mapping from agent state to reaction.
- [ ] Reactions are added and replaced as the state changes, and removed when the turn ends.
- [ ] Nothing in a reaction reveals private content.

## Where to start
Wait for the Socket Mode listener issue to land, or help with it. Then read `docs/slack-bridge.md` for the scopes the reactions need (`reactions:write`).
""",
    },
    {
        "title": "Add a sign-off (DCO) check that understands agent-authored commits",
        "labels": ["enhancement", "area:ci", "priority:p2", "help wanted", "mentor-available"],
        "body": """## Why
Our contribution rule is that a person signs off each commit (`git commit -s`) and an AI agent never does. Today maintainers check by hand. See [CONTRIBUTING.md](%(b)s/CONTRIBUTING.md) and the [AI policy](%(b)s/docs/contributing/ai-assisted-contributions.md).

## What done looks like
- [ ] A workflow that fails a pull request when a commit has no `Signed-off-by:` line from a person.
- [ ] Commits from the project's agent accounts (where a maintainer signs off at merge) are handled: decide how, and document it.
- [ ] It needs no third-party app and no secrets, and uses a read-only token.
- [ ] The failure message says exactly how to fix it (`git commit --amend -s`, `git rebase --signoff`).

## Where to start
Look at `.github/workflows/ci.yml` for the style we use (pinned actions, least privilege). A maintainer is happy to pair on the agent-commit question.
""",
    },
    {
        "title": "Find out whether `spawn events --exec` runs handlers one at a time",
        "labels": ["task", "area:runtime", "priority:p2", "help wanted"],
        "body": """## Why
If Spawn's client ever runs several handler processes at once, a crash could skip an older unfinished event, because the saved cursor only moves forward. We have not confirmed whether it ever does. See [cursor and replay](%(b)s/docs/operations.md#cursor-and-replay).

## What done looks like
- [ ] A short, reproducible experiment that shows whether two events can be handled at the same time (use a fake handler that sleeps and logs start and end).
- [ ] The result written into the operations doc.
- [ ] If handlers can overlap: a design for tracking in-flight events, as a follow-up issue.

## Notes
This needs only the public client and a test account of your own. Do not reverse engineer the client: observe its behavior from outside, and read only what it prints.
""",
    },
    {
        "title": "macOS: a launchd example for the listener",
        "labels": ["enhancement", "area:install", "priority:p3", "help wanted", "mentor-available"],
        "body": """## Why
The kit runs its listeners as systemd user services, which macOS does not have. People on a Mac can run `sdlca-listen` under any supervisor, but there is no tested example.

## What done looks like
- [ ] A `launchd` property list template, rendered by `scripts/install.sh` or documented by hand.
- [ ] A note on what had to change (paths, the `bun` location, logging).
- [ ] Tested on a real Mac, with the macOS and shell versions written down.

## Where to start
Read `systemd/sdlca-listener@.service.in` and `docs/operations.md`. You need a Mac; we do not have one to test on.
""",
    },
    {
        "title": "Screenshots: turn the camera toward an object before capturing",
        "labels": ["enhancement", "area:runtime", "priority:p3", "help wanted"],
        "body": """## Why
`sdlca-look` joins a world, waits for the first frame and saves one screenshot, but the camera always faces the same way, so an agent cannot look at what it just built.

## What done looks like
- [ ] A documented way to turn the view, using only what the joined body's page offers (keyboard and mouse as a player would use them).
- [ ] An option on `sdlca-look` to choose a direction, and a test with a stand-in page.
- [ ] Works with software rendering.

## Notes
Use only Spawn's documented client behavior. If something needs an undocumented call, stop and ask here first.
""",
    },
    {
        "title": "Verify and document agent commands for other providers (Codex, OpenCode, Cursor agent, Copilot CLI)",
        "labels": ["documentation", "area:providers", "priority:p2", "good first issue", "help wanted", "mentor-available"],
        "body": """## Why
`SDLCA_AGENT_CMD` takes any command that reads a prompt on standard input. We have tested only Claude Code. The docs show examples for other tools and mark them unverified, because we have not run them. See [configuration](%(b)s/docs/configuration.md#other-agent-tools-unverified-examples).

## What done looks like
Pick one tool you already use and, for it:
- [ ] Run the command by hand with a prompt on stdin, in a throwaway folder.
- [ ] Note the exact flags that make it non-interactive and that limit what it can do (the safest posture it offers).
- [ ] Open a pull request that moves the example from "unverified" to "verified with <tool> <version> on <date>", or fixes it.

One tool per pull request is perfect. Never paste keys or tokens.

## Where to start
Comment here with the tool you will try. We will help with the sandbox setup.
""",
    },
    {
        "title": "Check whether Bun honors NODE_EXTRA_CA_CERTS for the Spawn client behind a TLS-inspecting proxy",
        "labels": ["documentation", "area:docs", "priority:p3", "help wanted"],
        "body": """## Why
Behind a proxy or VPN that re-signs TLS traffic, the Spawn client can log `self signed certificate in certificate chain` and cannot connect. Our docs suggest trusting the proxy's certificate authority, for example with `NODE_EXTRA_CA_CERTS`, but we have not verified that Bun honors it. See [operations](%(b)s/docs/operations.md#self-signed-certificate-in-certificate-chain).

## What done looks like
- [ ] A tested recipe (or a clear "this does not work, do this instead") with the Bun and client versions.
- [ ] The troubleshooting entry updated.

## Where to start
You need a network with TLS inspection (or a local test proxy such as mitmproxy with its own CA). Do not disable certificate checks as the recommended fix.
""",
    },
    {
        "title": "Try the quick start on another Linux distribution and tell us what happened",
        "labels": ["task", "documentation", "priority:p3", "good first issue", "help wanted", "mentor-available"],
        "body": """## Why
We have tested only on Ubuntu under WSL2. Fresh eyes on Debian, Fedora, Arch or a plain Ubuntu install will find the gaps in [getting started](%(b)s/docs/getting-started.md).

## What done looks like
- [ ] You followed the guide (a read-only agent command is fine) on a distribution we have not listed.
- [ ] You told us which steps worked, which surprised you, and what you would change, in a comment here or as a pull request to the docs.

You do not need a Spawn account to try the install steps and the tests (`bash tests/run.sh`).
""",
    },
    {
        "title": "install.sh: check the Python and bash versions, not only that they exist",
        "labels": ["enhancement", "area:install", "priority:p3", "good first issue", "help wanted", "mentor-available"],
        "body": """## Why
The docs say we aim for Python 3.9 or newer and bash 4.4 or newer, and we have tested Python 3.12 and 3.14. `scripts/install.sh` only checks that `python3` and `bash` exist, so an older version passes the installer and then fails later in a confusing way.

## What done looks like
- [ ] `scripts/install.sh` reports `MISSING python3` (with a hint) when the version is older than 3.9, and the same for bash older than 4.4.
- [ ] A test with a stand-in `python3` that reports an old version (see `tests/shims/` and `tests/shell/test_onboard.sh`).
- [ ] The docs say what the installer checks (`docs/getting-started.md`, `docs/contributing/development.md`).
- [ ] Optional: a CI job on the oldest Python we claim.

## Where to start
Read `scripts/install.sh` (the `need` function) and `tests/shell/test_onboard.sh`. A first pull request that only does the Python check is perfect.
""",
    },
    {
        "title": "Keep saved failed events per account, so retention follows each account's own setting",
        "labels": ["enhancement", "area:runtime", "priority:p3", "help wanted"],
        "body": """## Why
Saved events (failed, timed-out or rate-limited turns) live in one folder, `run/failed/`, shared by every account in a runtime home. When any account handles an allowed event, the handler deletes files older than that account's `SDLCA_FAILED_KEEP_DAYS` (default 30). So one account's setting can delete another account's saved events, and an account that sets a longer time is not protected. See [configuration](%(b)s/docs/configuration.md) and [operations](%(b)s/docs/operations.md#replay-a-failed-turn).

## What done looks like
- [ ] Saved events go to `run/failed/<account>/<event-id>.json` (a grouped account is `run/failed/<group>/<name>/`), and the clean-up only looks at the handling account's own folder.
- [ ] Existing files in `run/failed/` are still found by the replay instructions, or the docs say how to move them.
- [ ] Tests in `tests/shell/test_on_chat.sh` cover two accounts with different settings.
- [ ] The docs that mention `run/failed` say the new path.

## Where to start
Read `keep_event` and the clean-up near the top of `bin/sdlca-on-chat`, and the tests for kept events in `tests/shell/test_on_chat.sh`. Comment here with how you would handle files that already exist.
""",
    },
    {
        "title": "Add `sdlca-doctor`: check prerequisites, permissions and configuration",
        "labels": ["enhancement", "area:install", "priority:p3", "help wanted"],
        "body": """## Why
When something does not work, people have to read several pages. A single command could check the usual causes and say what to fix.

## What done looks like
- [ ] A new `bin/sdlca-doctor` that checks tools (bun, spawn client, git, curl, flock, python3), the runtime home and token file modes, the account env (without printing secrets), the agent command, and the systemd unit.
- [ ] Output a newcomer can follow: one line per check, then what to do.
- [ ] Tests with shims, no network and no tokens.

## Where to start
Read `scripts/install.sh` (it already checks some tools) and `bin/sdlca-token`. Keep the style of the other commands: a usage header, `set -euo pipefail`, and nothing printed that could be a secret.
""",
    },
    {
        "title": "Translate the README and getting started: let us agree a plan first",
        "labels": ["documentation", "area:docs", "priority:p3", "discussion", "help wanted"],
        "body": """## Why
Many Spawn creators and newcomers to open source read more comfortably in their own language. We have no translation workflow yet.

## What done looks like
- [ ] A short plan in this issue: which languages, who reviews, where translated files live, and how we keep them in step with the English docs.
- [ ] A first translated page as a pull request once the plan is agreed.

Please start by commenting with the language you can help with. Nobody needs to commit to the whole project.
""",
    },
    {
        "title": "Ask Spawn about the project name and our disclaimer, and record the answer",
        "labels": ["compliance", "task", "priority:p1"],
        "body": """## Why
Spawn's Terms limit how its names and marks may be used, and Spawn tells people to ask before starting something doubtful. The project is unofficial and leads with its own name, but the repository name still contains the word Spawn, and no permission has been requested or received. See [the Spawn rules we follow](%(b)s/docs/compliance/spawn-rules.md#why-the-repository-is-called-sdlca-for-spawn).

## What done looks like
- [ ] A named maintainer asks Spawn (its Discord, or its published contact address) the questions listed in the page above: may we say "for Spawn", does Spawn prefer the name not to appear, is there wording it wants in our disclaimer, is there a path for tools like this one.
- [ ] The reply (or the fact that none came) is recorded in `docs/compliance/spawn-rules.md` with the date.
- [ ] We act on the answer, including a rename if Spawn prefers one.

This is a task for a person, not an AI agent. Please do not contact Spawn on the project's behalf without a maintainer agreeing.
""",
    },
    {
        "title": "Offer a tighter agent permission profile and test it",
        "labels": ["enhancement", "security", "area:providers", "priority:p2", "help wanted"],
        "body": """## Why
The builder example allows `Bash(git *)`, which is broad: git can run other programs through its configuration. We say so in the [security model](%(b)s/docs/security-model.md), and would like a narrower example people can copy.

## What done looks like
- [ ] A builder profile that lets an agent edit files, commit and push in a world clone, and reply in chat, with the narrowest command allowlist that works.
- [ ] A test or recipe that shows what it can and cannot do (with a stand-in agent or the provider's own flags), written down with the tool version.
- [ ] The example and the docs updated.

Please do not post exploit details in this issue. If you find a way past a profile that looks like a vulnerability, report it privately: see [SECURITY.md](%(b)s/SECURITY.md).
""",
    },
]


def bodies(repo):
    base = "https://github.com/%s/blob/main" % repo
    return [(issue["title"], issue["labels"] + [COMMON_LABEL], issue["body"] % {"b": base}) for issue in ISSUES]


def existing_titles(repo):
    out = subprocess.run(["gh", "issue", "list", "--repo", repo, "--state", "all", "--limit", "500", "--json", "title"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("seed-starter-issues: gh could not list the issues: %s" % out.stderr.strip())
    return {item["title"] for item in json.loads(out.stdout)}


def main(argv):
    repo, apply = DEFAULT_REPO, False
    args = list(argv)
    while args:
        arg = args.pop(0)
        if arg == "--apply":
            apply = True
        elif arg == "--repo" and args:
            repo = args.pop(0)
        else:
            sys.exit(__doc__)
    if not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", repo):
        sys.exit("seed-starter-issues: --repo must look like owner/name")
    known = existing_titles(repo) if apply else set()
    for title, labels, body in bodies(repo):
        if title in known:
            print("exists, skipped: %s" % title)
            continue
        if not apply:
            print("[dry-run] %s  [%s]" % (title, ", ".join(labels)))
            continue
        cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
        for label in labels:
            cmd += ["--label", label]
        out = subprocess.run(cmd, capture_output=True, text=True)
        print(out.stdout.strip() or out.stderr.strip())
        if out.returncode != 0:
            sys.exit(1)
    if not apply:
        print("Nothing was posted. Read the text in this file, then run again with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
