# Communication

This page is for anyone who wants to know where the SDLCA agent kit community talks, how fast to expect a reply, which languages we use, how we try to be accessible, how time zones work, and what is public and what is private. It lists every official channel, so if you meet something that is not on this page, it is not us.

## The short version

- **GitHub is our home and our record.** Issues, pull requests and Discussions are where things happen and where decisions are written down.
- **We are public by default.** Only security reports, conduct reports and a few similar matters are private.
- **We reply within about 7 days.** If you hear nothing after 14 days, a polite nudge is welcome. These are goals, not promises.
- **We work asynchronously.** Nobody is on call, and we do not expect you to be online at a set time.
- **Write in the language that is comfortable for you.** English is the project's working language, and we will do our best with the others.

## Channels

| Channel | What it is for | Who can see it |
| --- | --- | --- |
| [Issues](https://github.com/kdtix-open/sdlca-for-spawn/issues/new/choose) | Concrete bugs, documentation gaps and agreed work, through the forms | Everyone |
| [Discussions](https://github.com/kdtix-open/sdlca-for-spawn/discussions) | Questions (Q&A), ideas (Ideas), what you built (Show and tell), project news (Announcements, where only maintainers start threads), and anything else (General, Polls) | Everyone |
| Pull requests | Changes to the code and the docs, and the conversation about them | Everyone |
| The [project board](project-board.md) | Planning and triage | Everyone |
| Releases and [CHANGELOG.md](../../CHANGELOG.md) | What changed in each release | Everyone |
| Private vulnerability reporting, or security@kdtix.com | Security reports. See [SECURITY.md](../../SECURITY.md). | The reporter and the maintainers |
| Open.Source@kdtix.com | Conduct reports, privacy or personal-data concerns, and messages from rights holders who prefer not to use a public issue. See [SUPPORT.md](../../SUPPORT.md). | The sender and the people handling the message |

The maintainers set up the Discussions categories by hand, because we know of no way to create them from a file. If a category you need is missing, tell us in an issue.

**We run no chat server today.** We do not have a Slack, Discord or similar space for this project. If we ever open one, GitHub stays the record, and we will announce it here first.

**Spawn's own spaces belong to Spawn.** Its Discord server, its in-app reports and its support page are Spawn's channels. We do not run them or speak for them. We do not recruit or advertise in them, and we ask you not to do it for us. [Feedback and ideas](feedback-and-ideas.md) shows where Spawn feedback goes.

## GitHub is the record

If a question is settled in a call, a direct message or any other chat, someone writes a short summary in the issue, pull request or Discussion. This helps people in other time zones, helps newcomers who read the history later, and keeps decisions findable. It is also why we ask you to ask in public when you can. Other people learn from the answer.

You do not need to guess who to tag. Please do not @mention individual maintainers to speed things up. The forms, labels and [project board](project-board.md) send work to the right people.

## How fast to expect a reply

These are goals, because we are a small team. They are not promises, and there is no support contract. We will look at how we are doing from time to time, and change a goal that does not fit rather than keep a promise we cannot keep.

| What | Our goal |
| --- | --- |
| A first reply to a new issue, pull request or Discussion | Within about 7 days. After 14 days, a polite nudge is welcome. |
| A reply when you have updated a pull request after our comments | Within about 7 days |
| An idea or proposal | A first reply within about 7 days. A decision comes after the minimum comment time in [GOVERNANCE.md](../../GOVERNANCE.md), at least 7 days for most proposals. |
| A security report | Acknowledged within 3 business days, assessed within 7 days. See [SECURITY.md](../../SECURITY.md). |
| A conduct report | Acknowledged within 3 business days. See the [Code of Conduct](../../CODE_OF_CONDUCT.md). |

A business day means Monday to Friday. Holidays and busy weeks can slow us down, and we will say so when they do.

## Languages

- **The project's working language is English,** with American spelling and ISO dates. Repository files and decisions are in English. We write in short sentences and explain technical words once.
- **You may write in any language** in issues and Discussions. We will do our best to read it, with translation tools if we need them, and we will say so when we do. We usually reply in English, and we may add a translation.
- **Writing in English with help is fine.** If you used a translation tool or an assistant to write your words in English, that is welcome, and nobody holds it against you. A short note such as "translated with a tool" helps us understand you. The [AI policy](../contributing/ai-assisted-contributions.md) says what to tell us about AI help.
- **Translated docs** are planned and not started. See the [roadmap](roadmap.md).

## Accessibility

We want people with many different needs to be able to take part. We try to:

- **Use plain language,** short paragraphs, clear headings, and one idea at a time.
- **Put things in text.** If you add a screenshot, also describe it in words. Paste error messages as text in a code block, not only as a picture. If we ever publish a video, we will add captions or a transcript.
- **Write links that say where they go,** such as "the Code of Conduct", never "click here".
- **Never use color or emoji alone to carry meaning.** We keep emoji out of headings and labels.
- **Count reading, writing and reviewing as taking part.** You never have to speak on a call, appear on camera or be quick.
- **Listen when something is a barrier.** If our process, our words or our tools get in your way, tell us in an issue, or write to Open.Source@kdtix.com. We will work with you.

## Time zones

- We work asynchronously. Contributors and maintainers live in different time zones, and we promise no particular hours.
- Please write dates as `2026-11-17` and times with a zone, such as `14:00 UTC` (Coordinated Universal Time). Our monthly check of Spawn's terms, for example, starts at 14:17 UTC on the first day of each month.
- Our goals are in days, not hours. Nobody is on call. For a real emergency, such as a leaked token, follow the steps in [SECURITY.md](../../SECURITY.md) and [rotate the token](../operations.md#rotating-a-token) yourself right away.
- If we ever hold a public call, we will post the agenda beforehand and the notes within 48 hours, and we will not use recordings or AI note-takers unless everyone present agrees.

## What is public and what is private

**Public:** issues, pull requests, Discussions, the project board, labels, release notes, and our decisions with their reasons. Everything we write in `docs/` is public too.

**Private:** security reports, conduct reports, privacy or personal-data concerns, and messages from rights holders who ask for privacy. Maintainers talk in private only about those matters and about who has access to the repository. When something is decided in private, we summarize it in public when we can, without naming the people who reported it.

**For you:**

- Everything you post in a public place is public and may stay visible for a long time.
- Never post tokens, invite codes, personal data, or any other session, join or login credential, including values printed by `spawn client join`. Do not post other people's private messages, including chat lines from Spawn rooms. Replace such things with `REDACTED`.
- Your commits carry your name and email in the history. GitHub offers a private no-reply email address for commits. Check its settings if you want to keep your own address out of the history.
- We run few automations: the continuous integration check, a pull request labeler, a monthly reminder issue, and Dependabot. Any AI agent account of ours is marked as one and is owned by a named person. See the [AI policy](../contributing/ai-assisted-contributions.md).

## Announcements

We announce releases in GitHub Releases, in [CHANGELOG.md](../../CHANGELOG.md) and in the Announcements category of Discussions. Each release says that this is an unofficial community project. If we ever announce in a Spawn community space, we will read that community's rules first and say plainly that the kit is unofficial.

## Where this comes from

The Model Context Protocol community says plainly that chat is not the record: decisions move to GitHub, so everyone can follow them ([communication](https://modelcontextprotocol.io/community/communication), read 2026-11-17). Its working groups publish meeting notes within 48 hours ([working and interest groups](https://modelcontextprotocol.io/community/working-interest-groups), read 2026-11-17). OpenClaw's contributing guide tells people not to guess who to tag and to let forms and labels route work ([CONTRIBUTING.md](https://github.com/openclaw/openclaw/blob/main/CONTRIBUTING.md), read 2026-11-17). Spawn's own community lives mostly in one Discord server and in the product itself, and its FAQ points people there for feedback and rule questions ([Spawn FAQ](https://www.spawn.co/about/faq), read 2026-11-17). The full comparison is in [the community patterns digest](../research/oss-community-patterns-2026.md).

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
