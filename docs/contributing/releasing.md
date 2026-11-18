# Releasing

This page is for maintainers who cut a release of the SDLCA agent kit, and for contributors who want to know how their work reaches one. You will learn how we number versions, how release notes are made, how the monthly check of Spawn's terms works, and the checklist to follow every time.

Releases are cut by a person. An AI agent may draft notes or prepare the pull request, but a maintainer reads every public word and does the tagging and publishing. See [AI-assisted contributions](ai-assisted-contributions.md). Who the maintainers are is in [GOVERNANCE.md](../../GOVERNANCE.md).

## Versioning

We use [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html): `MAJOR.MINOR.PATCH`. The first release is planned as `0.1.0`, which is the number already in `package.json`.

- Until 1.0.0, the kit may still change shape. We raise MINOR for anything that breaks existing setups and PATCH for fixes and compatible additions. Breaking changes are always called out in the release notes.
- We treat these as the public interface: command names, arguments and exit codes; environment variable names; the layout and formats of files in the runtime home (account folder names, which are one word or `group/name`, and the account `env`, `allowlist.json`, `worlds.json`, the cursor, `handled.ids` and the events kept in `run/failed/`); the placeholders of the agent prompt; and the name of the systemd unit `sdlca-listener@.service`.
- We always say so in the notes when a change loosens or tightens a security promise (who may trigger work, where tokens go, what is logged).
- Tags look like `v0.1.0` and sit on `main`. The number must match `version` in `package.json`.
- **One name to decide before 1.0.0.** `SPAWN_USERNAME` is a variable this kit defines (the account's Spawn username, in each account's `env` file), but it shares the `SPAWN_` prefix with the variables Spawn's own client reads or sets, such as `SPAWN_TOKEN_FILE`, `SPAWN_ORIGIN`, `SPAWN_EVENT` and `SPAWN_TOKEN`. We keep it for now. Renaming it would break every existing account `env` file, so a rename needs a compatibility period (for example, reading both names for a while and saying so in the notes). Whether to rename it is a decision for the maintainers, to be made before 1.0.0.

## Release notes: two layers

1. **GitHub release notes** are generated from merged pull request titles. [`.github/release.yml`](../../.github/release.yml) groups them by label, and the groups appear in this order.

   | Heading in the notes | Label on the pull request |
   |---|---|
   | Security | `security` |
   | Breaking changes | `breaking-change` |
   | Features | `enhancement` |
   | Fixes | `bug` |
   | Compliance and licensing | `compliance` |
   | Documentation | `documentation` |
   | Dependencies | `dependencies` |
   | Other changes | anything else |

   Pull requests labeled `skip-changelog` are left out.
2. **[CHANGELOG.md](../../CHANGELOG.md)** is written by hand in the [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) format. It tells the story for people who use the kit; the generated notes list every change.

What this means day to day: before you merge, give each pull request the right label. The labeler workflow adds area labels, `dependencies`, `compliance` and `security` from the files a pull request changes ([`.github/labeler.yml`](../../.github/labeler.yml)), but it does not add `bug`, `enhancement` or `breaking-change`; a maintainer does that during triage (see [triage and labels](../community/triage-and-labels.md)). A pull request with no matching label lands in "Other changes". Because titles become the notes, write them for someone reading the release page.

## The changelog practice

- Add a line under `[Unreleased]` in the same pull request when a change is visible to people who use the kit. For a small contribution, a maintainer may add the line at merge time; it never blocks a first contribution.
- Use the Keep a Changelog headings: Added, Changed, Deprecated, Removed, Fixed, Security.
- At release time, move the entries to a new `## [x.y.z] - YYYY-MM-DD` section (ISO date), leave a fresh empty `[Unreleased]`, and fix the links at the bottom of the file. The first release has no earlier tag to compare with, so link its section to the tag page; later ones link to a compare view.
- Say "planned" for anything that does not work yet, and keep the planned list in step with the [roadmap](../community/roadmap.md).

## The monthly check of Spawn's terms

