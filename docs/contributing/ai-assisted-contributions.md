# AI-assisted contributions

This page is for everyone who sends something to this project, and for AI agents that work on it. It says that AI-assisted work is welcome, what we ask you to disclose, who is accountable, and what happens if something goes wrong.

**Version 0.1 (first draft). Last reviewed 2026-11-17. Next review due by 2027-05-17.**

This is a working policy. It was drafted with AI help from a comparison of other projects' policies, and it has not been reviewed by a lawyer. Some decisions are still open; they are listed at the end under [Decisions the maintainers are still making](#decisions-the-maintainers-are-still-making), and they are not settled just because the rest of the page reads firmly.

## Our position

This project is built with AI agents, and most of the repository is AI-assisted. We say so openly, so disclosure here is a record of how things were made, not a stigma. We welcome AI-assisted contributions.

- **People, not tools, are accountable.** A named person stands behind every change.
- **One bar for everything.** The same standards for quality, security and licensing apply whether a change was typed by hand or generated.
- **Worth more than it costs.** A contribution should save the reviewer more time than it takes. Changes that cost more review time than they add are hard to review as sent. [LLVM's policy](https://llvm.org/docs/AIToolPolicy.html) calls such contributions "extractive"; we name the problem after the change and not the person, and our label for it is `hard-to-review`.

We are neither against AI nor relaxed about it: use it, and take care.

## The short version

1. You may use AI tools to write code, docs, tests and issues.
2. Tell us when an AI tool did more than spelling, formatting, autocomplete or a mechanical rename: a section in the pull request, plus an `Assisted-by:` line in the commit.
3. A named person owns every pull request. They have read every changed line, can explain it without AI help, and answer review comments themselves.
4. Only a person signs off on the Developer Certificate of Origin. An AI agent never adds `Signed-off-by`.
5. Other people's autonomous agents do not open pull requests or issues here. Our own agent accounts follow the rules below.
6. Bug reports need evidence, checked by a human, in the reporter's own words.
7. No secrets in prompts, and no one else's Spawn content either.
8. If something goes wrong, we start with a friendly note.

## Disclose AI help

**What counts.** An AI tool did more than spelling, formatting, autocomplete or a mechanical rename. When in doubt, disclose. Nobody is penalized for honest disclosure. Hiding AI use is what we treat as a problem.

### Layer 1: the pull request section

The [pull request template](../../.github/PULL_REQUEST_TEMPLATE.md) has an "AI assistance" section. This is the layer that counts, because it explains the change to a human. Say:

- which tool and model helped;
- what it produced, and what you rewrote or checked by hand;
- how you tested it, and plainly what you did not test;
- for a large generated change, a short summary of the prompts or plan.

### Layer 2: the `Assisted-by` trailer

Add a trailer to each commit AI helped with:

```text
fix(runtime): free the world lock when a turn times out

Assisted-by: Claude Code claude-sonnet-5-5
Signed-off-by: Alice Example <alice@example.com>
```

To add both lines from a terminal, give the second line as a second message:

```bash
git commit -s -m "docs: fix typo in the quick start" -m "Assisted-by: Claude Code claude-sonnet-5-5"
```

If you edit on GitHub's website, type the `Assisted-by:` line and your `Signed-off-by:` line in the commit description box.

The form is `Assisted-by: <tool> <model or version>`. If almost all of a change was generated, `Generated-by:` with the same value is also fine. The trailer is machine-readable provenance. By itself it is a weak signal: the Linux kernel dropped its own `Assisted-by` tag in October 2026 after finding that only about one commit in ten carried it ([commit message](https://github.com/torvalds/linux/commit/1e035297ff)). That is why the pull request section matters more.

**`Co-Authored-By` lines.** Many agent tools add `Co-Authored-By` lines by default. We accept them. You do not need to remove them, and we do not require them. They do not replace the section and the `Assisted-by` trailer. Practice varies across projects: some projects forbid AI co-author trailers, for example [Kubernetes](https://www.kubernetes.dev/docs/guide/pull-requests/#ai-guidance) and [Mesa](https://gitlab.freedesktop.org/mesa/mesa/-/blob/main/docs/submittingpatches.rst), while others accept them. Never add a `Co-Authored-By` line for a person who did not take part.

**Naming a tool is provenance, nothing more.** It is a statement of fact. It does not mean the tool's maker, or Spawn, endorses this project.

### Issues, discussions and comments

The issue forms ask whether an AI tool helped. Mark any text you copied from an AI tool as a quote. Do not paste raw AI replies as your own words. Maintainers may apply these labels to help sort things: `ai-assisted`, `agent-authored`, `needs-human-explanation`, `hard-to-review` and `ai-disclosure-missing`. See [triage and labels](../community/triage-and-labels.md).

## A person is accountable

- Every pull request has one named accountable person, either the author or the person who directs and reviews an agent.
- They have read every changed line, can explain it in their own words without an AI, and will answer review comments themselves. Pasting a raw agent reply as a review response is not enough; quoting a draft is fine if you label it.
- Maintainers follow the same rules. We disclose too.
- New contributors are welcome to start small. We keep `good first issue` items for people who are learning, and our agent accounts do not take them. If you use an agent, please leave them for people who are learning too.

## Only people sign off (DCO)

Contributions are made under Apache-2.0 (section 5 of the [license](../../LICENSE)). We also ask for a sign-off under the [Developer Certificate of Origin 1.1](https://developercertificate.org/), or DCO (`git commit -s`). A sign-off is a person saying they take responsibility for the whole commit, including any generated parts.

The Linux kernel states the rule bluntly, and we follow it: "AI agents MUST NOT add Signed-off-by tags." ([kernel documentation](https://docs.kernel.org/process/coding-assistants.html)). Two ways of working both end with a human sign-off:

- **Mode A, a person with an assistant (the default).** Commits carry the person's name, their `Signed-off-by` and an `Assisted-by` trailer.
- **Mode B, a project agent account.** Commits are authored by the machine account with an `Assisted-by` trailer and no `Signed-off-by` from the agent. A named maintainer adds their own sign-off when reviewing or merging.

There is no automatic DCO check yet; it is planned (see the [roadmap](../community/roadmap.md)). When we build one, it will need to understand Mode B. Until then maintainers check by hand.

**The open legal question.** The certificate says the contribution was "created in whole or in part" by the person, or is based on material they have the right to submit. Some projects conclude nobody can honestly certify that for AI output and decline AI contributions; QEMU does ([code provenance policy](https://www.qemu.org/docs/master/devel/code-provenance.html)). Others, including the kernel, the Apache Software Foundation and the Linux Foundation, conclude that human review plus a good-faith check of the tool's terms and of third-party content is enough. We follow the second view for now. A lawyer has not reviewed that choice.

**Tool terms.** You must be allowed, by your AI tool's terms, to contribute its output under Apache-2.0. If the terms say otherwise, do not contribute that output. We have not yet reviewed any provider's terms, so the check is yours.

## Agent accounts and bots

### Project agent accounts (ours)

These are the rules we hold our own agent accounts to. Some of them depend on GitHub settings that the maintainers have to configure; see [GitHub settings for maintainers](../maintainers/github-settings.md).

- **Registered and human-owned.** Each account is created by a named person who accepts GitHub's terms and answers for what it does. GitHub's rules allow "machine accounts" on that basis ([GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)). The account's profile says it is automated and who operates it. The public list of these accounts and their owners is not published yet (see decision 6 below).
- **Clearly marked and blockable.** It never pretends to be a person or Spawn staff.
- **Least privilege.** It works on its own branches, never `main`. It cannot approve or merge pull requests or mark them ready for review, it has no admin rights, and it holds no secrets beyond what its task needs. CI on its pull requests waits for a human to approve the run. This copies the limits GitHub puts on its own [cloud agent](https://docs.github.com/en/copilot/concepts/security-governance-and-network-settings/risks-and-mitigations).
- **Narrow scope.** It acts only in `kdtix-open` repositories. It does not open issues, pull requests or comments in other repositories, in Spawn world repositories, or in Spawn, Slack or Discord channels, unless a person told it to and reviewed the exact text.
- **Capped.** At most three open pull requests per account at a time, drafts included (a starting number we may change).
- **Untrusted input.** It treats issue, pull request and comment text as untrusted, because hidden instructions in text are a known attack. It runs on a non-collaborator's content only when a maintainer starts it on purpose.
- **Honest public text.** A comment or announcement an agent wrote is either reviewed by a person who takes responsibility or visibly labeled as AI-generated. A bot that talks to people says it is a bot.

### Agents run by contributors

Using your own agent with you in charge, reading its work before you submit, is AI-assisted contribution, and welcome. Fully autonomous agents that open pull requests or issues with no accountable person reading them first are not accepted. This matches projects such as [PyTorch](https://github.com/pytorch/pytorch/blob/main/AI_POLICY.md) and LLVM, and the draft policy from the Open Source Security Foundation (OpenSSF). An exception needs to be arranged in advance with a maintainer, with a named human sponsor, and be written down. [OpenInfra](https://openinfra.org/legal/ai-policy) makes a similar exception for documented automation with an owner.

### Review bots

A review bot is allowed only if it is advisory: a separate, blockable account whose comments never block a merge until a human endorses them. A bot never approves. AI is never the sole or final judge of a change.

## Review requirements

- At least one human maintainer approves, and it is not the person who directed the agent. No agent merges its own work or anyone else's. While there is a single maintainer this cannot always be met (see [how decisions are made](../../GOVERNANCE.md#how-decisions-are-made)): the pull request says so, and someone reads it afterward.
- Changes to behavior come with tests. Failing tests are never edited or removed to get a green check.
- An AI-assisted pull request says how it was tested and what was not.
- Agent work comes as small pull requests, in draft until the accountable person has reviewed it themselves.
- Changes to token handling, the sender allowlist, routing, CI and agent instructions are security-sensitive. We want two human reviewers for them. We are a small team, so if we could not manage it, the pull request says so.
- Maintainers may apply `hard-to-review` or `needs-human-explanation` and move on without a detailed review.

## Reporting problems

- **Bug reports** use the issue forms, which ask for steps that reproduce the problem, the environment, and whether AI helped. If an AI tool found the problem, you check it yourself and write it up in your own words. A pasted, unchecked report may be closed. Evidence beats polish: [curl](https://curl.se/dev/contribute.html#on-ai-use-in-curl) requires disclosure when AI helped find a problem, and the [OpenSSF guide](https://best.openssf.org/Finding-and-Fixing-Vulnerabilities-Using-AI/handle-external-findings.html) records that asking for a reproducible case and a human author helped restore the signal in reports.
- **Feature requests** do not need an AI-written implementation plan. Describe the problem first; we agree the feature is wanted before anyone writes the change.
- **Security problems** go to the private channel in [SECURITY.md](../../SECURITY.md) with a reproducing input. AI-assisted reports are welcome if you have validated them.
- **Problems in Spawn itself** go to Spawn. We do not forward unreviewed AI-generated reports upstream, and nobody should on our behalf.

## When something goes wrong

We go in steps, and we give you one chance to explain unless the behavior is abusive or deceptive.

1. A friendly note and a label (`needs-human-explanation` or `ai-disclosure-missing`), with a link to this page. The item stays open.
2. If the note is ignored, the change is too hard to review as sent, or evidence is missing, we close it without a detailed review. You can reopen it once the gap is fixed.
3. A temporary limit on the account, using GitHub's tools.
4. For repeated violations, deliberately hiding AI use, fabricated reports or autonomous-agent abuse, a block from the project. Lying about AI use is handled under the [Code of Conduct](../../CODE_OF_CONDUCT.md).
5. If merged code may contain copied or incompatible material, we remove or rewrite it promptly, tell the people affected and record what happened.
6. If a project agent account misbehaves, we suspend its tokens first, review its session log and post an incident note. Its human owner is accountable.

To appeal, reply in the thread or use the conduct contact in the Code of Conduct. We do not publish lists of people. If we keep a list of repeat problems, it is private and has an appeal route (decision 5 below).

## Copyright, in plain words

This is a short guide, not legal advice. Ask a lawyer about your own situation, and follow your employer's rules, which may be stricter than ours.

- **Ownership is unsettled.** In the United States, output made purely by an AI is not protected by copyright, while a person's creative choices, selection and edits can be ([US Copyright Office](https://www.copyright.gov/ai/)). Other countries differ and are changing. Do not assume AI output is protected anywhere.
- **A license only binds what copyright covers.** Keep a real human role in the design, choices and edits of what you contribute, and do not claim exclusive rights in text a tool wrote alone.
- **The real risk is copying.** A tool can reproduce someone else's code under a license that does not fit ours. You check for this. Use a tool's similarity or public-code filter if it has one. If you later learn you contributed copied material, tell us so we can remove or rewrite it. The [Apache Software Foundation](https://www.apache.org/legal/generative-tooling.html) and the [Linux Foundation](https://www.linuxfoundation.org/legal/generative-ai) give similar guidance.
- **Tool terms matter.** Some providers restrict how output may be used or keep rights in it. Check yours.
- **Inputs matter as much as outputs.** What you put into a prompt can come out in the result. Do not paste Spawn's documentation, skills or other proprietary text, another creator's world code or assets (every Spawn world belongs to its creator), secrets, or private material into a prompt, a commit or an issue. See [the rules we follow](../compliance/spawn-rules.md).

## How this policy changes

- It has a version number and a review date at the top, and the table below records each change.
- We review it every six months, and sooner when something triggers it: new Spawn terms, a notable change in the policies we learned from, an incident, or a legal change. Other projects' policies change fast; the kernel reversed one of its rules within ten months.
- A change is a normal pull request, and it stays open for comment for at least 14 days, the minimum that [GOVERNANCE.md](../../GOVERNANCE.md#lazy-consensus-and-the-minimum-time) sets for this policy. A maintainer who is not its author approves it when there is one (see the limit under [Review requirements](#review-requirements)). For a significant change we first post it for discussion in Discussions when practical. [GOVERNANCE.md](../../GOVERNANCE.md) says how maintainers decide.

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-11-17 | First draft, revised the same day before publication: the label for changes that are hard to review is `hard-to-review`, the limit with one maintainer is stated, the amendment minimum is 14 days, and the commit command is shown. |

## Decisions the maintainers are still making

These are not settled. Until they are, the "today" column is what we do.

| # | Question | Today | Why it is open |
|---|---|---|---|
| 1 | Which legal stance on the DCO for AI output: "a person certifies after review" or "decline AI output"? | We follow "a person certifies" (kernel, Apache Software Foundation). | It is a risk decision for the owner, and counsel has not reviewed it. |
| 2 | Name the model in trailers, or use a vendor-neutral `Assisted-by: LLM`? | Name the tool and model. | The kernel and Mesa went vendor-neutral to avoid advertising; recording the model helps reproducibility and security triage. |
| 3 | Accept default `Co-Authored-By` lines from AI tools, and should we rewrite them to `Assisted-by`? | Accepted as they are. | Other projects forbid them; rewriting at merge time is a maintainer effort. |
| 4 | Gate first-time contributors (vouching or a pull request cap)? | No gate. | We want newcomers welcome. We keep the switches (collaborator-only pull requests and issues, caps, interaction limits) in reserve for a spike of low-quality items. |
| 5 | A public list of people who broke the policy, or a private list? | No public list. | A public list raises privacy and defamation risks; a private one needs an appeal route. |
| 6 | Who owns each project agent account? | Not published. | Each needs a named person, and GitHub allows one free machine account per person. |

Other gaps we know about: we have not reviewed any AI provider's terms; there is no automatic DCO check, and no check that agent pull requests carry the trailer and the section; and the squash-merge settings may drop the trailers on individual commits, which we still need to check.

## Where this comes from

We compared the public policies of about two dozen projects and bodies. They differ on whether AI is allowed, but agree that a person is accountable, that AI work meets the same bar, and that only a person signs off. Our research did the comparison on 2026-11-17, and it is not re-checked here; policies change fast. Main sources, read by that research on 2026-11-17:

- Linux kernel: [coding assistants](https://docs.kernel.org/process/coding-assistants.html) and [the commit that removed the tag](https://github.com/torvalds/linux/commit/1e035297ff)
- [QEMU](https://www.qemu.org/docs/master/devel/code-provenance.html), [LLVM](https://llvm.org/docs/AIToolPolicy.html), [PyTorch](https://github.com/pytorch/pytorch/blob/main/AI_POLICY.md), [Kubernetes](https://www.kubernetes.dev/docs/guide/pull-requests/#ai-guidance), [Mesa](https://gitlab.freedesktop.org/mesa/mesa/-/blob/main/docs/submittingpatches.rst), [curl](https://curl.se/dev/contribute.html#on-ai-use-in-curl)
- [Apache Software Foundation](https://www.apache.org/legal/generative-tooling.html), [Linux Foundation](https://www.linuxfoundation.org/legal/generative-ai), [OpenInfra](https://openinfra.org/legal/ai-policy), and the [OpenSSF draft policy](https://github.com/ossf/tac/pull/605) (a draft, not adopted)
- GitHub: [Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) and [cloud agent risks and mitigations](https://docs.github.com/en/copilot/concepts/security-governance-and-network-settings/risks-and-mitigations)
- [US Copyright Office](https://www.copyright.gov/ai/), [Developer Certificate of Origin](https://developercertificate.org/), [agents.md](https://agents.md/)

---

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
