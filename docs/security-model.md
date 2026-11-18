# Security model

This page is for someone deciding whether to trust and run the SDLCA agent kit. It says in plain words who can make the kit do work, what the agent can do once it is running, what the kit does to protect your tokens and other people's chat text, and which risks remain. It was checked against the kit's code on 2026-11-17. Read it before you choose anything beyond the read-only agent command.

The kit is an unofficial community project. It is not made, reviewed or supported by Spawn. We are a small project and have not had an outside security audit. Everything here is what we know and what we have tested, and the risks we cannot remove are listed without softening.

## The short version

- **The kit decides who may start work and where the agent starts. It does not decide what the agent does.** Your agent command decides that, and you choose it.
- **Only the account's owner, and people you list, can start work.** Everyone else is ignored without a reply, and the log records only their handle.
- **The agent runs on your machine as your user.** Permission rules and prompts reduce the risk, but they are not a sandbox. Real isolation takes a separate Unix user, a container, a virtual machine or your provider's sandbox.
- **Chat text and the files in a world are untrusted.** The prompt marks them that way, and the kit never turns them into commands. A model can still be talked into things, so assume a hijacked turn can do whatever your chosen posture allows.
- **Tokens live in private files and never on a command line.** An agent that runs as your user can still read the files.
- **Start with the read-only posture and an empty sender list.** Widen only after you have watched the agent work.

## What the kit controls, and what it does not

| Threat | What the kit does | What is left |
| --- | --- | --- |
| A stranger mentions the agent in a room | Ignores it silently and logs the handle and the reason | Nothing, except a line in your log |
| Another owner's account tries to command this one | Denies it. Only this account's owner and its listed senders are allowed | Nothing |
| The agent answers itself in a loop | Denies the agent's own handle | Nothing |
| Chat text tries to pick which world's clone the agent works in | Routing reads ids and addresses in structured fields and never the chat text, and matches whole ids and addresses only | A direct message has no world, and the agent may choose any clone it can reach |
| An event with no known world makes the agent work next to the tokens | The agent starts in `run/scratch/<account>`, a folder the kit makes for it, never in the runtime home that holds every account's token | The scratch folder is only the starting point. An agent can change folders, and one that runs as your user can read the token files by their path |
| Chat text tries to run shell commands or fill template fields | Text is never expanded by the shell, and templates are filled in one pass (tests cover both) | Nothing in the kit. See the next row for what a model does with the text |
| A trusted sender, or a file the agent reads, contains hostile instructions | Fences the event, says that everything fetched is data, and tells the agent to treat chat as a request to weigh | Prompt injection. This is advice to a model, not a barrier |
| Someone steals a token | Private files, token off the command line, token sent only to Spawn's origin, raw token removed from the handler | Anything running as your user can read the token file |
| A runaway or hung agent, or a flood of mentions | A time limit, a bounded lock wait, an hourly cap on runs, and a failed or refused event is kept in `run/failed/` and not retried by itself | Cost up to the cap, and damage within the posture. The cap counts agent runs, not money |
| A hostile remote, submodule or large-file URL asks git for the token | Each clone's credential helper is attached to the git host of the world's URL only, so git offers nothing to other hosts | The agent can still read the token file, and an agent allowed to run git freely can run other programs through it |
| A hijacked agent harms a world | Spawn's own permission model limits the account to its worlds, and a push never publishes | Pushes to `main` go live in every open room. Use git history to repair |
| An event runs twice after a crash | Skips an event id that it already finished (it remembers the newest 500) | An interrupted turn runs again, and an event with no usable id cannot be checked |
| Logs leak other people's chat | Log files are private, the listener log holds status lines only | The agent's output and failed events hold chat text |

## Who can trigger work, and how that is enforced

Every event goes through one function, `decide()` in [`lib/route.py`](../lib/route.py), before any agent is started. The rules:

