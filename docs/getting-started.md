# Getting started

This page is for someone who has never seen the SDLCA agent kit and has a Linux machine. Follow it and an AI agent of your choice will answer you in Spawn chat, in about 15 minutes if Bun, git and your agent tool are already installed and signed in and you are comfortable in a terminal. What this page says about the kit's own behavior was checked against the kit's code on 2026-11-17, and what it says about the git address, `sdlca-look` and the Claude Code option on 2026-11-18. Most of what it says about Spawn and about other tools names its source next to the statement.

The kit is an unofficial community project. It is not made, reviewed or supported by Spawn.

## What you are setting up

For each person an AI agent works for (called the *owner*), you create one agent account on Spawn and run one small background program, the *listener*, that watches that account's Spawn inbox. Here is what happens when the owner talks to the agent:

1. The owner mentions the agent in a world's chat, or sends it a direct message, in Spawn.
2. Spawn puts an event in the agent account's inbox. The listener receives it.
3. The kit checks who sent it. Only the owner, and people you add to an allowlist, can start work. Everyone else is ignored without a reply.
4. The kit finds the world the message came from and runs your agent command once, inside that world's git clone, with a prompt on standard input.
5. The agent answers by running `sdlca-say`, which splits long replies into Spawn's 200-character chat lines.

The five steps below cover install, account, agent command, listener and a first message.

## Read this first: what the agent can do

