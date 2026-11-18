# Third-party licenses

This page is for anyone who wants to know which other people's software and services the SDLCA agent kit uses, under what license or terms, and what that means for you. It also explains how our own license and NOTICE file work, and how a contributor adds a dependency. It was written from our licensing research of 2026-11-17 and from the files in this repository.

This is a plain-language guide, not legal advice. Licenses and terms change, so check the owner's own page before you rely on anything here.

## The short version

- **What our license covers.** Unless a file says otherwise, everything we wrote in this repository (code, documentation and templates) is licensed under Apache-2.0. [LICENSE](../../LICENSE) is the unmodified Apache License, Version 2.0. The Code of Conduct is adapted from the Contributor Covenant 2.1, which its authors release under CC BY 4.0 (see [below](#the-contributor-covenant)). The license does not cover Spawn, Savi, or any other party's names, code, art or documentation, or the content of your own worlds. It does not cover Slack, any AI provider or any program listed below either. Spawn's Terms of Service stay in force for everyone who uses Spawn. See [the Spawn rules](spawn-rules.md).
- **We run, document or depend on other programs. We never bundle them.** This repository contains no third-party source code, no binaries, no container images and no copies of anyone's documentation, apart from the Apache License text and the Code of Conduct, which is adapted from the Contributor Covenant 2.1 under CC BY 4.0. Each person installs the tools themselves, under each tool's own license.
- **A fork inherits our NOTICE.** If you fork this repository and distribute it, Apache-2.0 section 4(d) asks you to carry along the attribution notices in our [NOTICE](../../NOTICE). NOTICE says that, apart from the Apache License text and the Code of Conduct (adapted from the Contributor Covenant 2.1 under CC BY 4.0), the project does not contain or redistribute code, documentation, artwork or logos owned by Spawn, Savi, Anthropic, OpenAI or other third parties. If your fork bundles any such work, change that statement in your fork and add the notices that work needs.
- **There is one declared dependency:** `playwright-core`, an npm package under Apache-2.0. `bun install` fetches it into `node_modules/`, which git ignores and we never commit.
- **So far this asks little of us.** Running or documenting a program does not carry that program's license into our code. The duties below begin only if someone redistributes a tool together with the kit, for example in a container image, a virtual machine image or an installer. Please do not do that without reading the license of every tool inside it.

The words in the tables mean this:

| Word | Meaning |
| --- | --- |
| Invoke | The kit starts the program as a separate process and reads its text output or exit code. |
| Document | Our docs name the program or show an example command. The person installs it. |
| Depend on | It is declared in `package.json`, pinned in `bun.lock`, and installed by `bun install`. |
| Never bundle | A copy is never committed here, copied into a file here or shipped by us. |

## Programs the kit runs or needs

| Program | License | How we use it | What follows |
| --- | --- | --- | --- |
| Python 3 | PSF-2.0 ([source](https://github.com/python/cpython/blob/main/LICENSE)) | Invoke. It runs the routing, prompt rendering, chat splitting and world registry tools. They use only the standard library, and the shell scripts start them as `python3 -I -B`. | Nothing. |
| git | GPL-2.0-only, with LGPL-2.1 for some files ([source](https://github.com/git/git/blob/master/COPYING)) | Invoke. The kit clones worlds and sets options inside each clone. The agent runs git too. | Nothing for starting it as a separate program and reading its text. Copying git's code into our files, or shipping git binaries, would bring in GPL duties. We do neither. |
| curl | The curl license, an MIT-style license ([source](https://github.com/curl/curl/blob/master/COPYING)) | Invoke. Authenticated calls to Spawn, with the token read from standard input. | Nothing. |
| `flock` from util-linux | The file `flock.c` is MIT. The util-linux package as a whole mixes GPL, LGPL, MIT and BSD licenses ([source](https://github.com/util-linux/util-linux)). | Invoke. One lock per world. | Nothing. |
| `timeout` from GNU coreutils, and other standard tools such as bash, sed, awk and grep | GNU programs are mostly GPL-3.0-or-later. We checked `timeout`, not each of the others. | Invoke. | Nothing. |
| systemd | Mostly LGPL-2.1-or-later ([source](https://github.com/systemd/systemd)) | Invoke `systemctl` from the install script. The unit file in `systemd/` is our own text, not systemd code. | Nothing. systemd is part of your operating system. |
| Bun | MIT, with parts under other licenses, including JavaScriptCore under LGPL-2 ([source](https://github.com/oven-sh/bun/blob/main/LICENSE.md)) | Invoke. Spawn's client needs it, and the kit's screenshot script runs on it. Bun joined Anthropic in December 2025, and Anthropic said it stays open source and MIT-licensed ([announcement](https://www.anthropic.com/news/anthropic-acquires-bun-as-claude-code-reaches-usd1b-milestone), read 2026-11-17). | Nothing while the person installs it. By our inference (not checked), a program made with `bun build --compile` embeds Bun, so shipping one would be redistribution. We ship none. |
| Node.js | MIT, with a list of bundled third-party notices ([source](https://github.com/nodejs/node/blob/main/LICENSE)) | Document only. [Getting started](../getting-started.md) says Node was used only to install Bun. The kit does not run it. | Nothing. |
| `playwright-core` | Apache-2.0, by Microsoft Corporation. Its NOTICE says it contains code derived from Puppeteer, also Apache-2.0 ([source](https://github.com/microsoft/playwright)). | Depend on. Version 1.65.1 is pinned in `bun.lock`. Only `lib/shot.mjs` uses it, through `sdlca-look`, to attach to a page on this machine over a local debugging port. | Nothing while it stays in `node_modules/`. If anyone redistributes it, Apache-2.0 section 4 applies: include the license, keep its NOTICE, and mark changes. The package carries its own LICENSE, NOTICE and third-party notices when installed. |
| The browser Spawn's client opens | Chromium's source is under a BSD-style license, and builds include many third-party parts ([source](https://chromium.googlesource.com/chromium/src/+/main/LICENSE)). | Not ours. The comment in `lib/shot.mjs` says Spawn's client opens a Chromium tab, and the kit attaches to it. The kit installs, starts and ships no browser. | Nothing. |
| Spawn's client, `@spawnco/client` | UNLICENSED, which is Spawn's proprietary software | Document, and invoke the `spawn` command. The person installs it from npm. | See [the Spawn client](#the-spawn-client) below. |

## Agent tools you may choose

The kit needs a command that reads a prompt on standard input. It ships no adapter for any provider and installs none. The commands in [Configuration](../configuration.md) are examples, and the ones for tools other than Claude Code are unverified. Choose a tool yourself and read its terms.

| Tool | License or terms | How we use it | What follows |
| --- | --- | --- | --- |
| Claude Code (Anthropic) | Proprietary. Its repository says all rights are reserved and use is subject to Anthropic's Commercial Terms ([source](https://github.com/anthropics/claude-code)). Which terms apply depends on your plan: commercial terms for Team, Enterprise and API use, consumer terms for Free, Pro, Max and Ultra ([Anthropic's legal page](https://code.claude.com/docs/en/legal-and-compliance), read 2026-11-17). | Document. Our examples use `claude -p`, and the maintainers tested Claude Code 2.1. Anthropic documents `-p` as its [non-interactive mode](https://code.claude.com/docs/en/headless). | We do not copy, change or ship it. Anthropic says developers who build products or services should use API-key authentication, and must not route requests through other people's subscription credentials or collect or store claude.ai credentials. The kit collects and relays no credentials: each person uses their own. If anyone runs the kit as a service for other people, they need Anthropic's commercial terms. We name Claude Code in plain text only. |
| OpenAI Codex CLI | Apache-2.0, with a NOTICE that credits another project ([source](https://github.com/openai/codex)) | Document, as an unverified example. | Nothing for us. OpenAI's docs say to use API-key authentication for programmatic workflows and not to expose Codex execution in untrusted or public environments ([OpenAI docs](https://developers.openai.com/codex/auth), read 2026-11-17). A chat room is an untrusted channel, so keep the sender allowlist tight and read the [security model](../security-model.md). We could not read OpenAI's Terms of Use (the page refused our request). |
| OpenCode | MIT ([source](https://github.com/anomalyco/opencode)) | Document, as an unverified example. | Nothing for us. If you use it with Anthropic models, use an API key. |
| Cursor's command-line agent | Proprietary. Anysphere's Terms of Service, last updated 2026-09-03 ([terms](https://cursor.com/terms-of-service)). | Document, as an unverified example. | We do not copy or ship it. Its terms limit publishing benchmark results without enough detail for others to repeat them. If this project ever publishes a comparison of agents, it will either give full details or leave Cursor out. |
| Gemini CLI | Not checked by our research. | Document, as an unverified example. | Check the project's own license and terms before you use it. |
| Any other tool | Check it yourself. | Not documented. | The kit does not translate between tools, and we do not redistribute any. |

## Services and their terms

A service has terms of use, not a software license.

| Service | Terms | How we use it | What follows |
| --- | --- | --- | --- |
| Spawn | [Terms of Service](https://www.spawn.co/terms-of-service), last revised 2026-10-09 | The platform the kit works with. | Each person needs their own account and follows the Terms. See [the Spawn rules](spawn-rules.md). |
| Slack | [API Terms of Service](https://slack.com/terms-of-service/api) (effective 2025-10-10), the App Developer Policy and the Brand Terms | Planned only. The repository holds an example app manifest and no Slack code. We use no Slack software development kit. | If the bridge is built: each organization creates its own app from the manifest, for its own use, with the smallest set of permissions it needs. Slack's terms forbid using Slack data to train a large language model, and the kit does not. Slack's API Terms describe "commercial distribution" broadly, including a free app that connects to a paid product, and say this reaches app templates. We have not established whether an example manifest counts, and a maintainer should ask Slack before we offer it as a ready-made app. |
| GitHub | [Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service), effective 2026-04-27 | Hosts the repository, issues and builds. | A machine account must be set up by a human who accepts the terms. Automated bulk or fake activity is not allowed. What you push to a public repository is also covered by GitHub's terms. See [AI-assisted contributions](../contributing/ai-assisted-contributions.md). |
| Discord | Discord's Developer Terms and Policy. We could not read the primary texts, so we make no claim about them. | Document only: Spawn's community lives there, and we point people to Spawn's own channels for Spawn problems. The kit has no Discord integration. | If one is ever added, read the live policy first, and do not collect message content for training. |

## Tools for developing the kit

You do not need these to run the kit. CI and `scripts/lint.sh` use them. We invoke them and never copy their code or rule text into our files.

| Tool | License | How we use it |
| --- | --- | --- |
| ShellCheck | GPL-3.0. CI installs it through the `shellcheck-py` wrapper, which declares MIT. | Invoke, to lint shell scripts. |
| yamllint | GPL-3.0-or-later, as declared by version 1.38.0 | Invoke, to lint YAML. |
| actionlint | MIT, as declared by the `actionlint-py` wrapper, version 1.7.12.25 | Invoke, to lint workflows. |
| GitHub CLI (`gh`) | MIT ([source](https://github.com/cli/cli)) | Invoke, in the maintainers' setup scripts `scripts/setup-github.sh` and `scripts/setup-project.sh`. |
| `actions/checkout`, `actions/labeler`, `oven-sh/setup-bun` | MIT | Referenced by the workflows and pinned by commit. Never copied. Dependabot proposes updates. |

## The Spawn client

Spawn's client, `@spawnco/client`, is published on npm with its license field set to `UNLICENSED`. That value means no permission to copy, change or redistribute it has been granted. npm's documentation says to use it when you do not want to give others the right to use a package under any terms ([npm docs](https://docs.npmjs.com/cli/v11/configuring-npm/package-json), read 2026-11-17). The source repository named in its package metadata is not public: it returned "not found" on 2026-11-17 ([registry entry](https://registry.npmjs.org/@spawnco%2fclient)). So:

- **We never copy, bundle, vendor, fork, patch, repackage or mirror it,** and we never put it in a container image. It is not in `package.json` or `bun.lock`.
- **We tell people to install it themselves from npm,** with `bun add -g @spawnco/client`, which is what Spawn tells agents to do.
- **We run it as a separate program** (`spawn events`, `spawn login`, `spawn client ...`) and treat its output as data.
- **We describe it in our own words** and quote at most 25 words from it, with a link.
- **It is a loader.** At run time it downloads Spawn's current client from Spawn's server and runs it. That code is Spawn's software, under Spawn's Terms. This project neither has it nor ships it. For that reason the docs tell you to leave `SPAWN_ORIGIN` unset.

Spawn's own instructions tell agents to install and run the client, so using it for that purpose is what Spawn intends. That is permission implied by Spawn's instructions, not an express license. If we ever wanted more, such as a wrapper that includes its code or a container image with it inside, we would need Spawn's written permission first.

Two other Spawn packages on npm, `@spawnco/server` and `@spawnco/sdk-types`, list MIT as their license, but their packages ship no license text and no copyright holder line. We do not use them. Do not add them without asking Spawn which holder line to credit.

Spawn's documents, its API description and the starter files it puts in every world carry no license statement. Spawn's `robots.txt` has a line saying crawlers may collect its public pages for search, AI input and AI training. That is a preference for crawlers, not a license to copy or republish. We link to Spawn's pages and paraphrase them.

## The Contributor Covenant

Our Code of Conduct, [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md), is adapted from the Contributor Covenant. Its license requires credit. This is the Covenant's own attribution line, and we keep it here as well as in that file:

> This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org), version 2.1, available at <https://www.contributor-covenant.org/version/2/1/code_of_conduct.html>.

- **License.** Version 2.1 is released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Our evidence is a 2024 copy in the Internet Archive of the Contributor Covenant's own page, so please check it against the live page at your next review.
- **What CC BY 4.0 asks of us.** Credit the creator, link to the license, say that we changed the text, and link to the original. The changes (the enforcement contact and a short project addendum) are stated in the file.
- **It is a different license from our code.** Apache-2.0 does not cover that text, and CC BY 4.0 does not cover our code. If you adapt our Code of Conduct, keep the credit and say what you changed.
- **Do not mix in version 3.0.** That version is released under CC BY-SA 4.0, a share-alike license, and Creative Commons' list of licenses compatible with it does not include Apache-2.0 ([Creative Commons](https://creativecommons.org/share-your-work/licensing-considerations/compatible-licenses/), read 2026-11-17). Copying its text into this file would change the terms. If we ever move to 3.0, a maintainer decides that on purpose.

## Apache-2.0 and the NOTICE file

- **`LICENSE`** is the official Apache License, Version 2.0, unmodified. On 2026-11-17 it was 11,358 bytes with this SHA-256 checksum, matching the file the Apache Software Foundation serves. A maintainer checks it before each release (see [Releasing](../contributing/releasing.md)):

  ```bash
  echo "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30  LICENSE" | sha256sum -c -
  ```

  Never edit `LICENSE`, even to fill in the name in its appendix. The copyright line lives in [NOTICE](../../NOTICE) and in file headers.
- **`NOTICE`** holds the project name, the copyright line, the license statement, and our independence and trademark paragraph. It is short on purpose. Apache-2.0 section 4(d) lets a NOTICE file exist, says redistributors of derived works must carry its attribution notices, and says its contents are for information and do not change the license ([license text](https://www.apache.org/licenses/LICENSE-2.0.txt), read 2026-11-17). The Apache Software Foundation's guidance is to add nothing that is not legally required.
- **What does not go in NOTICE:** the license text; notices for things we only run or document, such as git, Bun or Claude Code; and the Contributor Covenant credit, which belongs in its own file and in this page.
- **When NOTICE grows:** if we ever copy or adapt Apache-2.0 code that has its own NOTICE, we carry the relevant parts of it and mark our changes (sections 4(b) and 4(d)).
- **File headers.** Every new source file starts with an `SPDX-License-Identifier: Apache-2.0` comment (`#` or `//`), a standard one-line tag, as [AGENTS.md](../../AGENTS.md) says.
- **If you redistribute the kit,** section 4 asks you to give recipients a copy of the license, keep the notices, mark files you changed, and carry the NOTICE. Section 6 grants no permission to use the Licensor's names or marks, and nothing here grants a right to use anyone else's. See [trademarks and credits](trademarks-and-credits.md).
- **Contributions** come in under Apache-2.0 (section 5), with a Developer Certificate of Origin sign-off. Section 3 also gives users a patent license from each contributor for what they contribute. Employers should know their staff grant it. See [CONTRIBUTING.md](../../CONTRIBUTING.md).

## How to add a dependency

Please ask first. A dependency is a promise to keep up with someone else's work, and each one adds a license to check. Our working rule below came from our 2026-11-17 research, and the maintainers decide.

1. **Open an issue or a discussion before you write code.** Say what the dependency does, why the standard library or a shell tool is not enough, and which license it has. AI agents working on this repository must ask a person before they change `package.json`, `bun.lock` or `NOTICE` ([AGENTS.md](../../AGENTS.md)).
2. **Python: no packages.** The Python code uses only the standard library, and we want to keep it that way.
3. **Check the license** of the package and of everything it pulls in. Permissive licenses such as Apache-2.0, MIT, BSD and ISC are fine. Do not import or link a GPL or AGPL library: call that program as a separate process instead. A package with no license is all rights reserved, so we cannot use it. We do not add any Spawn package (see above).
4. **Add it with Bun** (`bun add <package>`) and commit the updated `bun.lock`. CI runs `bun install --frozen-lockfile`, so the two files must agree. The labeler marks pull requests that change either file with `dependencies`, and Dependabot proposes later updates.
5. **Never vendor.** Do not copy a library's source, a binary or a built bundle into the repository. If you think you must, stop and ask a maintainer: it needs the license text, a NOTICE entry and a decision.
6. **Add a row to this page** in the right table, with the license, how we use it and what follows. If the kit calls a new external program, also add it to the checks in `scripts/install.sh`, to the prerequisites in [Getting started](../getting-started.md), and here.
7. **Say so in your pull request,** and in the AI-assistance section if a tool suggested the dependency. Do not take a package name on an AI tool's word alone: check that it exists and who publishes it.

## If you find a mistake

If a license or term on this page is wrong or out of date, please open an issue with the "Compliance or attribution concern" form on the [issue chooser](https://github.com/kdtix-open/sdlca-for-spawn/issues/new/choose). Thank you.

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