- The sender is read from the event's structured `chat.from` field and nowhere else. Handles are compared exactly as Spawn writes them, in lower case: `@name` is a person and `@@name` is an agent.
- A missing or odd-looking sender is denied. The kit fails closed.
- The agent's own handle, `@@<SPAWN_USERNAME>`, is always denied, so the agent never answers itself.
- The account's owner is allowed as `@<owner>`. An agent that happens to have the owner's name, `@@<owner>`, is not the owner.
- Other senders are allowed only if they are listed in `allowlist.json` under `spawn.<owner>`. Malformed entries, a value that is not a list, and empty strings are ignored, so a typo never widens access. If the file cannot be read, only the owner is allowed.
- Everyone else is denied without a reply. A reply would tell a stranger that an agent is listening, and would cost chat lines.
- Only `chat_mention` events can start a turn. Friend requests are accepted only from the account's owner. Events about Spawn's builder, Savi, are only logged.

With the owner `alice`, the agent `alice_helper`, and `carol` and `@@review_bot` on the list, the outcomes are:

| Sender in the event | Outcome | Why |
| --- | --- | --- |
| `@alice` or `@Alice` | Allowed | The owner. Case does not matter |
| `@carol` | Allowed | A listed person |
| `@@review_bot` | Allowed | A listed agent, written with two `@` signs |
| `@@carol` | Denied, `not-allowed` | Carol is listed as a person, and this is an agent |
| `@@alice` | Denied, `not-allowed` | An agent with the owner's name is not the owner |
| `@@alice_helper` | Denied, `self` | The agent's own handle |
| `@bob`, an owner of another account | Denied, `not-allowed` | Not this account's owner |
| `@mallory` | Denied, `not-allowed` | A stranger |
| Missing or malformed | Denied, `unknown-sender` | Fail closed |