Spawn changes its terms and rules often, and the kit's rules are built on them. So the workflow [`.github/workflows/compliance-reminder.yml`](../../.github/workflows/compliance-reminder.yml) runs at 14:17 UTC on the first day of every month (you can also start it by hand from the Actions tab). It opens an issue titled "Monthly check: re-verify Spawn's terms and rules (YYYY-MM)" with the `compliance` label, unless an open issue with that label and a title containing "Monthly check" already exists. So close last month's issue when you finish it, or no new one opens. The issue needs the `compliance` label to exist; `scripts/setup-github.sh --apply` creates the labels.

The person who takes the issue, a maintainer or a volunteer, works through its checklist, which usually takes about 20 minutes:

1. Re-read Spawn's terms of service and note the "last revised" date.
2. Re-read Spawn's page on what Spawn is for, and its FAQ.
3. Skim Spawn's `llms.txt` and `openapi.json` for changes to agent rules, limits or endpoints.
4. Check the Spawn client's page on npm for its version and license.
5. Record what changed, and the date you checked, in [the rules we follow](../compliance/spawn-rules.md), even when nothing changed.
6. Open issues for anything in the kit or the docs that no longer matches.

If a change affects what the kit may do, open an issue labeled `compliance` and `upstream:spawn`, hold the release until a maintainer has decided, and say so in the notes. We have not been able to read Spawn's Discord rules, so nobody should claim anything about them; if you can read them, say what you found in the issue.

## Release checklist

Copy this into the release pull request or an issue.

**Before you tag**

- [ ] `main` is green: the latest "Lint and test" run passed. On a fresh clone, `CI=true bash scripts/lint.sh` passes (that run includes the secrets check, the `LICENSE` check and the Markdown link check).
- [ ] No open issue labeled `security` or `breaking-change` still needs a decision. The monthly check issue is closed.
- [ ] **Spawn's terms re-checked today**, with the list above, even if this month's issue was closed last week. [`docs/compliance/spawn-rules.md`](../compliance/spawn-rules.md) shows today's date as "last verified".
- [ ] **License files checked.** `LICENSE` is the unmodified Apache-2.0 text (the lint run checks its checksum against the file the Apache Software Foundation publishes at [apache.org](https://www.apache.org/licenses/LICENSE-2.0.txt); compare by hand if that check fails). `NOTICE` names the right copyright holder and year and still says the project is unofficial. New source files start with the SPDX line. Dependencies in `package.json` and `bun.lock` have been reviewed, and [third-party licenses](../compliance/third-party-licenses.md) lists them.
- [ ] Nothing from Spawn was added: no Spawn text, art, logos or client code. `grep -rn spawnco package.json bun.lock` prints nothing, because users install the Spawn client themselves.
- [ ] The README status table, [roadmap](../community/roadmap.md) and docs match what is built. Every command shown in the docs exists.
- [ ] `CHANGELOG.md`: `[Unreleased]` moved to the new version section with today's date; a fresh `[Unreleased]` added; links fixed.
- [ ] `version` in `package.json` bumped.
- [ ] A pull request titled like `chore: release 0.1.0`, labeled `skip-changelog`, is approved and merged.

**Tag and publish**

There is no release workflow yet, so a maintainer does this by hand with git and the GitHub CLI. (Automating it is a fair first project for a contributor.) Create the release as a draft first, so you can add text before anyone sees it:

```bash
git switch main
git pull --ff-only
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
gh release create v0.1.0 --verify-tag --draft --generate-notes --latest --title "v0.1.0"
```

- [ ] Open the draft. Add two lines at the top: what this release is in a sentence, with a link to its section of `CHANGELOG.md`, and "Unofficial community project, not affiliated with Spawn."
- [ ] Read the generated notes. Check the headings make sense, nothing private or secret is in them, and any breaking or security-relevant change is under the right heading.
- [ ] Publish the release.

**After**

- [ ] Check the release page and that a fresh clone of the tag passes `bash tests/run.sh`.
- [ ] Close the issues the release finished, and update the "Target release" field on the public Project (see [the project board](../community/project-board.md)).
- [ ] If you announce it in Discussions, fine. If you announce it in a Spawn community space, read that community's rules first, say plainly that the kit is unofficial, and do not suggest Spawn endorses it.

## If a release is wrong

Do not move or delete a tag that people may have used. Fix forward: merge the fix, release a new PATCH version, and edit the notes of the bad release to point to it. For a security problem, work in a private advisory first and follow [SECURITY.md](../../SECURITY.md).

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
