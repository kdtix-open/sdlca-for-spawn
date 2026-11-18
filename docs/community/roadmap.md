# Roadmap

This page is for anyone who wants to know what the SDLCA agent kit does today, what we plan to build, and what we have decided not to build. It is honest about all three. It gives no dates, and it marks everything that is not built yet as planned.

**Last reviewed 2026-11-17.** We update this page in the same pull request whenever something moves from one list to another.

## How to read this page

- **Shipped** means it is in the repository today and works as described. The [testing guide](../contributing/testing.md#not-covered-yet) lists the parts the automated tests do not cover. Nothing has been released yet. The first release is planned as 0.1.0. See [CHANGELOG.md](../../CHANGELOG.md).
- **Next** means we intend to work on it first.
- **Later** means we want it, nobody has started, and it may depend on others.
- **Where it is tracked** links to a search for the open issues with that label. It can be short or empty; if it is empty, start a Discussion.
- **No dates.** Spawn changes fast, and we are a small team. Order on this page shows our current thinking and is not a promise. A planned item may change or be dropped. We will say so here when it does.

Our order of care is: first safety and Spawn's rules, then reliability, then new features.

## Shipped

These work today. They are described in [getting started](../getting-started.md) and in [the architecture](../architecture.md).

- A listener for each Spawn account, which watches the account's inbox and runs one agent turn for each message from the owner or an allowed sender.
- The agent command is whatever you choose. Any tool that reads a prompt on standard input works, and the kit has no default.
- A fail-closed sender gate, routing from structured fields only, one writer per world, and a cursor that only moves forward.
- Commands to set up accounts, accept the owner's friend requests, post replies in Spawn's 200-character chat lines, keep a registry of worlds and their clones, and take one screenshot of a world (the tests cover the command's argument checks, not the screenshot itself).
- A systemd user service for the listeners, and an install script. The tests check that the install script renders the service file, not that the service runs.
- Tests that use no network and no real accounts, and a continuous integration check that runs them.
- Community files: license, contributing guide, Code of Conduct, governance, security policy, issue forms and this documentation.

## Next

| Item | What it is | Where it is tracked |
| --- | --- | --- |
| The first release, 0.1.0 | Tag and publish what is in the repository, following the release checklist. | [The release checklist](../contributing/releasing.md#release-checklist) |
| An automatic DCO check (planned) | A check that every commit carries a person's Developer Certificate of Origin sign-off. It must also understand commits from a project agent account, where a maintainer adds the sign-off at merge. Until it exists, maintainers check by hand. See the [AI policy](../contributing/ai-assisted-contributions.md). | [Open issues labeled `area:ci`](https://github.com/kdtix-open/sdlca-for-spawn/issues?q=label%3Aarea%3Aci) |
| Hook concurrency robustness (planned) | If Spawn's client runs several handler processes at once, a crash can skip an older unfinished event. We have not confirmed that the client ever does this. The cursor write is now locked, so two handlers that finish together cannot undo each other's write; what is still unconfirmed is whether the client ever runs handlers at the same time, and what a crash then skips. The plan is to find out. See [cursor and replay](../operations.md#cursor-and-replay). | [Open issues labeled `area:runtime`](https://github.com/kdtix-open/sdlca-for-spawn/issues?q=label%3Aarea%3Aruntime) |
| The Slack bridge (planned) | Directing agents from a Slack workspace: slash commands, reactions as status, file exchange and canvases. A design and an example Slack app manifest exist. Nothing connects to Slack yet. See [the Slack bridge page](../slack-bridge.md). | [Open issues labeled `area:slack`](https://github.com/kdtix-open/sdlca-for-spawn/issues?q=label%3Aarea%3Aslack) |

## Later

| Item | What it is | Where it is tracked |
| --- | --- | --- |
| Provider adapters (planned) | Ready-made agent commands for particular AI tools. Today the kit only shows examples, and you check them against your provider's own documentation. Adapters need people who use each tool, and tests that do not need real accounts. | [Open issues labeled `area:providers`](https://github.com/kdtix-open/sdlca-for-spawn/issues?q=label%3Aarea%3Aproviders) |
| macOS service support, launchd (planned) | Running the listeners as a macOS service. Today the kit has systemd user services only. People on macOS can run `sdlca-listen` under any supervisor. We need someone with a Mac to test. | [Open issues labeled `area:install`](https://github.com/kdtix-open/sdlca-for-spawn/issues?q=label%3Aarea%3Ainstall) |
| Camera control for screenshots (planned) | Today the screenshot camera faces one direction and does not turn toward objects. We would like agents to be able to look at what they built. | [Open issues labeled `area:runtime`](https://github.com/kdtix-open/sdlca-for-spawn/issues?q=label%3Aarea%3Aruntime) |
| Translations (planned) | The docs in other languages. We have no translation workflow yet. If you want to help, open an idea in Discussions first, so we can agree how to organize it. | [Open issues labeled `area:docs`](https://github.com/kdtix-open/sdlca-for-spawn/issues?q=label%3Aarea%3Adocs) |

## Not on this roadmap

We will say no to these, and we would rather say it here than let anyone waste effort:

- **Anything Spawn's rules forbid.** Making an agent talk to Savi, running anything for Savi unattended, using Spawn as a free generator of assets for use elsewhere, porting Spawn games to other engines, and using anything but Spawn's published doors. See [the rules we follow](../compliance/spawn-rules.md).
- **Bundling Spawn's client** or any Spawn text, art or code. People install the client themselves.
- **A hosted service or a shared multi-user queue.** The kit runs on your own machine, for your own accounts.
- **Anything that suggests Spawn endorses the kit.**
- **A sandbox built into the kit.** A sandbox belongs to the operating system or your provider's tool. [The security model](../security-model.md#hardening-checklist) shows what to do.

[The architecture page](../architecture.md#what-is-deliberately-not-built-and-where-to-extend) has the longer list, with reasons.

## How to change this roadmap

The roadmap is shaped by what people tell us. If you want something added, moved or dropped:

1. Start a Discussion in the Ideas category. See [feedback and ideas](feedback-and-ideas.md).
2. If people want it, it becomes an issue and goes on the public [project board](project-board.md), where a "Target release" may be set. That is a goal and not a promise.
3. Pull requests are welcome for anything on this page. Comment on the issue first, so we can point you to the right place. [CONTRIBUTING.md](../../CONTRIBUTING.md) shows how.

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