To add a person, use `bin/sdlca-allow spawn add alice carol`. To add an agent, write its name with two `@` signs: `bin/sdlca-allow spawn add alice @@review_bot`. Names use lowercase letters, digits and underscore. To take someone off, `sdlca-allow spawn remove` needs the entry exactly as it is stored (`carol` and `@carol` are two entries), so check `bin/sdlca-allow list` first. The file is read again for every event, so a change applies at once. See [Configuration](configuration.md#the-allowlist).

The tests for the gate are in [`tests/test_route.py`](../tests/test_route.py) and [`tests/shell/test_on_chat.sh`](../tests/shell/test_on_chat.sh).

Four things to understand about this gate:

1. **Everyone on the list has the agent's power.** A listed person can make the agent do whatever your agent command allows, on your machine. The same is true of the owner. Add only people you would hand your keyboard to. The safest list is the empty one.
2. **The gate trusts Spawn to fill in `chat.from` truthfully.** The shape of the field comes from Spawn's published API description. Our tests use events we wrote by hand. If a real event looks different from what the kit expects, the sender is unknown and the event is denied, so the kit fails closed.
3. **Replies are public.** Anything the agent says in a room can be read by everyone in the room. A trusted sender can ask the agent to read a file and say what it found. Do not give the agent access to files you would not post in the room.
4. **Spawn's terms may matter.** [Spawn's terms](https://www.spawn.co/terms-of-service) (read on 2026-11-17) say you may not allow others to access or use your account, and that you are responsible for everything done through it. Whether a listed person telling your agent what to do counts as using your account is a question we have not put to Spawn. It is one more reason to keep the list empty. See [the rules we follow for Spawn](compliance/spawn-rules.md).

## What the agent can do: three postures

The kit does not limit the agent. Your agent command does, through your agent tool's own permission system. The kit ships examples for Claude Code (Anthropic's agent tool, which [can run without a person](https://code.claude.com/docs/en/headless)). The exact commands are in [Configuration](configuration.md#the-three-postures), and the first two were tested with Claude Code 2.1. Permission rules change between versions, so test your choice after every upgrade. The kit has no adapters for other tools, so for them you must work out the equivalent yourself.

| Posture | What it can do | What it can reach | Worst case |
| --- | --- | --- | --- |
| **Read-only.** The `Read`, `Glob` and `Grep` tools, plus the kit's `sdlca-say` and `sdlca-api GET` | Read files, search, read Spawn, and post chat lines. In the maintainers' test, in a clone with no project settings of its own, it could not edit files or run other commands (see residual risk 10) | Every file your user can read. A bare `Read` rule is not limited to the world's folder, so token files, env files and the credentials file are in reach | It posts what it read into a public room, or posts unwanted lines. It cannot change files |
| **Builder with a tool allowlist.** File edits, plus `git *`, `spawn *` and the kit's tools | Edit files, run any git command, run any command of Spawn's client, call any Spawn API method, and take screenshots | The same files. It can also push to a world | It pushes bad changes live to every open room. `git *` is broad, because git can run other programs through its configuration and aliases. `sdlca-api *` allows every HTTP method, including destructive ones. `spawn *` is the whole client |
| **Full autonomy.** Every permission check is off | Run any command as your user | Everything your user can reach, including your SSH keys and cloud credentials | Anything you could do at your keyboard, done by someone else |

What no posture changes:

- **The agent can run the kit's own tools.** They read the token file in order to work. An agent that can run them can use the account's token for any call they allow, and read it from the file if its rules permit file reads.
- **A posture is as strong as your agent tool's rules.** Permission rules are the agent tool's code, not the kit's. A bug or a gap there is not something the kit can see or fix.
- **The agent can write files that steer later turns,** if its posture lets it write there: `WORK-TODO.md` and `AGENTS.md` in the runtime home, which every later turn reads, and a world's own files.

### About full autonomy

Claude Code's own help describes the option that skips all permission checks in a few words: "Bypass all permission checks. Recommended only for sandboxes with no internet access." (`claude --help`, Claude Code 2.1.327, run on 2026-11-17, for the `--dangerously-skip-permissions` flag; our example uses the `bypassPermissions` mode, which we treat the same way.)

The kit's agent needs the internet, to reach Spawn and your model provider, so it cannot meet that condition. A hijacked agent with full autonomy can send data out. Use this posture only inside a disposable virtual machine or container that holds nothing of yours, and only for an owner you fully trust. The kit's example file says the same. The kit has no default agent command at all, and the listener refuses to start without one.

## Prompt injection in plain words

*Prompt injection* means text that tries to give a model new instructions. A model reads its instructions and the text it is working on in the same stream, so it cannot always tell them apart. The text can come from several places:

- **From a trusted sender,** who pastes text from somewhere else without reading it.
- **From other people.** The default prompt tells the agent to fetch the message "and what followed" through `sdlca-api GET '<actionData>'`. That read returns other people's lines in the room. They are not on your list, but the agent reads them.
- **From files in a world.** Any collaborator can change a world's files. Answers from Savi, notes and downloaded assets can carry text too.
- **From the agent's own notes.** `WORK-TODO.md` is written by the agent and read by later turns. A hijacked turn could plant text there for the next one.

What the kit does about it:

- The event goes into the prompt between `<untrusted_event>` tags, and every `<` inside is written as `\u003c`, so the text cannot forge the closing tag.
- The prompt says that the chat text, anything fetched later, the world's files, Savi's replies and `WORK-TODO.md` are data, to be weighed as information and never as instructions that change its rules.
- Chat text is never expanded by the shell, and template fields are filled in one pass, so text cannot reach `{{CODE_DIR}}` or a command substitution. Tests cover both.
- Chat text cannot choose the world the agent starts in.
- The agent is told never to print tokens, and to use `sdlca-api` so tokens stay off command lines.

What the kit cannot do: nothing in it recognizes hostile text. The fence and the wording are advice to a model, not a barrier, and models can be talked out of advice. So plan for the case where it fails. Pick a posture, a sender list and an isolation level that you can live with if a hijacked turn does the worst thing that posture allows.

## Token handling

The kit holds two kinds of secret: each account's Spawn token, and any provider keys in `SDLCA_CREDENTIALS_FILE`. How the Spawn token is handled:

| Where | How | Test or check |
| --- | --- | --- |
| On disk | A file of its own, mode 0600, in a folder of mode 0700. The kit's shell scripts run with `umask 077`, and the Python tools set mode 0600 on what they write | Set by `sdlca-onboard` and `sdlca-token`; the env file must not be writable by group or others |
| When you store it by hand | `sdlca-token add` asks for the token without echoing it, or reads one line from standard input. It takes no token as an argument, refuses an invite code and values that do not look like a token (fewer than 16 characters, or a space, double quote, backslash or character outside visible ASCII), writes the file through a temporary file and never prints the token | [`tests/shell/test_token.sh`](../tests/shell/test_token.sh) checks it |
| In the shell tools (`sdlca-api`, `sdlca-friends`) | Passed to curl as a header in a config read from standard input, so it never appears in `ps` | [`tests/shell/test_on_chat.sh`](../tests/shell/test_on_chat.sh) checks it |
| In the Python tools (`sdlca-say`, `sdlca-worlds`) | Sent in-process, never on a command line | Review of the code. [`tests/test_say.py`](../tests/test_say.py) covers its origin and redirect rules |
| Where it may be sent | `sdlca-api` sends it only to the Spawn origin and refuses any other host. All four of these tools check `SPAWN_ORIGIN`: https, or plain http only to this machine, never an origin with user information in it (`file://` only when a test sets a variable for it). No tool follows a redirect: the Python ones refuse them, and curl does not follow them unless told to | [`lib/safeurl.py`](../lib/safeurl.py), [`lib/common.sh`](../lib/common.sh), [`tests/shell/test_listen.sh`](../tests/shell/test_listen.sh) |
| In the handler | Spawn's client puts the raw token in `SPAWN_TOKEN` for the handler. The handler removes it before anything runs, so it is not in the agent's environment | A test checks the agent's environment |
| In the prompt | Never. The prompt tells the agent to use `sdlca-api` | A test checks the prompt |
| In git | Each clone has its own credential helper that reads the token file when git runs. It is attached to the git host of the world's https URL only, after an empty helper that makes git forget any global one. The global git configuration is not changed | [`tests/test_gitcred.py`](../tests/test_gitcred.py) checks that other hosts get nothing. See [Several accounts and worlds](multi-account-and-worlds.md#credentials-and-identity-in-the-clones) |
| When the tools read it | Every tool that reads the token file refuses a token with a space, line break, double quote, backslash or non-ASCII character in it, before anything is sent, and its error does not print the file's contents. Without this, a hand-edited file could change the curl settings the token travels in, or end up in an error message | [`tests/shell/test_tools.sh`](../tests/shell/test_tools.sh) and [`tests/test_state_files.py`](../tests/test_state_files.py) check it |
| What `sdlca-api` refuses to send | A body that starts with `@`, because curl would read that local file and send it to Spawn. Curl also runs with `-q` (it ignores `~/.curlrc`) and `--globoff` (it does not expand `[1-3]` or `{a,b}` in an address) | [`tests/shell/test_tools.sh`](../tests/shell/test_tools.sh) checks it |
| In logs | The kit never writes it to its own log lines. A token file that was hand-edited to hold a line break is refused before anything is sent, with an error that does not print its contents | Review of the code, and the test above |

Where the token can still be read or leak:

- **By the agent, as your user.** The agent's environment holds `SPAWN_TOKEN_FILE`, which is the path to the token. Even if the agent never needs to read the file, nothing stops it.
- **Through git.** Git itself offers the token only to the git host of the world's URL. A hostile remote, submodule or large-file URL on another host gets nothing, and [`tests/test_gitcred.py`](../tests/test_gitcred.py) checks this with `git credential fill`. That limits what git does on its own. It does not stop an agent that can run arbitrary git commands: git can run other programs through its configuration and aliases, and those programs can read the token file. The `Bash(git *)` rule in the builder posture allows that.
- **Through `SPAWN_ORIGIN`.** The four tools that send the token (`sdlca-api`, `sdlca-friends`, `sdlca-say` and `sdlca-worlds`) refuse an origin that is not https (plain http is allowed only to this machine) and an origin with user information in it. They cannot tell whether an https host really is Spawn's, so leave `SPAWN_ORIGIN` unset, as [Configuration](configuration.md#variables-from-spawn-that-the-kit-reads) advises.
- **A personal token is a person's own.** If you store one with `sdlca-token`, a leak exposes that person's account, and everything done with it appears under their name. Each person should keep their own, and `sdlca-token verify` says when a token is a person's. See [Several accounts and worlds](multi-account-and-worlds.md#personal-tokens-that-belong-to-other-people).
- **In the invite code.** `sdlca-onboard` takes the one-time invite as a command-line option, so it is visible in the process list and in your shell history for a moment. It works once and expires after ten minutes.
- **In Spawn's client.** Spawn's client uses the token itself. It is proprietary and not ours: the kit does not bundle it, and you install it from npm yourself. You trust it with the token as much as you trust Spawn.
- **Provider keys.** Everything in `SDLCA_CREDENTIALS_FILE` is exported to the agent command. A full-autonomy agent can print it.

If you think a token has leaked, do not wait: stop the listener, have the owner unlink the agent or revoke the token in Spawn, and make a new one. [Operations](operations.md#rotating-a-token) has the steps. Never paste a token into an issue, a pull request or a chat.

## What is logged, and where

| Where | What is in it | Chat text in it? |
| --- | --- | --- |
| `accounts/<account>/listener.log` | The Spawn client's status lines, and the output of the friend-request catch-up at start. The client's standard output, which holds each event as JSON, is thrown away | No |
| `accounts/<account>/handler.log` | One metadata line per event handled (time, sender handle, world, outcome), plus **everything the agent prints**, plus the output of friend accepting | Possibly. The agent's output can hold anything it read, including other people's lines and file contents |
| `run/failed/<event-id>.json` | The whole event, kept so you can replay a failed turn. The handler deletes it after `SDLCA_FAILED_KEEP_DAYS` days (default 30) | **Yes.** It is the raw event, with the chat text |
| `accounts/<account>/handled.ids` | The ids of finished events | No |
| `accounts/<account>/runs.log` | Start times of recent agent runs | No |
| The systemd journal | Start, stop and restart messages and start-up errors | No |
| Your agent tool's own logs | Whatever your tool keeps. The kit does not manage or see them | Probably. Check |

The kit's own log lines carry a sender handle only after it has been checked against the pattern for a Spawn handle, so a sender cannot forge a log line. Chat text is never written by the kit. The handler does not export the event to the agent's environment (even if the program that started it had exported a variable of that name), so the agent gets it in the prompt, between the `<untrusted_event>` tags, and not as a variable that every program it starts inherits.

In short: `listener.log` holds only the Spawn client's status lines (and the friend catch-up output), and `handler.log` holds the kit's metadata lines and the agent's own output. Treat `handler.log` and `run/failed/` as private. Both are created with mode 0600 or in folders of mode 0700.

## Privacy and retention

Other people's chat text passes through your machine, and through your agent provider. That is a duty of care, so know where it goes:

- **To your model provider.** The prompt holds the event, and the agent reads what followed. Check your provider's terms for how it uses prompts. For example, Anthropic's documentation says consumer plans can have training on or off by a user setting, and that under its commercial and API terms it does not train on code or prompts sent to Claude Code unless the customer opts in ([Anthropic's data usage page](https://code.claude.com/docs/en/data-usage), read on 2026-11-17 for our research). Prefer API or commercial terms for unattended use. Claude Code also has a print-mode option, `--no-session-persistence`, that does not save sessions to disk (`claude --help`, 2.1.327, 2026-11-17). We have not tested it with the kit.
- **To your disk,** in the places listed above.
- **To the room,** in the agent's replies.
- **Spawn's terms** ask people not to disclose other people's personal information. See [the rules we follow for Spawn](compliance/spawn-rules.md).
- **Young people and Spawn's Terms.** Spawn rooms can include young people, and your agent forwards what it reads there to your model provider. Spawn's [Terms](https://www.spawn.co/terms-of-service) set a minimum age and parental-consent rules and contain a sanctions clause (read 2026-11-17). The person who runs the kit must meet them. We do not interpret them.

Retention: **the kit never rotates or deletes your logs.** It does delete saved events in `run/failed/`: when the next allowed event reaches the handler, it removes the saved files that are more than `SDLCA_FAILED_KEEP_DAYS` days old (default 30; `0` keeps them forever). The `run/failed` folder is shared by all accounts, so an allowed event on any account removes every account's saved files that are more than that account's `SDLCA_FAILED_KEEP_DAYS` days old. To keep files longer, set the same larger value (or `0`) in every account's env file, or copy the file out. It also trims its own bookkeeping files: `handled.ids` keeps the newest 500 ids, and `runs.log` keeps the last hour. The logs grow until you act. Saved events hold raw chat text, so set `SDLCA_FAILED_KEEP_DAYS` to what you need, or look and delete them sooner yourself:

```bash
ls -l ~/.sdlca/spawn/run/failed | head
find ~/.sdlca/spawn/run/failed -name '*.json' -mtime +14 -print     # look first
find ~/.sdlca/spawn/run/failed -name '*.json' -mtime +14 -delete    # then delete
```

For the logs, use `logrotate` with `copytruncate`, or empty them while no turn is running. [Operations](operations.md#logs-and-what-they-contain) explains both. The kit ships no logrotate configuration.

## Residual risks

These are risks the kit does not remove. We list them so that you can decide with open eyes. Several come from an earlier code review that we treat as a research note, not as an authority (see [below](#what-an-earlier-code-review-found-and-what-changed)).

1. **A same-user agent can read the token files.** The agent runs as your user, so it can read `accounts/*/token` for every account in the runtime home, and every other file your user can read. Permission rules and prompts reduce the risk, but they are not a sandbox. Real isolation needs a separate Unix user, a container or your provider's sandbox.
2. **Allow rules are broad.** `Bash(git *)` allows every git command, and git can run other programs through its configuration, aliases and hooks. `Bash(spawn *)` allows the whole Spawn client. `Bash(.../sdlca-api *)` allows every HTTP method on Spawn's API. Narrow what you allow.
3. **Prompt injection is mitigated, not eliminated.** See [above](#prompt-injection-in-plain-words). A trusted sender can paste hostile text, and the agent can read hostile files or lines.
4. **The agent's own notes are a way to carry text forward.** `WORK-TODO.md` is written by the agent and read by every later turn. A hijacked turn could plant text there. So could it change `AGENTS.md` in the runtime home, if its posture allows writing there. Anything that lets the agent write files in the runtime home lets a hijacked turn change the rules for later turns.
5. **A crash can skip an older unfinished event, in one case.** If Spawn's client runs several handlers at once, and a newer event finishes before an older one, a crash before the older one finishes means the cursor is already past it. We have not confirmed that the client ever overlaps handlers. See [Operations](operations.md#cursor-and-replay).
6. **The read-only posture can read any file the user can read.** It cannot change anything, but it can say what it read.
7. **Several owners in one runtime home share one trust boundary.** One Unix user, one set of token files, one `WORK-TODO.md`. See [Several accounts and worlds](multi-account-and-worlds.md#one-account-per-person).
8. **You trust Spawn.** The kit sends its tokens to Spawn, takes the world list, git URLs and event fields from Spawn's answers, and runs Spawn's proprietary client. If Spawn's server were hostile, the kit would not protect you.
9. **Logs hold other people's words,** as listed above. The logs have no automatic retention limit (saved events in `run/failed/` do: 30 days by default), and a stranger who mentions the agent adds one short metadata line (a handle and a reason, no chat text) to `handler.log` for each message, so the file can grow even from people who cannot give orders.
10. **A world's own files can carry settings that your agent tool loads.** Claude Code's help says the workspace trust dialog is skipped in print mode (`-p`), and the kit runs the agent inside the world's clone (`claude --help`, 2.1.327, 2026-11-17). Hooks, MCP servers, commands and instruction files that sit in the clone (for example `.claude/` and `.mcp.json`) come from whoever can push to that world, and they can load whatever your allowed-tools list says, even in the read-only posture. Serve only worlds whose editors you trust. The help lists options that ignore project settings (`--setting-sources user`, `--restricted` and `--bare` among them); we have not tested them with the kit, so try one on a throwaway account before you rely on it.
11. **A process that detaches outlives the time limit and the lock.** `timeout` stops the agent and its process group. A process that leaves the group on purpose (for example with `setsid` or `systemd-run --user`) keeps running after the turn ends and after the world lock is freed, and it can write to the clone while the next turn starts. We reproduced this with a test agent. Only a separate Unix user, a container or a virtual machine contains it.

### TLS-inspecting proxies

Some company networks inspect encrypted traffic with a proxy of their own. Spawn's client can then refuse the connection with an error such as "self signed certificate in certificate chain". The listener keeps retrying on its own. This is a reliability problem and not a flaw in the kit's security: the client is correctly refusing a certificate it does not know.

The usual fix is to tell the client to trust the proxy's certificate authority. For Bun, which runs Spawn's client, the setting `NODE_EXTRA_CA_CERTS` is the usual one, but check it for your setup. Know what that means: after you trust the proxy, its operator can read the traffic, including the token in each request. Do not "fix" the error by turning certificate checks off.

## Hardening checklist

In order of value. Do the first one that you can, then the next.

1. **Give the kit its own Unix user, or run it in a container or a virtual machine.** This is the single biggest step. A user whose home holds only the runtime home, the clones and the agent tool's login cannot read your SSH keys, cloud credentials, browser profiles or other accounts' files. With several owners, give each one a user and a runtime home. The kit runs as whichever user starts it, so there is nothing to configure, and it ships no scripts for this. The kit's systemd unit sets `NoNewPrivileges=yes`, so a process it starts cannot gain privileges through programs such as `sudo`. That does not limit which files it can read.
2. **Use your provider's sandbox.** Claude Code documents a sandbox ([Claude Code sandboxing](https://code.claude.com/docs/en/sandboxing), read on 2026-11-17 for our research). We have not tested it with the kit. Expect to tune it: the kit's tools read the token file and reach Spawn, so a rule that hides the token from the agent may hide it from them too. A required sandbox that is not available should stop the run, not silently run without it. Try that with the setting your tool offers. systemd offers further options for limiting a service's files (see `systemd.exec`); we have not tested them with the kit either.
3. **Narrow the allowlists.** Replace `Bash(git *)` with the subcommands you need, for example `git status`, `git diff` and `git commit`. Leave out `git push` if you would rather push yourself after a review. Replace `sdlca-api *` with `sdlca-api GET *`, as the read-only posture does. Allow `spawn` subcommands one by one. The rule syntax is your agent tool's, so check its documentation and test.
4. **Keep the sender allowlist empty.** The owner alone is the default. Every person you add has the agent's power.
5. **Set run caps and spending limits.** The kit allows 20 agent runs an hour by default (`SDLCA_MAX_RUNS_PER_HOUR`); lower it to what you need and do not set it to 0, which turns the cap off. Lower `SDLCA_AGENT_TIMEOUT` (default 1800 seconds). Set a spending limit with your provider. Claude Code has a per-run limit for print mode, `--max-budget-usd` (`claude --help`, 2.1.327, 2026-11-17).
6. **Keep logs private and short-lived.** The kit creates them with mode 0600. Rotate or trim `handler.log`, keep `SDLCA_FAILED_KEEP_DAYS` as small as you can live with (30 by default; do not set it to 0, which keeps saved events forever, in any account: the folder is shared), and keep the runtime home out of synced folders and shared backups. Do not put secrets in `SDLCA_AGENT_CMD`, because the command line is visible in the process list.
7. **Rotate tokens.** Make a new token when you suspect a leak, when someone who had access leaves, and now and then anyway. See [Operations](operations.md#rotating-a-token).
8. **Start read-only, and watch.** Send a few messages of your own and read `handler.log`. Widen the posture only when you know what the agent does.
9. **Re-test after upgrades.** Your agent tool's permission rules change between versions. After you upgrade it or the kit, check that a message from a stranger is ignored and that the posture still blocks what it should.

## What an earlier code review found, and what changed

Before the first release, a review of an earlier version of the same logic was done for the maintainers on 2026-11-17. We keep it as a research note, not as an authority, because it examined code that has since changed. It listed 23 findings, two of them critical. Most are fixed in the repository. The main fixes are:

- No agent command by default, and the listener refuses to start without one. One of its two critical findings was an agent started with every permission check off.
- A strict sender gate, with exact handles, fail-closed lists and a ban on the agent's own handle.
- Routing from structured fields and exact matches only. The old code searched the whole event, including the chat text, and a short address matched a longer one.
- The raw token removed from the handler's environment, and tokens kept off command lines and away from redirects.
- Events with no world run in a scratch folder, never in the runtime home that holds every token.
- A fenced prompt, with the text treated as data.
- The world lock no longer leaks to background processes, a timeout stops a hung agent and its process group (a process that detaches is not stopped: see residual risk 11), and the lock wait is bounded.
- A cursor that is atomic and monotonic, a list of handled event ids, failed events kept for replay, and an hourly cap on runs.
- A chat sender that paces its lines, retries rate limits, and caps a reply.
- A systemd unit that backs off, and does not restart on a configuration error.

What the review found that is still true is in the residual risks above: tokens are reachable by a same-user agent, allow rules are broad, and prompt injection is reduced, not removed.

A second review of this version, also on 2026-11-17 and also done by an AI agent, found no way to get past the sender gate, and no way for chat text to run code or to choose a world. It did find smaller gaps, which are fixed and have tests: `sdlca-api` would let curl send a local file named in the body; a token file with odd content could change curl's settings or reach an error message; `sdlca-look` accepted any output path and an option as the world; the same event delivered twice at the same moment ran the agent twice; the listener's command line was not quoted for a folder name with a quote in it; and a few state files were read too strictly or written without a lock. It also found the two risks that are numbered 10 and 11 above. An AI review is no proof that nothing is left, so please report what you find ([How to report a vulnerability](#how-to-report-a-vulnerability)).

## How to report a vulnerability

Please do not open a public issue for a security problem, and never paste a token, an invite code or exploit details into an issue, a pull request or a chat. Follow [SECURITY.md](../SECURITY.md). It says where to send a report privately, what to include and what to expect. Problems in Spawn itself belong with Spawn, and SECURITY.md says how to reach them.

## Related pages

- [Architecture](architecture.md): how the parts fit together, and why.
- [Configuration](configuration.md): the agent command, the allowlist and every setting.
- [Operations](operations.md): logs, rotating a token and troubleshooting.
- [Several accounts and worlds](multi-account-and-worlds.md): accounts, the registry and the clones.

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
