# Triage and labels

This page is for anyone who opens an issue or a pull request and wonders what the labels on it mean, and for the maintainers and reviewers who sort them. It lists every label, shows how an item moves from "new" to "done", states how fast we aim to answer, and explains how we write beginner-friendly issues and what the AI labels mean.

*Triage* means looking at each new item, deciding what it is, and deciding what happens next. The labels are our notes to ourselves. They are never a judgment of you.

The file [`.github/labels.tsv`](../../.github/labels.tsv) is the single source of truth for label names and descriptions. If this page and that file ever disagree, the file is right, and we would be glad to hear about the mistake. The script `scripts/setup-github.sh` creates the labels from that file. [GitHub settings for maintainers](../maintainers/github-settings.md) has the setup steps.

## The labels you will meet first

You do not need to learn all of them. Our forms add the first ones for you, and a maintainer does the rest.

- `triage` means "a person has not looked at this yet". Every issue form adds it, and we remove it after the first look.
- `bug`, `enhancement` and `documentation` say what kind of item it is.
- `needs-info` means we asked you a question and are waiting for your answer.
- `good first issue` and `help wanted` mark places where new help is especially welcome.

Colors are only decoration. Every label also has a name and a description, and the name always carries the meaning.

## The full list

Here is every label, in groups. Descriptions are copied from the file. The last column says how we use each one.

### Type

| Label | What it means | How we use it |
| --- | --- | --- |
| `bug` | Something is not working | Added by the bug report form. Release notes: Fixes. |
| `enhancement` | A new feature or an improvement | Added by the feature request form. Release notes: Features. |
| `documentation` | Improvements or additions to documentation | Added by the documentation form. Release notes: Documentation. |
| `question` | A question; usually better asked in Discussions | A maintainer adds it, then points the person to Discussions, where anyone can answer. |
| `task` | A discrete unit of work | A maintainer adds it to planned work that did not come from a report. |
| `security` | Security-relevant; never put exploit details in a public issue | A maintainer adds it. The labeler adds it to pull requests that change `SECURITY.md` or the security model. Release notes: Security. |
| `compliance` | Spawn terms, licensing, attribution or acceptable-use matter | Added by the compliance form and by the monthly check issue. The labeler adds it to pull requests that change license or compliance files. Release notes: Compliance and licensing. |
| `agent-behavior` | An AI agent acted wrongly, unsafely or against policy | Added by the agent behavior form. |
| `breaking-change` | Changes behavior that people may rely on | A maintainer adds it to pull requests. Release notes: Breaking changes. |

### Priority

Priority is set by a maintainer during triage, and only for work we mean to do. Our rough meaning is below. These are goals and not promises.

| Label | What it means | How we use it |
| --- | --- | --- |
| `priority:p0` | Highest priority work item | Act now. For example tokens exposed, the sender gate bypassed, or a legal or compliance problem. |
| `priority:p1` | High priority work item | Wanted in the next release. |
| `priority:p2` | Medium priority work item | Wanted soon. This is the default for accepted work. |
| `priority:p3` | Lower priority work item | Good to have, with no hurry. |

### Triage and status

