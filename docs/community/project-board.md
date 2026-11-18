# The project board

This page is for contributors who want to see how the SDLCA agent kit's work is planned, and for the maintainers who run the board. It explains what the public GitHub Project holds, what its fields, statuses, workflows and views mean, and how an idea becomes planned work.

The board is a planning and triage tool, not a promise. It is also not a place to ask for help. For that, see [SUPPORT.md](../../SUPPORT.md).

## What it is

The board is a public GitHub Project called "SDLCA agent kit: roadmap and triage". It belongs to the `kdtix-open` organization, it is linked to this repository, and its description says it is unofficial and not affiliated with Spawn. You can find it on the organization's [projects page](https://github.com/orgs/kdtix-open/projects). It holds only public issues and pull requests, so nothing private is on it.

Maintainers create the Project with the script `scripts/setup-project.sh`. The script makes the Project and its fields. The script does not create the views, the Status options or the built-in workflows, so maintainers set those up by hand. The steps are in [GitHub settings for maintainers](../maintainers/github-settings.md). Where the board and this page disagree, the board shows what is really set. If you spot a difference, please tell us so we can fix this page.

You do not need to touch the board. Maintainers move items. If you want to say something about an item, comment on the issue instead.

## Fields

The script creates these fields. Each one says the same thing as a label, except Size and Target release.

| Field | Type | Options | Mirrors |
| --- | --- | --- | --- |
| Priority | Single select | P0, P1, P2, P3 | the `priority:p0` to `priority:p3` labels |
| Area | Single select | runtime, worlds, slack, providers, install, templates, docs, ci, tests | the `area:*` labels |
| Kind | Single select | Bug, Feature, Docs, Compliance, Agent, Task | the issue forms (Agent is the agent behavior problem) and the `task` label |
| Size | Single select | XS, S, M, L, XL | nothing. A rough guess of effort |
| Upstream impact | Single select | None, Spawn change, Spawn terms | the `upstream:spawn` label |
| Target release | Text | Free text, such as `0.1.0` or `Later` | nothing. Release planning |

Size is a guess and not a contract. As a rule of thumb, an item that fits a `good first issue` is XS or S, and an XL item should be split into smaller ones before it is ready to pick up. A label and its field are set by hand today, and no automation keeps them in step. [Triage and labels](triage-and-labels.md) explains the labels.

## Status

GitHub adds a built-in Status field. Maintainers set its options by hand to these six:

| Status | What it means |
| --- | --- |
| Triage | New. A person has not looked at it yet. |
| Backlog | Accepted, but not yet ready to pick up. It is not a promise to do it. |
| Ready | It is clear what to change, where, and how to check it. Someone can take it. |
| In progress | Someone is working on it. |
| In review | A pull request is open and being reviewed. |
| Done | Finished. Closed or merged. |

## Workflows

The Project has built-in workflows, which maintainers switch on by hand. The names below are how GitHub showed them on 2026-11-17, and they may change:

- **Auto-add to project** adds new issues and pull requests from this repository.
- **Item added to project** sets Status to Triage.
- **Item closed** and **Pull request merged** set Status to Done.
- **Item reopened** sets Status to Backlog.

## Views

Maintainers create five views. They are our proposals, and we change them as we learn what we use.

| View | Layout | Shows | Why it exists |
| --- | --- | --- | --- |
| Triage inbox | Table | Open items with the `triage` label | Everything that needs a first look. We aim to reply within about 7 days. |
| Board by status | Board | Everything, in columns by Status | The daily picture of the work. |
| Roadmap by target release | Table | Everything, grouped by Target release and sorted by Priority | What is planned for which release. It is a grouped table, not a chart with dates, because we do not use dates. |
| Good first issues | Table | Open items with the `good first issue` label, grouped by Area | A ready list for newcomers. |
| Upstream (Spawn) watch | Table | Open items with the `upstream:spawn` label, grouped by Upstream impact | Everything that depends on something Spawn does. We open it during the monthly check of Spawn's terms. |

## How a proposal becomes work

1. **An idea starts in Discussions.** Someone posts it in the Ideas category. It may be rough. See [feedback and ideas](feedback-and-ideas.md).
2. **If it seems worth doing, it becomes an issue.** The author, or a maintainer, opens one with the feature request form. The Project adds it with the status Triage.
3. **A maintainer takes a first look.** They set Kind, Area and Priority, and Size and Upstream impact when they can. If the idea needs design talk, it keeps the `discussion` label and stays in Triage while people comment. A proposal stays open for at least 7 days before a maintainer decides. [GOVERNANCE.md](../../GOVERNANCE.md) explains why.
4. **The outcome is written down.** If it is accepted, the status becomes Backlog. If the answer is "not now" or "no", the issue says why, and it is closed or parked. [How we say no](feedback-and-ideas.md#how-we-say-no) explains how.
5. **It becomes Ready.** When the scope is clear and there is a way to check the result, the status becomes Ready. This step is the gate. We do not ask people to start on something that is still a question. A maintainer may add `help wanted`, `good first issue` or `mentor-available`.
6. **Someone takes it.** The status moves to In progress, then In review once a pull request is open, then Done when it is merged.
7. **It may get a target release.** If we plan to include it in a release, a maintainer writes that release in the Target release field. That is a goal and not a promise. The [roadmap](roadmap.md) lists what is planned and what is not.

## Where this comes from

The statuses follow a common shape. The goose project, for example, keeps a public board whose statuses run from an inbox, through "Needs info", "Accepted / design" and "Ready", to "Done", and it asks outside contributors to wait until an issue is Ready before they send a pull request ([goose CONTRIBUTING.md](https://github.com/aaif-goose/goose/blob/main/CONTRIBUTING.md), read 2026-11-17). We use fewer statuses, and keep the Ready step. We also publish our board because one project we studied has no public roadmap, board or milestones, which leaves contributors unable to see its priorities ([CC Switch](https://github.com/farion1231/cc-switch), read 2026-11-17). The full comparison is in [the community patterns digest](../research/oss-community-patterns-2026.md).

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
