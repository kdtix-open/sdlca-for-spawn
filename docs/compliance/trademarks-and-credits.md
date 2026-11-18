# Trademarks and credits

This page is for anyone who wants to know how the SDLCA agent kit names other companies and their products, what we never do with their names and logos, the exact wording we use, and who we thank. It also helps contributors write docs that stay on the right side of all of this. It was written from our research of 2026-11-17, and it is not legal advice.

## The short version

- We use other companies' names in plain text, only to say what the kit works with.
- We use no logos, art, mascots or look-alike designs from anyone.
- We never say or suggest that anyone made, approved, sponsored or partnered with this project. None of them has.
- Every name belongs to its owner. Section 6 of the Apache License grants no permission to use the Licensor's names or marks, and nothing in this project grants any right to use another party's names, logos or trademarks.

## What we do and do not do

**We do:**

- Write each name as its owner writes it, in plain text: "Claude Code", "GitHub", "Spawn".
- Say plainly that this project is unofficial, independent and not affiliated with anyone it names. The notice goes with the name: in the README, in [NOTICE](../../NOTICE) and in the footer of every page in `docs/`. The agent's own prompt tells it that it is not Spawn staff and never speaks for Spawn.
- Say what the kit can be used with, in words that claim no relationship: "agents such as Claude Code or OpenAI Codex", "can be used with", "for Spawn".
- Use Slack's name as an adjective before a generic noun where practical: "Slack workspace", "Slack app". Slack's Brand Terms ask for that (they say not to use the name as a noun, verb, plural or possessive). We follow it in the app's name and in notices. In headings and running text we sometimes write "Slack's API terms" because it reads better.
- Write "Cursor", not "Cursor AI" or "Cursor Code", which is how Cursor asks to be named.
- Link to an owner's pages instead of copying them.

**We do not:**

