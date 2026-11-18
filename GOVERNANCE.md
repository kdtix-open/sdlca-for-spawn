# Governance

This page is for contributors who want to know how decisions are made in the SDLCA agent kit project, and for anyone who might one day become a reviewer or maintainer. It explains the roles, how we decide things, how to join the team and how to leave it, what happens when people disagree, and how this page itself changes.

**Last reviewed 2026-11-17. Next review due by 2027-05-17.**

## The short version

- **We are new and small.** The project is maintained by KDTIX Open, KDTIX's open projects program. We keep the rules light on purpose, and we say plainly where we have not decided something yet.
- **There are three roles:** contributor, reviewer and maintainer. Anyone can be a contributor, and every kind of help counts, not only code.
- **Decisions happen in public,** in the pull request, issue or Discussion where the question came up. Bigger changes start as a proposal and stay open for comment for at least 7 days.
- **We are independent of Spawn.** No one at Spawn has a say in our decisions, and nothing here means Spawn endorses us.

## Who runs the project

KDTIX Open owns the repository and the GitHub organization it sits in. It decides who holds administrator access, answers for the project's legal and licensing choices, and has the final say if the maintainers cannot agree (see [When people disagree](#when-people-disagree)). When it makes a decision, the reasons go in the thread where everyone can read them.

Unless a file says otherwise, everything we wrote in this repository (code, documentation and templates) is licensed under Apache-2.0. The Code of Conduct is the Contributor Covenant 2.1, which its authors release under CC BY 4.0. The license does not cover Spawn, Savi, or any other party's names, code, art or documentation, or the content of your own worlds. Contributors keep the copyright in what they write and license it to the project under the terms of section 5 of the [license](LICENSE). There is no contributor license agreement. We ask for a Developer Certificate of Origin sign-off instead (see [CONTRIBUTING.md](CONTRIBUTING.md)).

