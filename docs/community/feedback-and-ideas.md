# Feedback and ideas

This page is for anyone who wants to tell the SDLCA agent kit project something: a question, a suggestion, a complaint or an idea. It shows where to send it, what happens next, how we say no, and where feedback about Spawn itself should go, with one warning you should read before you send anything to Spawn.

You do not need to be a programmer or to know git. Plain words are fine. Half-formed ideas are welcome.

## Whose feedback is it?

| Your feedback is about... | Send it to... |
| --- | --- |
| This kit: a bug, a confusing page, a missing feature, something you built | This project. The rest of this page shows how. |
| The kit no longer matching Spawn (a rule, a command or an interface changed) | This project, with the "Spawn changed and the kit broke" form. If it looks like a bug on Spawn's side, tell Spawn too. |
| Spawn itself: a world, a player, Savi, Spawn's website or app, your Spawn account | Spawn, not us. See [Feedback about Spawn itself](#feedback-about-spawn-itself). |

We do not speak for Spawn, we cannot change Spawn, and we are not a way to reach Spawn.

## Giving feedback to this project

You need a free GitHub account to post. If you cannot use GitHub, write to the address in [SUPPORT.md](../../SUPPORT.md) and say so. GitHub requires users to be at least 13, and the minimum can be higher in your country ([GitHub's Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service), read 2026-11-17). If you are younger or unsure, ask a trusted adult to post for you. Never share personal details in public.

Pick the door that fits:

- **A question, or "I am stuck":** [Discussions, Q&A](https://github.com/kdtix-open/sdlca-for-spawn/discussions/new?category=q-a). No question is too small.
- **An idea, even a rough one:** [Discussions, Ideas](https://github.com/kdtix-open/sdlca-for-spawn/discussions/new?category=ideas). You do not need a finished proposal. This is where ideas start.
- **What you built or learned:** [Discussions, Show and tell](https://github.com/kdtix-open/sdlca-for-spawn/discussions/new?category=show-and-tell). Say what kind of feedback you would like. A quick opinion, a careful review and "I just wanted to share" are all fine.
- **A bug, a docs problem, or a concrete request:** an issue form on the [issue chooser](https://github.com/kdtix-open/sdlca-for-spawn/issues/new/choose). The forms ask only what we need.
- **A fix you made yourself:** a pull request. [CONTRIBUTING.md](../../CONTRIBUTING.md) shows the way, and it is fine to ask for help.

Never post a token, an invite code, another person's private message, or any other session, join or login credential, including values printed by `spawn client join`. Replace them with `REDACTED`. If you add a screenshot, also describe it in words, so everyone can read your report.

### A plain template for a good idea

Copy this into a Discussion and answer what you can. Skip what you do not know. The Ideas form in Discussions asks three of these questions.

```text
What I was trying to do:
What happened, or what is missing:
What I would like to happen:
What I have tried, or thought about, instead:
Who else this might help:
What I am unsure about:
What kind of feedback I would like (a quick opinion, a careful review, or just sharing):
```

Describe the problem before the solution. "I want to start a build from my phone when I am away from my computer" tells us much more than "add a button". We do not need an AI-written implementation plan. If an AI tool helped you write the idea, that is fine. Say so, and check that it says what you mean.

## What happens next

1. **We say thanks and read it.** We aim to reply within about 7 days. If you hear nothing after 14 days, a polite nudge is welcome.
2. **We may ask questions.** That is a good sign. It means we are taking it seriously.
3. **We give you one of four answers**, with the reasons written in the thread:
   - **Yes.** It becomes an issue, usually with the `enhancement` label, and goes on the public [project board](project-board.md). It may get `help wanted`, and if it is small, `good first issue`. See [triage and labels](triage-and-labels.md).
   - **Yes, but differently.** We say what we would change, and why.
   - **Not now.** We say what is in the way. The idea stays open in Discussions, and we look at it again when we plan a release. We do not close ideas with a bot.
   - **No.** We say why. See [How we say no](#how-we-say-no).
4. **We tell you when it ships.** The issue gets a link to the release, and the release notes list the change.

Bigger changes, such as a new command or a change to a security promise, stay open for comment for at least 7 days before a maintainer decides. [GOVERNANCE.md](../../GOVERNANCE.md) explains this. [The project board](project-board.md) shows how an idea becomes planned work. Our [roadmap](roadmap.md) lists what is planned today.

## How we say no

We will sometimes say no, and we would rather do it kindly and clearly. A no is about the change, never about you.

Common reasons:

- **Spawn's rules forbid it.** For example, making an agent talk to Savi unattended, using Spawn as a free generator of assets for use elsewhere, porting a Spawn game to another engine, or reaching Spawn through anything but its published doors. See [the rules we follow](../compliance/spawn-rules.md).
- **It would make the kit look official,** or use Spawn's names, art or text in a way that suggests Spawn stands behind us.
- **It weakens security,** for example by letting more people trigger work with fewer checks, or by sending tokens somewhere new.
- **It costs more to look after than it gives back,** or it belongs better in another tool.
- **It is not our job.** We cannot fix Spawn, an AI provider or Slack.

When we say no, we link to the reason, we say what would change our answer, and we leave the thread open for a reply. Disagreeing is fine. You may ask us to look again if something has changed. A "no" now is not forever. Spawn changes often, and so do we.

## Feedback about Spawn itself

If your feedback is about Spawn and not about this kit, please send it to Spawn. We cannot act on it, and we would only be passing it along second hand.

**Spawn's own doors.** Spawn's support page and FAQ describe them (read 2026-11-17):

- the in-app **Report a bug** button. In a game, press the gear and choose "Report a bug";
- [Spawn's support page](https://www.spawn.co/support), which lists how to write to Spawn and how to report a player, game or message;
- [Spawn's Discord server](https://www.spawn.co/discord), which Spawn's FAQ names as the place to share a game, ask for feedback and post a bug report, and where Spawn's rules page says to ask a rules question. We have not read that server's rules, so read them before you post.

Spawn's own advice for a useful bug report is to give the link to the game, what you did, what happened and what you expected, your device, and a screenshot or video if it looks wrong. That advice works here too.

**An important warning about Spawn's feedback terms.** Spawn's terms of service say, in section 19 (last revised 2026-10-09, read 2026-11-17), that feedback you give Spawn is "our exclusive property" ([Spawn terms of service](https://www.spawn.co/terms-of-service)). In our reading, this means that anything you send Spawn as feedback, including bug reports, ideas and suggestions, may be used and published by Spawn in any way, without payment, and that you give Spawn your rights in it. Those are Spawn's terms and not ours. We did not write them, we cannot change them, and we are not lawyers, so please read them yourself. Nothing here tells you not to send feedback to Spawn. We only want you to choose knowingly.

**What you send to us is different.** Text you send to this project to discuss and improve it is covered by the project's license, the Apache License 2.0, unless you mark it "Not a Contribution" (see sections 1 and 5 of the [license](../../LICENSE)). You keep your own copyright, and we may use your ideas to improve the kit. This is a plain-words summary and not legal advice. Please post only what you have the right to share.

**What we will not do.**

- We will not pass your message to Spawn for you. We cannot speak for Spawn, and doing it would put your words under Spawn's terms without your say.
- We will not say what Spawn "will do", "says" or "wants". We say where Spawn writes something, with the address and the date we read it.
- We do not ask our own agents to file reports with Spawn. A person reads any report before it is sent.

**If it is both.** When a Spawn change broke the kit, open the "Spawn changed and the kit broke" form here, so we can fix the kit. If you think Spawn has a bug, tell Spawn separately.

## Where these ideas come from

Other projects in this field also keep Q&A, ideas and bug reports apart and tell people where to take each one. The Model Context Protocol project, for example, sends usage questions to its docs and Discussions and keeps its issue tracker for reproducible bugs ([communication channels](https://modelcontextprotocol.io/community/communication), read 2026-11-17). The CC Switch project uses one support page to send usage questions, bugs, documentation problems, feature requests and security reports to different places ([SUPPORT.md](https://github.com/farion1231/cc-switch/blob/main/SUPPORT.md), read 2026-11-17). For Spawn, the rule that platform problems go to Spawn's own doors follows what Spawn's support page and FAQ say. The full research is in [the community patterns digest](../research/oss-community-patterns-2026.md).

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