- Use any logo, icon, avatar, mascot or ASCII art of Spawn, Savi, Claude Code, GitHub, Slack, Discord, OpenAI, Cursor, Microsoft, Playwright or Bun. That includes the README banner, the social preview, the Slack app icon and favicons.
- Copy anyone's look and feel: Slack's colors and typefaces, Discord's look, Claude Code's terminal visuals, Spawn's site style, Savi's face or voice.
- Put another company's name in our own names: the repository, package, commands, Slack app, bot, domain or social handles. The one exception is "for Spawn" as a plain description in the repository name, which carries a risk we explain in [the Spawn rules](spawn-rules.md#why-the-repository-is-called-sdlca-for-spawn).
- Name a bot or agent after a vendor, such as Claude, Savi, Codex or "Spawn Bot". It would suggest the vendor is speaking. Our example Slack bot is called `sdlca-agent`.
- Use "official", "certified", "verified", "approved", "authorized", "partner", "in partnership with", "sponsored by", "trusted by", "powered by", "built with", "worked with" or "partnered with" to describe the kit's relationship with anyone. (Saying that we are *not* any of these is fine, and we do.) OpenAI's brand page gives "building with OpenAI" and "worked with OpenAI" as examples of wording to avoid unless you are a partner. Anthropic's Agent SDK branding rules allow "Powered by Claude" only for products built on that SDK, and they do not allow "Claude Code" as a name for someone else's product (both read 2026-11-17, OpenAI's page through an archive copy of 2026-11-04). We say "can be used with" instead.
- List vendors under headings such as "Partners", "Sponsors" or "Supported by", or quote a vendor's staff, without written permission.
- Put a trademark symbol next to Anthropic's marks. Anthropic's guidelines ask us not to.
- Stuff vendor names into hidden text, meta tags or topic lists. The repository's topics contain no vendor name and no Spawn name (the list is in [GitHub settings for maintainers](../maintainers/github-settings.md)). Spawn's Terms ban hidden text that uses its names (section 4(k)).
- Show screenshots of Slack or Spawn that contain other people's content or identifiable people.

Naming an AI tool in a commit, for example an `Assisted-by:` line, records how a change was made. It does not mean the tool's maker endorses this project.

## How each name is written

Owners are as each owner's own pages state them, read 2026-11-17.

| Name | Owner | How we write it |
| --- | --- | --- |
| Spawn, and its AI companion Savi | AI Tools, Inc., which operates Spawn ([Terms](https://www.spawn.co/terms-of-service)) | "Spawn" and "Savi", with a capital letter. "For Spawn" only as a description. No logos or art. Spawn and Savi belong to their owners. |
| Claude, Claude Code, Anthropic | Anthropic, PBC | Plain text, such as "agents such as Claude Code". Anthropic's legal page allows saying accurately, in plain text, that a product runs Claude Code. Never in our names, and no "Powered by" ([Claude Code legal page](https://code.claude.com/docs/en/legal-and-compliance)). |
| OpenAI, Codex | OpenAI | "OpenAI Codex" or "Codex", with "can be used with". We treat Codex under the same rules as OpenAI's other names, because OpenAI's brand page does not mention it ([OpenAI brand page](https://openai.com/brand/), read through an archive copy from 2026-11-04). |
| Cursor | Anysphere, Inc. | "Cursor" only ([Cursor brand page](https://cursor.com/brand)). |
| Gemini | Not researched | Plain text only, with the disclaimer. We did not research its owner's brand rules. |
| Slack | Slack Technologies, LLC, part of Salesforce | An adjective before a noun ([Slack Brand Terms](https://slack.com/terms-of-service/slack-brand)). We keep it, and every other vendor's name, out of our app's name. That is our own choice. See [Slack's own terms that matter](../slack-bridge.md#slacks-own-terms-that-matter). |
| GitHub | GitHub, Inc. | Plain text. No logo, no Octocat ([GitHub brand toolkit](https://brand.github.com/foundations/logo)). |
| Discord | Discord Inc. | As an adjective, such as "Spawn's Discord". Never in a name of ours ([Discord brand page](https://discord.com/branding)). |
| Playwright | Microsoft Corporation (open source, Apache-2.0) | Plain text, as a credit. We do not claim anything about who holds the mark. |
| Bun | An open-source project (MIT) that joined Anthropic in December 2025 | Plain text. We found no brand rules for it, so we treat it like an Anthropic name. |
| Apache License | The Apache Software Foundation | The name of our license, in plain text. We use no ASF logo and no "Apache" in our own names. |

## Non-affiliation wording

### The long form

This text goes under the title of the README, in app listings and anywhere there is room:

> **Unofficial community project.** The SDLCA agent kit is an independent, open-source (Apache-2.0) starter kit. It is not created by, affiliated with, endorsed by, sponsored by, or supported by Spawn (www.spawn.co, operated by AI Tools, Inc.), Anthropic, OpenAI, Anysphere, Slack Technologies, LLC, GitHub, Microsoft, Discord, or any other company named in this repository. Product and company names are the property of their respective owners and are used only to describe compatibility. See the NOTICE file and the trademarks and credits page.

The example Slack app listing (`slack/manifest.yaml`) says the same. It uses Slack's own words for Slack: "not created by, affiliated with, or supported by Slack Technologies, LLC" ([Slack Brand Terms](https://slack.com/terms-of-service/slack-brand), read 2026-11-17). Slack's terms say it may ask for such a statement from an app that uses its API.

### The footer

Every page in `docs/` ends with this line, and it is the only footer you need to add:

> Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.

Where there is room for more, such as a web page footer, use the longer line:

> Unofficial community project. Not affiliated with, endorsed by or supported by Spawn, Anthropic, OpenAI, Slack, GitHub, Discord or Microsoft. Names and trademarks belong to their owners and are used only to describe compatibility. Licensed under Apache-2.0.

## Marking sentences

These short factual sentences name the owner of a mark. We add no (TM) or (R) symbols next to them.

| Owner | Sentence | Where it comes from |
| --- | --- | --- |
| Slack | Slack is a trademark and service mark of Slack Technologies, Inc., registered in the U.S. and in other countries. | Slack's own marking text, used as Slack gives it ([Slack Brand Terms](https://slack.com/terms-of-service/slack-brand), read 2026-11-17). Slack's page names the company "Slack Technologies, LLC" in other places, and we use each form where Slack does. It appears in NOTICE and in the example Slack app listing. |
| GitHub | GITHUB is a trademark of GitHub, Inc., registered in the United States and other countries. | Our wording, modeled on the legal line in [GitHub's brand toolkit](https://brand.github.com/foundations/logo) (read 2026-11-17). |
| Discord | Discord is a trademark of Discord Inc. | Our wording. |
| Anthropic | Claude and Claude Code are trademarks of Anthropic, PBC. | Our wording, with no trademark symbol, as [Anthropic's trademark guidelines](https://www.anthropic.com/legal/trademark-guidelines) ask. Those guidelines took effect on 2024-08-01, which is more than 12 months ago. |
| OpenAI | OpenAI and Codex are marks of OpenAI. | Our wording. |
| Cursor | Cursor is a product of Anysphere, Inc. | Our wording. |
| Playwright | Playwright is an open-source project of Microsoft Corporation, licensed under Apache-2.0. | Our wording. It says who makes it and under what license, and claims nothing about the mark. |
| Bun | Bun is an open-source JavaScript runtime licensed under MIT. | Our wording. |
| Spawn and Savi | Spawn and Savi belong to their owners. | Our wording. |

## Credits and attribution

This project stands on other people's work. We credit it here and take no credit for it.

- **Spawn** (www.spawn.co, operated by AI Tools, Inc.) makes the platform, the worlds, the agent interface and its AI companion, **Savi**. All of that belongs to Spawn. This project is an independent client of Spawn's published agent interface and is not part of Spawn. We link to Spawn's documentation instead of copying it.
- **Anthropic** makes **Claude** and **Claude Code**, one of the agents this kit can be used with. Our examples were tested with it. You use your own Anthropic account or API key. **Bun**, which Spawn's client requires, is MIT-licensed and joined Anthropic in December 2025.
- **OpenAI** makes **Codex**, another agent you may choose. The Codex command-line tool is Apache-2.0 licensed, and our example command for it is unverified.
- **Slack**, a Salesforce company, provides the Slack platform and APIs for the planned human-direction channel. The Slack bridge is not built yet, and the repository holds only an example app manifest.
- **Playwright**, an open-source project of Microsoft Corporation under Apache-2.0, drives the browser when an agent takes a screenshot of a world, as Spawn's own [short guide](https://www.spawn.co/llms.txt) suggests.
- **GitHub** hosts the repository and its issues, and runs our checks.
- The **Code of Conduct** is adapted from the [Contributor Covenant](https://www.contributor-covenant.org), version 2.1, which is released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The exact credit is in [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md) and on the [third-party licenses](third-party-licenses.md#the-contributor-covenant) page.
- **The Apache Software Foundation** publishes the Apache License, Version 2.0, whose unmodified text is our [LICENSE](../../LICENSE). The Foundation has no part in this project.
- **Conventions we follow:** [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) shape our changelog and version numbers. The [agents.md](https://agents.md/) convention shapes our AGENTS.md. We link the [Developer Certificate of Origin 1.1](https://developercertificate.org/) and do not copy it.
- **Communities whose patterns informed this project:** OpenClaw, the Model Context Protocol and Agentic AI Foundation projects, OpenCode, Everything Claude Code and CC Switch. We studied how they run their communities and borrowed ideas, not text; we copied no text from them. See [the research digest](../research/oss-community-patterns-2026.md) for what we looked at, with dates and sources. For the AI-assisted contributions policy, see its [Where this comes from](../contributing/ai-assisted-contributions.md#where-this-comes-from) section.

We studied ideas and structures from other communities, and we did not copy their text, unless the header of a file says so. Where a file adapts text, its header names the source and license. Where we only borrowed an idea or a structure, we say "inspired by".

Everything named above belongs to its respective owner. Its inclusion here is attribution, not endorsement, and none of the companies named has reviewed or approved this project.

## If you hold rights in something used here

If you speak for Spawn or another company named here, or you made something we should credit, please tell us. You can use the "Compliance or attribution concern" form on the [issue chooser](https://github.com/kdtix-open/sdlca-for-spawn/issues/new/choose). If you would rather not use a public issue, [SUPPORT.md](../../SUPPORT.md) lists the project's public contact address. We would much rather fix a mistake than leave it.

## If you write docs for this project

1. Use the footer above on every page in `docs/`.
2. Write names in plain text, as in the table. Say "for Spawn", never "Spawn Kit", "Spawn Mod" or anything that reads as a Spawn product.
3. Do not add a logo, even a small one, and do not copy text from a company's pages. Quote at most 25 words, with a link.
4. Before a release, a maintainer can search the docs for words that suggest a relationship, and read each hit in context. Most hits will be sentences like "this is not official".

   ```bash
   grep -rniE "official|certified|partner|powered by|built with|worked with" --include='*.md' .
   ```

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
