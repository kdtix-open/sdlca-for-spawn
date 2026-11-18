# Contributing to the SDLCA agent kit

This page is for anyone who wants to help, whether or not you write code, and it shows you the shortest path to a first merged contribution. You are welcome here. You do not need to be a programmer, you do not need a Spawn account, and you do not need anyone's permission to start.

The kit is an unofficial community project. It is not affiliated with Spawn. Please read the [Code of Conduct](CODE_OF_CONDUCT.md) first; it applies everywhere we talk.

## Ways to help

Code is only one way. Each of these matters, and we say thank you for every one:

- **Try it and tell us what happened.** Follow [getting started](docs/getting-started.md), then tell us in [Discussions](https://github.com/kdtix-open/sdlca-for-spawn/discussions) where you got stuck.
- **Report a bug** with the [issue forms](https://github.com/kdtix-open/sdlca-for-spawn/issues/new/choose). The smallest steps that show the problem are the best gift.
- **Tell us when Spawn changed** and the kit no longer matches. There is a form for that too.
- **Improve the docs.** Fix a typo, clear up a step, add what you wish you had known.
- **Answer a question** in Discussions. Sharing what you learned is real help.
- **Test on another system.** We have tested only on Ubuntu under WSL2. The CI job is set up to run the same checks on GitHub's Ubuntu runner. Other Linux distributions are the most useful to try today. macOS is not supported yet (planned).
- **Translate.** We have no translation workflow yet. Open an idea in Discussions first so we can agree how to organize it.
- **Share what you built** with the kit in the Show and tell category.

Found a security problem? Do not open a public issue. Follow [SECURITY.md](SECURITY.md).

## Your first contribution in 30 minutes

No git or terminal? Open the file on GitHub (for example under `docs/`), click the pencil icon, make your change, and choose Propose changes. GitHub makes your fork and opens the pull request for you. Add `Signed-off-by: Your Name <you@example.com>` as the last line of the commit description box. If you forget, a maintainer will ask; nothing is lost.

Comfortable with git? Follow these steps.

1. **Pick something small (5 minutes).** A typo or an unclear sentence in `docs/`, or an issue labeled [good first issue](https://github.com/kdtix-open/sdlca-for-spawn/labels/good%20first%20issue).
2. **Fork and clone (5 minutes).** Use the Fork button on GitHub, then clone your fork. Make a branch: `git switch -c docs/fix-quick-start-typo`.
3. **Make the change (10 minutes).** For code, set up with [the development guide](docs/contributing/development.md).
4. **Check it (2 minutes).** Run `bash scripts/lint.sh`. It runs the linters, a check for secrets, a check that `LICENSE` is unchanged, a check of the Markdown links, and the tests. If a linter is not installed it says so and skips it; CI is strict. On macOS or native Windows this script may not run yet (see [the development guide](docs/contributing/development.md)). Skip it and say so in the pull request; the checks on GitHub run it for you (a maintainer starts them for a first pull request).
5. **Commit with a sign-off (3 minutes).** `git commit -s -m "docs: fix typo in the quick start"`. If an AI tool helped, add the trailer as a second message: `git commit -s -m "docs: fix typo in the quick start" -m "Assisted-by: Claude Code claude-sonnet-5-5"`. In GitHub's web editor, put the `Assisted-by:` line in the commit description box.
6. **Open a pull request (5 minutes).** Push your branch, click the link GitHub prints, and fill in the template. Say in plain words what changed and why.

Stuck on any step? Ask in Discussions. Nobody minds, and the question helps the next person.

## How we work

- **Branches:** `type/issue-short-slug`, for example `fix/42-listener-restart` or `docs/17-clarify-allowlist`. The issue number is optional for tiny fixes.
- **Commit subjects:** `type(scope): what changed, in the imperative`. Types are `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `deps` and `revert`. The scope is optional; use the area names from our labels: `runtime`, `worlds`, `install`, `templates`, `slack`, `providers`, `docs`, `ci`, `tests`. Example: `fix(runtime): stop a hung agent turn from holding the world lock`.
- **Pull requests:** one idea each. Write the title in the same style, because we squash-merge and the title becomes the commit subject. Put `Closes #123` in the description.
- **Before you push:** `bash scripts/lint.sh` must pass, or you say in the pull request that you could not run it. Our automatic checks on GitHub (continuous integration, or CI) run exactly that script, as the check named "Lint and test".
- **Tests:** if you change behavior, add a test. See [testing](docs/contributing/testing.md). Tests never reach the internet and never use real accounts.

## Sign your commits (DCO)

Each commit needs a sign-off line. It says you wrote the change, or have the right to send it, under the [Developer Certificate of Origin 1.1](https://developercertificate.org/) (DCO). Add it with `git commit -s`. Git builds `Signed-off-by: Alice Example <alice@example.com>` from your own name and email. They stay in the public history for good, so use the name you go by in this project; we never ask for ID. A GitHub no-reply email address is fine. See [what is public and what is private](docs/community/communication.md#what-is-public-and-what-is-private).

Forgot? Use `git commit --amend -s` for the last commit, or `git rebase --signoff HEAD~3` for the last three (`HEAD~3` means "the last three commits"), then `git push --force-with-lease`. That last command replaces your own branch on GitHub with the signed commits, and it stops if someone else has pushed to that branch in the meantime. Only a person signs off. An AI agent never does. An automatic check is planned (see the [roadmap](docs/community/roadmap.md)); until then a maintainer checks by hand.

Your contribution is licensed under Apache-2.0, like the rest of the project (section 5 of the [license](LICENSE)). Do not copy text, code or art you cannot license that way. That includes Spawn's own docs, skills, art and client, which are not ours to copy.

## AI assistance

We build this project with AI agents and welcome AI-assisted work. A person is always accountable for what is sent, and we ask you to say so when an AI tool did more than spelling, formatting, autocomplete or a mechanical rename: a section in the pull request, plus an `Assisted-by:` line in the commit. It takes a minute and nobody is judged for it. An agent you direct and review is welcome. Fully autonomous agents that open pull requests or issues with nobody reading them first are not accepted. The full policy, with the reasons, is in [AI-assisted contributions](docs/contributing/ai-assisted-contributions.md). AI agents working on this repository read [AGENTS.md](AGENTS.md).

## What to expect from review

These are goals, not promises. The team is small.

- We aim to reply to a new issue or pull request within about 7 days. If you hear nothing after 14 days, a polite nudge is welcome.
- A reviewer checks that the change works, is clear, handles tokens and the sender allowlist safely, keeps to Spawn's rules, and is licensed correctly. Reviewers ask questions first.
- Our merge rules ask for one maintainer's approval and a passing "Lint and test" check. We squash-merge, so your branch becomes one commit.
- A "no" or "not yet" is about the change, never about you. We say why.

## How decisions get made

Small changes are decided in the pull request. Bigger ones start in an issue or a Discussion. [GOVERNANCE.md](GOVERNANCE.md) explains roles, how to become a maintainer, and how disagreements are settled.

## Reminders about Spawn

- **Never post a token.** That means `sak_...`, `sbk_...`, `xoxb-...` or `xapp-...` values, env files, invite codes, other people's messages, or any other session, join or login credential, including values printed by `spawn client join`. Not in issues, pull requests, Discussions or chat. Replace them with `REDACTED`. If you leaked one, revoke or replace it right away, then tell us.
- **Use only Spawn's documented doors.** The kit uses Spawn's published API, the client Spawn publishes and git over https. Please do not contribute code that replays a logged-in browser session or calls the website's internal endpoints, and never paste a browser cookie anywhere. A person makes a personal token by hand on their own Spawn settings page. See [the rules we follow](docs/compliance/spawn-rules.md).
- **Spawn platform bugs go to Spawn.** A broken world, player or website is not something we can fix. Use the in-app "Report a bug" or [Spawn's support page](https://www.spawn.co/support). We do not speak for Spawn.
- **Feedback sent to Spawn may become Spawn's.** Spawn's [terms of service](https://www.spawn.co/terms-of-service) (section 19, read 2026-11-17) give Spawn rights in feedback you send it. What you send to this project is covered by this project's license.
- **Do not make anything look official.** Please do not name commands, files or features "Spawn" or "Savi". Details are in [the rules we follow](docs/compliance/spawn-rules.md) and [names and credits](docs/compliance/trademarks-and-credits.md).

## More guides

[Development](docs/contributing/development.md), [testing](docs/contributing/testing.md), [releasing](docs/contributing/releasing.md), [where to ask what](SUPPORT.md), and the [welcome page](docs/community/welcome.md).
