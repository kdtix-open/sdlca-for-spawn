# Security policy

This page is for anyone who thinks they have found a security problem in the SDLCA agent kit, and for people who run the kit and want to know what we do with such reports. It tells you how to report in private, what we cover, what to send, and what to expect back.

The kit is an unofficial community project. It is not made or supported by Spawn. We are a small team, so every time on this page is a goal and not a promise.

**Last reviewed 2026-11-17.**

## How to report a vulnerability

Please do not open a public issue, pull request or Discussion for a security problem. Do not post a token, an invite code, exploit details, or any other session, join or login credential, including values printed by `spawn client join`, anywhere public. Use one of these two ways instead:

1. **GitHub private reporting (preferred).** Open the repository's Security tab and choose "Report a vulnerability", or go straight to the [private report form](https://github.com/kdtix-open/sdlca-for-spawn/security/advisories/new). Only you and the maintainers can see what you write. If you do not see the button, the setting may not be switched on yet, so use email.
2. **Email security@kdtix.com.** Use it if you cannot use GitHub. Ordinary email is not encrypted and we do not publish an encryption key. So send a short description first, and we will agree a safer way to share the details. Never put a working token in an email.

If you are not sure whether something is a security problem, report it privately anyway. We would much rather read one report too many.

## Which versions we get fixes for

| Version | Supported |
| --- | --- |
| The `main` branch | Yes. Fixes land here first. |
| The latest release | Yes. There is no release yet. The first one is planned as 0.1.0. |
| Older releases | No. Please update to the latest. |

The project is before version 1.0 and still changing shape, so we only fix the newest code.

## What is in scope

Problems in this repository's code, scripts, templates, workflows and documentation that could hurt someone who runs the kit or contributes to it. For example:

- **A way around the sender gate.** Any way to make an agent turn run for someone who is not the account's owner or on its allowlist. This includes a crafted event that the kit treats as allowed, or an agent handle that is accepted as a person.
- **Command execution for someone who is not allowed.** Message text, an event field or a file in a world that makes the kit itself run something, expand a template, or choose where to run, when it should not.
- **Token exposure.** A way for a Spawn token, an invite code or a provider key to reach a log, a command line, a process list, a prompt, a file with loose permissions, or any host other than Spawn.
- **Path traversal and wrong-place access.** An account name, world name or event field that makes the kit read or write outside its own folders, or run an agent in the runtime home (which holds every account's token) or in another world's clone.
- **A prompt fence that can be forged.** Text that escapes the `<untrusted_event>` wrapper in the agent prompt, or reaches the shell or the template filler.
- **CI and supply-chain problems in this repository.** A workflow that lets a pull request from a fork gain write access or read secrets, an action that is not pinned, a harmful or vulnerable dependency, or a secret in the history.
- **Documentation that makes people less safe than we claim.** For example an example command that is much broader than the text says.

## What is out of scope

- **Spawn itself.** The platform, its website, worlds, players, Savi, accounts and its client belong to Spawn, so report problems there: the in-app "Report a bug" button, [Spawn's support page](https://www.spawn.co/support), or the contact address Spawn lists there (contact@spawn.co). We found no separate security page for Spawn on 2026-11-17. Spawn's terms ask people to report promptly any bug that gives users unintended benefits, and not to tell other users about it (section 4(s), read 2026-11-17). We read that as a good reason to keep the details of any way to break Spawn out of public posts, here or anywhere.
- **Other people's software and services.** AI provider tools and the permission rules inside them, Slack, GitHub, Bun, git and systemd have their own security teams. Report there. If you find that something our documentation relies on does not hold, tell us as well, because then our docs need fixing.
- **Social engineering and spam.** Tricking a maintainer or a user is not a flaw in the kit.
- **Findings that need a machine that is already compromised.** If an attacker already runs as your user, holds your token files or has administrator access, the kit cannot help.
- **Known limits.** [The security model](docs/security-model.md) lists risks we already know and cannot remove, such as a same-user agent being able to read token files, broad allow rules, and prompt injection being reduced but not eliminated. A new way around a protection we claim is in scope. The known limits themselves are not new findings.
- **Things only an allowed person can do.** The owner and every listed sender have the agent's power by design, so what they can make it do is not a vulnerability.
- **Reports without a way to reproduce them.** Scanner output with no demonstrated impact, and purely theoretical findings, will be closed with a note.

## What to send

- A short description, and what could go wrong, in plain words.
- The smallest steps or input that show the problem. A failing test or a command with made-up input is ideal.
- The version: the release tag, or the output of `git rev-parse --short HEAD`.
- Your system: operating system, and the versions of bash, Python, Bun and the Spawn client, plus the agent command you used (without any keys).
- What you expected, and what happened instead.
- Optional: how you would fix it, and whether you want credit and under what name.

**Please do not send real tokens, invite codes, other people's messages, personal data, or any other session, join or login credential, including values printed by `spawn client join`, or the addresses of other people's worlds.** Replace them with `REDACTED`. If you used an AI tool to find the problem, that is welcome, but check it yourself first and write it up in your own words, as the [AI policy](docs/contributing/ai-assisted-contributions.md) asks.

## What to expect

These are goals. There is no service-level agreement.

| Step | Our goal |
| --- | --- |
| We acknowledge your report | Within 3 business days |
| We tell you whether we think it is a vulnerability, and how serious | Within 7 days of your report |
| We fix it, or reduce the risk with a safer default or a clear warning | Depends on how serious it is. The most serious come first, and we tell you our plan and keep you updated |
| We publish what happened | By default 90 days after your report, or earlier once a fix is out |

We follow *coordinated disclosure*, which means we agree a date with you before anything is made public. We may ask for more time for a hard fix, and we will give reasons. If a problem is already being used against people, we may publish sooner. We publish through a GitHub security advisory and mention the fix under "Security" in the release notes. We ask GitHub for a Common Vulnerabilities and Exposures (CVE) identifier when one applies. If you want credit, we name you in the advisory and the notes. If you prefer not to be named, we leave your name out.

## Testing safely

If you act in good faith and follow this page, we will not take legal action against you, and we will not ask anyone else to, for testing the kit **on your own installation**: your own machine, your own accounts, tokens and worlds, and your own data.

To stay inside that promise:

- Never test against other people's Spawn accounts or worlds, or against anyone else's machine.
- Do not access, change or keep other people's data. If you reach some by accident, stop and tell us.
- Do not run denial-of-service tests, send spam, or use social engineering.
- Do not do anything to Spawn's service that Spawn's own terms forbid. Test the kit, not Spawn.

This promise covers only what this project can promise. It does not speak for Spawn, GitHub, Slack, an AI provider or anyone else. Their terms still apply to you.

## No bounty

We cannot pay for reports. We can say thank you, give credit if you want it, and fix the problem.

## If you find a leaked token

If you find a real token, invite code or key in this repository, in an issue or anywhere else public, tell us privately, the same way as above. If it is yours, replace or revoke it first, before anything else. [Operations](docs/operations.md#rotating-a-token) shows how to rotate a Spawn token.

## More reading

[The security model](docs/security-model.md) explains who can trigger work, what the agent can do, how tokens are handled, and which risks remain. [SUPPORT.md](SUPPORT.md) says where to take other questions.