We do not publish a list of maintainers yet. If you want to know who holds a role, ask in Discussions. See [What we have not decided yet](#what-we-have-not-decided-yet).

## Roles

| Role | Who | What they can do | How to get there |
| --- | --- | --- | --- |
| Contributor | Anyone. You do not need permission or an invitation. | Open issues and pull requests, answer questions, improve docs, test, translate, give feedback. | Do something useful. That is all. |
| Reviewer | A contributor the maintainers trust to help with reviews and triage. | Review pull requests, add labels, assign and close issues. A reviewer has GitHub's Triage role, which cannot merge. | See [Becoming a reviewer](#becoming-a-reviewer). |
| Maintainer | A person who looks after the project day to day. | Approve and merge pull requests, cut releases, handle security reports and conduct reports with KDTIX Open, and keep the promises in our docs. A maintainer has GitHub's Write role or higher. | See [Becoming a maintainer](#becoming-a-maintainer). |

Reviewers and maintainers are people. An AI agent account never holds either role, never approves a pull request and never merges one. The [AI policy](docs/contributing/ai-assisted-contributions.md) says how our own agent accounts work.

Every kind of work counts toward every role: code, documentation, triage, answering questions, testing, security work, and helping newcomers. We look at the quality and care of what you did, not at which kind of work it was.

Reviewers and maintainers also promise to:

- follow the [Code of Conduct](CODE_OF_CONDUCT.md), and say so when they have a conflict of interest and step back from that decision;
- meet the response goals in [CONTRIBUTING.md](CONTRIBUTING.md) as best they can, and say so honestly when they cannot;
- disclose AI help in their own work, just as everyone else does;
- protect reporters: security reports and conduct reports stay private.

## How decisions are made

**Most decisions are small.** A bug fix, a typo, a test, a clearer sentence: a maintainer reads the pull request, and if it works and the checks pass, it is merged. Our rules ask for one maintainer's approval and the passing check named "Lint and test" before a merge. The details are in [GitHub settings for maintainers](docs/maintainers/github-settings.md).

**An honest limit.** While the project has only one maintainer, the person who wrote a change may be the one who merges it, because the repository rules let an administrator do that. When this happens, the pull request says so, and we ask any reviewer or contributor to read it afterward. We would much rather have a second maintainer.

### Proposals

Some changes need a proposal first, because other people rely on them or because they are hard to undo. They are:

- a new or changed command, option, environment variable, or file in the runtime home (we treat these as our public interface; see [releasing](docs/contributing/releasing.md));
- anything that changes who may trigger work, where tokens go, or what is logged;
- a new dependency, a new label, or a change to a policy file or to this page;
- anything that touches Spawn's rules, our license, or the way we name things.

A proposal works like this:

1. **Start with a Discussion** in the Ideas category. Early and half-formed ideas are welcome. Nobody needs a finished plan. [Feedback and ideas](docs/community/feedback-and-ideas.md) shows how.
2. **If people think it is worth doing, open an issue** with the feature request form. The issue states the problem, the proposed change and what else was considered. A maintainer labels it (`enhancement`, and `discussion` if it needs design talk) and adds it to the public [project board](docs/community/project-board.md).
3. **Wait for comments.** The clock starts when the issue is opened. Anyone may comment.
4. **A maintainer writes down the outcome** in the issue: accepted, accepted with changes, not now, or no, with the reasons. Accepted work becomes ready to pick up. Pull requests then refer to the issue.

### Lazy consensus and the minimum time

We use *lazy consensus*. It means a proposal is treated as agreed if, after the minimum time, no maintainer has objected. Silence is not a vote against, so people who are busy do not hold things up.

| What | Minimum time open for comment |
| --- | --- |
| A proposal (see the list above) | 7 days |
| A change to this page, the Code of Conduct, the security policy or the AI policy | 14 days |
| An urgent fix to a security problem or a legal or compliance problem | None. A maintainer may act at once and must explain in public within 7 days (details of a security problem stay private until fixed) |

The days are calendar days. A maintainer who objects must say why, and an objection stops the clock from running out until it is answered. Objections from contributors who are not maintainers are weighed seriously, and the maintainer who closes the discussion has to reply to them.

### Stopping the line

Any maintainer may pause or revert a change straight away if they think it may break Spawn's rules, a license or a security promise. They add the `blocked` label and say why. The pause is reviewed in public within 7 days, unless it involves a private security or conduct report.

### When people disagree

Disagreement is normal and often useful. We handle it in this order:

1. **Talk it through in the thread.** Say what you want, and why, and what would change your mind.
2. **Look for a version everyone can accept.** A smaller change or a trial often works.
3. **If the minimum time has passed and maintainers still disagree, they vote.** Each active maintainer has one vote, and a simple majority decides.
4. **If there is a tie, or only one maintainer, KDTIX Open decides** and writes the reasons in the thread.

Whatever the outcome, the reasons are written down, and you may ask for the decision to be looked at again when something has changed. Disagreements about conduct follow the [Code of Conduct](CODE_OF_CONDUCT.md) instead.

## Becoming a reviewer

There is no exam and no waiting list. A reviewer is someone the maintainers have seen helping, kindly and carefully, for a while. As a guide, we look for:

- a few accepted contributions of any kind, over about two months or more;
- reviews, answers or reports that were careful and kind;
- two-factor authentication turned on for the GitHub account;
- having read the Code of Conduct and the AI policy.

A maintainer can suggest you, or you can ask by opening an issue or a Discussion. If no maintainer objects within 7 days, an administrator gives you GitHub's Triage role. The decision and the reasons are recorded in the thread. If the answer is "not yet", we say what would help.

## Becoming a maintainer

A maintainer is usually a reviewer who has been active for about three months or more, and who has shown good judgment, especially on changes that touch tokens, the sender allowlist, routing, continuous integration (CI) or Spawn's rules. One maintainer sponsors the nomination. The proposal stays open for 7 days, and a majority of the active maintainers must agree. KDTIX Open then gives the access. We aim to have at least two maintainers who can review each other, and we will say so when we reach it.

Maintainers are chosen as individuals. No company has a reserved seat, and you do not need to work for KDTIX.

## Stepping down, and being away

You can step down from any role at any time, without giving a reason. Tell us in an issue or privately, and we will thank you. Your credit stays in the history and in the release notes. If you come back, the same process applies, and we will usually move quickly.

Life gets busy. If a reviewer or maintainer has been quiet for six months, a maintainer will ask whether they want to keep the role. If there is no answer after 30 more days, the role moves to *emeritus*, which means a thank-you and no access, and it is easy to return from. Access is also removed if a Code of Conduct decision says so. The reasons are given to the person, and they can ask for a second look.

If the project has no active maintainer, we will say so in a notice at the top of the README and in the Announcements category of Discussions, so nobody is left waiting for answers that cannot come.

## How this page changes

Governance is a pull request against this file. It is announced in Discussions when it opens, stays open for at least 14 days, needs the agreement of a majority of the active maintainers, and needs KDTIX Open to agree as the owner. The history of the file in git is the record. We review this page every six months, and sooner when the team changes.

## Our relationship to Spawn and to KDTIX Open

**Spawn.** This project is independent. It is not made, reviewed, supported or endorsed by Spawn, it is not a Spawn partner, and nobody at Spawn takes part in our decisions. We follow Spawn's published rules, because everyone who runs the kit is a Spawn user. The rules are listed, with their sources and dates, in [the Spawn rules we follow](docs/compliance/spawn-rules.md). If Spawn asks us to change something about our name, our wording or our use of its terms, a maintainer treats it as a compliance matter and answers promptly. Feedback about Spawn itself belongs with Spawn. [Feedback and ideas](docs/community/feedback-and-ideas.md) shows where to send it.

**KDTIX Open.** KDTIX Open owns the repository and the GitHub organization it sits in. The copyright line in `NOTICE` names KDTIX and the contributors. The project has no funding links and takes no sponsorship today. If that ever changes, sponsorship will not buy review or roadmap priority, and we will say so in public.

## What we have not decided yet

We would rather list these than pretend they are settled:

- whether to publish a roster of maintainers and reviewers, and where;
- whether to add a separate moderator role for community spaces, apart from the technical roles;
- whether to run a mentoring program, beyond the `mentor-available` label;
- how funding, if we ever take any, would be handled and recorded.

If you have a view, a Discussion in the Ideas category is the right place.

## Where these ideas come from

We looked at how other open source communities in the same field work, and borrowed the light parts, not the heavy ones. For example, the Model Context Protocol project's contributor ladder asks for a seven-day comment period before someone joins a role, and counts documentation, triage and community work alongside code ([contributor ladder](https://modelcontextprotocol.io/community/contributor-ladder), read 2026-11-17). Its working groups decide by lazy consensus with a minimum time ([working and interest groups](https://modelcontextprotocol.io/community/working-interest-groups), read 2026-11-17). The goose project asks for an issue or discussion and at least a week of open review for major changes ([goose governance](https://github.com/aaif-goose/goose/blob/main/GOVERNANCE.md), read 2026-11-17). We left out the steering committees, working groups and many tiers, which suit projects with hundreds of contributors, not a new one. The full comparison is in [the community patterns digest](docs/research/oss-community-patterns-2026.md).
