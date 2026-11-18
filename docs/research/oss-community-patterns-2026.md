# Open-source community patterns, 2026

This page is for the maintainers of the SDLCA agent kit, and for anyone who wants to reuse our research method: it tells you which five open-source communities we studied in November 2026, why we chose them, which of their patterns we adopted, adapted, planned or avoided, and how to repeat the work in six months.

**Research date: 2026-11-17. Next refresh due by 2027-05-17.** Every number below is a snapshot. Numbers about other projects were not re-fetched when this page was written; they come from our research run, and each one names its source and the date we read it.

## What we took away

1. **Say where each kind of question goes, at the front door.** Four of the five communities turn off the blank issue form and send questions, security reports and other kinds of problems to better places.
2. **Ask for evidence and a person who understands the change.** Asking for a reproduction, a test result and an explanation in the author's own words worked better than trying to spot AI-written text (see [what the AI policies taught us](#what-the-ai-policies-taught-us)).
3. **Keep the label set small, and keep it true.** Most of the five have a label, or a label description, that disagrees with their own automation.
4. **Promise only the response times you can keep, then measure them.** The communities with the fastest replies were fast because a bot or one owner answered. A stated review time that was not met cost one project credibility.
5. **Write governance down, lightly.** The one community with a published ladder and written decisions (MCP) also had the clearest written "where to start" for newcomers.
6. **Ship the health files on day one,** including a Code of Conduct with a contact someone really reads. Three of the five lacked one or had no working contact.
7. **Keep money and sponsor links away from the places contributors read first.**

