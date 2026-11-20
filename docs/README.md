# Documentation index

This page is for anyone looking for the right document about the SDLCA agent kit, whether you want to try it, understand it, help build it, come from the Spawn community, work at Spawn, or check the rules. You will get a short path for each of those and a table of every document with one line about each.

The kit is an unofficial community project. It is not made, reviewed or supported by Spawn. If you find a mistake or a gap in these pages, please tell us with the documentation form on the [issue chooser](https://github.com/kdtix-open/sdlca-for-spawn/issues/new/choose). Anything that is not built yet is marked "planned".

## I want to try it

- [Getting started](getting-started.md): from nothing to a first reply from your agent, about 15 minutes if Bun, git and your agent tool are already installed and signed in and you are comfortable in a terminal. It also shows how to remove everything again.
- [Configuration](configuration.md): settings, files and example agent commands.
- [Operations](operations.md): logs, upgrades and troubleshooting.
- [Giving an agent a body](giving-an-agent-a-body.md): day zero and day n+1 for `sdlca-body`, with what worked and what did not.
- [FAQ](faq.md): short answers.

## I want to understand it

- [Architecture](architecture.md): the parts and the life of one message.
- [Security model](security-model.md): who can start work, and which risks remain.
- [Several accounts and worlds](multi-account-and-worlds.md): accounts, the registry and clones.
- [Slack bridge](slack-bridge.md): planned, not built.

## I want to contribute

- [CONTRIBUTING.md](../CONTRIBUTING.md): the short entry point, including ways to help that are not code.
- [Welcome](community/welcome.md): who we are and how to take part.
- [Development guide](contributing/development.md) and [testing guide](contributing/testing.md): set up and write a test.
- [AI-assisted contributions](contributing/ai-assisted-contributions.md): our policy.
- [Roadmap](community/roadmap.md) and [project board](community/project-board.md): what is planned.

## I come from the Spawn community

- [Welcome](community/welcome.md): written for builders, creators, players and newcomers.
- [Feedback and ideas](community/feedback-and-ideas.md): how to tell us, and where Spawn feedback goes.
- [The Spawn rules we follow](compliance/spawn-rules.md): each rule and its source.
- [FAQ](faq.md): including whether the kit is official (it is not) and whether the agent can talk to Savi (it cannot).

## I work at Spawn, or hold rights in a name used here

- [The Spawn rules we follow](compliance/spawn-rules.md): each rule, its source and what the kit does about it.
- [Trademarks and credits](compliance/trademarks-and-credits.md#if-you-hold-rights-in-something-used-here): how we name Spawn and others, and how to tell us about a mistake.
- [SUPPORT.md](../SUPPORT.md) lists the public contact address for people who would rather not use a public issue.

## I need the rules

- [Code of conduct](../CODE_OF_CONDUCT.md), [governance](../GOVERNANCE.md), [security policy](../SECURITY.md) and [support](../SUPPORT.md).
- [License](../LICENSE) and [NOTICE](../NOTICE): Apache-2.0 for what we wrote (the Code of Conduct is the Contributor Covenant, under CC BY 4.0). It does not cover Spawn's names, code, art or documentation.
- [Third-party licenses](compliance/third-party-licenses.md) and [trademarks and credits](compliance/trademarks-and-credits.md).
- [AI-assisted contributions](contributing/ai-assisted-contributions.md) and [communication](community/communication.md).

## Every document

### In the repository root

| Document | What it is |
| --- | --- |
| [README.md](../README.md) | The front door: what the kit is, its status, a quick start and where to go next. |
| [LICENSE](../LICENSE) | The Apache License 2.0, unmodified. It covers what we wrote (code, documentation and templates), not Spawn's or anyone else's names, code, art or documentation. |
| [NOTICE](../NOTICE) | The copyright line, the notice that the project is unofficial, and a pointer to third-party notices. |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Ways to help, a first contribution, branch and commit conventions, sign-off and what review looks like. |
| [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | How we treat each other, based on the Contributor Covenant, with a short project addendum. |
| [GOVERNANCE.md](../GOVERNANCE.md) | Roles, how decisions are made, how to become a maintainer and how conflicts are handled. |
| [SECURITY.md](../SECURITY.md) | How to report a vulnerability privately, what is in scope and what to expect. |
| [SUPPORT.md](../SUPPORT.md) | Where to ask which kind of question. |
| [AGENTS.md](../AGENTS.md) | Rules for AI coding agents that work on this repository. |
| [CLAUDE.md](../CLAUDE.md) | A pointer that sends Claude Code to AGENTS.md. |
| [CHANGELOG.md](../CHANGELOG.md) | Notable changes in plain words. Nothing has been released yet. |

### In docs

| Document | What it is |
| --- | --- |
| [README.md](README.md) | This index. |
| [getting-started.md](getting-started.md) | Prerequisites, install, first account, agent command, listener, a first message and removal. |
| [configuration.md](configuration.md) | Every environment variable, every file in the runtime home, the allowlist, the world registry and the prompt override. |
| [operations.md](operations.md) | Running the listener, logs, upgrades, replay, troubleshooting, rotating a token, backups and uninstalling. |
| [giving-an-agent-a-body.md](giving-an-agent-a-body.md) | Two stories about `sdlca-body`: an agent's first body (day zero), and keeping, undoing and sharing it (day n+1). |
| [architecture.md](architecture.md) | The parts, the life of one event, design decisions and what is deliberately not built. |
| [multi-account-and-worlds.md](multi-account-and-worlds.md) | Several owners and accounts, the world registry, clones, renames and lost access. |
| [slack-bridge.md](slack-bridge.md) | The planned Slack bridge: its design and the example app manifest, explained scope by scope. |
| [security-model.md](security-model.md) | The threat model in plain words, token handling, logs, residual risks and a hardening checklist. |
| [faq.md](faq.md) | Short answers that link to the longer pages. |

### In docs/contributing

| Document | What it is |
| --- | --- |
| [development.md](contributing/development.md) | Set up a development environment, tour the repository, run the checks and add a command. |
| [testing.md](contributing/testing.md) | How the tests work without a network, and how to write one. |
| [ai-assisted-contributions.md](contributing/ai-assisted-contributions.md) | The policy on AI-assisted work: disclosure, accountability, sign-off and agent accounts. |
| [releasing.md](contributing/releasing.md) | How releases are cut, versioning, the changelog and the monthly re-check of Spawn's terms. |

### In docs/community

| Document | What it is |
| --- | --- |
| [welcome.md](community/welcome.md) | Who is welcome and how to take part, including ways to help that are not code. |
| [feedback-and-ideas.md](community/feedback-and-ideas.md) | How to give us feedback and ideas, and how to route Spawn feedback to Spawn. |
| [triage-and-labels.md](community/triage-and-labels.md) | The issue labels, how often we triage and how an issue moves. |
| [project-board.md](community/project-board.md) | The public project board: its fields and views, and how a proposal becomes work. |
| [roadmap.md](community/roadmap.md) | What is shipped, next and later, with no dates. Planned items are listed here. |
| [communication.md](community/communication.md) | Channels, response expectations, language, accessibility and time zones. |

### In docs/compliance

| Document | What it is |
| --- | --- |
| [spawn-rules.md](compliance/spawn-rules.md) | The Spawn rules we follow, each with a source, a date and the part of the kit that honors it. |
| [Third-party licenses](compliance/third-party-licenses.md) | Every outside tool or service the kit runs or documents, its license and how we use it. |
| [trademarks-and-credits.md](compliance/trademarks-and-credits.md) | How we name other companies and their products, the notice wording and the credits. |

### In docs/maintainers and docs/research

| Document | What it is |
| --- | --- |
| [github-settings.md](maintainers/github-settings.md) | For maintainers: repository settings, security features, labels, the ruleset, the project and Discussions. |
| [welcome-post.md](maintainers/welcome-post.md) | For maintainers: the text of the first post in Discussions, to read and post by hand. |
| [oss-community-patterns-2026.md](research/oss-community-patterns-2026.md) | The research behind our community practices: which projects were studied and what we adopted. |

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