- The agent command you choose runs on your machine, as your user. The kit does not put it in a sandbox.
- The sender check stops strangers. It does not stop hostile text that a trusted sender pastes, or hostile files inside a world. The prompt tells the agent to treat chat text as untrusted, but that is advice to a model, not a barrier.
- "Read-only" in this guide means the agent cannot edit files or run other commands (except the kit's `sdlca-say` and `sdlca-api GET`). It does not mean it can only see the world. With the shipped Claude Code example it can read any file your user can read, including your tokens, and it can post what it read in the room.
- Start with the read-only choice. Widen it only when you have seen how the agent behaves. Consider a separate Linux user or a virtual machine for the listener.

The full threat model is in [Security model](security-model.md). Read it before you pick anything beyond read-only.

## Before you start: Spawn's terms and you

- You need your own Spawn account, and Spawn's Terms of Service apply to you, not to the kit. The kit gives no protection against any of what follows.
- Spawn's Terms say that "you" includes "any person acting as your agent or with your permission". Whether an AI agent counts as such a person is not settled by the Terms; in our reading (not legal advice), you answer for what your agent does under your account. The Terms also contain an indemnity clause, let Spawn suspend an account at any time, and let Spawn change the Terms with immediate effect ([Terms of Service](https://www.spawn.co/terms-of-service), read 2026-11-17, sections 10, 11 and 26).
- Spawn's Terms set a minimum age and parental-consent rules and contain a sanctions clause (read 2026-11-17). The person who runs the kit must meet them. We do not interpret them.
- Spawn rooms can include young people, and your agent forwards what it reads there to your model provider.

[The Spawn rules we follow](compliance/spawn-rules.md) lists the rest.

## Prerequisites

You need a Linux machine, a Spawn account for the owner, and an agent command-line tool that can run without a person at the keyboard.

| Need | Why the kit needs it | Tested with |
| --- | --- | --- |
| bash 4.4 or newer | Every kit script | GNU bash 5.3 |
| Python 3 | Routing, reply splitting, cursor, world sync (the installer only checks that `python3` exists; we aim for 3.9 or newer and have tested 3.12 and 3.14) | Python 3.14 locally, 3.12 in CI |
| git 2.29 or newer | World clones, and the update of a clone before each turn | git 2.53 |
| curl | Authenticated calls to Spawn | curl 8.18 |
| `flock` (util-linux) and `timeout` (coreutils) | One turn at a time per world, and a time limit per turn | util-linux 2.41; `timeout` from Ubuntu 26.04 |
| Bun | Runs Spawn's client | Bun 1.4 |
| Spawn's client, the `spawn` command | Reads the inbox, logs in, joins worlds | the latest version npm serves (the kit does not pin one) |
| systemd user services (optional) | Keeps the listener running | systemd 259 with lingering enabled |
| An agent command-line tool that reads a prompt on standard input | Does the work | Claude Code 2.1 |

The last column says what the maintainers used on 2026-11-17. It is not a promise that older versions fail or that newer ones work. Under WSL2 (Windows Subsystem for Linux), turn systemd on for your distribution first (see Microsoft's WSL documentation); that is how the maintainers tested.

Spawn's client is Spawn's own proprietary software. The npm registry lists its license as UNLICENSED ([package page](https://www.npmjs.com/package/@spawnco/client), checked 2026-11-17). You install it yourself from npm. This repository does not contain or redistribute it, and your use of it is covered by Spawn's terms.

You also need a Spawn account for the owner. That is a person's normal account, and the owner creates the invite in step 2. Once the tools in the table are installed and signed in, allow about five minutes for step 1, three for step 2 and five to seven for the rest.

## Step 1: install the kit

Install Bun if you do not have it (see [bun.sh](https://bun.sh)), then install Spawn's client, then get the kit:

```bash
bun add -g @spawnco/client
git clone https://github.com/kdtix-open/sdlca-for-spawn.git ~/repos/kdtix-open/sdlca-for-spawn
cd ~/repos/kdtix-open/sdlca-for-spawn
scripts/install.sh
```

The installer is safe to run again. It does four things:

1. Checks that each tool exists (not its version) and prints `ok`, `MISSING` or `optional`. `bash`, `python3`, `git`, `curl`, `flock`, `bun` and `spawn` are required, and it stops if one is missing. `systemctl` and `claude` are optional. It does not look for `timeout`, which the kit also needs.
2. Creates the *runtime home* (`~/.sdlca/spawn` by default, mode 0700) and copies in starter files, but only the ones that do not exist yet.
3. Runs `bun install` in the kit folder to fetch `playwright-core`, which only the screenshot tool uses. This step needs network access.
4. If `systemctl` exists, writes the systemd unit to `~/.config/systemd/user/sdlca-listener@.service` and runs `systemctl --user daemon-reload`.

The unit stores the kit folder's absolute path, so where systemd is present the installer refuses a path that has a space or a character that is special to systemd or `sed`. Letters, digits and `. _ / + @ : -` are fine. If you move the folder, run `scripts/install.sh` again.

Optional check that the kit works on your machine (no network, no tokens):

```bash
bash tests/run.sh
```

It ends with `all tests passed`.

## Step 2: create the agent account

### Get an invite from the owner

The agent account is created with a one-time code from the person it will work for. Spawn calls this an invite. It starts with `sbk_`, works once and expires after ten minutes ([Spawn's API description](https://www.spawn.co/openapi.json), retrieved 2026-11-17). The owner copies it from their own Spawn account. Spawn's documentation names the "your agents" list, the settings page for tokens and a world's code page as places that give the prompt. Menus change, so follow Spawn's current on-screen steps.

Two things to know before you ask:

- **Pick the world first.** If the owner copies the prompt from a world's code page, Spawn adds the new agent as an editor of that world in the same step ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17). That is the easiest way to give the agent a world to work in.
- **The invite is consent.** Spawn's guide says linking lasts until the owner unlinks the agent, and that a linked agent runs under the owner's allowance, including features that cost the owner ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17). The kit's own commands do not use those features, but an agent you run might. The owner can unlink the agent in Spawn at any time.

Choose a username for the agent: lowercase letters, digits and underscores, and not taken by anyone else on Spawn. A display name that makes clear it is an AI agent helps other people in shared worlds.

### Run onboarding

Within ten minutes of the owner copying the code, run this from the kit folder. Here the owner is `alice` and the agent will be `alice_helper`. Replace the placeholder with the code, and keep the single quotes:

```bash
bin/sdlca-onboard --owner alice --invite 'sbk_PASTE_THE_CODE_HERE' --username alice_helper
```

| Option | Meaning |
| --- | --- |
| `--owner` | The owner's Spawn username. Also the account's folder name and the name of its systemd service. Lowercase letters, digits and underscores only. |
| `--invite` | The one-time code. |
| `--username` | The agent's own Spawn username, same character rules. |
| `--display-name` | Optional. The name Spawn shows for the agent. Defaults to the username. |
| `--token-file` | Optional. Where to keep the token. Defaults to `accounts/<owner>/token` in the runtime home. |

The code shows up in your shell history and in the process list while the command runs. It works once and expires, so the exposure is small, but do not paste it anywhere else.

When it finishes you will see a few identifying lines from the login (such as the username), `wrote .../accounts/alice/env`, lines such as `new world @alice/game-1 -> ...` and `cloned` for each world the agent can reach, and a short "Next" list. A brand-new agent that has no world yet prints no world lines.

### What onboarding does, and what it leaves alone

It does these things:

- Creates `accounts/alice/` and `run/` in the runtime home, and sets the runtime home, `accounts/`, `accounts/alice/` and `run/` to mode 0700.
- Runs Spawn's `spawn login` with the invite. The token goes into the account's token file (mode 0600). The kit never prints it.
- Writes `accounts/alice/env` if it does not exist yet. It never overwrites an existing one.
- Asks Spawn to set the agent's display name. If that fails it only prints a warning.
- Runs `sdlca-worlds --apply`, which clones every world the agent can reach (into `~/repos/<world owner>/<world>` by default) and records them in `worlds.json`, together with the git address that Spawn lists for each (the kit's update before a turn fetches from that address only).

It does not touch these things:

- **Your global git configuration.** `spawn login` adds a git credential helper for Spawn's git host to your global config. Onboarding saves what was there before and puts it back when it finishes, even if login fails. Each world clone gets its own helper, bound to that account's token file and used for Spawn's git host only. If something stops the script abruptly, check with `git config --global --get-all credential.https://git.spawn.co.helper`.
- **systemd.** It does not start the listener. You do that in step 4.
- **The agent command.** Nothing runs until you choose one in step 3.
- **Anyone else's account.** It sends no chat message and no friend request.

### Check that the token works (optional)

```bash
bin/sdlca-as alice bin/sdlca-api GET /api/agent/v1/me
```

`sdlca-as` runs a command with that account's settings and token loaded. This prints JSON about the agent account, including the worlds it can reach. An error ending in `401` means Spawn refused the token.

### Keep a token you made yourself (optional)

`sdlca-onboard` is how you get an agent account, and the rest of this guide uses it. The kit also has `bin/sdlca-token`, which stores a Spawn token that a person made by hand (a personal token from their own Spawn settings) where the kit's tools and your own scripts can find it. A personal token signs in as that person, not as an agent: what it does appears under their name. Spawn's settings page describes personal tokens as being for your own scripts and says agents make their own (seen 2026-11-17).

An account name is one word (`alice`) or `group/name` (`sdlca-for-spawn/alice`), which keeps several tokens in one group folder. A grouped account cannot be a systemd listener instance, because an instance name cannot contain a slash. Use one-word names for accounts that need a listener.

```bash
bin/sdlca-token add alice-scripts --owner alice   # asks for the token without showing it
bin/sdlca-token verify alice-scripts              # asks Spawn whose token it is
```

Each person should make their own token and keep it. [Spawn's terms](https://www.spawn.co/terms-of-service) (checked 2026-11-17) restrict letting other people use your account, and the kit never asks anyone to send a token to someone else. For another person's account, use the invite flow above. [Configuration](configuration.md#grouped-accounts-and-sdlca-token) describes all five `sdlca-token` commands.

## Step 3: choose how the agent runs

The listener refuses to start until you set `SDLCA_AGENT_CMD` in the account's env file. This is deliberate: the kit has no default agent, so nothing can run by accident. Open the file:

```bash
${EDITOR:-nano} ~/.sdlca/spawn/accounts/alice/env
```

The file already holds `OWNER`, `SPAWN_USERNAME` and `SPAWN_TOKEN_FILE`, followed by commented examples. Add one line that sets `SDLCA_AGENT_CMD`. The command receives the prompt on standard input and runs inside the world's clone. Keep the whole command inside single quotes. The kit reads this file as shell, and the single quotes make sure `$SDLCA_CODE_DIR` is expanded when the command runs, not when the file is read.

Pick the narrowest posture that does the job. These four come from [`templates/account.env.example`](../templates/account.env.example); the Claude Code flags were checked against `claude --help` for version 2.1.327 on 2026-11-17 (`--setting-sources` again on 2026-11-18). Every example passes `--setting-sources user`, which keeps a world's own `.claude/settings.json` and `.mcp.json` from running code on your machine (see [A world's own settings can run code](security-model.md#a-worlds-own-settings-can-run-code)). Keep it if you change the command.

**Read-only helper.** It can read files and answer in chat. It cannot edit files or run other commands. Start here.

```bash
SDLCA_AGENT_CMD='claude -p --setting-sources user --allowedTools "Read" "Glob" "Grep" "Bash($SDLCA_CODE_DIR/bin/sdlca-say *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-api GET *)"'
```

**Read-only with sight.** The read-only helper, plus the kit's screenshot tool, so the agent can look at a world this account serves. While a look runs (it waits for the world to load, which can take a minute or two with a software renderer, plus the join), the agent's body stands in the world and every player in the room can see it, and your model provider reads the picture. Read [what allowing `sdlca-look` means](security-model.md#what-allowing-sdlca-look-means) first, and run `bin/sdlca-look --check alice` to see whether the machine is ready for it (it joins nothing and uses no network; see [Operations](operations.md#a-look-does-not-work)).

```bash
SDLCA_AGENT_CMD='claude -p --setting-sources user --allowedTools "Read" "Glob" "Grep" "Bash($SDLCA_CODE_DIR/bin/sdlca-say *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-api GET *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-look *)"'
```

**Builder with a tool allowlist.** It can edit files and run only the commands listed. Adjust the list to your needs.

```bash
SDLCA_AGENT_CMD='claude -p --setting-sources user --permission-mode acceptEdits --allowedTools "Bash(git *)" "Bash(spawn *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-say *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-api *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-look *)"'
```

Be clear about what that allowlist permits. `git *` includes pushing to the world, which goes live in every open room. `sdlca-api *` allows every HTTP method on Spawn's API with the agent's token, so it can change or delete things the account can reach. `spawn *` is Spawn's whole client.

**Full autonomy.** The agent can run any command as your user. It is not part of this first setup. If you later decide you need it, read [about full autonomy](security-model.md#about-full-autonomy) first, then see [Configuration](configuration.md#the-postures).

The maintainers checked the read-only and builder postures against Claude Code 2.1. Read-only with sight is the read-only one plus one more rule, and had not been tested with a real agent run when this page was written. Permission rules differ between versions, so test the posture you choose (see the next section). Other agent tools work too if they read a prompt on standard input. See [Configuration](configuration.md#other-agent-tools-unverified-examples).

Systemd does not read your shell profile, so API keys exported there are invisible to the listener. If your agent needs a key, put it in a file and point `SDLCA_CREDENTIALS_FILE` at it (see [Configuration](configuration.md#provider-keys)).

### Test the agent command by hand

This runs your command once with a trivial prompt. It uses your provider account, so it may cost a little:

```bash
bin/sdlca-as alice bash -c 'printf "Reply with the single word ready.\n" | bash -c "$SDLCA_AGENT_CMD"'
```

If you see an answer, the tool is installed and signed in. If you see `command not found`, the tool is not on your `PATH`. The row for `status 127` in [Operations: troubleshooting](operations.md#troubleshooting) explains the fix.

## Step 4: start the listener

```bash
loginctl enable-linger "$USER"
systemctl --user enable --now sdlca-listener@alice.service
systemctl --user status sdlca-listener@alice.service
```

The first command keeps your user services running after you log out and starts them at boot (it may ask for your password). The second starts the listener now and at every login. Look for `Active: active (running)` in the third.

Without systemd, you can run `bin/sdlca-listen alice` in a terminal while you test (Ctrl-C stops it). For a lasting setup under another supervisor, see [Operations](operations.md#running-without-systemd).

## Step 5: send a first message

1. Open a world in Spawn where the agent has been added, such as the one named in the invite.
2. In that world's chat, mention the agent. Spawn writes agent accounts with two at signs ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17), so for `alice_helper` type `@@alice_helper` followed by a simple request, for example: `@@alice_helper what files are at the top level of this world?`
3. Send it from the owner's own Spawn account (`alice`). A message from anyone else is ignored on purpose.

You can also send the agent a direct message. In the maintainers' testing, a direct message worked once the owner and the agent were friends, so if Spawn does not let you start one, send the agent a friend request from the owner's account. The listener accepts friend requests from the owner automatically, and from nobody else.

Replies are normal chat lines from the agent, so everyone in the room can read them. By default the agent starts a reply by naming the world it acted on and ends it with a line beginning "Handler notes:". Both come from the default prompt, which you can change (see [Configuration](configuration.md#the-prompt-override)).

## How to tell it worked

Watch the handler log while you send the message:

```bash
tail -f ~/.sdlca/spawn/accounts/alice/handler.log
```

Within a few seconds you should see a line like this:

```text
2026-11-17T18:04:11Z event sender=@alice world=@alice/game-1
```

Reading it from left to right:

- The time is UTC.
- `event` means an allowed message started a turn.
- `sender=` is the sender's handle as Spawn writes it: `@name` for a person, `@@name` for an agent.
- `world=` is the world whose clone the agent works in. A dash means the kit did not identify a world, as with most direct messages. The agent then starts in a scratch folder (`run/scratch/alice` in the runtime home) and the message must name the world.

When the message came from a world, a second line follows it before the agent starts, for example `WORLD @alice/game-1 clone current/ok: already at 8c0d4e1`. It says whether the kit brought the world's clone up to date for this turn (by fast-forward only, never a merge), and the agent is told the same. If it says `skipped` or `failed`, the turn still ran and the agent was told that its clone may lag the latest push: see [The clone was not brought up to date](operations.md#the-clone-was-not-brought-up-to-date). Whatever the agent prints appears after those lines. There is no "done" line: a turn that ends normally logs nothing more. A turn that fails adds a line such as `WARN agent exited with status 127; event kept in run/failed`. The reply itself appears in Spawn chat, and files named `cursor` and `handled.ids` appear in `~/.sdlca/spawn/accounts/alice/`. The log holds no chat text from the kit itself, but the agent's own output can. Keep the file private; it is created with mode 0600.

A reply can take as long as the model needs. After 30 minutes the kit stops the turn by default.

## If it did not work

| What you see | Where to look |
| --- | --- |
| `systemctl --user status` shows `failed` with `status=78` | The agent command is not set. Go back to step 3. |
| The service keeps restarting | `journalctl --user -u sdlca-listener@alice.service` names the problem. |
| No new line in `handler.log` after your message | [Nothing happens when I message](operations.md#nothing-happens-when-i-message) |
| `DENIED` lines | [DENIED lines](operations.md#denied-lines) |
| An `event` line but no reply in chat | [The agent never answers](operations.md#the-agent-never-answers) |
| `WARN ... event kept in run/failed` | The turn failed. [Replay a failed turn](operations.md#replay-a-failed-turn) after you fix the cause, and do it soon: when the next allowed event arrives, the kit deletes saved events that are more than 30 days old (`SDLCA_FAILED_KEEP_DAYS`; `0` keeps them forever). |
| `self signed certificate in certificate chain` in `listener.log` | [Self signed certificate in certificate chain](operations.md#self-signed-certificate-in-certificate-chain) |

The full table, with a fix for each symptom, is in [Operations: troubleshooting](operations.md#troubleshooting). If you are still stuck, see [SUPPORT.md](../SUPPORT.md). Never paste tokens or invite codes, or any other session, join or login credential, including values printed by `spawn client join`, into an issue or a chat.

## Remove everything

This undoes a trial setup with one account, using the default locations. For several accounts, backups and what stays behind, see [Operations: uninstalling](operations.md#uninstalling).

```bash
# 1. Stop the listener and stop it starting again
systemctl --user disable --now sdlca-listener@alice.service
# 2. Delete the account's token, settings, cursor and logs
rm -rf ~/.sdlca/spawn/accounts/alice
# 3. List the clones the kit made, check each for unpushed work, then delete them
grep clone_path ~/.sdlca/spawn/worlds.json
git -C ~/repos/alice/game-1 status
rm -rf ~/repos/alice/game-1
# 4. Delete the rest of the runtime home and the service file
rm -rf ~/.sdlca/spawn
rm -f ~/.config/systemd/user/sdlca-listener@.service
systemctl --user daemon-reload
# 5. Delete the kit itself
rm -rf ~/repos/kdtix-open/sdlca-for-spawn
```

Notes:

- Deleting a clone also deletes any commits you have not pushed. Spawn's git remote keeps only what was pushed. Use the paths that `grep` printed, not a guess: a folder such as `~/repos/alice` may hold other work of yours.
- Your global git configuration needs no clean-up, because the kit never leaves anything in it.
- Spawn's client is yours, not the kit's. Remove it the way you installed it, for example `bun remove -g @spawnco/client`. It also keeps its own files, such as `~/.spawn` and `~/.cache/spawnco-client`, which belong to Spawn's client and not to this kit.
- Removing the kit does not delete the agent account on Spawn. To end the link, the owner unlinks the agent in Spawn. To make the token stop working, see [Operations: removing an account](operations.md#removing-an-account).

## Where to go next

- [Configuration](configuration.md): every setting, file and example command.
- [Operations](operations.md): running it for weeks, logs, upgrades, troubleshooting.
- [Security model](security-model.md): who can trigger work and what the agent can do.
- [Architecture](architecture.md): how the pieces fit together.
- [Rules we follow for Spawn](compliance/spawn-rules.md): the Spawn terms this kit respects.
- [Giving an agent a body](giving-an-agent-a-body.md): make a body from a picture, then keep it (optional).
- [FAQ](faq.md): short answers.

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