| Label | What it means | How we use it |
| --- | --- | --- |
| `triage` | Needs a maintainer to look at it | Added by every issue form. Removed after the first look. |
| `needs-info` | Waiting for more information from the reporter | A maintainer adds it with a question, then waits for the answer. |
| `needs-reproduction` | Needs steps or input that reproduce the problem | Added when we cannot make a bug happen yet. The smallest steps that show it are the best help you can give. |
| `blocked` | Cannot proceed until something else is resolved | Added to the item that is stuck, with a note of what it waits for. Maintainers also use it to pause a risky change. |
| `blocks` | Other work is waiting on this | Added to the item that others are waiting for. |
| `duplicate` | This already exists | Added when we close an item that repeats another, with a link to the other. |
| `invalid` | This does not seem right | Added when we close something that is not a problem with this project. We always say why, kindly. |
| `wontfix` | This will not be worked on | Added when we decide not to do something. We always say why. See [how we say no](feedback-and-ideas.md#how-we-say-no). |

### Community

| Label | What it means | How we use it |
| --- | --- | --- |
| `good first issue` | Good for newcomers | A maintainer adds it to a small, well-described item. It is reserved for people who are learning. See [how we write good first issues](#how-we-write-good-first-issues). |
| `help wanted` | Extra attention is welcome | A maintainer adds it when outside help is especially welcome. |
| `mentor-available` | A maintainer will guide a first-time contributor through this | A maintainer adds it when they will answer questions and review a first contribution closely. |
| `discussion` | Needs design discussion; open-ended topics belong in Discussions | Added by the Ideas form in Discussions. A maintainer adds it to an issue that needs design talk before anyone builds anything. |

### Area

The labeler workflow adds these to pull requests from the names of the files they change. A maintainer adds them to issues.

| Label | What it means | How we use it |
| --- | --- | --- |
| `area:runtime` | Listener, handler, routing, cursor, locks (bin/, lib/) | The core of the kit. |
| `area:worlds` | World registry, clones, renames | |
| `area:slack` | Slack bridge and manifest | The bridge is planned, not built. See the [roadmap](roadmap.md). |
| `area:providers` | Agent command and provider integrations | |
| `area:install` | Install script, systemd, onboarding | |
| `area:templates` | Prompt, runtime guide and example files | |
| `area:docs` | Documentation | |
| `area:ci` | Workflows, linting and tests infrastructure | |
| `area:tests` | Tests and test tooling | |

### Spawn

| Label | What it means | How we use it |
| --- | --- | --- |
| `upstream:spawn` | Depends on, or is caused by, something on the Spawn platform | Added by the "Spawn changed and the kit broke" form. Items with this label are re-read during the monthly check of Spawn's terms. |

### AI policy

These five come from the [AI-assisted contributions policy](../contributing/ai-assisted-contributions.md). A maintainer adds them by hand, with a friendly note. No workflow adds them. See [What the AI labels mean](#what-the-ai-labels-mean).

| Label | What it means | How we use it |
| --- | --- | --- |
| `ai-assisted` | The pull request or issue discloses AI assistance | Descriptive only. It thanks you for telling us. |
| `agent-authored` | Opened by one of the project agent accounts | Added to items opened by our own agent accounts. |
| `needs-human-explanation` | The author is asked to explain the change in their own words | A friendly request, with a link to the policy. |
| `hard-to-review` | Hard to review as sent: please make it smaller or explain it | Used rarely, and only after a friendly note. It describes the change, not the person. |
| `ai-disclosure-missing` | AI involvement is evident but not disclosed | A friendly reminder, with a link to the policy. |

### Automation and release notes

| Label | What it means | How we use it |
| --- | --- | --- |
| `dependencies` | Dependency updates | Added by Dependabot and by the labeler. Release notes: Dependencies. |
| `skip-changelog` | Leave out of generated release notes | A maintainer adds it to a pull request that should not be listed, such as a release preparation. |

## Where labels come from

- **Issue forms** add a type label and `triage`. The bug report form adds `bug`, the feature request form `enhancement`, the documentation form `documentation`, the compliance form `compliance`, the agent behavior form `agent-behavior`, and the "Spawn changed" form `upstream:spawn`. The Ideas form in Discussions adds `discussion`. Every label a form adds is in the list above.
- **The labeler workflow** reads the file names a pull request changes and adds the `area:*` labels, `dependencies`, `compliance` and `security`. It never adds `bug`, `enhancement` or `breaking-change`, because only a person can judge those. The patterns are in [`.github/labeler.yml`](../../.github/labeler.yml).
- **Maintainers** add everything else by hand during triage.

The labels also sort the release notes, which GitHub generates from merged pull requests. [`.github/release.yml`](../../.github/release.yml) puts each pull request under the first heading it matches:

| Heading in the release notes | Label |
| --- | --- |
| Security | `security` |
| Breaking changes | `breaking-change` |
| Features | `enhancement` |
| Fixes | `bug` |
| Compliance and licensing | `compliance` |
| Documentation | `documentation` |
| Dependencies | `dependencies` |
| Other changes | any other label |

Pull requests labeled `skip-changelog` are left out. [Releasing](../contributing/releasing.md) has the rest of the release process.

Labels and the fields on the public [project board](project-board.md) say the same things in two places. Priority, area, kind and "upstream impact" appear in both. Today a maintainer sets both by hand, and no automation keeps them in step.

## How an issue moves from "new" to "done"

1. **New.** You open an issue with a form. The form adds a type label and `triage`. On the project board the item gets the status Triage.
2. **First look.** A maintainer or reviewer reads it, thanks you, and checks whether it already exists. They set the area, and a priority if it is work we mean to do. They remove `triage`. If it is a question, they point you to Discussions. If it is a vulnerability, they move it to a private report and ask you to follow [SECURITY.md](../../SECURITY.md). If it repeats another item, they close it with `duplicate` and a link.
3. **Waiting for you.** If we need something, we add `needs-info` or `needs-reproduction` and ask one clear question. We remind you once after 14 days. If there is still no answer 30 days after the reminder, a person closes it with a kind note that says you can reopen it at any time. We have no bot that closes items for us.
4. **Accepted.** The item stays open, with its priority and area. On the board it is in Backlog. When it is clear what to change, where, and how to check it, it moves to Ready. It may get `help wanted`, `good first issue` or `mentor-available`. If we plan it for a release, a maintainer sets the board's Target release field.
5. **In progress.** Someone says in a comment that they would like to take it, and a maintainer assigns it to them. If they go quiet for 30 days, we ask whether someone else can take it. Taking an issue never locks anyone out of helping with it.
6. **In review.** A pull request is opened with `Closes #123` in the description. A reviewer asks questions first. [CONTRIBUTING.md](../../CONTRIBUTING.md) says what review checks.
7. **Done.** The pull request is merged, the issue closes by itself, and the board moves it to Done. The change appears in the release notes under the heading its label picks, and in [CHANGELOG.md](../../CHANGELOG.md) if people who use the kit will notice it.

Some items leave early. We close an item as `duplicate`, `invalid` or `wontfix` with a clear reason every time, never in silence. `blocked` items wait with a note saying what they wait for.

## How fast we aim to answer

These are goals, because we are a small team. They are not promises. They match the goals in [CONTRIBUTING.md](../../CONTRIBUTING.md) and [SECURITY.md](../../SECURITY.md).

| What | Our goal |
| --- | --- |
| A first reply to a new issue or pull request | Within about 7 days. After 14 days, a polite nudge is welcome. |
| Looking through the Triage inbox | A maintainer looks at least once a week |
| A security report | Acknowledged within 3 business days. See [SECURITY.md](../../SECURITY.md). |
| Items labeled `security` or `compliance` | Looked at before other items |
| Items waiting for information (`needs-info`, `needs-reproduction`) | One reminder after 14 days, then a kind close 30 days later if there is no answer |
| The monthly check of Spawn's terms | An issue opens by itself on the first of each month. See [releasing](../contributing/releasing.md#the-monthly-check-of-spawns-terms). |

## How we write good first issues

A good first issue is a small, kind introduction to the project. We write each one so that a newcomer can finish it without guessing, and we keep a few open at a time (three to five), so that the label stays true. An item with the label that nobody has looked after in months is worse than no label.

Every good first issue should:

- **Be small.** Something a newcomer can finish in an hour or two, in one file or a few.
- **Be self-contained.** No Spawn account, no token and no big design decision.
- **Say exactly where.** Name the file and the section, and link to it.
- **Say what "done" looks like,** in a sentence or two.
- **Say how to check it.** Usually `bash scripts/lint.sh`, which runs the linters and the tests.
- **Say who can help.** The `mentor-available` label means a maintainer will answer questions in the thread and review it closely.
- **Explain the why,** so the task feels meaningful.

It is reserved for people who are learning. Our own agent accounts do not take these items, and if you use an agent, we ask you to leave them for people who are learning too.

A good one looks like this:

```text
Title: [Docs] Make the quick-start example command easier to copy

Why: A new reader tried the command in step 3 and it failed, because the
placeholder looks like a real value.

Where: docs/getting-started.md, the section "Start the listener".

What done looks like: The placeholder is clearly marked, and one sentence
says what to put there.

How to check: Run `bash scripts/lint.sh`. It also checks the links.

Help: A maintainer will answer questions here (label: mentor-available).
No Spawn account or token is needed.
```

## What the AI labels mean

We build this project with AI agents and welcome AI-assisted work, and the five AI labels are not penalties. They are notes that help us sort things and a way to start a friendly conversation.

- `ai-assisted` and `agent-authored` only describe. The first thanks you for saying that a tool helped. The second marks items opened by our own agent accounts, so that readers know.
- `needs-human-explanation`, `hard-to-review` and `ai-disclosure-missing` are first steps in a kind conversation. A maintainer adds one with a note that links to [the policy](../contributing/ai-assisted-contributions.md#when-something-goes-wrong). The item stays open. You get a chance to explain or fix the gap, and we remove the label when you do.
- A label never closes anything by itself, and nobody is blocked because of one. We do not keep a public list of people. Honest disclosure is never held against you. Hiding AI use on purpose is what we treat as a problem, under the [Code of Conduct](../../CODE_OF_CONDUCT.md).
- We use `hard-to-review` rarely. It means that an item is hard to review as it was sent, for example a very large generated change that nobody has read, and that a smaller change or a short explanation would help. It is a note about the change and not about you.

## Where this comes from

We grouped our labels so they are easy to scan, and we describe every one in [`.github/labels.tsv`](../../.github/labels.tsv). The set is bigger than some projects keep (when we looked on 2026-11-17, CC Switch had 24 labels and goose 13), so we may drop labels that nobody uses. The Model Context Protocol project asks its SDK repositories to use a standard set of type, status and priority labels with priorities P0 to P3 ([SDK tiers](https://modelcontextprotocol.io/community/sdk-tiers), read 2026-11-17), and our priority labels follow that idea. We also make sure every label that a form adds exists, because one project we looked at had a form whose label did not exist in its repository ([issue forms](https://github.com/modelcontextprotocol/modelcontextprotocol/tree/main/.github/ISSUE_TEMPLATE), read 2026-11-17). We keep the `good first issue` label curated because, when we looked on 2026-11-17, it had two or fewer open items in the main repositories of [OpenClaw](https://github.com/openclaw/openclaw/labels), [OpenCode](https://github.com/anomalyco/opencode/labels), [Everything Claude Code](https://github.com/affaan-m/ECC/labels) and [CC Switch](https://github.com/farion1231/cc-switch/labels), which leaves beginners few visible places to start. The full comparison is in [the community patterns digest](../research/oss-community-patterns-2026.md).

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
