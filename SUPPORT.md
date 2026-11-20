# Support

This page is for anyone who needs help with the SDLCA agent kit, or who has something to tell us. It shows where to take each kind of question, what to include so we can help quickly, what we cannot help with, and how fast to expect an answer.

The kit is an unofficial community project. It is not made, reviewed or supported by Spawn, and Spawn's support team cannot help with the kit. We are a small team of volunteers, so please be kind to us and to each other. You will not be judged for asking a basic question.

## Where to ask what

| I want to... | Go here |
| --- | --- |
| Ask how to do something, or why it does not work for me | [Discussions, Q&A](https://github.com/kdtix-open/sdlca-for-spawn/discussions/new?category=q-a). First look at [getting started](docs/getting-started.md), the [troubleshooting table](docs/operations.md#troubleshooting) and the [FAQ](docs/faq.md). |
| Share an idea that is not fully formed | [Discussions, Ideas](https://github.com/kdtix-open/sdlca-for-spawn/discussions/new?category=ideas). [Feedback and ideas](docs/community/feedback-and-ideas.md) shows how. |
| Show what I built or learned | [Discussions, Show and tell](https://github.com/kdtix-open/sdlca-for-spawn/discussions/new?category=show-and-tell) |
| Report a bug in the kit | The "Bug report" form on the [issue chooser](https://github.com/kdtix-open/sdlca-for-spawn/issues/new/choose) |
| Ask for a feature with a clear problem and proposal | The "Feature request" form |
| Fix or question something in the docs | The "Documentation improvement" form |
| Tell us an AI agent run by the kit did something wrong or unsafe | The "Agent behavior problem" form |
| Tell us Spawn changed something and the kit no longer matches | The "Spawn changed and the kit broke" form |
| Raise a concern about Spawn's terms, a license, a name or credit | The "Compliance or attribution concern" form, or write to Open.Source@kdtix.com (see below) |
| Report a security vulnerability | Private only. Follow [SECURITY.md](SECURITY.md) (GitHub private reporting, or security@kdtix.com). Never use a public issue. |
| Report behavior that breaks our Code of Conduct | Write to Open.Source@kdtix.com. See the [Code of Conduct](CODE_OF_CONDUCT.md). |
| Report a problem with Spawn itself (a world, a player, Savi, Spawn's website or app, your Spawn account) | Spawn, not us. See [Problems with Spawn](#problems-with-spawn). |

## Our public contact address

**Open.Source@kdtix.com** is KDTIX Open's public contact address. Use it for:

- conduct reports, privately (the Code of Conduct explains what happens next);
- rights holders, such as Spawn or anyone else with a copyright, trademark or name concern, who would rather not use a public issue;
- a privacy or personal-data concern that you would rather not post in public;
- if you cannot use GitHub for any reason, to tell us and ask for another way to reach us.

Please do not send tokens, invite codes, other people's private messages, or any other session, join or login credential, including values printed by `spawn client join`, to it, and use SECURITY.md, not this address, for security problems.

## Problems with Spawn

We cannot fix Spawn. We do not run it, we cannot see inside it, and we do not speak for it. For a problem with Spawn itself, use Spawn's own doors, which Spawn's support page and FAQ describe (read 2026-11-17):

- the in-app **Report a bug** button (in a game, press the gear and choose "Report a bug", as Spawn's support page explains);
- [Spawn's support page](https://www.spawn.co/support), which lists how to write to Spawn and how to report a player, game or message;
- [Spawn's Discord server](https://www.spawn.co/discord), which Spawn's FAQ and rules page name as the place for bug reports, feedback and rule questions. We have not read its rules, so read them before you post.

**One warning.** Spawn's terms of service (section 19, read 2026-11-17) say feedback you give Spawn becomes Spawn's property and may be used by Spawn in any way. If that matters to you, read the terms before you send. [Feedback and ideas](docs/community/feedback-and-ideas.md) says more.

If a Spawn change broke the kit, tell us with the "Spawn changed and the kit broke" form, and tell Spawn too if it looks like a bug on their side.

## What to include

The more you tell us, the faster we can help. You do not need to know the technical words. Plain language is fine.

- **What you were trying to do,** and what happened instead.
- **The steps**, or the command you ran. The smallest steps that show the problem are the best gift.
- **Your version:** run `git rev-parse --short HEAD` in your clone of the kit, or give the release tag.
- **Your system:** the operating system, and the versions of bash, Python, Bun and the Spawn client if you know them.
- **Your agent command**, written without any keys (for example `claude -p --setting-sources user`).
- **Log lines** from `handler.log` or `listener.log`: only the few lines that matter, and only after you remove tokens and other people's messages. `handler.log` can hold anything the agent printed, so also remove file contents, home-folder paths, usernames and world names you do not want public. Replace what you remove with `REDACTED`.
- **A description of any screenshot.** Describe what is in it in words as well, so everyone can read your report.

**Never paste a token, an invite code, a password, or any other session, join or login credential, including values printed by `spawn client join`,** and do not post other people's names or private messages. If you leaked one by mistake, replace or revoke it right away, then tell us. [Rotating a token](docs/operations.md#rotating-a-token) shows how.

## What we cannot help with

- Problems inside Spawn: worlds, players, Savi, its website, its app, billing, or your Spawn account.
- Your AI provider's account, limits or prices, and bugs in your agent tool itself. The kit runs any command that reads a prompt on standard input, but your tool's own features are your tool's business. Check its documentation.
- Making Savi work unattended, using Spawn as a free asset generator, moving a Spawn game to another engine, or anything else Spawn's rules forbid. See [the Spawn rules we follow](docs/compliance/spawn-rules.md).
- Slack workspace administration. The Slack bridge is planned and not built yet. See the [roadmap](docs/community/roadmap.md).
- Legal advice. We can say what our docs claim, but we are not lawyers.
- Running the kit as a service on Windows or macOS. We have tested only on Ubuntu under WSL2. The CI job is set up to run the same checks on GitHub's Ubuntu runner. macOS service support (launchd) is planned.

## How fast to expect an answer

We aim to reply to a new question, issue or pull request within about 7 days. If you hear nothing after 14 days, a polite nudge is welcome. Security reports and conduct reports get a faster first reply, as a goal: within 3 business days. All of these are goals, not promises, because we are a small team and nobody here is paid to be on call. There is no support contract. [Communication](docs/community/communication.md) has more about channels, languages and time zones.
