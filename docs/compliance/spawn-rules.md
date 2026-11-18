# The Spawn rules this project follows

This page is for anyone who wants to know which of Spawn's rules the SDLCA agent kit follows, where each rule comes from, and which part of the kit honors it. You will also find what changed recently, how we re-check the rules every month, why the repository has the name it has, and what we could not verify.

**Last verified: 2026-11-17.**

## Read this first

- **We are unofficial.** This project is not made, reviewed or supported by Spawn. Spawn's own pages are the source of truth. If this page and Spawn disagree, Spawn is right, and we want to hear about it (use the "Compliance or attribution concern" form on the [issue chooser](https://github.com/kdtix-open/sdlca-for-spawn/issues/new/choose)).
- **This is our reading, not legal advice.** The rules are Spawn's words. The summaries are ours. A human maintainer should ask Spawn about anything unclear, and a lawyer should review anything marked **Risk** below.
- **How it was checked.** Our research read Spawn's public pages on 2026-11-17, without signing in, joining Spawn's Discord, using a token or calling its API. This page was written from that research. Every row below says when its source was read.
- **No permission has been requested or received.** As of 2026-11-17 nobody has asked Spawn for written permission to use its name, and Spawn has not given any. See [Why the repository is called sdlca-for-spawn](#why-the-repository-is-called-sdlca-for-spawn).
- **Spawn's Terms bind each person who uses Spawn, not this kit.** Unless a file says otherwise, everything we wrote in this repository (code, documentation and templates) is licensed under Apache-2.0. The Code of Conduct is adapted from the Contributor Covenant 2.1, which its authors release under CC BY 4.0. The license does not cover Spawn, Savi, or any other party's names, code, art or documentation, or the content of your own worlds, and it does not change Spawn's Terms. Spawn's Terms say that "you" includes anyone acting as your agent, so, in our reading, the person who runs the kit answers for what their agent does ([Terms of Service](https://www.spawn.co/terms-of-service), read 2026-11-17).
- **Spawn can change or end things at any time.** Its Terms let it change them with immediate effect and suspend an account for any reason. The kit can stop working without warning.

## The good news

Spawn says outside coding agents are welcome. Its rules page lists "Bring your own AI agent into your world" as allowed, and says the agent can playtest, play alongside you or build ([what Spawn is for](https://www.spawn.co/about/what-spawn-is-for), dated 2026-11-05, read 2026-11-17). Its FAQ names Codex and Claude Code as examples ([Spawn FAQ](https://www.spawn.co/about/faq), read 2026-11-17). Spawn also publishes an agent API and its own client for exactly this. The kit stays on those doors. That is not an endorsement of this kit by Spawn: Spawn has not reviewed it.

## Where the rules live

Spawn has no single rulebook for people who build tools. We found no developer terms, API terms, brand guidelines, acceptable-use policy, community guidelines or copyright-notice page on www.spawn.co (the usual addresses returned "not found" on 2026-11-17). The rules are spread over these pages:

- [Terms of Service](https://www.spawn.co/terms-of-service), last revised 2026-10-09 (cited below as "Terms").
- [What Spawn is for (and what it isn't)](https://www.spawn.co/about/what-spawn-is-for), dated 2026-11-05 (cited as "rules page").
- [FAQ](https://www.spawn.co/about/faq), undated.
- Spawn's agent guides: [short](https://www.spawn.co/llms.txt) and [long](https://www.spawn.co/llms-full.txt), both undated, and the machine-readable [API description](https://www.spawn.co/openapi.json).
- The [Spawn client's page on npm](https://www.npmjs.com/package/@spawnco/client) and [its registry entry](https://registry.npmjs.org/@spawnco%2fclient), for its license.

## The rules

In the last column, **Yes** means the kit does it today, **Partly** means it does some of it and the text says what is missing, **Docs only** means we only tell people, and **Risk** marks a reading that a lawyer should review. Rules are in groups. We keep the numbers fixed, so you can refer to them in issues.

Our research read every source below on 2026-11-17.

### Names, marks and affiliation

| # | The rule, in our words | Source | Retrieved | Where the kit honors it |
| --- | --- | --- | --- | --- |
| 1 | Say plainly that the kit is unofficial and not affiliated with Spawn. Do not pretend to be Spawn or speak for it. | [Terms](https://www.spawn.co/terms-of-service), sections 4(p) and 16 | 2026-11-17 | **Yes.** [NOTICE](../../NOTICE), the footer of every page in `docs/`, the README, the agent prompt (`templates/handler-prompt.md`, which tells the agent it is "not Spawn staff"), the first-reply rule in [AGENTS.md](../../AGENTS.md), and the example Slack manifest. |
| 2 | Do not use Spawn's names or marks as the name of something that is not Spawn's. Do not adopt a confusingly similar name. Do not claim a partnership: Spawn decides who is a partner. | [Terms](https://www.spawn.co/terms-of-service), sections 2(c), 4(k), 9 and 16 | 2026-11-17 | **Yes, with a Risk.** The kit and its commands use our own name (`sdlca-*`). "For Spawn" appears only in plain descriptive sentences and in the repository name. We never use "official", "partner" or "certified" to describe the kit's relationship with Spawn. The Terms, read literally, bar using Spawn's names with "any product or service that is not Spawn's" and Spawn publishes no exception. See [the name note](#why-the-repository-is-called-sdlca-for-spawn). |
| 3 | Do not use Spawn's or Savi's logos, art, fonts or screenshots of Spawn's interface. Do not copy Spawn's docs, skills, `llms.txt` or world guide files beyond short attributed quotes. Spawn states no license for them. | [Terms](https://www.spawn.co/terms-of-service), sections 4(j) and 16; [short guide](https://www.spawn.co/llms.txt) and [API description](https://www.spawn.co/openapi.json) (no license text in either) | 2026-11-17 | **Yes.** The repository holds no Spawn images or fonts and no copied Spawn text. We link and paraphrase. A quote is 25 words or fewer and comes with its URL. See hard rule 9 in [AGENTS.md](../../AGENTS.md) and the checklist in the pull request template. |
| 4 | Do not ship content from anyone's world. Other creators' work is licensed to other users only through Spawn's own features. The starter files Spawn puts in a world are Spawn's. | [Terms](https://www.spawn.co/terms-of-service), section 6; [FAQ](https://www.spawn.co/about/faq) ("Who owns my game and its assets?") | 2026-11-17 | **Yes.** Tests and examples use invented data (alice, bob, `@alice/game-1`). World clones live in the person's own `SDLCA_REPOS` folder, outside this repository. The pull request template asks contributors to confirm they copied nothing from a world. |
| 5 | Do not bundle, vendor, mirror or republish Spawn's client, `@spawnco/client`. It is listed as UNLICENSED, so no one has been given a right to copy it. People install it from npm. | [npm registry entry](https://registry.npmjs.org/@spawnco%2fclient); [Terms](https://www.spawn.co/terms-of-service), sections 2(d) and 4(m) | 2026-11-17 | **Yes.** No Spawn package is in `package.json` or `bun.lock`. `scripts/install.sh` checks that `spawn` is installed and prints `bun add -g @spawnco/client` if not. See [third-party licenses](third-party-licenses.md#the-spawn-client). |

### Use only Spawn's documented doors

| # | The rule, in our words | Source | Retrieved | Where the kit honors it |
| --- | --- | --- | --- | --- |
| 6 | Use only what Spawn publishes: its agent API, the client Spawn publishes, installed by the person, and git over https with that person's own token. No scraping, no undocumented endpoints, no reverse engineering, no reading the engine's internals. The Terms bar automated systems "other than through the application programming interfaces and other tools that Spawn makes available for that purpose". | [Terms](https://www.spawn.co/terms-of-service), sections 4(n), 4(l) and 2(d); [Spawn's engine skill](https://www.spawn.co/.well-known/agent-skills/spawn-engine/skill.md); [API description](https://www.spawn.co/openapi.json) | 2026-11-17 | **Yes for the kit's own code, Partly for agents.** The kit runs Spawn's client (`spawn events`, `spawn login`, and `spawn client join` and `leave`), clones worlds over git from Spawn's git host, and calls only `/api/agent/v1/me`, `/api/agent/v1/chat/room`, `/api/agent/v1/chat/dm`, `/api/social/friends` and `/api/social/relation`, which are in Spawn's published API description. `sdlca-api` is a general wrapper: it keeps the token on Spawn's origin but does not limit which paths an agent asks for. The prompt tells the agent to use documented paths, and nothing enforces it. **Risk:** Spawn has not said whether it counts a third-party kit as one of "the tools that Spawn makes available". We read the published API as covered. |
| 7 | Do not disguise automation to get in as a guest. A browser that is not signed in is refused on creators' worlds. Spawn documents two ways in: its own client, and its `login-link` call, which signs a browser that a script drives in as your own account. Do not use an unsigned automated browser. | [Short guide](https://www.spawn.co/llms.txt), "Make a game, by yourself"; [API description](https://www.spawn.co/openapi.json) | 2026-11-17 | **Yes.** `sdlca-look` uses the first way: the page Spawn's client prints, with software rendering on this machine. `lib/shot.mjs` attaches over a debugging port and refuses an endpoint that is not on this machine. |
| 8 | Tokens are secrets. Keep them out of logs, commits and screens. | [Long guide](https://www.spawn.co/llms-full.txt), "Sign Up" | 2026-11-17 | **Yes, with a limit.** Token files are mode 0600. The token goes to `curl` on its standard input, never on a command line. `sdlca-api` and `sdlca-say` send it only to Spawn's origin and never follow a redirect. `sdlca-on-chat` removes `SPAWN_TOKEN` before it runs the agent. The kit's own log lines hold metadata, not chat text. The limit: an agent running as the same user can read the token file. See [Configuration](../configuration.md) and the [security model](../security-model.md). |
| 9 | One person, one invitation. Link an agent to a person only with the one-time code that person gives you: the code is the consent. Do not make extra or throwaway accounts, or sign up in bulk, to get around limits or a suspension. | [Rules page](https://www.spawn.co/about/what-spawn-is-for), "You can't"; [long guide](https://www.spawn.co/llms-full.txt), "Link to a Person" | 2026-11-17 | **Yes.** `sdlca-onboard` needs a code from the owner. The kit's code never calls Spawn's signup endpoint and never makes or reuses codes. It creates an account only through `spawn login --invite`, run by Spawn's client. One account belongs to one owner. |
| 10 | Do not turn the kit into a hosted service, reseller or go-between for other people, and do not share one person's account among several humans. | [Terms](https://www.spawn.co/terms-of-service), sections 2(e), 3, 4(m) and 4(o) | 2026-11-17 | **Yes by design, with a Risk.** The kit is run by each person on their own machine. Each account has its own token and owner. There is no hosted part. **Risk:** an owner can put another Spawn user on the allowlist so that person can start work. That person never holds the token, but we have not established that this is allowed by section 3. See [what we could not verify](#what-we-could-not-verify). |

### Savi and unattended work

| # | The rule, in our words | Source | Retrieved | Where the kit honors it |
| --- | --- | --- | --- | --- |
| 11 | Agents cannot message Savi. Spawn writes: "Savi stays closed to every agent account, linked or not." Never try. A 403 `agent_lane_closed` answer is final. | [Long guide](https://www.spawn.co/llms-full.txt), "The Budget Law" | 2026-11-17 | **Yes.** No code in the kit calls a door to Savi. The prompt tells the agent it cannot message her and to end with an "Ask Savi:" line for the person instead. Commit messages serve as notes to her. `sdlca-say` does not retry a 403. Savi events in the inbox are only logged. |
| 12 | Do not run Savi unattended. Spawn writes: "If you're not there, it shouldn't be running." The rule is about Savi, and a linked agent spends the person's own allowance, so we apply its spirit to both. | [Rules page](https://www.spawn.co/about/what-spawn-is-for), "You can't" | 2026-11-17 | **Partly.** Work starts only when the owner, or a person the owner put on the allowlist, sends a message. The kit has no scheduler, loop or timer. Each turn has a time limit (30 minutes by default) and an account may start at most 20 turns an hour (`SDLCA_MAX_RUNS_PER_HOUR`). The kit cannot tell whether the owner is still there while a long turn runs, so do not ask for overnight or multi-day work. |
| 13 | Spawn is for making things people play on Spawn. Do not use it as a free asset or video generator for use elsewhere, do not port Spawn games to other engines or platforms, do not rebuild platform features (custom login, payments, unmoderated chat), and stay inside Spawn's content lines. | [Rules page](https://www.spawn.co/about/what-spawn-is-for), "You can't" | 2026-11-17 | **Docs only.** The kit ships no workflow, game template or example for any of these. It cannot stop a person from asking their own agent to do one. Each person is responsible for that. |
| 14 | Spawn says: an unlinked agent account cannot use the generation lanes (403 `agent_lane_closed`), a linked account runs on the person's allowance, and a world's cover is the creator's to pick, so an agent asks the person. **Our practice, not a Spawn rule:** also ask the person before publishing, approving build requests or invites (which give edit rights), and deleting a world. | [Long guide](https://www.spawn.co/llms-full.txt), "Make" and "With People" (for what Spawn says) | 2026-11-17 | **Partly.** The prompt tells the agent to say what it will change before changing something shared, and that publishing is a separate step the owner asks for. The only thing the kit approves by itself is a friend request from the account's owner. No code limits which methods `sdlca-api` may send, so the posture you choose in `SDLCA_AGENT_CMD` is your protection. See [Configuration](../configuration.md#the-three-postures). |

### Limits

| # | The rule, in our words | Source | Retrieved | Where the kit honors it |
| --- | --- | --- | --- | --- |
| 15 | Follow Spawn's rate limits and retry hints. Spawn writes: "Follow Retry-After on 429 or 503." Treat a typed refusal as an answer, and do not retry around a closed door. | [Short guide](https://www.spawn.co/llms.txt); [API description](https://www.spawn.co/openapi.json) | 2026-11-17 | **Partly.** `sdlca-say` retries a 429 (waiting for `Retry-After` or `retry_after_ms`) and a 5xx (with a growing pause), up to six tries in all, then stops. `sdlca-api` and `sdlca-friends` make one try and do not retry. The systemd unit backs off between restarts, up to five minutes, and does not restart on exit status 78. |
| 16 | Chat lines are at most 200 characters, about five lines in 10 seconds and 20 a minute into one room. Everyone in the room can read a line, and Spawn moderates it. | [API description](https://www.spawn.co/openapi.json), chat operations; [long guide](https://www.spawn.co/llms-full.txt), "The Chat" | 2026-11-17 | **Partly.** `sdlca-say` splits a reply into numbered lines of 200 characters or fewer, sends them 2.2 seconds apart (`SDLCA_SAY_PAUSE`) and sends at most 8 lines a call (`SDLCA_SAY_MAX_LINES`). The 20-a-minute total is not counted across separate calls. The hourly turn cap in rule 12 limits it. |
| 17 | Read the inbox through Spawn's event stream, or poll no more than 30 times a minute. | [Long guide](https://www.spawn.co/llms-full.txt), "Your Inbox" | 2026-11-17 | **Yes.** The listener uses Spawn's client stream (`spawn events`) and resumes from a saved cursor. It does not poll. |
| 18 | Unlinked agent accounts have small budgets: about 3 worlds a day, 2 bodies at once, 60 body mints a minute, 1,000 distinct bodies a day and 3,000 pushes per world per hour. They never use Spawn's inference or GPU until a person links them. These are Spawn's current numbers and they can change. | [Long guide](https://www.spawn.co/llms-full.txt) and [docs page](https://www.spawn.co/docs/the-budget-law), "The Budget Law" | 2026-11-17 | **Partly.** The kit creates no worlds. `sdlca-look` joins one body, ends it after 300 seconds and leaves when it exits. The account is created from the owner's code, so it is linked to that person (the code carries the link). Open item: `sdlca-look` names each body with a per-run name, and we have not tested whether Spawn counts that as a new distinct body each time. |
| 19 | Accept friend requests only from people you mean to. Do not add friends in bulk: Spawn paces it. | [Long guide](https://www.spawn.co/llms-full.txt), "With People"; [API description](https://www.spawn.co/openapi.json) | 2026-11-17 | **Yes.** `sdlca-friends` accepts a pending request only from the account's owner (compared without regard to case). The kit never sends a friend request. |

### Content, feedback and the person's own duties

| # | The rule, in our words | Source | Retrieved | Where the kit honors it |
| --- | --- | --- | --- | --- |
| 20 | Report Spawn platform bugs and abuse to Spawn, and do not publish exploitable platform bugs in public. | [Terms](https://www.spawn.co/terms-of-service), section 4(s); [FAQ](https://www.spawn.co/about/faq); [Spawn support](https://www.spawn.co/support) | 2026-11-17 | **Docs only.** The issue chooser sends Spawn problems to Spawn's support page. [CONTRIBUTING.md](../../CONTRIBUTING.md) says our issues are for the kit. |
| 21 | Anything you send Spawn as feedback may become Spawn's property. | [Terms](https://www.spawn.co/terms-of-service), section 19 | 2026-11-17 | **Docs only.** [CONTRIBUTING.md](../../CONTRIBUTING.md) says so next to the feedback advice. What you send this project is covered by its Apache-2.0 license. |
| 22 | Do not post tokens, or any other session, join or login credential (including values printed by `spawn client join`), other people's chat or personal data in public. | [Terms](https://www.spawn.co/terms-of-service), section 4(d); [long guide](https://www.spawn.co/llms-full.txt), "Sign Up" | 2026-11-17 | **Docs only.** The pull request template and issue forms say it, and [AGENTS.md](../../AGENTS.md) forbids agents from printing or committing tokens. `.gitignore` excludes token and env files. |
| 23 | The Terms apply to the person who uses Spawn: their own account, age rules, content rules, third-party asset licenses, sanctions rules, arbitration and indemnity. | [Terms](https://www.spawn.co/terms-of-service), the introduction and sections 3, 5, 10 and 23 to 25 | 2026-11-17 | **Docs only.** The README and [Getting started](../getting-started.md#before-you-start-spawns-terms-and-you) tell people that Spawn's Terms apply to them, not to the kit, and that Spawn's client and their use of it are covered by those Terms. This page links to the Terms. Spawn's Terms set a minimum age and parental-consent rules and contain a sanctions clause (read 2026-11-17). The person who runs the kit must meet them. We do not interpret them; the age wording is one of the places where the Terms disagree with themselves (see [what we could not verify](#what-we-could-not-verify)). Spawn rooms can include young people, and your agent forwards what it reads there to your model provider. |

### Known gaps

These are the main places where the kit falls short of a rule or leaves a question open, gathered in one list. Anyone may open an issue with the compliance form.

- `sdlca-api` does not limit which paths or methods an agent may use on Spawn's origin.
- `sdlca-look` uses a per-run body name, and the effect on Spawn's daily count of distinct bodies is untested.
- The kit does not listen for Spawn's `agent_unlinked` event, so it will not notice by itself when a person unlinks the agent.
- The 20-lines-a-minute chat total is not counted across separate calls.
- The kit cannot tell whether a person is present during a long turn.

## What changed recently

Spawn changes these documents often. Treat everything here as a snapshot.

| Date | What changed | Source |
| --- | --- | --- |
| 2026-10-09 | The Terms were rewritten (their last-revision date). Compared with the 2026-10-08 copy in the Internet Archive, the clause on automation now allows Spawn's own APIs and tools, a Partner Program section appears, the license other users get to your content now mentions adapting and remixing, and the AI wording changed. Changes take effect immediately (section 26). | [Terms](https://www.spawn.co/terms-of-service); Internet Archive copies from [2026-10-08](https://web.archive.org/web/20261008212303/https://www.spawn.co/terms-of-service) and [2026-11-10](https://web.archive.org/web/20261110121847/https://www.spawn.co/terms-of-service) (third-party copies) |
| 2026-11-05 | Spawn dated its rules page. It lists what is allowed (including bringing your own agent), and what is not (automating Savi, using Spawn as a free generator, porting out, extra accounts, rebuilding platform features, content over the line). The archive first holds it on 2026-11-10. | [Rules page](https://www.spawn.co/about/what-spawn-is-for) |
| Label of 2025-04-01 | Spawn's Privacy Policy still says "Last Updated: April 1, 2025", but archived copies show its text changed. Do not trust that label. | [Privacy Policy](https://www.spawn.co/privacy-policy) |

Other things to keep in mind:

- The FAQ and the agent guides carry no date. The numbers in them are examples at the time we read them, and one example in the long guide shows a different daily body cap from its own text. Read the numbers from your account at run time.
- Spawn describes itself as in beta since February 2026. Anything written about it before then refers to an earlier product ([long guide](https://www.spawn.co/llms-full.txt), "The Team").
- Spawn's pages disagree with each other in places (the age wording in the Terms, whether the weekly jam is still running, whether paid access is open to makers). We do not rely on any of those points.

### History of this page

| Date | Change |
| --- | --- |
| 2026-11-17 | First version. All rows read on this date. |
| 2026-11-17 | Review pass before the first push: rows 7, 14, 22 and 23 reworded, the license, trademark and name notes updated, and a place added to record our question to Spawn. No source was re-read. |

## How we re-check every month

A person does this, not an AI agent. An agent may help compare text, but a person reads the pages and takes responsibility for the result.

1. **The reminder.** The workflow [Monthly compliance check](../../.github/workflows/compliance-reminder.yml) runs at 14:17 UTC on the first day of every month, and a maintainer can also start it by hand from the Actions tab. It opens an issue titled "Monthly check: re-verify Spawn's terms and rules (YYYY-MM)" with the `compliance` label. If an open issue with that label and "Monthly check" in its title already exists, it does nothing, so close last month's issue when you finish.
2. **The checklist** in that issue, about 20 minutes:
   - Re-read Spawn's [Terms of Service](https://www.spawn.co/terms-of-service) and note the "last revised" date.
   - Re-read [what Spawn is for](https://www.spawn.co/about/what-spawn-is-for) and the [FAQ](https://www.spawn.co/about/faq).
   - Skim [llms.txt](https://www.spawn.co/llms.txt) and [openapi.json](https://www.spawn.co/openapi.json) for changes to agent rules, limits or endpoints.
   - Check the [Spawn client on npm](https://www.npmjs.com/package/@spawnco/client): its version and its license.
   - Update this page with what changed and the date you checked, even if nothing changed.
   - Open issues for anything in the kit or the docs that no longer matches.
3. **Record it here.** Change the "Last verified" date at the top, update the "Retrieved" date of each row you re-read, add a line to the history table above, and add a row to "What changed recently" if Spawn's text changed.
4. **If something changed that affects what the kit may do,** open an issue labeled `compliance` and `upstream:spawn`, hold the next release until a maintainer has decided, and say so in the release notes. [Releasing](../contributing/releasing.md#the-monthly-check-of-spawns-terms) has the release checklist.
5. **Rules for the person checking.**
   - Read the real pages. If you cannot reach one, say so in the issue. Do not fill the gap from memory.
   - Paraphrase. Quote at most 25 words from a page, and give its URL.
   - Do not paste secrets or personal data into the issue. The check does not need you to sign in to Spawn or join its Discord. If you read Spawn's Discord under your own account, write only what you found and do not paste its text.
   - Check again on release day, even if this month's issue was closed last week.

## Why the repository is called sdlca-for-spawn

Spawn's Terms limit how anyone may use its names and marks. They bar names that might be confusingly similar to Spawn's, bar using Spawn's trade names with a product that is not Spawn's, and bar misrepresenting affiliation with Spawn (sections 2(c), 4(p) and 16 of the [Terms](https://www.spawn.co/terms-of-service), read 2026-11-17). Spawn publishes no brand page, logo rules or process for asking permission. The usual addresses for them returned "not found" on 2026-11-17.

So the project leads with its own name. "SDLCA" is KDTIX Open's name for its agent team, and the kit works with any agent name. "For Spawn" says what the kit works with, in the same plain way that "for Slack" does. The repository was renamed before its first push, as part of that plan. This follows the 'rename and use for Spawn only descriptively' option from our research; the remaining risk is that Spawn's Terms make no exception for descriptive use.

What the name does not do:

- **It is not permission.** The name still contains the word Spawn, and the Terms, as written, make no exception for descriptive use. We have not asked. **Risk:** a lawyer should review this, and a human maintainer should ask Spawn. Questions worth asking: may we say "for Spawn" in the repository name and description, does Spawn prefer that its name is not in the repository or Slack app name, is there wording it wants in our disclaimer, is there a path for tools like this one, and is there anything in the Terms it wants us to highlight.
- **It has not been asked about yet.** As of 2026-11-17 no question has been sent. When a named maintainer sends one, write the date, the sender's role and the reply (summarized, with a link) in this bullet, and change the first bullet in "Read this first" to match, for example: "As of <ISO date>, <role> asked Spawn at contact@spawn.co; <no reply yet | reply summarized and linked>. This is not permission." Do not claim any endorsement. The steps before an announcement are in [GitHub settings for maintainers](../maintainers/github-settings.md#before-you-announce-the-project).
- **It is not a mark.** Nothing in this project claims Spawn's or Savi's names as ours. They belong to their owners. See [trademarks and credits](trademarks-and-credits.md).
- **It does not stand alone.** The notice that this project is unofficial goes with it everywhere: [NOTICE](../../NOTICE), the README and the footer of every page in `docs/`.

The word "spawn" is also used by unrelated projects and products, which is another reason to lead with our own name.

## What we could not verify

Please do not read any of these as a claim either way.

- **Spawn's Discord rules.** Reading them needs a login, and we did not join. Spawn tells people to ask in its Discord before starting something doubtful, and we have not done that.
- **The Partner Program terms.** The page is behind a sign-in. All we have is one section of the Terms and one FAQ sentence. We do not claim partner status, and we do not know whether a tool project can have it.
- **Any trademark application or registration for Spawn or Savi.** We make no statement about the status of any trademark application or registration for Spawn or Savi; check the USPTO or your own country's register. Spawn and Savi belong to their owners, and nothing here should be called registered.
- **Whether Spawn welcomes third-party kits.** No Spawn document says yes or no. Spawn welcomes outside agents and publishes an agent API, but has not said whether it sees kits like this one as welcome. No written permission has been requested or received as of 2026-11-17.
- **Account sharing.** Whether letting an allowlisted second person start work on an owner's agent fits section 3 of the Terms (rule 10).
- **Spawn's own inconsistencies.** The Terms have an unclear age statement, no governing-law clause that we found, and a copyright-agent entry we could not check. We do not interpret them. Read the Terms yourself, and ask a lawyer if it matters to you.
- **The numbers.** Spawn's limits (rule 18) can change, and one example in its guide differs from its text.
- **Files inside a world and the engine.** No license is stated for starter files, engine documents or the engine itself. We treat them as Spawn's and have not read them in full.
- **The Privacy Policy and Data Privacy Agreement.** The Privacy Policy label is more than 12 months old, and the agreement is undated. We read them only for what matters to tool builders.
- **What the client does with a per-run body name** (rule 18).

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
