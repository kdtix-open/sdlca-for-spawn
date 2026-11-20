# Frequently asked questions

This page is for anyone with a quick question about the SDLCA agent kit. You will get a short answer and a link to the page that explains it in full. What it says about the kit's own behavior was checked against the kit's code on 2026-11-17, and what it says about the git address, `sdlca-look` and the Claude Code option on 2026-11-18. What it says about Spawn comes from the source named next to each statement.

The kit is an unofficial community project. It is not made, reviewed or supported by Spawn. If your question is not here, ask in [Discussions](https://github.com/kdtix-open/sdlca-for-spawn/discussions) or see [SUPPORT.md](../SUPPORT.md) for where to ask what.

## The basics

### What is the SDLCA agent kit, and what do I need to use it?

It is a set of small command-line tools that you run from a clone of this repository on a Linux machine. When you message your AI agent in Spawn chat, the kit runs the agent command you chose, once, inside the right world's git clone, and the agent answers in chat. You need a Spawn account, Bun, git, Python 3, curl, an agent command-line tool such as Claude Code, and Spawn's own client. This repository does not contain Spawn's client, which is proprietary and listed as UNLICENSED on npm, so you install it from npm yourself. The full list, with the versions the maintainers tested, is in [Getting started](getting-started.md#prerequisites).

### Is this official, or affiliated with Spawn?

No. The kit is an independent community project from KDTIX Open. It is not created by, affiliated with, endorsed by, sponsored by or supported by Spawn, and we claim no partner status. Spawn and Savi belong to their owners, and we use their names only to say what the kit works with. See [NOTICE](../NOTICE) and [trademarks and credits](compliance/trademarks-and-credits.md).

### Why is it called an unofficial kit, and why is the repository named sdlca-for-spawn?

Spawn's terms limit the use of its names and marks and bar implying affiliation with Spawn. So we lead with our own name, SDLCA, and use "for Spawn" only as a plain description, the way "for Slack" describes an app. The repository was renamed from `spawn` to `sdlca-for-spawn` before its first push, and the word "unofficial" is there so nobody mistakes the kit for a Spawn product. The name still contains "Spawn", Spawn's terms make no exception for descriptive use, and we have not asked Spawn about it, which is a risk we state openly. See [why the repository is called sdlca-for-spawn](compliance/spawn-rules.md#why-the-repository-is-called-sdlca-for-spawn).

### Which agents and providers work?

Any command-line tool that reads a prompt on standard input, does the work in the current folder and exits can be used. You set it in `SDLCA_AGENT_CMD`. The maintainers tested one tool: Claude Code 2.1, with the read-only and the builder postures. The kit ships no adapters for other tools. Examples for OpenAI Codex CLI, OpenCode, Cursor's command-line agent and Gemini CLI are in [Configuration](configuration.md#other-agent-tools-unverified-examples), marked unverified because we have not run them, so check any example against your provider's own documentation first.

### Does it cost money, and who pays for what?

The kit is free software under Apache-2.0, and you pay for your own computer and for whatever your agent provider charges, so check that provider's terms for automated use. On Spawn, an agent account that a person has linked runs under that person's allowance, and [Spawn's agent guide](https://www.spawn.co/llms-full.txt) (read 2026-11-17) says that includes features that cost them. The kit's own commands do not use those features, but an agent you run might, and the owner can unlink the agent at any time (see [the invite step](getting-started.md#step-2-create-the-agent-account)). We do not know Spawn's current prices, so please ask Spawn. To cap your own spend, lower `SDLCA_MAX_RUNS_PER_HOUR` (default 20) and `SDLCA_AGENT_TIMEOUT` (default 1800 seconds), and set a limit with your provider.

## Safety and data

### Is my data sent anywhere?

The kit sends no telemetry: it has no analytics and never contacts its maintainers. Spawn receives what the kit and Spawn's client send it, which is API calls (with the account's token), chat lines, git fetches (the kit fetches the world's branch before each turn that came from the world's chat) and git pushes. Your agent provider receives each prompt, which includes the chat line that started the turn and whatever the agent reads while it works. Tokens, logs and world clones stay on your machine, although `handler.log` holds whatever the agent prints, which can include other people's chat lines, and `run/failed` holds the raw event of any turn that failed (by default the kit deletes saved events that are more than 30 days old). See [Security model: privacy and retention](security-model.md#privacy-and-retention), and remember that replies appear in the room, where everyone can read them.

### What can the agent do to my computer, and how do I limit it?

The agent runs as your user on your machine, and the kit does not put it in a sandbox. What it can do depends on the agent command you choose, and the listener refuses to start until you choose one. The kit's four Claude Code examples are read-only (reads files and answers in chat), read-only with sight (the same, plus a screenshot of a world the account serves), builder with a tool allowlist (edits files, runs git and Spawn commands, and can push changes that go live), and full autonomy (runs any command, only for a machine and an owner you fully trust). Start read-only, keep the sender list empty, and think about a separate Linux user or a virtual machine, because even the read-only choice can read any file your user can read, tokens included. See the [security model](security-model.md#what-the-agent-can-do-the-postures) and its [hardening checklist](security-model.md#hardening-checklist).

### Who can give the agent orders?

The account's owner, and any Spawn usernames you add to the allowlist for that owner. Everyone else is ignored with no reply, and the log records only their handle. The agent's own handle is always denied, and the sender is read from a structured field of the event, never from chat text. Everyone on the list has the agent's full power on your machine, so the safest list is the empty one, and you add a person with `bin/sdlca-allow spawn add alice carol`. Spawn's terms bar letting others use your account, and whether a listed person counts is a question we have not put to Spawn (see [Spawn rules](compliance/spawn-rules.md)).

### How do I stop it or remove it?

To stop a listener, run `systemctl --user disable --now sdlca-listener@alice.service`, with your own account name. A turn that is running ends with it. To remove a trial setup, follow [Remove everything](getting-started.md#remove-everything), and see [Operations: uninstalling](operations.md#uninstalling) for several accounts. Check each clone for unpushed work first, because deleting a clone deletes commits that were never pushed. Removing the kit does not delete the agent account on Spawn: the owner unlinks the agent in Spawn, which also ends its standing in their worlds.

## Running it

### Can the agent talk to Savi?

No. Spawn says "Savi stays closed to every agent account, linked or not" ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), read 2026-11-17), and a 403 answer called `agent_lane_closed` is final. The kit never tries to reach her. The agent's prompt says it cannot message Savi and tells it to end with an "Ask Savi:" line, so the person can pass the request on. See [rule 11 of the Spawn rules](compliance/spawn-rules.md#savi-and-unattended-work).

### Can my agent have a body of its own?

Yes, a body made from a picture of yours. Run `sdlca-body <account> <picture>` to see the plan, then again with `--apply`: it uploads the picture, has Spawn sculpt a rigged 3D body from it (the person the agent is linked to pays), waits, and wears it. See [Giving an agent a body](operations.md#giving-an-agent-a-body). The agent is not meant to run it, and the tool refuses inside an agent turn. A body shows only while the agent is in a world, and the kit's agent is there only while it takes a screenshot. A second agent can wear the same body for one join, but we could not yet make it the second agent's profile body without a sculpt of its own (see [Giving an agent a body, day zero and day n+1](giving-an-agent-a-body.md)). A face for the agent is planned and not built.

### Can I run it overnight or unattended?

The listener can stay up in the background, but the kit only acts when someone who is allowed messages the agent, and it has no scheduler, loop or timer. Spawn's rule about Savi is "If you're not there, it shouldn't be running" ([Spawn's rules page](https://www.spawn.co/about/what-spawn-is-for), dated 2026-11-05). The agent cannot reach Savi, but we apply the spirit to your agent too, because a linked agent spends the owner's allowance ([rule 12](compliance/spawn-rules.md#savi-and-unattended-work)). So please do not ask for overnight or multi-day work, because the kit cannot tell whether you are still there during a long turn. Each turn stops after 30 minutes by default, and an account starts at most 20 turns an hour.

### Does it work on macOS or Windows?

Only Linux is supported today. The maintainers tested Ubuntu 26.04 under WSL2 (Windows Subsystem for Linux) with systemd, so on Windows use WSL2. Native Windows is not supported, because the tools are bash scripts. macOS is untested and the kit ships no launchd service (planned), though you can run `bin/sdlca-listen` under any supervisor, and the scripts need bash 4.4 or newer, `flock` and `timeout`. See [Getting started](getting-started.md#prerequisites), [Operations: running without systemd](operations.md#running-without-systemd) and the [roadmap](community/roadmap.md).

### What is the Slack bridge, and when will it exist?

It is planned and not built. The idea is to direct your agents from a Slack workspace, with slash commands, reactions as status, file exchange and canvases. Today the repository holds only an example Slack app manifest, an example file for two tokens, and an allowlist that can store Slack member ids, which nothing reads yet. We have set no date. See [Slack bridge](slack-bridge.md) and the [roadmap](community/roadmap.md).

## Accounts and tokens

### How do I add another owner, or a coordinator account?

For another person, make another account from that person's own one-time invite (`bin/sdlca-onboard --owner bob ...`), so each owner has their own agent account, token, listener and logs (see [Operations: adding an account](operations.md#adding-an-account)). For one coordinator that works across several people's worlds, an account name may be grouped, such as `sdlca-for-spawn/alice`, and `bin/sdlca-token` stores, checks and lists the tokens without ever printing one; grouped accounts are for scripts and tools, because a systemd listener name cannot contain a slash. A personal token, which a person makes on their own Spawn tokens page for their own scripts, acts as that person, so everything it posts or pushes appears under their name, and each person should mint and keep their own because Spawn's terms bar letting others use your account. An AI agent should have its own agent account instead, which an owner's one-time invite creates and which other owners can add as an editor of their worlds, because it shows as an agent, needs one token, and is revoked by unlinking. See [Several accounts and worlds](multi-account-and-worlds.md).

### Can I script minting tokens, or reuse my browser session cookies?

No. As far as we know, Spawn publishes no API for minting personal tokens, and a person makes one by hand on the tokens page in their own Spawn settings. Replaying a signed-in browser session, or calling the website's own internal requests, is outside the documented doors Spawn allows: its terms allow automated access only through the APIs and tools it publishes and bar reverse engineering. A session cookie is effectively your account password, and those internal calls change with each Spawn release, so anything built on them breaks. Please mint by hand, use the documented invite flow for agent accounts (`bin/sdlca-onboard`), or ask Spawn for an API, and see [rule 6 of the Spawn rules](compliance/spawn-rules.md#use-only-spawns-documented-doors).

## Spawn and the project

### How do I report a bug in Spawn versus in the kit?

A problem in the kit, such as a failing command, an agent working in the wrong world or a wrong document, belongs in an [issue](https://github.com/kdtix-open/sdlca-for-spawn/issues/new/choose), and the forms ask for the steps that show it. A problem in Spawn itself, such as a broken world, player or website, goes to Spawn: use its in-app "Report a bug" or its [support page](https://www.spawn.co/support), and its FAQ also points to a `#bug-reports` channel in its Discord. We cannot fix Spawn and do not speak for it, and feedback you send to Spawn may become Spawn's under its terms. Never paste tokens, invite codes, other people's messages, or any other session, join or login credential (including values printed by `spawn client join`) anywhere, and for a security problem in the kit follow [SECURITY.md](../SECURITY.md).

### Can I contribute if I am not a programmer?

Yes, and you do not need a Spawn account. Trying the quick start and telling us where you got stuck, fixing a sentence in the docs, answering a question in Discussions, testing on another Linux system and telling us when Spawn changed all help. Start with [CONTRIBUTING.md](../CONTRIBUTING.md) or the [welcome page](community/welcome.md). Nobody minds a beginner's question.

### Is AI-assisted code accepted?

Yes. We build this project with AI agents ourselves and welcome AI-assisted work. A named person is accountable for every change, you tell us when an AI tool did more than spelling, formatting, autocomplete or a mechanical rename (a section in the pull request and an `Assisted-by:` line in the commit), and only a person signs off under the Developer Certificate of Origin. Autonomous agents that open pull requests or issues with no person reading them first are not accepted. The policy is a first draft that no lawyer has reviewed, and it is in [AI-assisted contributions](contributing/ai-assisted-contributions.md).

### What license applies to my own world content?

Not ours. The Apache-2.0 license covers what we wrote in this kit, not your world. Your world's content falls under Spawn's terms and your own choices, and [Spawn's FAQ](https://www.spawn.co/about/faq) (read 2026-11-17) says shared or third-party assets keep their own licenses, so check anything you bring in. The kit makes no claim on your world: clones live on your machine, and none of their content is copied into this repository. If you contribute here, your contribution is under Apache-2.0, so send nothing from a world unless you may license it that way.

### What happens when Spawn changes its rules?

Spawn changes its terms and guides often, says changes take effect at once, and can end an account for any reason, so the kit can stop working without warning. We re-check Spawn's rules every month: a reminder issue opens on the first of the month, a person re-reads the pages, and the "Last verified" date on [the rules page](compliance/spawn-rules.md) is updated. If a change affects what the kit may do, we hold the next release and say so in the release notes. If you notice a change first, please use the "Spawn changed and the kit broke" issue form.

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
