# Configuration

This page is for someone who runs the SDLCA agent kit and wants the complete reference: every environment variable, every file in the runtime home, and every setting you can change. It was checked against the kit's code on 2026-11-17. If you are new, start with [Getting started](getting-started.md).

## How configuration works

The kit has no central configuration file. Settings live in three places:

1. **Your environment.** Variables in your shell, or in the systemd service, that the commands read.
2. **The account env file.** One file per account at `$SDLCA_SPAWN_HOME/accounts/<account>/env`. The kit reads it as shell, so it can set any variable. An account name is one word, or `group/name` (see [Grouped accounts and sdlca-token](#grouped-accounts-and-sdlca-token)).
3. **Files in the runtime home.** The allowlist, the world registry, the optional prompt override and the agent's notes.

The *runtime home* is `$SDLCA_SPAWN_HOME`, which is `~/.sdlca/spawn` unless you set it. The kit creates it with mode 0700.

### When a change takes effect

For every event, Spawn's client (which the listener runs) starts a fresh `sdlca-on-chat` process. That process reads most settings again each time.

| You change | It takes effect |
| --- | --- |
| `allowlist.json` | On the next event |
| `worlds.json` | On the next event |
| `handler-prompt.md` | On the next event |
| `AGENTS.md`, `WORK-TODO.md` | On the next turn, when the agent reads them |
| The account env file, for anything the handler uses (`SDLCA_AGENT_CMD`, `SDLCA_AGENT_TIMEOUT`, `SDLCA_LOCK_WAIT`, `SDLCA_MAX_RUNS_PER_HOUR`, `SDLCA_FAILED_KEEP_DAYS`, `SDLCA_CREDENTIALS_FILE`, `SDLCA_SAY_PAUSE`, `SDLCA_SAY_MAX_LINES`, extra variables) | On the next event |
| The account env file, for anything the listener process itself uses (`SPAWN_TOKEN_FILE`, `SPAWN_ORIGIN`, the start-up check of `SDLCA_AGENT_CMD`) | After you restart the listener |
| `SDLCA_SPAWN_HOME`, the systemd unit or a drop-in | After a restart (the unit also needs `daemon-reload`) |

When in doubt, restart the listener while no turn is running. [Operations](operations.md#restart-and-upgrade) shows how to check.

## Environment variables

### Variables the kit defines

| Variable | Set it in | Default | Read by | What it does |
| --- | --- | --- | --- | --- |
| `SDLCA_SPAWN_HOME` | Your shell or the service environment. Not the account env, because the kit needs it to find that file. | `~/.sdlca/spawn` | Every command | The runtime home: accounts, tokens, logs and state. For a custom location in the service, see [Operations](operations.md#systemd-unit-settings). |
| `SDLCA_CODE_DIR` | Automatic. Do not set it. | The folder the kit was cloned into | Shell scripts, the prompt, your agent command | Where the kit's code lives. You can use it inside `SDLCA_AGENT_CMD`. |
| `SDLCA_AGENT_CMD` | Account env | None. Required. | `sdlca-listen`, `sdlca-on-chat` | The command that performs one agent turn. The prompt arrives on stdin. Without it the listener exits with status 78 and no agent runs. |
| `SDLCA_AGENT_TIMEOUT` | Account env | `1800` | `sdlca-on-chat` | Time limit for one turn, passed straight to `timeout`, which sends SIGTERM at the limit and SIGKILL 10 seconds later if the command is still running. Seconds, or a duration such as `30m`. `0` turns the limit off, which is not recommended. A value `timeout` cannot read makes every turn fail with status 125. |
| `SDLCA_LOCK_WAIT` | Account env | `3600` | `sdlca-on-chat` | Seconds a turn waits for its world's lock. After that the agent does not run and the event is kept in `run/failed`. |
| `SDLCA_MAX_RUNS_PER_HOUR` | Account env | `20` | `sdlca-on-chat` | The most agent turns the account may start in one hour (every turn can cost money). Past the cap the agent does not run and the event is kept in `run/failed`. `0` turns the cap off (so does a negative number). It must be a whole number: anything else logs `ERROR the run cap could not be checked` and no agent runs. |
| `SDLCA_FAILED_KEEP_DAYS` | Account env | `30` | `sdlca-on-chat` | How many days a saved event stays in `run/failed`. When the next allowed event reaches the handler, it deletes the saved `.json` files that are more than this many days old (age counted in whole days). The `run/failed` folder is shared by all accounts, so an allowed event on any account removes every account's saved files that are more than that account's `SDLCA_FAILED_KEEP_DAYS` days old. To keep files longer, set the same larger value (or `0`) in every account's env file, or copy the file out. `0` keeps them forever, and so does a value that is not a whole number above 0. Saved events hold raw chat text, so keep the number small. See [Replay a failed turn](operations.md#replay-a-failed-turn). |
| `SDLCA_CREDENTIALS_FILE` | Account env | Unset | `sdlca-on-chat` | A file the kit reads as shell around the agent command only, so provider keys reach the agent without a second copy. See [Provider keys](#provider-keys). |
| `SDLCA_REPOS` | Your shell when you run `sdlca-onboard` or `sdlca-worlds`, or the account env | `~/repos` | `sdlca-worlds` | Where world clones live: `$SDLCA_REPOS/<world owner>/<world>`. Existing clones keep the path recorded in `worlds.json`. |
| `SDLCA_GIT_NAME` | Same as `SDLCA_REPOS` | `sdlca-agent` | `sdlca-worlds` | The `user.name` set inside each clone the kit makes. |
| `SDLCA_GIT_EMAIL` | Same as `SDLCA_REPOS` | `sdlca-agent@users.noreply.invalid` | `sdlca-worlds` | The `user.email` set inside each clone the kit makes. |
| `SDLCA_SAY_PAUSE` | Account env | `2.2` | `sdlca-say` | Seconds to wait between the lines of a long reply (Spawn allows about 5 chat lines in 10 seconds, per [Spawn's API description](https://www.spawn.co/openapi.json), read 2026-11-17). Raise it if you still see rate-limit errors. |
| `SDLCA_SAY_MAX_LINES` | Account env | `8` | `sdlca-say` | The most chat lines one reply sends (at least 2: a smaller number counts as 2, so there is always one line of text before the note). A longer reply is cut and its last line says how many lines were not sent. |
| `SDLCA_HTTP_TIMEOUT` | Account env | `30` | Commands that use the kit's curl helper: `sdlca-friends` and `sdlca-api` (and so the display-name call in `sdlca-onboard` and `sdlca-token verify`) | Seconds before curl gives up. `sdlca-say` and `sdlca-worlds` use a fixed 30 seconds for each request. |
| `OWNER` | Account env, written by `sdlca-onboard` and `sdlca-token` | None. Required. | Routing, prompt, friend accepting | The Spawn user who may command this account. `sdlca-onboard` also names the account's folder after it. |
| `SPAWN_USERNAME` | Account env, written by `sdlca-onboard` and `sdlca-token` | None. Required. | Routing, prompt, `sdlca-worlds` | The Spawn username the token signs in as. The kit ignores messages from `@@<this name>` (the agent form of the handle), which prevents reply loops. It is also the username in each clone's credential helper. |

`OWNER` and `SPAWN_USERNAME` are the kit's variables even though the second one starts with `SPAWN_`.

### Variables from Spawn that the kit reads

| Variable | Set it in | Default | What it does |
| --- | --- | --- | --- |
| `SPAWN_TOKEN_FILE` | Account env, written by `sdlca-onboard` | Required | Path of the account's token file. The kit reads the token from it. Spawn's client also honors it ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17), so `spawn` commands the agent runs use this account's token. |
| `SPAWN_ORIGIN` | Leave it unset | `https://www.spawn.co` | The Spawn server to talk to. The kit sends the token only to this origin, and refuses one that is not https (plain http is accepted only for localhost) or that contains user information such as `https://www.spawn.co@elsewhere.example`. Spawn's client fetches its own code from the origin it is given and runs it (see the package's launcher script, listed on the [npm page](https://www.npmjs.com/package/@spawnco/client), checked 2026-11-17), so point this at a server you control only for testing. |
| `SPAWN_EVENT` | Set by Spawn's client for each event | None | The event as JSON. `sdlca-on-chat` reads it, or reads standard input if it is not set, and then removes it from the environment, so the agent does not inherit it. |
| `SPAWN_TOKEN` | Do not set it | None | Spawn's guide says its tools read the token from this variable first and from the token file only if it is not set ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17). Setting it for the listener would make every account use one token. Spawn's client also passes the raw token to the event hook in this variable, so `sdlca-on-chat` removes it before anything else runs and the agent never inherits it. |

### What the agent inherits

The agent command runs as a child of `sdlca-on-chat`. It inherits everything below, and it runs as your user, so it can also read your token files.

| Variable | Value |
| --- | --- |
| `ACCOUNT`, `ACC` | The account's name (`alice`, or `group/name`), and the full path of its folder |
| `OWNER`, `SPAWN_USERNAME`, `SPAWN_TOKEN_FILE` | From the account env |
| `SDLCA_SPAWN_HOME`, `SDLCA_CODE_DIR` | As above |
| `PATH` | The `PATH` of the process that started the listener (under systemd, its own short one), with `~/.bun/bin` and `~/.local/bin` added in front when those folders exist |
| Everything in the account env | The kit exports every assignment in that file |
| Everything in `SDLCA_CREDENTIALS_FILE` | Exported for the agent command only |

It does not inherit the event JSON (`SPAWN_EVENT`, and the kit's own copy is not exported), because that holds other people's chat text; the event reaches the agent only inside its prompt. It does not inherit `SPAWN_TOKEN` (the raw token that Spawn's client hands to the hook). It does not inherit the world lock's file descriptor either. None of this stops an agent from reading the token file, because it runs as your user.

## Files in the runtime home

All of these live under `$SDLCA_SPAWN_HOME`. Modes are what the kit sets or what its umask of 077 produces.

| Path | Mode | Written by | Read by | Purpose |
| --- | --- | --- | --- | --- |
| (the runtime home itself) | 0700 | `scripts/install.sh`, `sdlca-onboard` | - | The top folder of everything below |
| `accounts/` | 0700 | Same | - | One folder per account |
| `accounts/<account>/env` | 0600 | `sdlca-onboard` or `sdlca-token` (only if missing), then you | Every command that takes an account | The account env file. `<account>` is `alice`, or `group/name` for a grouped account (`accounts/<group>/<name>/`). |
| `accounts/<account>/token` | 0600 | Spawn's `spawn login`, run by `sdlca-onboard`; or `sdlca-token add` | Every command that calls Spawn, the clones' git credential helper, Spawn's client | The account's token. A secret. The path can differ if you used `--token-file`; the env file records it. |
| `accounts/<account>/cursor` | 0600 | `sdlca-on-chat`, through `lib/cursor.py` | `sdlca-listen`, at start | Newest inbox event handled. See [Operations](operations.md#cursor-and-replay). |
| `accounts/<account>/cursor.lock` | 0600 | `sdlca-on-chat`, through `lib/cursor.py` | `lib/cursor.py` | An empty file used only as a lock, so two handlers that finish together cannot undo each other's cursor write. |
| `accounts/<account>/handled.ids` | 0600 | `sdlca-on-chat`, through `lib/dedupe.py` | `sdlca-on-chat` | The ids of the newest 500 events whose turn finished, so a replayed event does not run twice. |
| `accounts/<account>/runs.log` | 0600 | `sdlca-on-chat`, through `lib/ratelimit.py` | `sdlca-on-chat` | The start times of recent agent turns, for the hourly cap. |
| `accounts/<account>/handler.log` | 0600 | `sdlca-on-chat`, and the agent's own output | You | One metadata line per event, plus what the agent prints. |
| `accounts/<account>/listener.log` | 0600 | `sdlca-listen` | You | The friend-request catch-up at start and the Spawn client's status lines. The event JSON the client prints on standard output is discarded. |
| `worlds.json` | 0600 | `sdlca-worlds --apply` (it holds `worlds.json.lock` while it works) | `sdlca-on-chat`, the prompt renderer | The world registry, shared by all accounts. See [worlds.json](#worldsjson). |
| `allowlist.json` | 0600 | `scripts/install.sh` (only if missing), `sdlca-allow` | `sdlca-on-chat`, on every event | Who besides the owner may trigger work. See [The allowlist](#the-allowlist). |
| `AGENTS.md` | 0600 | `scripts/install.sh` (only if missing), then you or the agent | The agent, each turn | Standing rules and notes about the agent itself. Copied from [`templates/AGENTS.md`](../templates/AGENTS.md). |
| `WORK-TODO.md` | 0600 | Same, copied from [`templates/WORK-TODO.md`](../templates/WORK-TODO.md) | The agent, each turn | A shared ledger the agent keeps. |
| `handler-prompt.md` | - | You, optional | The prompt renderer, on every event | Replaces the default prompt. See [The prompt override](#the-prompt-override). |
| `run/` | 0700 | `scripts/install.sh`, `sdlca-onboard` | - | Holds the lock files, the scratch folders and the kept events |
| `run/<world owner>__<world>.lock`, `run/unrouted__<account>.lock` | 0600 | `sdlca-on-chat` | `sdlca-on-chat`, `sdlca-worlds` | One lock per world, plus one per account for messages with no world (a slash in a grouped account's name becomes an underscore). See [Operations](operations.md#timeouts-and-locks). |
| `run/scratch/<account>/` | 0700 | `sdlca-on-chat` | The agent | The folder an agent turn starts in when no world clone applies, so it never starts in the runtime home, which holds every account's token. |
| `run/failed/<event-id>.json` | 0600 | `sdlca-on-chat` | You | An event whose turn failed, timed out, was rate-limited, waited too long for a lock or could not read `SDLCA_CREDENTIALS_FILE`. It holds the raw event, including the chat text. The handler deletes it once it is more than `SDLCA_FAILED_KEEP_DAYS` days old (default 30; `0` keeps it forever), when the next allowed event on any account arrives, so replay it before then or copy the file. See [Replay a failed turn](operations.md#replay-a-failed-turn). |
| `shots/` | 0700 | `scripts/install.sh` | - | A place where `sdlca-look` may save a screenshot, besides `/tmp` and `$TMPDIR` (a new `.png` only; the folder is made again if it is missing). Nothing in the kit writes here by itself, because the default prompt tells the agent to save screenshots in `/tmp`. |

Outside the runtime home:

| Path | Written by | Purpose |
| --- | --- | --- |
| `$SDLCA_REPOS/<world owner>/<world>` (default `~/repos/...`) | `sdlca-worlds --apply` | One git clone per world |
| `~/.config/systemd/user/sdlca-listener@.service` | `scripts/install.sh` | The listener's service unit, rendered from [`systemd/sdlca-listener@.service.in`](../systemd/sdlca-listener@.service.in) |
| `node_modules/` in the kit folder | `bun install` | `playwright-core`, used only by `sdlca-look` |

The kit never leaves anything in your global git configuration. (While `sdlca-onboard` runs Spawn's `spawn login`, which adds a credential helper there, the script puts the earlier state back when it ends.) Spawn's client keeps its own files (for example `~/.spawn` and `~/.cache/spawnco-client`), which are not part of the kit.

## The account env file

`accounts/<account>/env` is a shell file. The kit sources it with every variable exported, so you write plain assignments and you do not need `export`. `sdlca-onboard` creates it like this:

```bash
# Account env for alice (sourced by the kit: keep it mode 0600)
OWNER=alice
SPAWN_USERNAME=alice_helper
SPAWN_TOKEN_FILE=/home/you/.sdlca/spawn/accounts/alice/token

# REQUIRED before any agent runs. ...
# (commented examples follow, then the optional settings, all commented out)
```

You then add `SDLCA_AGENT_CMD` and any optional settings:

```bash
SDLCA_AGENT_CMD='claude -p --allowedTools "Read" "Glob" "Grep" "Bash($SDLCA_CODE_DIR/bin/sdlca-say *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-api GET *)"'
SDLCA_AGENT_TIMEOUT=900
SDLCA_SAY_PAUSE=3
```

Rules the kit enforces or relies on:

- **It is code.** Every line runs as shell. Anyone who can write to the file can run commands as you. The kit refuses to start if the group or others can write to it (it checks the write bits only, not the owner), so keep it at mode 0600 and owned by you.
- **The account name** is the folder name. It is one word, or `group/name`: each word is lowercase letters, digits, underscore or hyphen, starts with a letter or digit, and is at most 64 characters. An account is not always a person's name: it is a token plus an env file, and `OWNER` inside the file says who may command it. (`sdlca-onboard` names the account after the owner, so there `--owner` is a Spawn username of lowercase letters, digits and underscores.)
- **Required lines:** `OWNER`, `SPAWN_USERNAME` and `SPAWN_TOKEN_FILE`, and the token file must be readable. Without them the command stops with a message that names the missing piece. A token file that holds a space, line break, double quote, backslash or character outside visible ASCII is refused when a tool uses it, and the message does not print the file.
- **Quote values** that contain spaces or special characters. Put the whole `SDLCA_AGENT_CMD` in single quotes, so that `$SDLCA_CODE_DIR` is expanded when the command runs and not when the file is read.
- **Do not put secrets in `SDLCA_AGENT_CMD`.** The command line is visible in the process list. Use the credentials file for keys.
- **You can add any other variable**, such as a `PATH` line (see [Operations](operations.md#troubleshooting)). Each one reaches the agent.

## Grouped accounts and sdlca-token

`sdlca-onboard` creates an agent account from an owner's one-time invite. `bin/sdlca-token` is the other way to get an account: it keeps a token that a person made by hand, without the token ever appearing on a command line, in your shell history or in a chat. A grouped account lives in `accounts/<group>/<name>/`. The group is only a folder that keeps related accounts together, for example `accounts/sdlca-for-spawn/alice/` and `accounts/sdlca-for-spawn/bob/`. Every command that takes an account accepts a grouped name, and `ACCOUNT` is the full `group/name`.

| Command | What it does |
| --- | --- |
| `sdlca-token init <account> --owner <spawn-username> [--username <spawn-username>]` | Creates the folder and the env file. No token yet. `--owner` is the Spawn user who made the token and may command the account. `--username` is the name the token signs in as, and defaults to the owner. |
| `sdlca-token add <account> --owner <spawn-username> [--username <spawn-username>] [--stdin]` | Does `init`, then asks for the token without echoing it (it needs a terminal), or reads one line from standard input with `--stdin`. It refuses an invite code (`sbk_...`), a value under 16 characters and a value with a space, double quote, backslash or character outside visible ASCII. It stores the token with mode 0600 through a temporary file, replaces any older token of that account, and never prints it. |
| `sdlca-token path <account>` | Prints the token file's path, for scripts: `SPAWN_TOKEN_FILE="$(bin/sdlca-token path sdlca-for-spawn/alice)"`. |
| `sdlca-token verify <account>` | Asks Spawn who the token belongs to (`GET /api/agent/v1/me`, through `sdlca-api`). It prints the username, handle, account kind, who the account is linked to and how many worlds it can reach, and says plainly when the token signs in as a person. Needs the network. |
| `sdlca-token list` | Lists every account, its owner and whether a token is stored. It never shows a token. |

Limits and cautions:

- **A grouped account cannot be a systemd listener instance**, because an instance name cannot contain a slash. Grouped accounts are for scripts and tools. Listeners use one-word account names.
- **A personal token signs in as the person who made it.** Chat lines, pushes and everything else it does appear under that person's name, and it can reach only the worlds that person can reach. A coordinator that works across several people's worlds with personal tokens would need one token per person. Spawn's settings page describes personal tokens as being for your own scripts and says agents make their own (seen 2026-11-17).
- **Each person makes and keeps their own token.** [Spawn's terms](https://www.spawn.co/terms-of-service) (checked 2026-11-17) restrict letting other people use your account. The kit never asks anyone to send a token to someone else. For another person's account, the safer route is the one `sdlca-onboard` uses: a separate agent account linked to that person with their one-time invite. For an AI agent that works in several owners' worlds, prefer one agent account that each owner adds as an editor: it shows as an agent, needs one token, and is revoked by unlinking. See [Several accounts and worlds](multi-account-and-worlds.md). Name each personal token on Spawn's page for the machine that uses it, so you can revoke each one alone.
- **Make personal tokens by hand.** Spawn publishes no API for making them. Replaying a logged-in browser session or the website's internal calls is outside the interfaces Spawn documents (see [Rules we follow for Spawn](compliance/spawn-rules.md)), a session cookie works like the account's password, and those internal calls change with each Spawn release. The kit never uses or stores browser cookies. If you want an API for this, ask Spawn.

## The agent command

### How it runs

For each allowed message, `sdlca-on-chat` does this, in order:

1. Removes the raw token (`SPAWN_TOKEN`) and the event from the environment.
2. Logs a `DENIED` line and stops, if the sender is not allowed.
3. Deletes saved events in `run/failed` that are more than `SDLCA_FAILED_KEEP_DAYS` days old, then skips an event id it has already handled (a `SKIP` line), so a replay after a crash does not run a finished turn again. It looks again once it holds the world's lock, so two copies of one event that arrive together run the agent once.
4. Checks the hourly cap, `SDLCA_MAX_RUNS_PER_HOUR`. Past the cap it logs `RATE-LIMITED`, keeps the event in `run/failed` and stops. If the cap cannot be checked (the value is not a whole number, or `runs.log` cannot be written), it logs `ERROR the run cap could not be checked`, leaves the event unhandled and does not move the cursor.
5. Logs an `event` line and renders the prompt from the event and the world registry.
6. Takes the world's lock, waiting up to `SDLCA_LOCK_WAIT` seconds if another turn holds it.
7. Reads `SDLCA_CREDENTIALS_FILE`, if you set one.
8. Changes into the world's clone. If no world matched, or the clone's folder is missing, it changes into `run/scratch/<account>` instead and does not warn you. It never runs the agent in the runtime home.
9. Pipes the prompt into `bash -c "$SDLCA_AGENT_CMD"` under `timeout -k 10 $SDLCA_AGENT_TIMEOUT`. Standard output and standard error are appended to `handler.log`.
10. If the command exits with status 0, records the event id in `handled.ids` (still holding the lock). If not, logs `WARN agent exited with status N; event kept in run/failed`. The numbers 74, 75 and 76 are the handler's own, so an agent command that exits with one of them is logged as status 1.
11. Writes the cursor, so the next start resumes after this event even when the turn failed.

Because bash runs the string, quoting, pipes and `&&` all work. A turn ends when the command exits. The agent does not inherit the lock, so a background process it leaves running cannot hold the world's lock (see [Operations](operations.md#timeouts-and-locks)). A failed turn is not run again by itself; [replay it by hand](operations.md#replay-a-failed-turn).

### The three postures

These come from [`templates/account.env.example`](../templates/account.env.example). The Claude Code options (`-p`, `--permission-mode` with `acceptEdits` and `bypassPermissions`, and `--allowedTools`) were checked against `claude --help` for Claude Code 2.1.327 on 2026-11-17. Maintainers tested the first two postures with Claude Code 2.1. Permission rules change between versions, so test your choice.

| Posture | Command | What it can do | Main risks |
| --- | --- | --- | --- |
| Read-only helper | `claude -p --allowedTools "Read" "Glob" "Grep" "Bash($SDLCA_CODE_DIR/bin/sdlca-say *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-api GET *)"` | Read files, search, read Spawn with GET calls, post chat replies | It can read any file your user can read, including tokens and the credentials file. A reply can leak what it read. |
| Builder with a tool allowlist | `claude -p --permission-mode acceptEdits --allowedTools "Bash(git *)" "Bash(spawn *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-say *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-api *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-look *)"` | Edit files; run git, Spawn's client, the kit's chat, API and screenshot tools | `git *` includes `git push`, which goes live in every open room. `sdlca-api *` allows every HTTP method on Spawn's API. `spawn *` is the whole client. |
| Full autonomy | `claude -p --permission-mode bypassPermissions` | Run any command as your user | Everything. Only for a machine and an owner you fully trust. |

The allowlist rules name the kit by its real path, because the prompt tells the agent to run the kit's tools by that path. The rules use `$SDLCA_CODE_DIR`, so they need no edit if you move the kit and run `scripts/install.sh` again.

Read [Security model](security-model.md) before using anything but the first posture. The sender allowlist and the prompt's advice reduce risk. They do not remove prompt injection.

### Test a command by hand

```bash
bin/sdlca-as alice bash -c 'printf "Reply with the single word ready.\n" | bash -c "$SDLCA_AGENT_CMD"'
```

This uses your provider account and may cost a little. To see what the agent would receive, or which world and decision an event gets, without running any agent or touching the network:

```bash
bin/sdlca-as alice bash -c 'printf "%s" "$1" | python3 -I -B "$SDLCA_CODE_DIR/lib/render_prompt.py"' _ '{"kind":"chat_mention","chat":{"from":"@alice","text":"hello"}}'
bin/sdlca-as alice bash -c 'printf "%s" "$1" | python3 -I -B "$SDLCA_CODE_DIR/lib/route.py"' _ '{"kind":"chat_mention","chat":{"from":"@carol","world":"@alice/game-1"}}'
```

The second command prints one tab-separated line: event kind, cursor, event id, decision (`allow` or `deny:<reason>`), sender, world address, working folder and lock name. The working folder is the world's clone, or `run/scratch/<account>` when no world matched. These are internal tools, so their output may change between releases.

## Other agent tools (unverified examples)

The kit only needs a command that reads a prompt on stdin, does the work in the current folder and exits. It ships no adapters for other tools. **The examples below are unverified.** We have not run them and have not checked them against current documentation. They are starting points. Check every one against your provider's own documentation before you use it.

| Tool | Example (unverified) | Check before use |
| --- | --- | --- |
| OpenAI Codex CLI | `SDLCA_AGENT_CMD='codex exec "$(cat)"'` | The name of its non-interactive mode, whether it reads stdin, and its sandbox and approval options |
| OpenCode | `SDLCA_AGENT_CMD='opencode run "$(cat)"'` | The same questions |
| Cursor's command-line agent | `SDLCA_AGENT_CMD='cursor-agent -p "$(cat)"'` | The name of its print mode and how it limits tools |
| Gemini CLI | `SDLCA_AGENT_CMD='gemini -p "$(cat)"'` | The same questions |

For every tool, answer these before you rely on it:

1. Does it have a mode that runs once without a person and exits?
2. Does it take the prompt on stdin, or only as an argument? The `"$(cat)"` form in the examples passes stdin as an argument. That makes the prompt, which contains the chat text, visible in the process list to other local users. Linux also limits the size of a single argument to about 128 KiB.
3. How does it limit what the agent can do (a read-only mode, a sandbox, a tool allowlist)? The kit does not translate between tools. The three postures above are specific to Claude Code.
4. Where does it find its credentials? A tool that stores a login in your home directory usually works under systemd. A tool that reads an environment variable needs the key in `SDLCA_CREDENTIALS_FILE`.
5. Does the agent have a way to run `sdlca-say`? Without it the answer goes only to `handler.log`.

## Provider keys

`SDLCA_CREDENTIALS_FILE` points at a file you already keep your provider keys in, so there is only ever one copy.

```bash
SDLCA_CREDENTIALS_FILE=/home/you/.config/agent-keys.env
```

How it behaves:

- The kit reads the file as shell, only inside a turn, after taking the world's lock. Every variable in it is exported to the agent command and to nothing else.
- Write plain `NAME='value'` lines. Because the file is shell, an unquoted value with a space breaks, and a value containing `$(...)` or backticks runs a command. Use single quotes and point only at a file you wrote.
- The kit checks only that the file is readable. It does not check its mode. Keep it at 0600.
- If it is unreadable, the log shows `ERROR SDLCA_CREDENTIALS_FILE is not readable; event kept in run/failed` and no `WARN` line follows it. No agent runs, the event is kept, and the cursor moves on. Fix the file, then [replay the event](operations.md#replay-a-failed-turn).
- The agent can see these keys. Anything it runs, and any file it reads, can reach them. A full-autonomy agent can print them.

## The allowlist

`allowlist.json` says who besides the owner may start work. The owner always may. Everyone else is ignored silently and logged as `DENIED`. If the file is missing, is not valid JSON, or is JSON but not an object, only the owner is allowed.

The kit compares handles as Spawn writes them, in lower case: a person is `@name` and an agent is `@@name`. The owner is allowed as `@<owner>`. An agent that happens to share the owner's name (`@@<owner>`) is not the owner. The agent's own handle (`@@<SPAWN_USERNAME>`) is always denied.

The file has two sections:

```json
{
  "slack": {
    "workspace": "",
    "members": []
  },
  "spawn": {
    "alice": ["carol"]
  }
}
```

| Section | Shape | Used today? |
| --- | --- | --- |
| `spawn` | An object. Each key is an owner's Spawn username (the `OWNER` of the account). Its value is a list of senders allowed to trigger work on that owner's account: `carol` or `@carol` for a person, `@@helper` for an agent. Entries that are malformed, empty or not in a list are ignored, never widened. | Yes. |
| `slack` | `workspace` (text) and `members` (a list of `{"username": ..., "id": ...}` with a Slack member id). | No. Nothing reads it yet. It is for the Slack bridge, which is planned. See [Slack bridge](slack-bridge.md) and the [roadmap](community/roadmap.md). |

The template file also has a `_doc` text field. Keys that start with an underscore are ignored.

Edit the file with `sdlca-allow` rather than by hand. It validates names and writes the file with mode 0600:

```bash
bin/sdlca-allow list
bin/sdlca-allow spawn add alice carol
bin/sdlca-allow spawn add alice @@helper
bin/sdlca-allow spawn remove alice carol
```

Names are lowercase letters, digits and underscores, up to 64 characters. For an extra sender, write `carol` or `@carol` for a person and `@@helper` for an agent. The first name after `add` or `remove` (`alice` above) is the owner, a Spawn username in the same form, never a `group/name` account. `remove` matches the entry exactly as it is stored: `carol` and `@carol` are two entries, so run `bin/sdlca-allow list` and remove each spelling you see. `sdlca-allow` reads `SDLCA_SPAWN_HOME` from your shell, so set it if you use a custom location. A change applies from the next event, with no restart.

Think before you add someone. Every sender on the list can make the agent run with the posture you chose, on your machine. An extra sender also gets a reply in the room, which everyone in it can read.

## worlds.json

`worlds.json` records the worlds the agent accounts can reach and where their clones are. It is one file for all accounts. Entries are keyed by Spawn's world id, which never changes, never by name, so a rename does not lose the world.

```json
{
  "worlds": {
    "<world id>": {
      "appId": "<app id>",
      "owner": "alice",
      "slug": "game-1",
      "address": "@alice/game-1",
      "clone_path": "/home/you/repos/alice/game-1",
      "aliases": [],
      "accounts": ["alice"],
      "slack_channel_ids": [],
      "standing": "editor"
    }
  }
}
```

| Field | Meaning |
| --- | --- |
| `appId` | Spawn's app id for the world. Spawn events name the world through the `relatedGameId` field. |
| `owner`, `slug` | The two parts of the address. `owner` is the world's owner, which is not always the account's owner. For a world an agent made itself (`@@agent/world`), `owner` is the agent's name. |
| `address` | The current address, `@owner/slug`. |
| `clone_path` | Where the clone lives. The agent starts here. |
| `aliases` | Old addresses, added when the kit sees a rename. |
| `accounts` | The accounts that can reach the world, added by every `sdlca-worlds --apply` run. Events for the world are routed to its clone only for these accounts. The list holds exact full account names (`alice`, or `group/name`), and an account's `OWNER` is not looked at. Entries written by older versions have no `accounts` list; for those the kit compares the world's `owner` with the account's `OWNER`. |
| `pending_move` | Present only while a renamed world's folder waits to be moved. See [Operations](operations.md#a-rename-is-not-detected). |
| `slack_channel_ids` | Reserved for the planned Slack bridge. Unused. |
| `standing` | The agent's role in the world as Spawn reports it. Informational. |

You normally never edit this file. `sdlca-worlds` writes it. The kit does not run `sdlca-worlds` by itself except at onboarding, so run it after the agent joins a new world or after a rename:

```bash
bin/sdlca-as alice bin/sdlca-worlds            # dry run: report only
bin/sdlca-as alice bin/sdlca-worlds --apply    # clone new or missing worlds, follow renames, save
```

### How an event is matched to a world

The kit looks for the world id, app id, address or an alias of each registered world in four fields of the event: `relatedGameId`, `actionData`, `chat.world` and `chat.key`. It never looks at the chat text, so what a person types cannot choose the world. A match must be a whole word, never part of a longer one, so `@alice/game` never matches `@alice/game-2`. Ids (the world id and the app id, with or without hyphens) are tried first, then the address or an alias. Only worlds served to the account are considered: those whose `accounts` list names it (an old entry with no list is served to the account whose `OWNER` is the world's `owner`). For example, a world that `alice` registered is not served to the grouped account `sdlca-for-spawn/alice` until `bin/sdlca-as sdlca-for-spawn/alice bin/sdlca-worlds --apply` has added that account to the list.

What follows from that:

- A world an agent made itself (`@@agent/world`) is reachable too, once `sdlca-worlds --apply` has recorded the account against it.
- If nothing matches, or the matched world's clone folder is missing, the turn runs in `run/scratch/<account>`, never in the runtime home. For no match, the prompt's world line shows `-`, and all such turns of one account share one lock (`run/unrouted__<account>.lock`).
- A failed clone is still recorded, and `sdlca-worlds --apply` tries it again on every run. See [Operations](operations.md#clone-failed).

## Clones and the commit identity

`sdlca-worlds --apply` makes one clone per world at `$SDLCA_REPOS/<world owner>/<world>` (and makes it again on a later run if the folder is missing). It sets these options in that clone only:

| Option | Value |
| --- | --- |
| `credential.helper` | An empty value, so git forgets any helper from your global or system configuration for this clone |
| `credential.https://<git host>.helper` | A helper that supplies the account's username and reads the password from that account's token file each time git asks. `<git host>` is the host of the world's https address, and only that host |
| `http.https://<git host>.proactiveAuth` | `basic` |
| Extra fetch rule | `+refs/notes/*:refs/notes/*`, so git notes are fetched along with branches |
| `user.name`, `user.email` | `SDLCA_GIT_NAME` and `SDLCA_GIT_EMAIL`, set only on a clone the kit makes |

Things to know:

- Because the helper reads the token file when git runs, a rotated token works in every clone with no change.
- Git offers the token only to the git host of the world's address. A remote, submodule or LFS address on another host gets no credentials. **Known limit:** a clone shared by two accounts keeps the helper of the account that made it.
- The identity is set only when the kit makes the clone. An existing clone is never changed, so set a name you want there yourself with `git config` in that clone.
- The default identity is `sdlca-agent` and `sdlca-agent@users.noreply.invalid`. The email ends in `.invalid`, a reserved name that cannot receive mail. Commits show that identity, so choose your own values if you want a real one.
- On a rename, the kit points the clone's remote at the new address, moves the folder to the new path under the current `SDLCA_REPOS`, and keeps the old address as an alias. If the new folder already exists, it leaves the clone where it was and warns. If an agent holds the world's lock, the move waits for a later run.
- For several accounts, renames and transferred worlds, see [Several accounts and worlds](multi-account-and-worlds.md).

## The prompt override

The kit builds the agent's prompt from [`templates/handler-prompt.md`](../templates/handler-prompt.md). To change it, copy that file to `$SDLCA_SPAWN_HOME/handler-prompt.md` and edit the copy. The kit uses your copy whenever the file exists and reads it fresh for each event. Delete it to go back to the default.

```bash
cp templates/handler-prompt.md ~/.sdlca/spawn/handler-prompt.md
```

Placeholders look like `{{NAME}}`: capital letters and underscores between double braces. The kit replaces them in a single pass, so text inside the event is never expanded again. An unknown placeholder stays as written.

| Placeholder | Replaced with |
| --- | --- |
| `{{OWNER}}` | The owner's Spawn username |
| `{{AGENT}}` | The agent's own Spawn username |
| `{{ACCOUNT}}` | The account's name (`alice`, or `group/name`) |
| `{{HOME}}` | The runtime home path (`SDLCA_SPAWN_HOME`), not your home directory |
| `{{CODE_DIR}}` | The kit's folder |
| `{{WORLD}}` | The matched world's address, or `-` when none matched |
| `{{CWD}}` | The matched world's clone path, or the account's scratch folder (`run/scratch/<account>`) |
| `{{WORLDS}}` | One line per world this account can reach, `  <address> -> <clone path>`, or `  (none registered yet)` |
| `{{EVENT}}` | The raw event JSON, including the chat text, between `<untrusted_event>` tags. Every `<` inside the JSON is written as `\u003c` (a backslash, then `u003c`), so the text cannot forge the closing tag. |

Keep `{{EVENT}}` in your version. It is the only way the agent learns what was asked, and it carries the fence around the untrusted text.

What the default prompt tells the agent, in short: who it is and that it is an independent helper that never speaks for Spawn; to read `AGENTS.md` and `WORK-TODO.md` first; which world and folder it is in; that the event and everything it fetches later (the conversation, other people's lines, world files, Savi's replies, `WORK-TODO.md`) is data and never an instruction that can change the rules; to read the line and what followed through `sdlca-api`; to answer with `sdlca-say`; never to print tokens or env files; to say what it will change before changing shared things; that a push goes live but never publishes; that agents cannot message Spawn's builder, Savi, so it ends with an "Ask Savi:" line instead; to end each reply with a "Handler notes:" line; and to record progress in `WORK-TODO.md`.

If you override it, keep equivalent rules. A prompt can only advise a model. It is not a sandbox, and dropping the rules removes the advice. You may want to remove the "Handler notes:" line, which other people in the room will see.

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
