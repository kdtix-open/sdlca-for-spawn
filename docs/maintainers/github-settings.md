# GitHub settings for maintainers

This page is for the people who run the `kdtix-open/sdlca-for-spawn` repository on GitHub. It lists every repository setting and security feature the project relies on, shows how to apply each one (a script does most of it), explains the labels, the branch rules, the Discussions categories and the public Project, and gives you a checklist to work through before you announce the project. It also says what to do if a token leaks.

**Last reviewed: 2026-11-17.** Please update this page in the same pull request whenever you change a setting, a label or a file in `.github/`.

## Where things stand

The repository already exists on GitHub and is public. Our research on 2026-11-17 found it empty: no commits, Discussions switched off, every security feature switched off, and only GitHub's nine default labels. So at that point nothing below had been applied. Check the current state before you rely on this page. The "before you announce" list at the end is about what remains before you announce the project; the repository itself is already public. If the repository is pushed before step 2 below has been run, the links in the README, SUPPORT.md, the issue chooser and the issue forms that lead to Discussions, private vulnerability reporting and the labels do not work until it has.

GitHub changes its settings pages often. The names below are the ones we know. If a name on your screen differs, trust the screen and tell the other maintainers so this page can be fixed.

## What you need

- Admin rights on the repository, and the [GitHub CLI](https://cli.github.com/) (`gh`) signed in as that person (`gh auth login`).
- For the Project: the `project` scope on your token (`gh auth refresh -s project`) and permission to create Projects in the `kdtix-open` organization.
- A clone of this repository. Run the scripts from its root.

Both scripts print what they would do and change nothing until you add `--apply`. A dry run prints the same `gh` commands that `--apply` runs, so read it first. Each script's header comment is the source of truth for its options (`bash scripts/setup-github.sh --help`).

## Set it up in this order

On an empty repository the order matters, because the branch rules need pull requests and a pull request needs a branch to aim at.

1. **Read the plan.** `bash scripts/setup-github.sh --repo kdtix-open/sdlca-for-spawn`
2. **Apply the settings, without the ruleset.** `bash scripts/setup-github.sh --repo kdtix-open/sdlca-for-spawn --apply`. This turns on secret scanning and push protection first, before anything is pushed. If GitHub refuses a step (for example on an empty repository), the script carries on with the other steps, lists what it could not do and exits with status 1. Do not push until secret scanning and push protection are on: if either was refused, turn it on by hand (Settings, in the code security section). After the first push, run the script again for the steps that were refused. It is safe to run again.
3. **Make the first commit, scan, then push it to `main`.** Make the first commit with an `Assisted-by: <tool> <model>` trailer (a `Co-Authored-By` line may be added but does not replace `Assisted-by`). If you make it yourself, use `git commit -s`. An AI agent never adds the sign-off, even when a maintainer asks it to make the commit: the maintainer reads the result and signs it off afterwards (`git rebase --root --signoff`, then `git push --force-with-lease`; rewriting history is safe only while nobody has cloned or forked the repository), or records that the first commit has no sign-off. Set the public identity first (`git config user.name` and `user.email`, with your GitHub no-reply address), and before you push check what the history will show: `git log --format='%an <%ae> | %cn <%ce>' | sort -u` must list only the identity you intend. A commit's name and email become public for good. A trailer such as `Co-Authored-By` can carry an address too, so also run `git log --format=%B | grep -iE '^(co-authored-by|signed-off-by|assisted-by):' | sort -u`. Then run `bash scripts/check-secrets.sh` and read `git status --short --ignored` (see the checklist below). A maintainer pushes; the script does not. Before you push, read the first item under "Spawn and the name" in the checklist at the end: the naming decision can wait until just before the announcement, but it is the one checklist item worth doing before the first push.
4. **Wait for the first CI run on `main`.** The check "Lint and test" should pass.
5. **Apply the ruleset.** `bash scripts/setup-github.sh --repo kdtix-open/sdlca-for-spawn --apply --ruleset`. If a ruleset named `main` exists, the script updates it instead of making a copy.
6. **Do the manual steps** in the sections on Discussions and the Project below, and any step the script reported as refused.
7. **Create the Project.** `bash scripts/setup-project.sh` (dry run), then `bash scripts/setup-project.sh --apply`. It makes a new Project every time, so it stops if one with the same title exists. If a run stops half way, finish the Project with `--number <its number>`: nothing is created, and a field that exists is skipped. Only an organization owner can make a Project public. If the account that runs the script is a member, the script leaves the Project private, says so, and an owner makes it public afterwards (the Project's settings, Visibility).
8. **Work through the "before you announce" checklist.**

## Repository settings

`scripts/setup-github.sh` applies the rows marked "script". The rows marked "manual" are done by hand: for some of them (the Discussions categories, the social preview image) we know of no API, and the others we have not scripted.

| Setting | Value | Why | Applied by |
| --- | --- | --- | --- |
| Description | "Unofficial starter kit for directing AI coding agents on Spawn from chat. Not affiliated with Spawn." | The first line anyone sees in search results and link previews says "unofficial". | script |
| Website (About box) | Empty, or a link to our docs. Never www.spawn.co. | A Spawn address would suggest this is Spawn's page. | manual |
| Topics | `ai-agents`, `agentic`, `developer-tools`, `multiplayer-games`, `starter-kit`, `unofficial` | Few and factual. No topic contains a vendor's name or Spawn's name: the description already says "on Spawn", and [trademarks and credits](../compliance/trademarks-and-credits.md) lists vendor names in topic lists as something we do not do. `unofficial` is a cheap visible notice. A topic for the Slack bridge waits until it ships (it is planned, not built), and a maintainer decides then. The script replaces the whole list, so topics added by hand are lost. | script |
| Issues | On | Bug reports and tracked work. Blank issues are off; the forms in `.github/ISSUE_TEMPLATE/` are used. | script |
| Discussions | On | Questions, ideas and show and tell. The categories are a manual step. | script, then manual |
| Projects | Left as GitHub has it | The public Project is an organization Project that `scripts/setup-project.sh` links to this repository (see below). The script does not change the repository's own Projects switch. If the Projects tab does not show after linking, turn Projects on in Settings > General > Features. | manual, only if needed |
| Wiki | Off | Docs live in `docs/`, where a pull request reviews every change. | script |
| Merge methods | Squash only. Merge commits and rebase merges are off. | One commit per pull request, and the pull request title becomes its subject (as [CONTRIBUTING.md](../../CONTRIBUTING.md) says). | script |
| Squash commit message | Title from the pull request title, body from the commit messages | Keeps the `Signed-off-by` and `Assisted-by` lines of the individual commits. See the note below the table. | script |
| Auto-merge | Off | The [AI policy](../contributing/ai-assisted-contributions.md) says no agent merges. A person can switch it on later if the team wants it. | script |
| Delete branch on merge | On | Keeps the branch list short. | script |
| Web commit sign-off | Required | A commit made in this repository's GitHub web editor then carries a `Signed-off-by` line, in line with our sign-off rule. We have not verified that it applies to a contributor's own fork, so [CONTRIBUTING.md](../../CONTRIBUTING.md) tells people who edit in the browser to add the line themselves. It does not affect commits made with git on a computer; those need `git commit -s`. | script |
| Actions token | Read-only by default, and Actions may not approve pull requests | Our workflows ask for the access they need, in the file. No automation can stand in for the human approval the ruleset asks for. | script |
| Actions approval for outside contributors | Require approval for all external contributors | A person must click "Approve and run" before a workflow runs for a pull request from a fork. Project agent accounts are outside contributors (see the agent accounts section). The AI policy's promise that CI on agent pull requests waits for a person depends on this. In the web page it is under Settings > Actions > General. | script (if GitHub refuses the call, the script says so: set it by hand) |
| Dependabot alerts | On | Tells us about known problems in dependencies. | script |
| Dependabot security updates | On | Opens a pull request for a fix. | script |
| Dependabot version updates | Weekly, for GitHub Actions and Bun packages | Set in [`.github/dependabot.yml`](../../.github/dependabot.yml). It starts when that file is on `main`. It waits 7 days (a cooldown) before it proposes a new release. It does not update the Bun version pinned in `ci.yml`: raise that by hand, and run `bun install` so `bun.lock` stays in step. | file |
| Secret scanning | On | Alerts on known token formats in the repository. | script |
| Push protection | On | Blocks a push that contains a known token format. | script |
| Private vulnerability reporting | On | Lets people report a vulnerability privately. [SECURITY.md](../../SECURITY.md) and the issue forms point to it. | script |
| Code scanning | Not set up | Optional, and only after the first push, because there must be code to analyze. In Settings, in the code security section, find Code scanning and choose the default setup. GitHub proposes the languages it finds; we expect Python and GitHub Actions (our workflows), and perhaps JavaScript for `lib/shot.mjs`. If you turn it on, say so in this table. | manual |
| Sponsor button | None | See the funding section. | no file |
| Social preview image | GitHub's default, or an image we made ourselves | No vendor logos, and nothing that looks like Spawn's or Savi's art. | manual |

**The squash note.** With these settings the squash commit's subject is the pull request title, and its body lists each commit's message. So a sign-off or `Assisted-by` line from a commit ends up in the body, but not necessarily in the last paragraph that git tools read as trailers. We have not checked how GitHub lays it out. Look at the first squash-merged commit on `main`. If the trailers are missing from the end, add them by editing the message in the merge box. For a pull request from a project agent account (Mode B in the AI policy), the merging maintainer adds their own `Signed-off-by` there.

Labels are applied by the same script and have their own section below. The script never deletes a label it does not know about.

## Security features

| Feature | What it does | How to check it |
| --- | --- | --- |
| Secret scanning | GitHub looks for secrets in formats it knows and raises an alert. | Security tab > Secret scanning. |
| Push protection | Stops a push that contains such a secret. A person can bypass it by giving a reason, so look at bypasses in the alerts. | Settings, in the code security section. |
| Dependabot alerts and security updates | Warn about vulnerable dependencies and open fix pull requests. | Security tab > Dependabot. |
| Private vulnerability reporting | Opens a private channel between a reporter and the maintainers, at `https://github.com/kdtix-open/sdlca-for-spawn/security/advisories/new`. | Security tab > Advisories shows a "Report a vulnerability" button to outsiders. |

Two limits to know about:

- **GitHub does not know Spawn's token formats** as far as we can tell. `scripts/check-secrets.sh` looks for Spawn tokens and invite codes (`sak_...`, `sbk_...`) and for other common token shapes. `bash scripts/lint.sh` runs it, so CI does too. If GitHub offers custom secret-scanning patterns for this repository, adding patterns for those two prefixes would be a good follow-up.
- **The alerts reach only people who are set to receive them.** Make sure at least two maintainers watch the repository for security alerts, and that nobody relies on a single person's inbox.

Dependabot pull requests carry no `Signed-off-by` line, because a bot made them. A maintainer who merges one is responsible for it like any other change.

## Labels

[`.github/labels.tsv`](../../.github/labels.tsv) is the only list of labels. `scripts/setup-github.sh` reads it and creates each label, or updates it if the name already exists (this also rewrites GitHub's nine default labels to our colors and descriptions). To rename a label, change the file, run the script, and delete the old label by hand. The tables below repeat the file; if they ever differ, the file is right and this page needs fixing.

Contributors read the shorter version in [triage and labels](../community/triage-and-labels.md). The labeler workflow adds the `area:*` labels, `dependencies`, `compliance` and `security` to pull requests from the names of the files they change. See [`.github/labeler.yml`](../../.github/labeler.yml) for the exact patterns. It never adds `bug`, `enhancement` or `breaking-change`; a maintainer does that.

### Type

| Label | Color | What it means | How it is used |
| --- | --- | --- | --- |
| `bug` | `d73a4a` | Something is not working | The bug report form adds it. Release notes: Fixes. |
| `enhancement` | `a2eeef` | A new feature or an improvement | The feature request form adds it. Release notes: Features. |
| `documentation` | `0075ca` | Improvements or additions to documentation | The documentation form adds it. Release notes: Documentation. |
| `question` | `d876e3` | A question; usually better asked in Discussions | A maintainer adds it, then points the person to Discussions. |
| `task` | `0052cc` | A discrete unit of work | A maintainer adds it to planned work that did not come from a report. |
| `security` | `b60205` | Security-relevant; never put exploit details in a public issue | A maintainer adds it; the labeler adds it for `SECURITY.md` and the security model. Release notes: Security. |
| `compliance` | `0e8a16` | Spawn terms, licensing, attribution or acceptable-use matter | The compliance form and the monthly reminder add it; the labeler adds it for license and compliance files. Release notes: Compliance and licensing. |
| `agent-behavior` | `5319e7` | An AI agent acted wrongly, unsafely or against policy | The agent behavior form adds it. |
| `breaking-change` | `b60205` | Changes behavior that people may rely on | A maintainer adds it to pull requests. Release notes: Breaking changes. |

### Priority

| Label | Color | What it means | How it is used |
| --- | --- | --- | --- |
| `priority:p0` | `B60205` | Highest priority work item | A maintainer sets it in triage. The Project field Priority uses P0 to P3. |
| `priority:p1` | `B60205` | High priority work item | As above. |
| `priority:p2` | `FBCA04` | Medium priority work item | As above. |
| `priority:p3` | `1D76DB` | Lower priority work item | As above. |

### Triage and status

| Label | Color | What it means | How it is used |
| --- | --- | --- | --- |
| `triage` | `ededed` | Needs a maintainer to look at it | Every issue form adds it. A maintainer removes it after the first look. |
| `needs-info` | `d876e3` | Waiting for more information from the reporter | A maintainer adds it and waits for the reporter. |
| `needs-reproduction` | `fef2c0` | Needs steps or input that reproduce the problem | A maintainer adds it when a bug report cannot be reproduced yet. |
| `blocked` | `b60205` | Cannot proceed until something else is resolved | A maintainer adds it to the item that is stuck. |
| `blocks` | `ee0701` | Other work is waiting on this | A maintainer adds it to the item others wait on. |
| `duplicate` | `cfd3d7` | This already exists | A maintainer adds it when closing. |
| `invalid` | `e4e669` | This does not seem right | A maintainer adds it when closing. |
| `wontfix` | `ffffff` | This will not be worked on | A maintainer adds it when closing. |

### Community

| Label | Color | What it means | How it is used |
| --- | --- | --- | --- |
| `good first issue` | `7057ff` | Good for newcomers | A maintainer adds it to a small, well-described item. Reserved for people who are learning. |
| `help wanted` | `008672` | Extra attention is welcome | A maintainer adds it when outside help is especially welcome. |
| `mentor-available` | `7057ff` | A maintainer will guide a first-time contributor through this | A maintainer adds it when they will guide a first-time contributor. |
| `discussion` | `d876e3` | Needs design discussion; open-ended topics belong in Discussions | The ideas discussion form adds it. A maintainer adds it to issues that need design talk first. |

### Area

| Label | Color | What it means | How it is used |
| --- | --- | --- | --- |
| `area:runtime` | `c5def5` | Listener, handler, routing, cursor, locks (bin/, lib/) | The labeler adds it to pull requests; a maintainer adds it to issues. |
| `area:worlds` | `c5def5` | World registry, clones, renames | As above. |
| `area:slack` | `c5def5` | Slack bridge and manifest | As above. |
| `area:providers` | `c5def5` | Agent command and provider integrations | As above. |
| `area:install` | `c5def5` | Install script, systemd, onboarding | As above. |
| `area:templates` | `c5def5` | Prompt, runtime guide and example files | As above. |
| `area:docs` | `c5def5` | Documentation | As above. |
| `area:ci` | `c5def5` | Workflows, linting and tests infrastructure | As above. |
| `area:tests` | `c5def5` | Tests and test tooling | As above. |

### Spawn

| Label | Color | What it means | How it is used |
| --- | --- | --- | --- |
| `upstream:spawn` | `fbca04` | Depends on, or is caused by, something on the Spawn platform | The Spawn change form adds it. It feeds the Upstream (Spawn) watch view of the Project. |

### AI policy

These five come from the [AI policy](../contributing/ai-assisted-contributions.md). A maintainer applies them by hand, with a friendly note and a link to the policy. No workflow applies them yet.

| Label | Color | What it means | How it is used |
| --- | --- | --- | --- |
| `ai-assisted` | `bfd4f2` | The pull request or issue discloses AI assistance | A maintainer adds it by hand. No workflow adds it yet. |
| `agent-authored` | `bfd4f2` | Opened by one of the project agent accounts | A maintainer adds it by hand to items opened by a project agent account. |
| `needs-human-explanation` | `d93f0b` | The author is asked to explain the change in their own words | A maintainer adds it, with a friendly note, under the AI policy. |
| `hard-to-review` | `ededed` | Hard to review as sent: please make it smaller or explain it | A maintainer adds it, with a friendly note, when a change is too big or too hard to follow as sent. See the AI policy. |
| `ai-disclosure-missing` | `fbca04` | AI involvement is evident but not disclosed | A maintainer adds it, with a friendly note, under the AI policy. |

### Automation and release notes

| Label | Color | What it means | How it is used |
| --- | --- | --- | --- |
| `dependencies` | `0366d6` | Dependency updates | Dependabot and the labeler add it. Release notes: Dependencies. |
| `skip-changelog` | `ededed` | Leave out of generated release notes | A maintainer adds it to leave a pull request out of generated release notes. |

## The ruleset for main

[`.github/rulesets/main.json`](../../.github/rulesets/main.json) holds the branch rules for the default branch.

**It is not applied by default.** `scripts/setup-github.sh` creates it only when you pass `--ruleset`, so a plain run changes settings but does not protect `main`. Apply it after the first push (see the order above).

| Rule | What it means | Why |
| --- | --- | --- |
| Applies to | The default branch (`~DEFAULT_BRANCH` in the file). Enforcement is "active". | The rules follow the default branch if it is ever renamed. |
| Restrict deletions | Nobody can delete `main`. | A deleted branch is hard to recover. |
| Block force pushes | History on `main` cannot be rewritten by a push. | Tags, releases and everyone's clones depend on stable history. |
| Require a pull request | Every change goes through a pull request with one approving review. New commits dismiss earlier approvals. Every review conversation must be resolved. | A second pair of eyes sees the final version, and questions do not get lost. |
| Code owner review | Not required. | There is no CODEOWNERS file (see below). |
| Approval of the last push | Not required. | With one maintainer, requiring it would block every merge. Turn it on once two maintainers can review each other. |
| Required status check | The check named **Lint and test** must pass. | It is the job in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) that runs `bash scripts/lint.sh`: linters, link and secret checks, and the tests. |
| Up to date with `main` | Not required. | Fewer reruns for a small team. Change it if `main` starts breaking after merges. |

**The check name must match exactly.** The ruleset looks for a check called "Lint and test", which is the `name:` of the job in `ci.yml`. If you rename that job, change `main.json` too and run the script with `--ruleset --apply`, or every pull request waits forever for a check that never reports.

**The bypass actor.** The file lists one: the repository role Admin (`actor_id` 5), with the mode "pull request". That means an admin can merge a pull request that does not meet the rules, but cannot push straight to `main`. It exists because a project with a single maintainer cannot give itself a second approval. While there is only one maintainer, the bypass is how that person merges, so the "approved by someone who is not the author" rule in the AI policy is only as strong as the maintainers' habits. When a second maintainer joins, set `"bypass_actors": []` in the file, turn on approval of the last push, and run the script again.

**Not covered by the ruleset today:** signed commits, a DCO check (planned; see the [roadmap](../community/roadmap.md)), tag protection, and a merge queue. A rule on tags named `v*` that blocks deletion and moving would fit [the release practice](../contributing/releasing.md), and could be added as a second ruleset.

**Changing it.** Edit `main.json`, open a pull request, and after it merges run `bash scripts/setup-github.sh --repo kdtix-open/sdlca-for-spawn --apply --ruleset`. The script updates the existing ruleset. A rewrite of history on `main` needs the ruleset switched off for a short time, which is one more reason to decide it together.

## Actions approval and agent accounts

The [AI policy](../contributing/ai-assisted-contributions.md) holds the project's own agent accounts to rules that need GitHub settings behind them. This table connects each rule to its setting.

| Rule in the policy | The setting behind it | Where |
| --- | --- | --- |
| An agent account cannot approve or merge. | Give it the Read or Triage role at most, never Write or Admin, and let it work from a fork. As we understand GitHub's rules, only approvals from people with write access count toward the required review. If you give an agent account Write so it can push branches here, its approval could count, and CI would no longer wait for approval, so decide that on purpose and write it down. Auto-merge is off, and Actions may not approve pull requests. | Settings > Collaborators and teams, plus the script. |
| CI on its pull requests waits for a person. | Outside contributors need approval before workflows run. | The script, or Settings > Actions > General. |
| No admin rights. | No bot or agent account holds the Admin role. Review the collaborator list now and at every release. | Settings > Collaborators and teams. |
| At most three open pull requests per account. | GitHub has no setting for this. Maintainers count by hand. | None. |
| Reserve switches for a flood of low-quality items. | Temporary interaction limits (for example, only collaborators or prior contributors may comment or open issues). | Settings > Moderation options. |
| Trailers survive the squash. | See the squash note above. Check it after the first merge. | The merge box. |

Name agent accounts after the project (SDLCA). Do not start a name with Spawn, Savi, Claude or another vendor's name. This goes for GitHub accounts and for local account names. The kit's own examples follow it: the Slack manifest uses `sdlca-agent` for the bot, and the tests use a local account called `sdlca-for-spawn`. A name like that follows the "for Spawn" pattern and still contains the word, so mention it in the question you put to Spawn (see the checklist).

## Discussions

Turning Discussions on is a script step (`gh repo edit --enable-discussions`). We know of no API for creating categories, so that part is manual.

When Discussions is first turned on, GitHub offers to set up its default categories. As we know them, they are these six. Our three templates in [`.github/DISCUSSION_TEMPLATE/`](../../.github/DISCUSSION_TEMPLATE/) match three of them.

| Category | Format | Template | Use |
| --- | --- | --- | --- |
| Announcements | Only maintainers start threads | none | Releases and project news. |
| General | Open-ended | none | Anything that fits nowhere else. |
| Ideas | Open-ended | `ideas.yml` | Early ideas. The template adds the `discussion` label. |
| Polls | Poll | none | Quick votes. |
| Q&A | Question and answer | `q-a.yml` | Questions, with a marked answer. |
| Show and tell | Open-ended | `show-and-tell.yml` | What people built or learned. |

GitHub matches a template to a category by file name, which must equal the category's slug: `ideas`, `q-a` and `show-and-tell`. If you rename a category, its slug may change and the template silently stops applying. Rename the file to match.

Manual steps:

1. Open the Discussions tab. If GitHub shows a setup page, accept the default categories and its welcome post.
2. Check that the six categories above exist. Edit them from the pencil icon beside "Categories" on the Discussions page. Add or remove categories only if the team agrees, and keep the three template names in step.
3. Write a short, warm pinned post in General or Announcements that says who the project is for, links [the welcome page](../community/welcome.md) and [where to ask what](../../SUPPORT.md), and says plainly that the project is unofficial.
4. Open each category's "New discussion" form once and check that the template shows.

## The Project

`scripts/setup-project.sh` creates one public Project for the `kdtix-open` organization, titled "SDLCA agent kit: roadmap and triage", gives it a short description that says it is unofficial, and links it to `kdtix-open/sdlca-for-spawn`. It uses `gh project`, so it needs the `project` scope. Options are `--owner`, `--repo`, `--title`, `--number` and `--apply`.

It creates these fields:

| Field | Type | Options | Mirrors |
| --- | --- | --- | --- |
| Priority | Single select | P0, P1, P2, P3 | the `priority:p0` to `priority:p3` labels |
| Area | Single select | runtime, worlds, slack, providers, install, templates, docs, ci, tests | the `area:*` labels |
| Kind | Single select | Bug, Feature, Docs, Compliance, Agent, Task | the issue forms and the `task` label |
| Size | Single select | XS, S, M, L, XL | a rough effort guess |
| Upstream impact | Single select | None, Spawn change, Spawn terms | the `upstream:spawn` label |
| Target release | Text | free text, for example `0.1.0` or `Later` | release planning; see [releasing](../contributing/releasing.md) |

GitHub adds a built-in Status field. Its default options are not ours.

[The project board](../community/project-board.md) explains to contributors how proposals become work.

### Manual steps for the Project

We have not scripted these. GitHub may offer API calls for views and for a field's options, and we know of no API for the built-in workflows. Menu names may differ from what is written here.

1. **Status options.** Edit the Status field and set its options to: Triage, Backlog, Ready, In progress, In review, Done.
2. **Built-in workflows.** In the Project's menu, open Workflows and turn these on, as they are named when we write this: "Auto-add to project" for `kdtix-open/sdlca-for-spawn` (issues and pull requests); "Item added to project", which sets Status to Triage; "Item closed" and "Pull request merged", which set Status to Done; and "Item reopened", which sets Status to Backlog.
3. **Views.** Create the five views below. These are our proposals; change them as you learn what you use.
4. **Visibility.** If the script said it could not make the Project public, an organization owner sets it: open the Project, then Settings, then Visibility, and choose Public. Until then only the organization's members can see it.

| View | Layout | Filter | Group and fields | Why |
| --- | --- | --- | --- | --- |
| Triage inbox | Table | `is:open label:triage` | Show Kind, Area, Priority, Upstream impact | Everything that needs a first look. We aim to reply within about 7 days (a goal from [CONTRIBUTING.md](../../CONTRIBUTING.md)). |
| Board by status | Board | none | Columns by Status; show Priority, Area, Size on the cards | The daily picture of the work. |
| Roadmap by target release | Table | none | Group by Target release; sort by Priority | What is planned for which release. GitHub's Roadmap layout draws bars from date or iteration fields, which this Project does not have, so use a grouped table. If grouping by a text field is not offered, use a milestone for each release and group by milestone. |
| Good first issues | Table | `is:open label:"good first issue"` | Group by Area; sort by Size | A ready list for newcomers. Keep three to five items here before you announce. |
| Upstream (Spawn) watch | Table | `is:open label:"upstream:spawn"` | Group by Upstream impact | Everything that depends on something Spawn does. Open it during the monthly check of Spawn's terms. |

## CODEOWNERS

**There is no CODEOWNERS file, on purpose. Do not add one yet.**

A CODEOWNERS file asks named people or teams to review changes to named paths. For that to work, each owner needs explicit write access to this repository. Our research on 2026-11-17 found that the organization teams named in the organization's own CODEOWNERS file have no access to this repository. A file naming them would request no reviews and would do nothing. The organization's file does not carry over to this repository either, because it lives in the organization's `.github` repository, and CODEOWNERS files are read per repository. That file also uses `!` to exclude paths, which GitHub's CODEOWNERS format does not support. Both points are from [GitHub's CODEOWNERS documentation](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners), as our research read it on 2026-11-17.

When you are ready:

1. Give a team, or named people, write access to the repository.
2. Add `.github/CODEOWNERS` with a catch-all line such as `* @kdtix-open/<team>`, and lines for the paths where a mistake costs most: `.github/`, `LICENSE`, `NOTICE`, `package.json`, `bun.lock`, `AGENTS.md`, `lib/route.py`, `lib/common.sh`, `bin/sdlca-on-chat` and `bin/sdlca-api`. Use no `!` lines.
3. Only then set `require_code_owner_review` to `true` in the ruleset, and only if at least two people own the paths. With a single owner, the author of a change would be the only person who could approve it, and nothing could merge without the bypass.

## Funding

**There is no `FUNDING.yml`, and nobody should add one without a decision by the maintainers.** A Sponsor button on an unofficial kit could suggest that the money goes to Spawn, or that Spawn endorses the project. The organization's own file, as our research read it, sits at the top of the organization's `.github` repository rather than inside a `.github` folder, so GitHub probably does not apply it here. We could not confirm that.

After the first push, open the repository page and check that no Sponsor button shows. If one does, the organization's default is being inherited; ask the organization owners to fix it. If the maintainers later decide to add funding, say plainly next to the link that gifts support KDTIX Open's maintainers and not Spawn, keep it out of the top of the README, and record the decision here.

## Branch and merge practice

Contributors work from forks, on branches named `type/issue-slug`, and never push to `main` (the ruleset enforces it). Every change is a pull request that is squash-merged, and the head branch is deleted afterward. The pull request title becomes the commit subject, so ask authors to write it in the `type(scope): summary` style from [CONTRIBUTING.md](../../CONTRIBUTING.md). Before you merge, give the pull request its labels (see [releasing](../contributing/releasing.md#release-notes-two-layers)), and check that the AI assistance section is filled in.

## Releases

How a release is cut is in [releasing](../contributing/releasing.md): Semantic Versioning, a `v0.1.0`-style tag on `main`, a draft release created by hand with `gh release create`, and notes generated from labels by [`.github/release.yml`](../../.github/release.yml). There is no release workflow yet. The settings that matter to releasing are the squash-merge rule (clean history), the ruleset (a green `main`), and the labels (the sections of the notes).

## Recurring checks

| When | What | Where |
| --- | --- | --- |
| Monthly, on the 1st (an issue opens by itself) | Re-verify Spawn's terms and rules. | See below, and [the rules we follow](../compliance/spawn-rules.md#how-we-re-check-every-month). |
| Every release | The release checklist, which includes a fresh Spawn check. We suggest adding a look at the collaborator list: no bot or agent account should hold the Admin role. | [releasing](../contributing/releasing.md) |
| Every six months (next by 2027-05-17) | Review the AI policy. | [AI-assisted contributions](../contributing/ai-assisted-contributions.md#how-this-policy-changes) |
| Every three months (our suggestion) | Re-read the terms of the other services the kit documents. | [third-party licenses](../compliance/third-party-licenses.md) |
| When a second maintainer joins | Remove the bypass actor, turn on approval of the last push, and consider CODEOWNERS. | The ruleset and CODEOWNERS sections above. |
| When you change a GitHub setting | Update this page. | This page. |

**The monthly Spawn terms check.** [`.github/workflows/compliance-reminder.yml`](../../.github/workflows/compliance-reminder.yml) runs at 14:17 UTC on the first day of each month, and you can start it from the Actions tab. It opens an issue with a checklist, unless an open issue with the `compliance` label and "Monthly check" in its title already exists. Close last month's issue when you finish, or no new one opens. The `compliance` label must exist, which the setup script takes care of. GitHub may switch off scheduled workflows in a repository that has been quiet for a long time. If the monthly issue stops appearing, check the Actions tab and re-enable the workflow. A person does the check, reads Spawn's real pages, and records the date in [the rules we follow](../compliance/spawn-rules.md).

## What each file in .github does

| File | What it does | Depends on |
| --- | --- | --- |
| [`labels.tsv`](../../.github/labels.tsv) | Names, colors and descriptions of every label. | `scripts/setup-github.sh` applies it. |
| [`labeler.yml`](../../.github/labeler.yml) and [`workflows/labeler.yml`](../../.github/workflows/labeler.yml) | Add labels to pull requests from the files they change. The workflow runs on `pull_request_target` so it can label pull requests from forks. That is safe here because it never checks out or runs the pull request's code. | The labels must exist. |
| [`release.yml`](../../.github/release.yml) | Groups generated release notes by label. | The labels must exist. |
| [`dependabot.yml`](../../.github/dependabot.yml) | Weekly updates for GitHub Actions and Bun packages, labeled `dependencies`, with commit prefixes `ci` and `deps`. | Dependabot must be on. |
| [`rulesets/main.json`](../../.github/rulesets/main.json) | The branch rules. Not applied unless you pass `--ruleset`. | The job name "Lint and test". |
| [`ISSUE_TEMPLATE/`](../../.github/ISSUE_TEMPLATE/) | Six forms: bug report, feature request, documentation improvement, compliance concern, agent behavior problem, and "Spawn changed and the kit broke". `config.yml` turns blank issues off and adds links to Discussions, private vulnerability reporting, Spawn's own support page, [SUPPORT.md](../../SUPPORT.md) and the Code of Conduct. | The labels the forms name must exist. A repository's own forms replace the organization's defaults. |
| [`DISCUSSION_TEMPLATE/`](../../.github/DISCUSSION_TEMPLATE/) | Forms for the Ideas, Q&A and Show and tell categories. | The category slugs. |
| [`PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md) | The pull request form: what and why, how it was tested, a checklist, the DCO line, and the AI assistance section from the [AI policy](../contributing/ai-assisted-contributions.md). | None. |
| [`workflows/ci.yml`](../../.github/workflows/ci.yml) | The job "Lint and test" runs `bash scripts/lint.sh` on pushes to `main` and on pull requests. Actions are pinned to full commit hashes, and Dependabot keeps them current. | The ruleset names this job. |
| [`workflows/compliance-reminder.yml`](../../.github/workflows/compliance-reminder.yml) | The monthly issue. | The `compliance` label. |

There is deliberately no `CODEOWNERS` and no `FUNDING.yml` (see above). All six issue forms add the `triage` label, ask whether an AI tool helped, and tell people not to paste tokens.

## Before you announce the project

The repository is already public, so these are the things that remain. Work through them, and write the date next to each item you finish.

**Spawn and the name**

- [ ] **Decide about the name, before the first push or at the latest before any announcement.** Either (a) a named maintainer sends the drafted question to contact@spawn.co and the date and the reply are recorded in [the rules we follow](../compliance/spawn-rules.md#why-the-repository-is-called-sdlca-for-spawn), or (b) the maintainers record that they accept the risk described there and that counsel has been asked to review it. Do not announce the project (README links, Slack, Discord, social posts) before one of the two is done. If there is no reply within 14 days, announce only with the unofficial notices in place, record the silence, and revisit the rename.
- [ ] **Ask Spawn first, and record the answer.** Spawn's own pages ask people to ask before they start, and no permission has been requested yet. A named maintainer writes a short, courteous message, in the way Spawn asks to be contacted: its home page says to ask in its Discord, and its published contact address is `contact@spawn.co`. Do not join Spawn's Discord as a bot. The message asks:
  - whether the project may describe itself as "for Spawn";
  - whether Spawn would rather that the project's and the Slack app's names did not contain "Spawn" (this includes agent account names such as `sdlca-for-spawn`);
  - whether Spawn wants particular wording in our disclaimer;
  - whether anything in its terms should be highlighted for agent integrations;
  - whether a path exists for tools or integrations.

  Keep the date, the channel and the reply (a link or screenshot). An answer that is not in writing is informal and is not an endorsement. If there is no reply within 14 days, say so in the record, keep the unofficial notices and revisit the rename. Then update the statement in [the rules we follow](../compliance/spawn-rules.md) that no permission has been requested, for example: "As of <ISO date>, <role> asked Spawn at contact@spawn.co; <no reply yet | reply summarized and linked>. This is not permission." Claim no endorsement.
- [ ] **Confirm the repository name.** It is `kdtix-open/sdlca-for-spawn`; it was renamed from `spawn` before the first push, because Spawn's terms bar names confusingly similar to its own and bar suggesting an affiliation (sections 2(c), 4(p) and 16; see [the rules we follow](../compliance/spawn-rules.md)). A name that leads with the project's own name, with "for Spawn" only as a descriptor, lowers the risk but still contains the word, so it still needs the question above. If Spawn prefers that its name is not in the repository name, a rename is cheap while the project is new; see "If the repository is renamed" below. Record the decision.
- [ ] **Check the Slack app name and descriptions against the code.** Open [`slack/manifest.yaml`](../../slack/manifest.yaml). The app name, bot name and slash commands should contain no vendor name. Read every sentence of the long description, especially each "does not" sentence, and check it against what the code does today. For example, the kit keeps a person's own tokens in files on their machine and sends each only to the service it belongs to, so a sentence about credentials must say what is true of that. Features must be worded as planned, because the bridge is not built.
- [ ] **Search the repository for risky words.** From the repository root, run the command below. Every hit should be a sentence that says "unofficial", "not official", "not affiliated" or "not a partner", or one that talks about the word itself (for example Spawn's own Partner Program, or this page). Anything else needs a human decision.

  ```bash
  grep -rniE 'official|certified|partner|powered by|built with|worked with|partnered' . \
    --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=design --exclude=bun.lock --exclude=LICENSE
  grep -rnE '\(TM\)|\(R\)|™|®' . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=design --exclude=bun.lock --exclude=LICENSE
  ```

- [ ] **No logos anywhere.** Not in the README, the social preview, the Slack app icon, a favicon or a screenshot. Names appear as plain text only.
- [ ] **Nothing copied, nothing vendored.** No text, art or code from Spawn, Anthropic, Slack or anyone else. `grep -rn spawnco package.json bun.lock` prints nothing, because users install the Spawn client themselves.

**Security**

- [ ] **Secret scanning and push protection are on.** Check them in Settings, in the code security section. Do this before the first push.
- [ ] **Private vulnerability reporting is on,** and [SECURITY.md](../../SECURITY.md) exists and matches it.
- [ ] **Run `bash scripts/check-secrets.sh`,** and read `git status --short --ignored` before the first push. Look at every untracked or ignored path, including anything excluded in `.git/info/exclude`, and make sure nothing that should stay private is going out.
- [ ] **Check the commit identity before the first push** (step 3 above): `git log --format='%an <%ae> | %cn <%ce>' | sort -u` lists only the identity you intend, the first commit carries an `Assisted-by` trailer, and a person has signed it off (`Signed-off-by`) or has recorded that it has none. The name and email on a commit become public for good. Use GitHub's no-reply address if you want to keep your own private, and consider the account setting "Block command line pushes that expose my email".
- [ ] **The contact mailboxes are read by two people.** The Code of Conduct names `Open.Source@kdtix.com`, and the security policy names `security@kdtix.com`. Two people must be able to read both mailboxes before the project is announced. Our research could not confirm that anyone reads either, so send a test message to each and confirm who answers. Also check that the Code of Conduct's conflict-of-interest sentence says what really happens when nobody uninvolved is available: "someone outside the project that we trust".
- [ ] **Optional: set up code scanning after the first push.** See the Code scanning row in the settings table. If you do, say so there.

**Contributions and the law**

- [ ] **The DCO decision is recorded.** The [AI policy](../contributing/ai-assisted-contributions.md) says we follow "a person certifies the DCO after review", and that it is open. Confirm that stance or change it. Decide whether the web sign-off setting (the script turns it on) stays on, whether to build the DCO check (planned) and whether to require it in the ruleset, and how a maintainer signs off for a project agent account. Write the outcome in the policy's decision table.
- [ ] **A lawyer has looked at the AI policy and the DCO stance.** The policy says it has not been reviewed by one. Ask the same person about the "for Spawn" naming question, which [the rules we follow](../compliance/spawn-rules.md) marks as a risk, and about the "Testing safely" section of [SECURITY.md](../../SECURITY.md), which promises that we will not take legal action against good-faith testing of someone's own installation, and will not ask anyone else to.
- [ ] **`LICENSE` is the unmodified Apache-2.0 text, and `NOTICE` names the right holder and year** and still says the project is unofficial.
- [ ] **The funding decision still stands.** No Sponsor button shows (see the funding section).

**Readiness**

- [ ] **CI is green on `main`, and the ruleset is applied.** Open a test pull request and check that "Lint and test" appears as required.
- [ ] **Labels, Discussions categories and the Project exist** as described above. The Project is public.
- [ ] **Click-test the links.** After the push, and after Discussions is on, click every `github.com/kdtix-open/sdlca-for-spawn` link in README.md, CONTRIBUTING.md, SUPPORT.md and `.github/ISSUE_TEMPLATE/config.yml`. Each should open the page it names (Discussions and its categories, the private reporting form, the issue chooser, the labels).
- [ ] **The CI badge renders.** Actions has run once on `main`, so the badge at the top of the README shows a result instead of "no status".
- [ ] **Community standards are complete.** On GitHub, Insights > Community standards should show the README, license, Code of Conduct, contributing guide, security policy, issue forms and pull request template.
- [ ] **Starter issues exist.** One issue per planned item on the [roadmap](../community/roadmap.md), each with an `area:*` label, so the roadmap's tracking links are not empty. Three to five of them are labeled `good first issue`, each small and well described. Run `python3 -I -B scripts/seed-starter-issues.py` to read them (a dry run), then again with `--apply` to post them. It skips a title that already exists, so it is safe to run twice. The project's AI policy says an agent never posts for a person, so a maintainer runs it and answers for the text.
- [ ] **A welcome post is pinned in Discussions.** The text is in [welcome-post.md](welcome-post.md): read it, change it, post it by hand in the Announcements category and pin it.
- [ ] **Read Spawn's terms again on the day,** and note their "last revised" date. Spawn changes them often.
- [ ] **Plan the announcement.** If you post in a Spawn community space, read that community's rules first, say plainly that the kit is unofficial, and do not suggest Spawn endorses it. See [communication](../community/communication.md).

## If a token leaks

A token is anything that lets someone act as a person or a service: a Spawn token (`sak_...`), a Spawn invite code (`sbk_...`), a Slack token (`xoxb-...` or `xapp-...`), an AI provider key, a GitHub token, or any other session, join or login credential, including values printed by `spawn client join`. It can leak in a commit, an issue, a comment, a Discussion, a pasted log or a screenshot. Work in this order, and stay calm: a leak is common and fixable.

1. **Revoke or replace it first.** Before any cleanup. Deleting the text does not make a token safe; assume someone copied it.
   - A Spawn token or invite code: the account's owner replaces it. See [rotating a token](../operations.md#rotating-a-token).
   - A Slack token: regenerate it in the Slack app's settings, following Slack's own documentation.
   - An AI provider key: delete it in the provider's console and create a new one.
   - A GitHub token: delete it in the account's settings, or ask its owner to.
2. **Tell the token's owner now,** even if they are not a maintainer. If one of our own agent accounts caused the leak, suspend that account's tokens first, as the [AI policy](../contributing/ai-assisted-contributions.md) says.
3. **Take the text out of sight.** For an issue, pull request or Discussion comment, delete the whole comment. Editing alone leaves the old text in the edit history. If you cannot remove something, ask GitHub Support. Never copy the token into an incident note or another issue.
4. **Rewrite nothing in history without the maintainers' agreement.** Once the token is revoked, the copy in history can no longer be used. A rewrite changes every later commit, breaks forks and open pull requests, and cannot take back copies that others already fetched. The ruleset blocks force pushes to `main` on purpose, so a rewrite means switching it off for a while. If the maintainers do agree, announce it first and follow [GitHub's guide to removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository), which also says when to contact Support to clear cached views.
5. **Work the secret-scanning alert.** Open Security > Secret scanning. Each alert shows the kind of secret and where it was found. Revoke the secret first. Then close the alert and pick the honest reason: "Revoked" once it is revoked, "False positive" if it was never a secret, or "Used in tests" if it is a fake value. Do not close an alert as revoked before it is. Also check for alerts that say a push protection block was bypassed. GitHub may not recognize Spawn's token formats, so also run `bash scripts/check-secrets.sh` on the working tree, and search the history with `git log --all --oneline -G'sak_[A-Za-z0-9_-]{24,}|sbk_[0-9a-f]{24,}'` (it lists commits whose changes add or remove such a string).
6. **Look for use.** Check whatever activity records the service offers (the provider's usage page, the Slack app's logs). If a Spawn token was used, its owner should tell Spawn through Spawn's own channels. We cannot act for them.
7. **Write it down and fix the cause.** Keep a short private note: what leaked, where, when it was found and revoked, and who was told. If people who use the kit could be affected, publish an advisory through private vulnerability reporting and mention it under Security in the release notes. If a template or a document invited the leak, fix it and label that work `security`.

If other people's private messages were pasted by mistake, treat that the same way: remove the comment, tell the people involved, and say how you will keep it from happening again.

## If the repository is renamed

GitHub redirects the old address after a rename, so existing links keep working for now. Decide the new name together, then:

1. Rename it in Settings > General.
2. In every clone, run `git remote set-url origin <new address>`.
3. Search for the old name and change it everywhere: `grep -rn "kdtix-open/<old-name>" . --exclude-dir=.git --exclude-dir=node_modules`. The name appears in the issue forms and `config.yml`, `scripts/setup-project.sh` (the default for `--repo`), `slack/manifest.yaml`, `CONTRIBUTING.md`, `CHANGELOG.md`, and several pages in `docs/`. We always write it as exactly `kdtix-open/sdlca-for-spawn`, so one search and replace does it.
4. Settings, rulesets, labels and the Project link belong to the repository, so they stay with it. The monthly workflow reads the repository name from GitHub, so it needs no change.
5. Update the README badges, the repository description if it names the project, and the Spawn record from the checklist.
6. Do not create a new repository with the old name, because that ends the redirect.

## Troubleshooting

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| A pull request says it is waiting for the status "Lint and test". | The check has not run or has a different name. | Look at the Actions tab. For a pull request from a fork, click "Approve and run". If the job was renamed, fix `main.json`. |
| A new issue lacks its labels. | The labels do not exist. | Run `bash scripts/setup-github.sh --repo kdtix-open/sdlca-for-spawn --apply`. |
| The issue chooser shows the organization's forms, or none of ours. | Our `.github/ISSUE_TEMPLATE/` is not on the default branch yet. | Push or merge it. |
| A Discussions category shows no form. | The file name does not equal the category slug. | Rename the file in `.github/DISCUSSION_TEMPLATE/`. |
| The monthly issue did not open. | The `compliance` label is missing, an open "Monthly check" issue exists, or GitHub switched the schedule off. | Fix the cause, then run the workflow from the Actions tab. |
| A Sponsor button shows. | The organization's funding default is inherited. | Ask the organization owners. See the funding section. |
| A script step fails with 403 or 404. | You are not an admin, a feature is not available for this repository, or the repository is empty. | The script carries on and lists the failed steps at the end. Check your role, push the first commit, and run the script again. |
| `gh project` complains about a scope. | The token lacks the `project` scope. | `gh auth refresh -s project` |

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