These five are not the five fastest by stars. We balanced growth with governance diversity; see [how we chose the communities](#how-we-chose-the-communities) and the [runner-ups](#runner-ups-and-why-we-did-not-choose-them).

## What we did, and what we did not do

- **We studied structure and ideas. We copied no text.** Everything here is in our own words. Where this page quotes another source, the quote is under 25 words and has a link. The licenses of the studied projects (MIT for four of the five; the fifth mixes Apache-2.0, MIT and CC BY 4.0) would let us reuse wording if we kept their notices, but we did not need to. If we ever adapt wording, we will keep the notice and credit the source. Credits are on the [names and credits](../compliance/trademarks-and-credits.md) page.
- **We only read public pages and public data.** We made read-only requests, signed in nowhere, joined no Discord or Slack server, and made no calls to Spawn's API.
- **Nothing here is an endorsement,** and none of these projects has reviewed or approved ours. Their names belong to their owners.
- **AI research agents did the reading.** People directed the work and did not re-check every figure. Treat this page as a careful first pass, not an audit.

## How we chose the communities

### The question

Which fast-growing, AI-adjacent open-source communities of 2026 should a new, small, unofficial project study before it opens its doors, so that it welcomes newcomers, copes with a flood of AI-written contributions, and stays inside another company's rules? That company is Spawn. The research agents were given this project context.

### Three lenses and a judge

Three research agents worked separately and in parallel, each with its own lens. A fourth agent, the judge, re-checked their evidence and made the choice.

| Lens | What it looked for | Main sources |
|---|---|---|
| Growth metrics | The fastest-growing AI and developer-tool projects of 2026, picked only from cited evidence | GitHub Octoverse 2026, the Runa Capital ROSS Index, OSS Insight, Star History, Linux Foundation releases, GitHub's REST API, and Internet Archive captures used as star baselines |
| Community health | Communities with proof of healthy contributor activity, not stars alone | GitHub's REST API, the OpenSSF Scorecard public API, Octoverse, and projects' own governance pages |
| AI-native relevance | AI agents and agent tooling, game-engine and creator communities with AI or mod ecosystems, and Spawn's own ecosystem; a project's own claims were marked as marketing claims | The same, plus the projects' own pages |

About 45 distinct projects came out of the three lenses. The judge then applied three gates:

1. **Real 2026 growth,** confirmed by at least two independent sources (for example GitHub's API plus an Internet Archive baseline, Octoverse, or the ROSS Index).
2. **A visible contributor path:** the project tells newcomers how to take part.
3. **Public artifacts** to study: contribution guide, issue forms, labels, boards, Discussions.

Next, the judge **balanced the five by governance model** instead of taking the top five by growth. Octoverse's own split between community or independent projects and single-vendor projects served as an independent label. The ranks reflect overall fit for our kit: closest peer, quality of structure, and neutrality between agent providers. They do not reflect raw star growth.

### What the judge re-checked

The judge re-read current stars, forks, licenses, contributor counts, label counts and key policy files for 11 repositories (all matched within normal drift); compared merged pull request counts for the 12 months to 2026-11-17 against the 12 months before; read the Internet Archive baselines directly; read the Octoverse 2026 lists twice; and read the ROSS Index editions, Linux Foundation releases and Spawn's public pages.

### The deep studies

Each chosen community then got its own deep study, with the same fifteen questions: governance and decisions; the contribution funnel; issue and pull request forms and contact links; label taxonomy; triage and bots; roadmap and project boards; Discussions, forum and chat split; docs layout; AI-assisted contribution and agent policy; security reporting; releases, changelog and credit; inclusion, Code of Conduct, translations and recognition; funding; metrics; and what feels welcoming or not. Three companion studies ran alongside: how Spawn's own community is organized, which neighboring projects exist (prior art), and which conventions our own organization already uses. A fourth compared the AI contribution policies of about two dozen projects. That one fed [AI-assisted contributions](../contributing/ai-assisted-contributions.md).

### As-of dates

The research ran on the evening of 2026-11-17 US Pacific time, which was already 2026-11-18 on GitHub's UTC clocks. We write "2026-11-17" for everything we read in that session, including GitHub figures stamped 2026-11-18 UTC.

- **Octoverse 2026** was published 2026-10-28 and updated 2026-11-06. Its data window is 2025-10-01 to 2026-09-30. It publishes ranks, not numbers.
- **Star baselines** come from Internet Archive captures: 2025-11-18 (OpenCode and CC Switch), 2026-01-30 (OpenClaw) and 2025-11-11 (the MCP specification repository, which is 12 months and 6 days old, so we flag it).
- **Staleness rule:** we flagged anything older than 12 months and did not use it as evidence. We did not use Octoverse 2025.

### Honest caveats

- **Stars are a weak signal.** One of our five has about 305,000 stars, yet in a sample of 40 recent outside pull requests only 17 got any human comment. A skills collection that the judge passed over has about 327,000 stars and only 9 contributors. Octoverse's "most engaged" list blends stars with forks and with the number of different people who open pull requests and issues, and it lists none of that first project.
- **Metrics decay in weeks.** One project's daily star growth fell about sevenfold within its first year (our arithmetic from three data points). Another had published no release for 48 days against a promise of one every two weeks. Several policies changed while we were reading them.
- **Selection bias.** We chose from lists of fast growers. Survivors and loud projects are over-represented, everything is hosted on GitHub, and no game-engine community cleared the growth bar. What works at 400,000 stars may not suit a project with a handful of contributors.
- **Self-reported and conflicting figures.** Event counts and sign-up counts in one foundation post are marketing. Contributor counts include anonymous commit emails: one project shows 3,806 contributors with them and 387 linked accounts without. Counts of poisoned skills in one registry disagree across sources. The ROSS Index's growth multiples are Runa's own and pages carry no publication date.
- **Small samples.** First-response times come from samples of 40 to 80 items and count any non-author, non-bot comment as a human reply. In three of the five communities we sampled, the first reply was usually a bot.
- **GitHub's community profile score is not a quality signal.** It ignored the issue forms at four of the five communities, and one project's score of 100 was months old.
- **A fast-moving platform.** Spawn changes its rules often. Our statements about Spawn carry dates and are re-checked monthly (see [the rules we follow](../compliance/spawn-rules.md)).

### What we could not verify

- Any Discord server: we did not join one, so channel lists, rules, moderation and welcome flows are unread. Member counts come from public invite metadata at one moment.
- Fields and views of public GitHub Project boards. Reading them needs a signed-in browser or a write-type API call, and neither was allowed.
- Whether MCP's rule for AI agents is enforced by a bot, whether any of the five enforces a CLA or DCO outside its workflow files, and the bylaws and finances of the OpenClaw Foundation.
- Primary reports on the ClawHub registry poisoning; we read secondary coverage only.
- Spawn's partner terms, how mods are reviewed or reported, why SpawnJam ended, and any Spawn brand policy. We found none that is public.
- Trademark registrations for any name here.

### Process notes for people who reuse the method

- All requests were reads. One call in the OpenCode study was sent as a write request by mistake and was rejected with an error (HTTP 422), so nothing was created or changed.
- Two agents wrote into the same scratch folder, mixed up label counts, and the numbers were recomputed. Give every agent its own folder.

## The five communities

| Community | Governance model | License | Stars (2026-11-17) | Growth evidence |
|---|---|---|---|---|
| [OpenClaw](#openclaw) | Founder-created, foundation-hosted, founder-steered | MIT | about 394,700 | 106,177 stars on 2026-01-30; Octoverse 2026 #1 on the most-engaged list for community or independent projects |
| [MCP and the Agentic AI Foundation](#mcp-and-the-agentic-ai-foundation) | Vendor-neutral foundation under the Linux Foundation | Apache-2.0 for code, CC BY 4.0 for docs (MCP is moving from MIT) | about 9,700 (MCP specification), about 56,700 (goose) | Foundation members 146 on 2026-02-24, 305 on 2026-10-22 |
| [OpenCode](#opencode) | Company-led | MIT | about 227,600 | 33,178 stars on 2025-11-18; Octoverse 2026 #3 fastest-growing and #2 most-engaged among single-vendor projects |
| [Everything Claude Code (ECC)](#everything-claude-code-ecc) | One owner, with a commercial companion product | MIT | about 305,500 | ROSS Index #1 in Q1 2026 and #2 in Q2 2026; on no Octoverse 2026 list |
| [CC Switch](#cc-switch) | Volunteer grassroots, one main maintainer | MIT | about 155,200 | 4,558 stars on 2025-11-18; Octoverse 2026 #1 fastest-growing for community or independent projects |

All five are about AI coding agents or the tools around them, which is why they are close to what our kit does. Sources for each row are in its section below.

### OpenClaw

An assistant that runs on your own machine and talks to you through chat apps, with community-built skills. Repository: [openclaw/openclaw](https://github.com/openclaw/openclaw).

**Governance.** The founder created it. A US non-profit, the OpenClaw Foundation, announced on 2026-07-08 that it hosts the project. The foundation's own announcement says the founder still makes the technical calls, so we call it foundation-hosted and founder-steered. The people page lists 30 Core Maintainers. There is no governance file. Larger changes go through a separate proposals repository.

**Why we chose it.** It is the closest peer to what the kit does (an agent that meets people in chat) and the fastest verified grower.

- Created 2025-11-24. About 394,700 stars on 2026-11-17, against 106,177 on 2026-01-30.
- About 73,000 merged pull requests in its first year.
- 3,806 contributors if you count anonymous commit emails; only 387 are linked GitHub accounts.
- One account holds 53.8% of its 129,768 commits.

**What is notable about how it welcomes people.**

- CONTRIBUTING opens with a five-way routing list and a table of situation, destination and the evidence to bring.
- Blank issues are off, and the contact links send setup and support questions to a forum.
- The pull request template asks in plain language for the problem, the effect on people, the reason and the evidence.
- An "AI pull requests welcome" section asks for an evidence block and a statement that you understand the code, with no disclosure label.
- A vision document lists what the project will not merge, and says it is a guardrail, not a law.
- A third-party notices file records the origin and license of adapted code.
- Moderation principles and an incident playbook are public and tell staff to help first.
- Release notes carry pull request numbers and a thank-you per handle.

**Cautions.**

- Bots answer fast. On 60 sampled new issues the first reply came from a bot with a median of 7.6 minutes, and a human member replied within the window on 5 of the 60.
- About 8,300 items are open. There are 409 labels, mostly set by bots. The `good first issue` label was applied to 15 items ever, and only 1 is open.
- There is no Code of Conduct file.
- Its skills registry was hit by a poisoning campaign in early 2026. One vendor's audit flagged 341 of 2,857 skills, and other counts are higher and disagree.
- Some text drifts: a label that closes support requests still names Discord, although support moved to a forum.

**Sources, all read 2026-11-17 unless noted:** [CONTRIBUTING](https://github.com/openclaw/openclaw/blob/main/CONTRIBUTING.md); [issue chooser configuration](https://github.com/openclaw/openclaw/blob/main/.github/ISSUE_TEMPLATE/config.yml); [vision](https://github.com/openclaw/openclaw/blob/main/VISION.md); [third-party notices](https://github.com/openclaw/openclaw/blob/main/THIRD_PARTY_NOTICES.md); [community and moderation repository](https://github.com/openclaw/community); [foundation announcement](https://openclaw.ai/blog/introducing-openclaw-foundation) (2026-07-08); [people page](https://www.openclaw.org/people); [Internet Archive capture of 2026-01-30](https://web.archive.org/web/20260130041944/https://github.com/openclaw/openclaw); [GitHub's REST API for the repository](https://api.github.com/repos/openclaw/openclaw); [Octoverse 2026](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/); [secondary coverage of the registry campaign](https://thehackernews.com/2026/02/researchers-find-341-malicious-clawhub.html).

### MCP and the Agentic AI Foundation

The Model Context Protocol (MCP) and its sibling projects under the Agentic AI Foundation (AAIF): the goose coding agent, the AGENTS.md convention and Agent Skills. Repositories: [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol), [goose](https://github.com/aaif-goose/goose), [agents.md](https://github.com/agentsmd/agents.md) and [agentskills](https://github.com/agentskills/agentskills).

**Governance.** AAIF launched on 2025-12-09 under the Linux Foundation with MCP, goose and AGENTS.md. MCP has four tiers (Lead Maintainers, Core Maintainers, Maintainers, Contributors) plus a parallel Community Moderator track. A published contributor ladder asks for sponsors, a 7-day comment period and an inactivity rule that moves people to emeritus status while keeping their credit. Proposals are pull requests that add a file to a proposals folder. goose is lighter, with three tiers. Licenses are Apache-2.0 for code and the specification (moving from MIT) and CC BY 4.0 for the documentation.

**Why we chose it.** The judge picked it mainly for governance diversity and the quality of its written artifacts, not for star growth.

- AAIF had 146 member organizations on 2026-02-24 and 305 on 2026-10-22.
- The MCP specification repository has about 9,700 stars, up from 6,192 on 2025-11-11 (a baseline we flag as slightly over 12 months old).
- Of 964 pull requests opened there in the last 12 months, 704 were merged, with a median of 16 hours from opening to merge. For goose, 3,280 of 5,063 were merged, with a median of about 26 hours.
- A related list repository, awesome-mcp-servers, is #2 on Octoverse 2026's fastest-growing list for community or independent projects.
- It is also the protocol stack that the agents our kit drives are likely to use: MCP for tools, AGENTS.md for agent instructions, Agent Skills for packaged behavior.

**What is notable about how it welcomes people.**

- The contributing page says you need no invitation or role to comment, open an issue or attend a meeting, and gives a numbered "where to start".
- The fastest way in, it says, is to offer to take the notes or prepare an agenda.
- Only organization members may open pull requests on the specification repository. The docs explain the path for everyone else: file an issue and ask a member to open a pull request that credits you.
- A written escalation table promises replies in 5, 7 or 10 business days, and "immediately" for conduct and security matters.
- Decisions are recorded in GitHub, not left in chat.
- Its Code of Conduct builds on Contributor Covenant 2.0, adds an enforcement ladder, and bans third-party AI note-takers in meetings, because they record people without consent.
- Its security policy sets out a trust model and a list of behaviors that are not vulnerabilities.
- The Agent Skills project publishes a list of what it does not accept yet.
- It ships an AGENTS.md that tells AI agents not to open issues or pull requests unless the user is a listed maintainer or has more than three merged pull requests.

**Cautions.**

- The README says MIT while the LICENSE announces a move to Apache-2.0.
- The bug form adds a `needs-triage` label that is not among the repository's 63 labels, so it is silently dropped.
- The agents.md repository shows what happens to a donated repository without a process: 9 of its 87 pull requests from the last 12 months were merged, and 61 are open.
- The proposal, working-group and charter machinery suits a multi-vendor standard, not a small kit.
- Sibling projects disagree on AI: MCP requires disclosure, goose does not.

**Sources, all read 2026-11-17 unless noted:** [contributor ladder](https://modelcontextprotocol.io/community/contributor-ladder); [communication](https://modelcontextprotocol.io/community/communication); [contributing](https://modelcontextprotocol.io/community/contributing); [governance](https://modelcontextprotocol.io/community/governance); [AI policy](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/AI_POLICY.md); [AGENTS.md](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/AGENTS.md); [Code of Conduct](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/CODE_OF_CONDUCT.md); [goose governance](https://github.com/aaif-goose/goose/blob/main/GOVERNANCE.md); [Agent Skills contributing guide](https://github.com/agentskills/agentskills/blob/main/CONTRIBUTING.md); [AAIF formation release](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation) (2025-12-09); [member count release](https://www.linuxfoundation.org/press/agentic-ai-foundation-welcomes-97-new-members) (2026-02-24); [300 members release](https://www.linuxfoundation.org/press/agentic-ai-foundation-surpasses-300-members-in-less-than-one-year) (2026-10-22); [Internet Archive capture of 2025-11-11](https://web.archive.org/web/20251111005526/https://github.com/modelcontextprotocol/modelcontextprotocol); GitHub's REST API for the repositories above (pull request counts computed by us); [Octoverse 2026](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/).

### OpenCode

An open-source coding agent for the terminal and desktop that works with many model providers. Repository: [anomalyco/opencode](https://github.com/anomalyco/opencode) (formerly under another organization name).

**Governance.** Company-led, with no foundation, no published contributor ladder, no governance file and no Code of Conduct file. A team list in the `.github` folder tells automation who counts as the team. Octoverse files it under single-vendor projects, and says that split describes who steers the project, not who pays.

**Why we chose it.** It fills the company-led slot, it is a possible provider for our kit, and it is the best worked example of keeping a fast company-led repository usable under a flood of AI-generated issues and pull requests.

- About 227,600 stars on 2026-11-17, against 33,178 on 2025-11-18: 6.9 times in 12 months.
- 1,094 contributors counting anonymous emails; 450 are linked accounts.
- 11,538 merged pull requests in the last 12 months, against 839 in the 12 months before.
- Octoverse 2026: #3 fastest-growing and #2 most-engaged among single-vendor projects.

**What is notable about how it welcomes people.**

- Very short README with a language switcher and a pointer to the docs.
- Blank issues are off and the one contact link sends support to Discord.
- The pull request template asks how you verified the change and asks for a short description in your own words.
- A triage bot replied on every one of 39 sampled new issues, with a median of about a minute, by reproducing the bug or linking a duplicate.
- An automatic pull request check names what to fix and gives a visible 72-hour window before closing.
- Release highlights are in plain language and link every pull request.
- A published brand page explains which "works with" badges are allowed. Its README asks projects that use the name to say they are not affiliated, which is the model for our own "unofficial" line.

**Cautions.**

- In a complete cohort of 341 pull requests opened between 2026-10-01 and 2026-10-03, the team's own pull requests were merged 133 times out of 152, but outside people's only 9 times out of 156. The rest were closed without merging, many by a sweep.
- Its text disagreed with its automation: the guide said two hours to fix a flagged item while the workflow waited 72 hours.
- It tried a vouching gate on 2026-02-09 and removed it by 2026-05-03.
- Some wording is hostile ("automatic ban", "automatically rejected").
- Discussions are off and no `good first issue` item is open.

**Sources, all read 2026-11-17 unless noted:** [CONTRIBUTING](https://github.com/anomalyco/opencode/blob/dev/CONTRIBUTING.md); [pull request template](https://github.com/anomalyco/opencode/blob/dev/.github/pull_request_template.md); [workflows](https://github.com/anomalyco/opencode/tree/dev/.github/workflows); [brand rules](https://opencode.ai/brand); [Internet Archive capture of 2025-11-18](https://web.archive.org/web/20251118143750/https://github.com/sst/opencode); GitHub's REST and search APIs for the repository (the 341-pull-request cohort is computed by us); [Octoverse 2026](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/).

### Everything Claude Code (ECC)

A bundle of agents, skills, hooks, commands and settings for several coding-agent tools, with folders for each tool. Repository: [affaan-m/ECC](https://github.com/affaan-m/ECC).

**Governance.** One owner, on a personal account, with a commercial companion product and a paid-sponsor program. There is no governance file and no published ladder. Two accounts hold 53.4% of 4,986 commits. In November 2026 the owner opened a public call for maintainers, on terms that can include pay.

**Why we chose it.** It is the closest content analogue to our kit and the clearest 2026 example of rate limits written as code to cope with AI-era floods.

- Created 2026-01-18. About 305,500 stars on 2026-11-17.
- ROSS Index: #1 in Q1 2026 (119.8K stars) and #2 in Q2 2026 (223.5K stars); absent from Q3. The multiples are Runa's own.
- OSS Insight, published 2026-03-30: 120,120 stars and 1,646.8 stars a day, on a small sample of eight repositories whose author warns about it.
- 401 contributors on GitHub's linked count and 534 with anonymous ones.
- Counter-signal: it is on neither Octoverse 2026 list, so stars overstate how many people take part.

**What is notable about how it welcomes people.**

- A contribution recipe and short checklist for each kind of content (skill, agent, hook, command).
- A short install-problem form with an "impact" dropdown, and a one-click feedback form that says leaving the project is valid feedback.
- Written limits for floods, kept in JSON files with tests and explained to contributors up front: more than 5 new items from one author in 20 minutes are closed and locked, more than 10 alert a maintainer, and 10 open items per author is the cap. People with write access are exempt from the burst limit.
- A policy to copy ideas, not another project's identity, with provenance notes for imported material.
- A security policy with named response goals (acknowledge in 48 hours, assess in 7 days, fix critical issues in 14) and a list of the official places the project is distributed.
- A roadmap file with a "not on this roadmap" list and dated decision points; immutable tags and releases.

**Cautions.**

- The README is 2,215 lines, and the project's own roadmap sets a goal of under 1,200.
- Blank issues are enabled, so the forms can be bypassed.
- The Code of Conduct has a blank enforcement contact.
- The contributing page promises a review within 48 hours. In a sample of 40 recent outside pull requests, 17 got any human comment, with a median first reply of 196 hours.
- The sponsorship page says feature requests are prioritized partly by sponsor tier.
- A public moderation file names a blocked account and the contributors in an incident.
- Rules for the owner's own agents tell them to leave out co-author and "generated with" trailers.
- No release since 2026-10-01 (48 days at the time), and 1,547 Markdown files under `docs/`.

**Sources, all read 2026-11-17 unless noted:** [CONTRIBUTING](https://github.com/affaan-m/ECC/blob/main/CONTRIBUTING.md); [issue moderation policy](https://github.com/affaan-m/ECC/blob/main/.github/ISSUE_MODERATION.md); [pull request moderation policy](https://github.com/affaan-m/ECC/blob/main/.github/PR_MODERATION.md); [SECURITY](https://github.com/affaan-m/ECC/blob/main/SECURITY.md); [roadmap](https://github.com/affaan-m/ECC/blob/main/docs/ROADMAP.md); [sponsoring page](https://github.com/affaan-m/ECC/blob/main/SPONSORING.md); [agent lane rules](https://github.com/affaan-m/ECC/blob/main/docs/LANE-RULES.md); [maintainer call](https://github.com/affaan-m/ECC/discussions/3842) (2026-11-02); [ROSS Index Q2 2026](https://runacap.com/ross-index/q2-2026/); [OSS Insight, 2026-03-30](https://ossinsight.io/blog/skills-layer-takes-over-2026); GitHub's REST API for the repository (response times computed by us on small samples).

### CC Switch

A desktop app for switching between several coding-agent tools and their model providers. Repository: [farion1231/cc-switch](https://github.com/farion1231/cc-switch).

**Governance.** Volunteer-run, no foundation and no company. One maintainer wrote 75.2% of 3,744 commits. Five named maintainers are listed in the contributing guide. There is no governance file and no published ladder.

**Why we chose it.** It is the grassroots slot, with independent confirmation from GitHub itself, and its premise matches ours: people run several agents and want a neutral layer.

- Created 2025-08-04. About 155,200 stars on 2026-11-17, against 4,558 on 2025-11-18: about 34 times.
- 353 contributors counting anonymous emails; 71% of them have exactly one commit.
- 895 merged pull requests in the last 12 months, against 33 in the 12 months before.
- Octoverse 2026: #1 on the fastest-growing list and #5 on the most-engaged list for community or independent projects.

**What is notable about how it welcomes people.**

- One SUPPORT file routes by intent (usage question, bug, doc issue, feature, security) and says plainly that the project is volunteer-run.
- Four short issue forms, in two languages, each with required "I searched first" boxes and a free-text note where you state your goal in your own words.
- An "AI-assisted contributions" section with six rules: understand and test every line, keep pull requests small, open an issue first, expect unreviewed AI output to be closed, and write the note yourself.
- On 59 sampled issues the first human reply came from the owner, with a median of 0.5 hours. The sample leaves out issues nobody commented on.
- Release notes thank code contributors and, separately, the people who reported problems.
- A bot that closes a change reserved for maintainers says it is not a judgment on the idea.
- A security policy with an input trust model and the same 48-hour, 7-day and 14-day goals.
- An `llms.txt` file and an "only official website" notice against look-alike sites.

**Cautions.**

- About a third of the README is sponsor and referral content, placed before the product description.
- No roadmap, no Project board and no milestones. 504 issues and 381 pull requests are open, and all 7 sampled merges were by the owner.
- A stale bot closed about 1,079 issues.
- Docs lag releases: the user manual says version 3.16.0 while the latest release is 4.0.34, and the security policy still lists "latest 3.x".
- The Code of Conduct contact is a personal email address, and the README has no non-affiliation notice although the name echoes a vendor's product.

**Sources, all read 2026-11-17 unless noted:** [CONTRIBUTING](https://github.com/farion1231/cc-switch/blob/main/CONTRIBUTING.md); [SUPPORT](https://github.com/farion1231/cc-switch/blob/main/SUPPORT.md); [issue forms and chooser](https://github.com/farion1231/cc-switch/tree/main/.github/ISSUE_TEMPLATE); [SECURITY](https://github.com/farion1231/cc-switch/blob/main/SECURITY.md); [workflows](https://github.com/farion1231/cc-switch/tree/main/.github/workflows); [latest release notes](https://github.com/farion1231/cc-switch/releases/tag/v4.0.34); [Internet Archive capture of 2025-11-18](https://web.archive.org/web/20251118160123/https://github.com/farion1231/cc-switch); [project site `llms.txt`](https://ccswitch.io/llms.txt); GitHub's REST and search APIs for the repository (response times computed by us); [Octoverse 2026](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/).

## Spawn's own community sites

We studied Spawn's public pages alongside the five, because our kit's contributors will include people from the Spawn community. We read only what a visitor can read, on 2026-11-17, without signing in. None of this is endorsed by Spawn, and we do not speak for it.

| Site | What we saw | What we took from it |
|---|---|---|
| [Mods catalog](https://www.spawn.co/mods) | A catalog of reusable tools made by creators, in 11 departments, with install counts, likes, comments, version history, a Report link, and public, unlisted or private visibility. Every page carries a standing line: "Makers wrote these words. Spawn hasn't checked what they claim." | If we ever list community-made recipes, label them as not reviewed by Spawn and say who reviewed them. We have no such list, so this is only an idea for later. |
| Public game pages | Reviews carry a proof-of-play tag, makers reply in public, and makers pin a review and post update notes. | Show evidence of use as context and not as a gate, and answer in public. |
| [SpawnJam](https://www.spawn.co/jam) | Weekly jams with a theme, a three-day build and winners picked on Friday, per an [archived copy of the page from 2026-09-08](https://web.archive.org/web/20260908162333/https://www.spawn.co/jam). Jam 1 was in December 2025 and jam 29 on 2026-09-17. The page now says the weekly jams are over. We found no public reason, and the home page FAQ still describes them. | Programs end and docs lag. We promise no recurring events, and the roadmap gives no dates. |
| [Support page](https://www.spawn.co/support) | An in-product "Report a bug" button, a separate lane for abuse reports, a contact address and account deletion. | Our issue chooser sends problems in Spawn itself to this page. |
| [About page, FAQ and release notes](https://www.spawn.co/about) | A checklist for a useful bug report (game link, what you did, what happened, what you expected, device, screenshot) and dated, plain-language release notes with a "known rough edges" habit. | Our bug form asks for similar details, and our changelog says plainly what is not built yet. |
| [Docs for agents](https://www.spawn.co/llms.txt) | Agent-facing documents (`llms.txt`, `llms-full.txt`, `openapi.json`) and an AGENTS.md in every world. Outside coding agents are named as welcome. | We link to these documents and do not restate them. Our own AGENTS.md follows the same convention. |
| Discord, as far as publicly visible | A public invite to a community server with onboarding turned on, about 1,700 members at one moment on 2026-11-17 (public invite metadata). Spawn's pages name `#bug-reports` and `#announcements`. | We say nothing about its rules, because we could not read them. We send Spawn bugs where Spawn says to send them. Before anyone announces the kit in a Spawn space, they read that community's rules first (see the [release checklist](../contributing/releasing.md#release-checklist)). |
| Partner program and money programs | Partners are chosen at Spawn's discretion under its Terms. A creator fund was announced on 2026-11-05, and Spawn's pages also describe a revenue share and one-off grants. | We are not a partner. We never use "partner", "official" or "certified". See [the rules we follow](../compliance/spawn-rules.md). |

## Runner-ups, and why we did not choose them

The judge named these and gave one reason each. Figures are from the research run on 2026-11-17, and where the judge marked a figure as reported by a lens and not re-run, we say so.

| Project | Why it was not chosen |
|---|---|
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | About 264,000 stars and a very strong grower, but it lost the company-led slot to OpenCode on artifacts: no Code of Conduct, blank issues enabled, 129 labels with no starter labels, and 74 of its latest 100 pull requests came from authors with no earlier connection to the repository, which looks like a flood and not a managed path. Still worth reading for its guide to skills, tools and plugins. |
| Home Assistant core | Octoverse 2026 #9 on the most-engaged list, with a health score of 100. Not AI tooling, and its growth in 2026 is moderate. A good later reference for many small hobbyist contributions. |
| [Godot Engine](https://godotengine.org/article/contribution-policy-2026/) | The nearest game-engine analogue, but on no Octoverse 2026 list and slowing (lens-reported). Its policy of 2026-06-30 bans autonomous agents and vibe coding and requires disclosure of any AI use. The judge suggested that our docs warn people not to point agents at upstream projects with rules like that. We have not written that warning yet. |
| vLLM and SGLang | The strongest contributor funnels we saw among foundation projects (vLLM: 8 issue forms including one for proposals, 14 open starter issues). Inference engines, so little to do with agents or games. A secondary reference for issue forms and AI disclosure wording. |
| llama.cpp | Octoverse 2026 #5 fastest-growing. A local inference runtime with marginal relevance. |
| [OpenAI Codex CLI](https://github.com/openai/codex) | Apache-2.0 and fast-growing, but thinner community files (health score 62) and a large backlog. Treat it as a provider our kit may work with. |
| [Claude Code](https://github.com/anthropics/claude-code) | Fast-growing, but not open source: the repository's license reserves all rights. We may work with it and must never copy or redistribute it. |
| [mattpocock/skills](https://github.com/mattpocock/skills) | About 327,000 stars but 9 contributors: stars without a contributor funnel. |
| [Graphify](https://github.com/Graphify-Labs/graphify) and [Paperclip](https://github.com/paperclipai/paperclip) | Ranked on the ROSS Index and Octoverse lists, but they are a helper tool and a company-backed project that would repeat the OpenCode pattern. |
| [Multica](https://github.com/multica-ai/multica) | Its license adds conditions to Apache-2.0 and has commercial terms for some folders. We must not copy its code or text without legal review. |
| [Cline](https://github.com/cline/cline) | Apache-2.0 with a health score of 100, but modest 2026 growth and on no Octoverse 2026 list. |
| Pi, LiteLLM, Gemini CLI, Zed, Kilo Code and GitHub Copilot CLI | Company-led, so they repeat the OpenCode pattern. We did not check their community files one by one. |
| [first-contributions](https://github.com/firstcontributions/first-contributions) | Octoverse 2026 #4 fastest-growing community repository, but a tutorial and not an AI or game community. We could link it for people new to open source. |
| [Unity MCP](https://github.com/CoplayDev/unity-mcp) and Godot AI bridges | The nearest peers to an AI agent in a game engine. Small, with only API and archive evidence, and we did not re-verify them. |

Rank evidence for most rows: [Octoverse 2026](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/) and the [ROSS Index](https://runacap.com/ross-index/q2-2026/), read 2026-11-17. Star and contributor counts: GitHub's REST API for each repository, read 2026-11-17.

## Neighboring projects, for positioning

A separate prior-art search (2026-11-17) found these neighbors. They are not community models, but each taught us something about how to set up a project like ours.

- **A Spawn-specific MCP server** ([wfbcargo/wfbcargo_spawn_mcp](https://github.com/wfbcargo/wfbcargo_spawn_mcp), MIT, 3 stars): it keeps a plain-language getting-started file apart from its technical README, has a "worth knowing before you run it" security section, and states that it is unofficial. It is the project a Spawn reader could most easily confuse with ours, so we suggest linking to it as a related project.
- **[NanoClaw](https://github.com/nanocoai/nanoclaw)** (MIT, about 31,100 stars, health score 100): issue forms for capability requests and security hardening, and a one-command quick start.
- **[Open SWE](https://github.com/langchain-ai/open-swe)** shows a banner saying it is not accepting issues or outside contributions. That is the opposite of what we want.
- **[Mindcraft](https://github.com/mindcraft-bots/mindcraft)** states honestly that its maintainers are slow to answer issues. Setting expectations beats silence.
- **[OpenRouterLabs/spawn](https://github.com/OpenRouterLabs/spawn)** is a deprecated command-line tool with the same word in its name and the same audience. We ship no command called `spawn` and say "unofficial starter kit for Spawn" up front so search results tell the two apart.

## The patterns, and where each one landed

**Status words.** *Adopted* means we did it in about the same shape. *Adapted* means the same idea, changed in strength or form to fit our size. *Planned* means decided but not built, and tracked in [the roadmap](../community/roadmap.md). *Avoided* means we saw it and chose not to do it, at least for now.

| Pattern | Seen in | What we did here | Where in this repository | Status |
|---|---|---|---|---|
| Issue forms, with blank issues off | [OpenClaw](#openclaw), [ECC](#everything-claude-code-ecc), [CC Switch](#cc-switch), [MCP](#mcp-and-the-agentic-ai-foundation), [OpenCode](#opencode) | Six short forms: bug, feature, docs, compliance concern, agent behavior, and "Spawn changed and the kit broke". Every form tells people not to paste secrets and asks whether an AI tool helped. The bug form asks the reporter to confirm they searched first. | [issue chooser](../../.github/ISSUE_TEMPLATE/config.yml), [bug form](../../.github/ISSUE_TEMPLATE/bug_report.yml) | Adapted |
| Sending questions elsewhere | OpenClaw and OpenCode (a forum or Discord), CC Switch (a SUPPORT file that routes by intent), MCP (no usage questions in repositories) | The chooser sends questions and ideas to Discussions, vulnerabilities to private reporting, problems in Spawn itself to Spawn's support page, and everything else to SUPPORT.md. The Spawn lane exists because we are not Spawn. | [issue chooser](../../.github/ISSUE_TEMPLATE/config.yml), [SUPPORT.md](../../SUPPORT.md), [feedback and ideas](../community/feedback-and-ideas.md) | Adapted |
| A plain-language pull request template | OpenClaw, OpenCode, CC Switch, MCP | What changed and why, how it was tested and what was not, a checklist (lint, tests, no secrets, no copied text, DCO) and an AI assistance section. | [pull request template](../../.github/PULL_REQUEST_TEMPLATE.md) | Adapted |
| A small label set that stays true | OpenClaw (409 labels), ECC (42, with duplicates), MCP (a form names a missing label), CC Switch (24), goose (13) | 42 labels in eight families (type, priority, triage and status, community, area, upstream, AI policy, release notes), each with a one-line description, created from one file by a script. We checked by hand that every label used by a form, the labeler or the release-notes settings is in that file; no automatic check exists yet. | [labels.tsv](../../.github/labels.tsv), [triage and labels](../community/triage-and-labels.md), [labels in the maintainers guide](../maintainers/github-settings.md#labels) | Adapted |
| Labels from changed file names | OpenClaw (about 205 path rules), CC Switch | Area labels, `dependencies`, `compliance` and `security` are added from the files a pull request changes. The workflow never checks out the pull request's code. A maintainer adds `bug`, `enhancement` and `breaking-change` by hand. | [labeler rules](../../.github/labeler.yml), [labeler workflow](../../.github/workflows/labeler.yml) | Adopted |
| A triage cadence, stated as a goal | OpenClaw (a bot answers in minutes, humans rarely), ECC (a 48-hour promise that was not met), MCP (written 5, 7 and 10 business day escalation), CC Switch (one owner answers fast) | A goal, not a promise: a first reply within about 7 days, and a nudge is welcome after 14. A `triage` label stays until a maintainer looks. A Project view lists everything labeled `triage`. A monthly reminder issue opens for the check of Spawn's terms. | [what to expect from review](../../CONTRIBUTING.md#what-to-expect-from-review), [the Project](../maintainers/github-settings.md#the-project), [monthly workflow](../../.github/workflows/compliance-reminder.yml) | Adapted |
| Closing stale items automatically | OpenClaw (7 to 30 days), OpenCode (60 days for issues, a month for pull requests), ECC (30 plus 7 days), CC Switch (60 plus 14; about 1,079 closed), goose (pull requests only) | We run no stale bot, so nothing closes automatically. For an item waiting on information, a person reminds once after 14 days and, if there is still no answer 30 days later, closes it with a kind note that says it can be reopened. If we ever automate this, it should warn first, spare `help wanted`, `good first issue`, security and roadmap items, and say how to reopen. | [triage and labels](../community/triage-and-labels.md), [workflows](../../.github/workflows/ci.yml) (none for stale items) | Avoided, for now |
| A public roadmap and Project | MCP (a roadmap page with priority areas, 8 public boards), ECC (a roadmap file with "not on this roadmap" and dated decision points), OpenCode and goose (one board each), CC Switch (none) | A short roadmap of what is shipped, next and later, with no dates and a "not on this roadmap" list. One public Project with Priority, Area, Kind, Size, Upstream impact and Target release fields and five views. A script creates the Project and its fields; a maintainer does a few manual steps. | [roadmap](../community/roadmap.md), [project board](../community/project-board.md), [setup script](../../scripts/setup-project.sh), [the Project](../maintainers/github-settings.md#the-project) | Adapted |
| Discussions as the support door | MCP (ideas, Q&A and decision notes), ECC and CC Switch (Q&A as the support door, with thin or unanswered threads), OpenClaw and OpenCode (off) | Discussions are on, because we run no forum or chat server. Three category templates: ideas, Q&A and show and tell. We watch them against the same reply goal as issues. | [discussion templates](../../.github/DISCUSSION_TEMPLATE/q-a.yml), [Discussions setup](../maintainers/github-settings.md#discussions), [communication](../community/communication.md) | Adapted |
| Starter issues and mentoring | All five barely curate. Open `good first issue` items on 2026-11-17: OpenClaw 1, CC Switch 2, and 0 each for OpenCode, ECC and the MCP specification. MCP offers other ways in, such as taking meeting notes. | Labels `good first issue`, `help wanted` and `mentor-available`. A first-contribution path of about 30 minutes in which a docs fix counts. Our own agent accounts leave starter items to people who are learning. Seeding three to five items before the announcement is a to-do on the maintainers' checklist. | [CONTRIBUTING](../../CONTRIBUTING.md#your-first-contribution-in-30-minutes), [labels.tsv](../../.github/labels.tsv), [before you announce](../maintainers/github-settings.md#before-you-announce-the-project) | Adapted |
| Recognition of contributors | OpenClaw (thanks per handle in every release, an avatar wall), CC Switch (thanks to code contributors and to reporters), MCP (emeritus roles keep credit), ECC (thanks in the changelog) | CONTRIBUTING thanks every kind of help, not only code. Generated release notes list merged pull requests. The credits page names the projects whose work we build on. We have no avatar wall and publish no contributor emails. Thanking reporters by name in release notes is not yet a written practice. | [CONTRIBUTING](../../CONTRIBUTING.md#ways-to-help), [releasing](../contributing/releasing.md#release-notes-two-layers), [names and credits](../compliance/trademarks-and-credits.md) | Adapted |
| An AI-assisted contribution policy | All five differ. MCP requires disclosure. OpenClaw asks for evidence and no label. OpenCode wants short, own-words text. CC Switch has six rules and a note in your own words. ECC has volume limits only. | A middle path: AI-assisted work is welcome; say so when an AI tool did more than spelling, formatting, autocomplete or a mechanical rename (a pull request section and an `Assisted-by` trailer); a named person is accountable; evidence beats polish. The policy has a version, a review date and a list of open decisions. | [AI-assisted contributions](../contributing/ai-assisted-contributions.md), [pull request template](../../.github/PULL_REQUEST_TEMPLATE.md) | Adapted |
| An agent-account policy | MCP (an AGENTS.md rule for when an agent may file), ECC (lane rules for the owner's agents), OpenClaw (limits for everyone, no separate page), CC Switch (no rule); PyTorch, LLVM and Godot (autonomous agents not accepted, or only with approval) | Rules for our own agent accounts: owned by a named person, marked as automated, least privilege, own branches, never approve or merge, at most three open pull requests, only our repositories. Other people's autonomous agents are not accepted unless a maintainer arranged it. The list of accounts and owners is not published yet. | [agent accounts and bots](../contributing/ai-assisted-contributions.md#agent-accounts-and-bots), [GitHub settings for agent accounts](../maintainers/github-settings.md#actions-approval-and-agent-accounts) | Adapted |
| An AGENTS.md for visiting agents | MCP, goose, OpenCode, OpenClaw | AGENTS.md lists the commands that must pass and a short list of hard rules (never add `Signed-off-by`, always disclose, no secrets, post nothing for anyone). It makes the agent say on its first turn that the project is unofficial. CLAUDE.md points to it. | [AGENTS.md](../../AGENTS.md), [CLAUDE.md](../../CLAUDE.md) | Adopted |
| Security reporting | OpenClaw (private advisories, a "not a security bug" list, no response time), MCP (a trust model), OpenCode (threat model first), ECC and CC Switch (48 hour, 7 day and 14 day goals) | Private reporting on GitHub plus the organization's security mailbox; lists of what is in and out of scope; goals (not promises) of 3 business days to acknowledge, 7 days to assess and, by default, 90 days to publish; a good-faith testing promise; no bounty; never post secrets. A plain-language threat model and its known limits are on the security model page. | [SECURITY.md](../../SECURITY.md), [security model](../security-model.md), [security features](../maintainers/github-settings.md#security-features) | Adapted |
| Release notes and a changelog | OpenClaw (pull request numbers and thanks), OpenCode (plain highlights linking every pull request), ECC (immutable tags), CC Switch (thanks to reporters), Spawn (dated plain notes with known rough edges) | Two layers: notes generated from labeled pull requests, and a hand-written changelog in Keep a Changelog form. Tags are never moved; fix forward. The changelog lists what is not built yet. | [releasing](../contributing/releasing.md), [release settings](../../.github/release.yml), [CHANGELOG.md](../../CHANGELOG.md) | Adapted |
| Governance and written decisions | MCP (a ladder, sponsors, a 7-day window, decisions in writing), goose (three tiers), OpenClaw (a proposals repository, no governance file), ECC, CC Switch and OpenCode (none written) | A short governance file: three roles (contributor, reviewer, maintainer) and no tiers above them, a 7-day open period for proposals with lazy consensus, a vote and then KDTIX Open as the tie-breaker, stepping down with an emeritus step that keeps credit, and a list of what is not decided yet (a roster, a moderator role, mentoring). It is honest that the project is new and run by KDTIX Open. Small changes are decided in the pull request. The AI policy keeps a table of open decisions. | [GOVERNANCE.md](../../GOVERNANCE.md), [how decisions get made](../../CONTRIBUTING.md#how-decisions-get-made), [open decisions](../contributing/ai-assisted-contributions.md#decisions-the-maintainers-are-still-making) | Adapted |
| A docs layout that people can navigate | OpenClaw (a goal table in the README), MCP (community pages), CC Switch (a numbered manual whose version stamp drifted), ECC (about 1,500 Markdown files, README as the index) | A short README, an index by audience, one topic per file, a first sentence saying who the page is for, an unofficial footer, and dated claims about Spawn. A link checker and a secret check run as part of the lint script. | [docs index](../README.md), [link checker](../../scripts/check-links.py), [lint script](../../scripts/lint.sh), [the rules we follow](../compliance/spawn-rules.md) | Adapted |
| Onboarding | MCP (a numbered "where to start"), goose (counts questions and showcases as contributions), CC Switch (pinned toolchains, tests that never touch your home folder), OpenClaw (a routing table, but long) | Non-code ways to help, a suggested first week, a first contribution in about 30 minutes, a development guide with tested versions, and tests that need no network or tokens. | [CONTRIBUTING](../../CONTRIBUTING.md), [development](../contributing/development.md), [testing](../contributing/testing.md), [welcome](../community/welcome.md) | Adapted |
| A Code of Conduct with a working contact | Missing at OpenClaw and OpenCode; blank contact at ECC; a personal email at CC Switch; MCP builds on Covenant 2.0 with an enforcement ladder | The Contributor Covenant 2.1, credited as its license requires, with a role mailbox that people actually read as the contact, and a short addendum about honesty on AI use and respect for Spawn's community rules. | [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md), [Covenant credit](../compliance/third-party-licenses.md#the-contributor-covenant) | Adopted |
| Developer Certificate of Origin sign-off | We found no DCO or CLA workflow in any of the five. The Linux kernel and others say only a person signs off. | Sign-off with `git commit -s` is required today and checked by hand. Only a person signs; an agent never does. An automatic check is planned. | [sign your commits](../../CONTRIBUTING.md#sign-your-commits-dco), [AGENTS.md](../../AGENTS.md), [roadmap](../community/roadmap.md) | Adapted; check planned |
| Crediting other people's work | OpenClaw (a third-party notices file with license and copyright), ECC (copy ideas, not identity; provenance notes), MCP (CC BY 4.0 docs need credit) | A NOTICE file, a table of third-party licenses, a credits page and a pull request checkbox saying you copied nothing you cannot license. We never bundle Spawn's client. | [NOTICE](../../NOTICE), [third-party licenses](../compliance/third-party-licenses.md), [names and credits](../compliance/trademarks-and-credits.md) | Adopted |
| A visible non-affiliation notice | OpenCode (a brand page and a request that projects using its name say they are not affiliated), the Spawn-specific MCP server (an unofficial line); CC Switch has none | Said first and everywhere: NOTICE, the first reply of every agent session, the footer of every page in `docs/`, and the repository description. | [NOTICE](../../NOTICE), [AGENTS.md](../../AGENTS.md), [names and credits](../compliance/trademarks-and-credits.md), [setup script](../../scripts/setup-github.sh) | Adopted |
| Limits for flood days | OpenClaw (20 open pull requests per author), ECC (a burst guard in code) | Nothing automatic. Our own agent accounts are capped at three open pull requests, counted by hand. GitHub's switches (collaborator-only pull requests or issues, interaction limits) are listed in reserve. | [agent accounts and bots](../contributing/ai-assisted-contributions.md#agent-accounts-and-bots), [GitHub settings](../maintainers/github-settings.md#actions-approval-and-agent-accounts) | Adapted, in reserve |
| Safe workflows | MCP, OpenCode, ECC | Actions are pinned by commit with a version comment, the default token is read-only, credentials are not kept, and the labeler never runs pull request code. The setup script stops Actions from approving pull requests. | [CI workflow](../../.github/workflows/ci.yml), [setup script](../../scripts/setup-github.sh) | Adopted |
| CODEOWNERS for sensitive paths | OpenClaw (security and release paths only), OpenCode and CC Switch (the `.github` folder) | None yet, on purpose: the organization teams named in a shared file have no access to this repository, so a file would request no reviews. Add one when a team has write access, and keep it to sensitive paths. | [CODEOWNERS section](../maintainers/github-settings.md#codeowners) | Avoided, for now |
| Funding and sponsorship | ECC (sponsor tiers), CC Switch (a third of the README), OpenClaw (foundation donors), OpenCode (company products), MCP (members fund the foundation) | No FUNDING file, no Sponsor button and no sponsor content. See the next section. | [funding section](../maintainers/github-settings.md#funding) | Avoided |
| Translations | Four of the five translate their docs or README (OpenClaw 13 locales by machine translation, OpenCode 21 README translations, ECC 17 languages, CC Switch 8 locales) | No translation workflow yet. It is on the roadmap under "Later". CONTRIBUTING asks people to open an idea in Discussions first so we can agree how to organize it. | [roadmap](../community/roadmap.md), [ways to help](../../CONTRIBUTING.md#ways-to-help) | Planned |

### Why we did not add a sponsor button

1. **It could look like Spawn's money or Spawn's blessing.** A Sponsor button on an unofficial kit could suggest that gifts go to Spawn, or that Spawn endorses the project. Spawn's terms bar implying affiliation, so we keep money out of the picture (see [the rules we follow](../compliance/spawn-rules.md)).
2. **Money near contributors raised neutrality questions for our peers.** One studied project says feature requests are prioritized partly by sponsor tier. Another spends a third of its README on sponsors and referral links. A related list project sells advertising in its README.
3. **We could not confirm that our organization's existing funding links work.** Its shared funding file may not even apply to this repository.
4. **We are new.** There is nothing to fund yet.

If the maintainers decide otherwise later, we would say next to the link that gifts support the KDTIX Open maintainers and not Spawn, keep it out of the top of the README, and record the decision in [the maintainers guide](../maintainers/github-settings.md#funding). [GOVERNANCE.md](../../GOVERNANCE.md#our-relationship-to-spawn-and-to-kdtix-open) already says that sponsorship would not buy review or roadmap priority.

### What the AI policies taught us

Our AI policy draws on a survey of about two dozen projects (read 2026-11-17). Four findings shaped it.

- **An accountable person is the one universal rule.** Projects differ on whether AI is allowed, but nearly all say a person answers for the change.
- **A trailer alone is a weak signal.** The Linux kernel added an `Assisted-by` tag, then removed it on 2026-10-13 after finding that only about one commit in ten carried it ([commit](https://github.com/torvalds/linux/commit/1e035297ff)). We pair the trailer with a pull request section. Practice on `Co-authored-by` for AI is split: [Kubernetes](https://www.kubernetes.dev/docs/guide/pull-requests/#ai-guidance) and [Mesa](https://gitlab.freedesktop.org/mesa/mesa/-/blob/main/docs/submittingpatches.rst) forbid it.
- **Evidence works better than detection.** [curl](https://curl.se/dev/contribute.html#on-ai-use-in-curl) and the draft [OpenSSF policy](https://github.com/ossf/tac/pull/605) record that asking for a reproduction and a human author restored the signal in reports.
- **Policies change fast.** The kernel reversed a rule within about ten months, and Hugging Face's transformers project rewrote its text twice between July and November 2026. So ours has a version and a review date.

One preprint (not peer reviewed, read through a summary) reports that coding agents rarely open a contribution guide but do load an AGENTS.md ([arXiv 2607.26819](https://arxiv.org/html/2607.26819v1), 2026-07-29). That is why our rules for agents are in [AGENTS.md](../../AGENTS.md) as well as in CONTRIBUTING.

## Anti-patterns we saw and avoided

Numbers in this table are explained, with sources, in the community sections above.

| Anti-pattern | Where we saw it | How we avoid it |
|---|---|---|
| No Code of Conduct, or none that someone reads | None at OpenClaw or OpenCode; a blank contact at ECC; a personal email at CC Switch | The Covenant 2.1 with a monitored role mailbox ([CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md)) |
| A README that is a wall | ECC at 2,215 lines; a third of CC Switch's README is sponsors; OpenClaw's is mostly an avatar wall | A short README that points into `docs/` ([README.md](../../README.md), [docs index](../README.md)) |
| Bots standing in for people, or promises not kept | OpenClaw: bot first reply in minutes, human replies rare; ECC: a 48-hour promise, median first human reply of 196 hours | A goal of about 7 days, not a promise ([CONTRIBUTING](../../CONTRIBUTING.md#what-to-expect-from-review)); we have no reply bot |
| A gate that closes most outsiders' pull requests | OpenCode: 9 of 156 outside pull requests merged in one cohort, threatening wording, a vouching gate adopted and dropped | No gate. Friendly steps first when something goes wrong ([AI policy](../contributing/ai-assisted-contributions.md#when-something-goes-wrong)) |
| Docs that disagree with automation | OpenCode (2 hours versus 72), OpenClaw (a label naming a channel it no longer uses), CC Switch (manual version 3.16.0 versus 4.0.34), MCP (a form label that does not exist), ECC (release-note settings naming labels that do not exist) | Labels created from one file; the monthly check; "last verified" dates ([the rules we follow](../compliance/spawn-rules.md)). A check that forms and labels agree is not automatic yet |
| Label sprawl and near-duplicates | OpenClaw 409 labels; ECC `docs` and `documentation`, `enhancement` and `feature` | 42 labels in families, each described ([labels.tsv](../../.github/labels.tsv)) |
| A starter-issue label that is empty | Open counts on 2026-11-17: OpenClaw 1, CC Switch 2, OpenCode 0, ECC 0, MCP 0 | Seed three to five before announcing; keep them for learners ([before you announce](../maintainers/github-settings.md#before-you-announce-the-project)) |
| Money that touches priority or the first page | ECC's sponsorship text; CC Switch's sponsor-first README; ads in a related list's README | No sponsor content ([funding](../maintainers/github-settings.md#funding)) |
| Naming people in public policy files | ECC's moderation files name a blocked account and incident contributors; [Ghostty](https://github.com/ghostty-org/ghostty/blob/main/AI_POLICY.md) keeps a public denounce list (read 2026-11-17) | No public list. If we keep one, it is private and has an appeal route ([open decision 5](../contributing/ai-assisted-contributions.md#decisions-the-maintainers-are-still-making)) |
| Telling agents to hide attribution, or contradicting yourself about it | ECC tells its agents to omit trailers; MCP's AGENTS.md forbids model names in commit messages while its CONTRIBUTING keeps co-author trailers | AGENTS.md says always disclose; the open questions are in the AI policy ([decisions 2 and 3](../contributing/ai-assisted-contributions.md#decisions-the-maintainers-are-still-making)) |
| One person carries everything, with no written rules | CC Switch (75.2% of commits; all 7 sampled merges by the owner), OpenClaw (53.8%), ECC (53.4% by two accounts) | Written governance; a plan for a second maintainer ([recurring checks](../maintainers/github-settings.md#recurring-checks)) |
| Publishing contributor emails in a credits file | OpenClaw's credits page | We publish no personal emails. The only addresses are the organization's two public ones |
| An open registry of add-ons with no scanning | OpenClaw's skills registry poisoning in early 2026 | We run no registry. Before listing community add-ons we would need scanning, declared secrets, a ban on pipe-to-shell installs and a report path |
| Trusting GitHub's community score | It missed the issue forms at four of the five communities; ECC's 100 was months old | We use our own checklist ([before you announce](../maintainers/github-settings.md#before-you-announce-the-project)) |
| Closing the door, or leaving it unmarked | Open SWE's banner says it takes no outside contributions; CC Switch has no non-affiliation notice | Anyone may open a pull request; we say first that we are unofficial |
| Silent mass closing | CC Switch's stale bot closed about 1,079 issues | No automatic closing; a person closes with a reason and a kind note |

## What we would study next

1. **Our own numbers.** After about three months of public life, measure our first reply time, time to first merge, and share of first-time contributors with the same method, and compare them to our 7-day goal.
2. **Spawn's Discord, read by a person.** A member who reads it under their own account, after asking Spawn staff first, could tell us about its channels and norms. We would write only what they found, and we would not post there in the project's name without asking Spawn staff first, as Spawn's own pages invite.
3. **Public Project boards.** Their fields and views need a signed-in reader. We only know that boards exist.
4. **Close cousins.** Hermes Agent's contribution guide, vLLM's issue forms and AI disclosure wording, Home Assistant's newcomer docs, Godot's agent rules, and small game-engine bridges such as Unity MCP.
5. **Marketplace safety,** if we ever list community recipes: ClawHub's acceptable-use, content-rights and moderation pages, and Spawn's own process for reporting a mod, which is not public.
6. **Accessibility and plain-language practice** in contributor docs. None of the five reported on it, so we have no evidence yet.
7. **Handling AI-written security reports,** where curl and OpenSSF have the most to teach.
8. **Communities off GitHub:** forums, Reddit and video. We did not study them.
9. **Small improvements to ourselves,** such as an automatic check that forms, the labeler and release settings only use labels that exist, thanking reporters by name in release notes, a link to a newcomer tutorial for people new to open source, and a warning for users about upstream projects that ban agents.

## How to refresh this research in six months

Plan to finish by **2027-05-17**, the same date the AI policy is due for review. Open an issue labeled `documentation` to track it.

1. **Choose the as-of date and write it down first.** Say which time zone your clocks use.
2. **Rerun the three lenses with the same questions.** Octoverse appears once a year (the 2026 edition on 2026-10-28), so in May 2027 do not count its 2026 ranks as new evidence. Use the ROSS Index quarterly editions, OSS Insight and direct GitHub reads, with Internet Archive captures for baselines.
3. **Apply the same three gates and the governance balance,** and say what you changed and why. Replace a community if its growth, activity or policies have changed enough to make it a poor model.
4. **Redo the deep studies with the same fifteen questions,** starting with what changed: policies on AI, label sets, contribution guides and governance files churn fastest.
5. **Measure the same way, and say how.** State sample sizes and biases for every response-time figure, and say whether a bot or a person replied.
6. **Check the table.** Every link in the patterns table should still resolve and every status should match the repository. Move items between adopted, adapted, planned and avoided as the project changes.
7. **Keep the rules of the run.** Read-only requests, no sign-in, no joining servers, short quotes with a link, no copied text, and one scratch folder per agent. Record what you could not verify.
8. **Update the credits.** Add or remove communities in [names and credits](../compliance/trademarks-and-credits.md), and bump the date at the top of this page.

## Credits

We thank the maintainers and contributors of OpenClaw, the Model Context Protocol and the Agentic AI Foundation projects, OpenCode, Everything Claude Code and CC Switch, and of the projects named in the runner-ups and neighbors sections. We studied how they work in public, and we learned a great deal from it. Their names belong to their owners. Mentioning a project here is attribution and not endorsement, and none of them has reviewed or approved ours.

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
