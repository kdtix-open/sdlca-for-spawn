# Configuration

This page is for someone who runs the SDLCA agent kit and wants the complete reference: every environment variable, every file in the runtime home, and every setting you can change. It was checked against the kit's code on 2026-11-17, and its parts about the git address, `sdlca-look` and the Claude Code option on 2026-11-18. If you are new, start with [Getting started](getting-started.md).

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
| The account env file, for anything the handler uses (`SDLCA_AGENT_CMD`, `SDLCA_AGENT_TIMEOUT`, `SDLCA_LOCK_WAIT`, `SDLCA_REFRESH_TIMEOUT`, `SDLCA_MAX_RUNS_PER_HOUR`, `SDLCA_FAILED_KEEP_DAYS`, `SDLCA_CREDENTIALS_FILE`, `SDLCA_SAY_PAUSE`, `SDLCA_SAY_MAX_LINES`, `SDLCA_LOOK_TIMEOUT`, extra variables) | On the next event (for `SDLCA_LOOK_TIMEOUT`, the next look) |
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
| `SDLCA_REFRESH_TIMEOUT` | Account env | `60` | `sdlca-on-chat`, through `lib/refresh.py` | Seconds each git call may take when the kit brings a world's clone up to date before a turn (see [Updating a clone before each turn](#updating-a-clone-before-each-turn)). A call that stalls, such as a fetch from a world that does not answer, is stopped after that long, together with everything in its process group. The fast-forward itself gets at least 600 seconds whatever this says, because stopping a checkout half way leaves a half-updated work tree. The handler also stops the whole update after four times this value plus 660 seconds, so a hung update cannot hold the world's lock for ever. `0` turns the update off: no git runs, nothing is logged and the prompt gets no clone paragraph, even if `lib/refresh.py` is missing. A value that is not a whole number counts as 60, and more than a day counts as a day. |
| `SDLCA_MAX_RUNS_PER_HOUR` | Account env | `20` | `sdlca-on-chat` | The most agent turns the account may start in one hour (every turn can cost money). Past the cap the agent does not run and the event is kept in `run/failed`. `0` turns the cap off (so does a negative number). It must be a whole number: anything else logs `ERROR the run cap could not be checked` and no agent runs. |
| `SDLCA_LOOK_POLL` | Account env (a value in your shell is overridden by it) | `10` | `sdlca-look` | Seconds a look waits before it takes another picture when the last one was blank (under 20000 bytes): a whole number from 1 to 300. See [Seeing a world with sdlca-look](#seeing-a-world-with-sdlca-look). |
| `SDLCA_LOOK_SETTLE` | Account env (a value in your shell is overridden by it) | `20` | `sdlca-look` | Seconds a look waits, after a real picture that came only after blank ones, for the scene to fill in before it takes the last picture: a whole number from 0 to 300. |
| `SDLCA_LOOK_TIMEOUT` | Account env (a value in your shell is overridden by it) | `240` | `sdlca-look` | The most seconds one look may take, the join and the pictures together: a whole number from 1 to 3600. a whole number from 1 to 3600. Anything else is refused before anything is joined, and so is a `wait-seconds` that is not smaller than it. When the time is up, the join or the screenshot is stopped, the body leaves and the browser the join started is stopped, which takes up to about 20 seconds more. The body is also told to end by itself 30 seconds after the limit. A hung join therefore cannot hold an agent turn for the whole `SDLCA_AGENT_TIMEOUT`. See [Seeing a world with sdlca-look](#seeing-a-world-with-sdlca-look). |
| `SDLCA_BODY_POLL` | Account env (a value in your shell is overridden by it) | `10` | `sdlca-body` | Seconds between the checks on a sculpt that is still running: a whole number from 1 to 300. See [Giving an agent a body](operations.md#giving-an-agent-a-body). |
| `SDLCA_FAILED_KEEP_DAYS` | Account env | `30` | `sdlca-on-chat` | How many days a saved event stays in `run/failed`. When the next allowed event reaches the handler, it deletes the saved `.json` files that are more than this many days old (age counted in whole days). The `run/failed` folder is shared by all accounts, so an allowed event on any account removes every account's saved files that are more than that account's `SDLCA_FAILED_KEEP_DAYS` days old. To keep files longer, set the same larger value (or `0`) in every account's env file, or copy the file out. `0` keeps them forever, and so does a value that is not a whole number above 0. Saved events hold raw chat text, so keep the number small. See [Replay a failed turn](operations.md#replay-a-failed-turn). |
| `SDLCA_CREDENTIALS_FILE` | Account env | Unset | `sdlca-on-chat` | A file the kit reads as shell around the agent command only (after the clone update, so git never sees the keys), so provider keys reach the agent without a second copy. See [Provider keys](#provider-keys). |
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
| `SPAWN_TOKEN` | Do not set it | None | Spawn's guide says its tools read the token from this variable first and from the token file only if it is not set ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17). Setting it for the listener would make every account use one token. Spawn's client also passes the raw token to the event hook in this variable, so `sdlca-on-chat` removes it before anything else runs and the agent never inherits it. Every tool that takes an account (`sdlca-as`, `sdlca-look`, `sdlca-worlds` and the rest) removes it too, when it loads the account, so a `SPAWN_TOKEN` left in your terminal (a personal token used for a test, say) cannot make a command run as the wrong account: the client reads this variable before the token file, and would otherwise answer "this account is a person's". |

### What the agent inherits

The agent command runs as a child of `sdlca-on-chat`. It inherits everything below, and it runs as your user, so it can also read your token files.

| Variable | Value |
| --- | --- |
| `ACCOUNT`, `ACC` | The account's name (`alice`, or `group/name`), and the full path of its folder |
| `SDLCA_TURN_ACCOUNT` | The account's name again, set by the handler for the agent command only. `sdlca-look` takes an account as an argument, and inside a turn it refuses any account but this one; `sdlca-body` refuses to run at all while it is set. The account env file and the credentials file cannot change it (the handler's own assignment comes last), and it is not set when a person runs a tool by hand. |
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
| `accounts/<account>/body-sculpt.json` | 0600 | `sdlca-body` | `sdlca-body` | The record of a paid sculpt that was asked for and is not yet worn: its state, its job id, the character and the time. While it exists, a picture run for the account refuses. It is removed when the body is worn or the sculpt has failed, and you delete it by hand to start over. See [Giving an agent a body](operations.md#giving-an-agent-a-body). |
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
SDLCA_AGENT_CMD='claude -p --setting-sources user --allowedTools "Read" "Glob" "Grep" "Bash($SDLCA_CODE_DIR/bin/sdlca-say *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-api GET *)"'
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
7. Checks that `SDLCA_CREDENTIALS_FILE` is readable, if you set one. It does not read the file yet. An unreadable file stops the turn here, before the update runs.
8. Brings the world's clone up to date, still holding the lock, but only for an event that matched a world (a direct message has no world, so it runs no update). `lib/refresh.py` fetches the checked-out branch from the git address that `sdlca-worlds` recorded for the world (the `git` field in `worlds.json`, which `lib/route.py` hands to the handler) and fast-forwards when that is a straight line, and otherwise changes nothing. A world with no recorded address is not updated and no git runs (`skipped/unverified`). The handler logs one `WORLD` line and ends the prompt with a paragraph that says how it went. A failed, crashed, stopped or timed-out update never fails the turn. `SDLCA_REFRESH_TIMEOUT=0` skips this step, even when `lib/refresh.py` is missing. See [Updating a clone before each turn](#updating-a-clone-before-each-turn).
9. Reads `SDLCA_CREDENTIALS_FILE`, if you set one. This comes after the update on purpose: git, and every program git starts, never has the provider keys in its environment.
10. Changes into the world's clone. If no world matched, or the clone's folder is missing, it changes into `run/scratch/<account>` instead and does not warn you. It never runs the agent in the runtime home.
11. Pipes the prompt into `bash -c "$SDLCA_AGENT_CMD"` under `timeout -k 10 $SDLCA_AGENT_TIMEOUT`. Standard output and standard error are appended to `handler.log`.
12. If the command exits with status 0, records the event id in `handled.ids` (still holding the lock). If not, logs `WARN agent exited with status N; event kept in run/failed`. The numbers 74, 75 and 76 are the handler's own, so an agent command that exits with one of them is logged as status 1.
13. Writes the cursor, so the next start resumes after this event even when the turn failed.

Because bash runs the string, quoting, pipes and `&&` all work. A turn ends when the command exits. The agent does not inherit the lock, so a background process it leaves running cannot hold the world's lock (see [Operations](operations.md#timeouts-and-locks)). A failed turn is not run again by itself; [replay it by hand](operations.md#replay-a-failed-turn).

### The postures

These come from [`templates/account.env.example`](../templates/account.env.example). The Claude Code options (`-p`, `--setting-sources`, `--permission-mode` with `acceptEdits` and `bypassPermissions`, and `--allowedTools`) were checked against `claude --help` for Claude Code 2.1.327 on 2026-11-17, and `--setting-sources` and `--restricted` again on 2026-11-18. Maintainers tested the read-only and builder postures with Claude Code 2.1. Read-only with sight is the read-only helper plus one more rule. The kit's tests cover the tool that rule allows (with a stand-in client and browser), but it had not been tested with a real agent run when this page was written. Permission rules change between versions, so test your choice.

| Posture | Command | What it can do | Main risks |
| --- | --- | --- | --- |
| Read-only helper | `claude -p --setting-sources user --allowedTools "Read" "Glob" "Grep" "Bash($SDLCA_CODE_DIR/bin/sdlca-say *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-api GET *)"` | Read files, search, read Spawn with GET calls, post chat replies | It can read any file your user can read, including tokens and the credentials file. A reply can leak what it read. |
| Read-only with sight | `claude -p --setting-sources user --allowedTools "Read" "Glob" "Grep" "Bash($SDLCA_CODE_DIR/bin/sdlca-say *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-api GET *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-look *)"` | Everything the read-only helper can do, and take a picture of a world this account serves, then read it | The same as the read-only helper. Besides: while a look runs, the agent's body stands in the world where every player in the room can see it, and it counts against the account's body budget; the picture goes to your model provider; and text in the world can try to steer the model. See [what allowing `sdlca-look` means](security-model.md#what-allowing-sdlca-look-means). |
| Builder with a tool allowlist | `claude -p --setting-sources user --permission-mode acceptEdits --allowedTools "Bash(git *)" "Bash(spawn *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-say *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-api *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-look *)"` | Edit files; run git, Spawn's client, the kit's chat, API and screenshot tools | `git *` includes `git push`, which goes live in every open room. `sdlca-api *` allows every HTTP method on Spawn's API. `spawn *` is the whole client. |
| Full autonomy | `claude -p --setting-sources user --permission-mode bypassPermissions` | Run any command as your user | Everything. Only for a machine and an owner you fully trust. |

The allowlist rules name the kit by its real path, because the prompt tells the agent to run the kit's tools by that path. The rules use `$SDLCA_CODE_DIR`, so they need no edit if you move the kit and run `scripts/install.sh` again.

**Why every example has `--setting-sources user`.** In print mode (`-p`) Claude Code skips the question about trusting a folder, and with its default settings it loads the folder's own `.claude/settings.json` (hooks) and `.mcp.json` (MCP servers). The kit runs the agent in world clones that other people can push to, so a hook or a server they add would run a command as your user before any tool rule applies. The option loads only your own user settings: `~/.claude/settings.json` and its hooks still apply, and so do managed settings. Keep it in every Claude Code command you write. [The security model](security-model.md#a-worlds-own-settings-can-run-code) has what we tested and the stronger `--restricted` option, and `tests/test_claude_examples.py` fails when an example in the templates or the docs lacks it. Other tools may have the same problem and need their own answer. If your Claude Code version is older, check `claude --help` for the option.

**Tip: pin the model.** An account's default model can reach its usage limit, and the agent then fails every turn. Adding `--model` with a model id makes it use the one you choose, for example `claude -p --setting-sources user --model <model-id> --allowedTools "Read" "Glob" "Grep"` followed by the rest of your rules. `claude --help` says `--model` takes an alias for the latest model or a model's full name. This is a tip, not a default: the kit does not choose a model, and you should [test the command by hand](#test-a-command-by-hand) after you change it.

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

The second command prints one tab-separated line: event kind, cursor, event id, decision (`allow` or `deny:<reason>`), sender, world address, working folder, lock name and the git address recorded for the world. The working folder is the world's clone, or `run/scratch/<account>` when no world matched, and the git address is a dash when none is recorded. These are internal tools, so their output may change between releases.

### Seeing a world with sdlca-look

`bin/sdlca-look <account> <@owner/world> <out.png> [wait-seconds]` joins a world with a software-rendered body, saves one screenshot (with `lib/shot.mjs`, through Playwright) and leaves. The default prompt tells the agent to use it, so allowing it in `SDLCA_AGENT_CMD` (the read-only with sight posture, or the builder one) is what lets the agent see a world. A person can run it by hand too. Before it joins anything it refuses:

- **A world this account does not serve.** The address must be listed for the account in `worlds.json`, by the same rule that routes chat events (see [How an event is matched to a world](#how-an-event-is-matched-to-a-world)): the `accounts` list names the account, or an older entry with no list has the account's `OWNER` as its `owner`. An old address of a renamed world is accepted and joined under the current one. For anything else the message says to run `<kit folder>/bin/sdlca-as <account> <kit folder>/bin/sdlca-worlds --apply --only <@owner/world>` first, and a registry file that is damaged (not a JSON object) is reported as damaged, not as "not served".
- **Another account, inside an agent turn.** The handler sets `SDLCA_TURN_ACCOUNT` (see [What the agent inherits](#what-the-agent-inherits)), and then only that account may be named. A person at a shell has no such variable and may name any account.
- **An output that is not a new `.png`**: it must be an absolute path under `/tmp`, `$TMPDIR` or `$SDLCA_SPAWN_HOME/shots`, with no `..`, and nothing at it yet (no file, no link, no folder), so pick a new name for every look. Also **a world not written `@owner/world`**, and a `wait-seconds` that is not a whole number smaller than the time limit.

**Where it runs, and how the picture is saved.** The client's join and leave and the screenshot tool run in a private, empty folder that the tool makes under `$TMPDIR` (or `/tmp`), never in the folder you started it from. An agent works in a world's clone, which other people can push to, and bun, which runs both the client and the screenshot tool, loads a `bunfig.toml` (its `preload` setting runs code) and a `.env` from the folder it starts in, so running them in the clone would run whatever a world's builders put there, as the kit's user. The picture is made in that folder as well, and it is placed at the output path at the very end, as a new file that never follows a link, so a link or a file that somebody puts at the path while the look runs (a look takes seconds, and `/tmp` is shared) is not written through: the look then fails with `could not save the picture`. On success the tool prints one line, `saved <path>`.

The software renderer draws nothing until the world has loaded, which took about a minute and a half on the machine we tried it on (an Intel Core i7-7800X, no graphics card in use), so the first pictures are blank: about 4 KB, where a real scene is hundreds of kilobytes. The tool takes the first picture after `wait-seconds` (default 8). While a picture is blank (under 20000 bytes) it waits `SDLCA_LOOK_POLL` seconds (default 10) and takes another, until the time limit; when a real picture came only after blank ones, the scene is still filling in, so it waits `SDLCA_LOOK_SETTLE` seconds (default 20), takes one more and keeps that one. A real picture at the first try is kept as it is. If every picture is blank when the time runs out, the look fails and says so; raise `SDLCA_LOOK_TIMEOUT`. A picture that takes too long to make is skipped and tried again while there is time.

The join and the pictures together get `SDLCA_LOOK_TIMEOUT` seconds (default 240). However a look ends (done, refused, out of time, `SIGTERM` or `SIGHUP`), the body leaves with `spawn client leave`, which is stopped after 12 seconds if it hangs. Then, on Linux, a browser that the join started and left behind is stopped: the tool finds what listens on the page's port (it reads `/proc`), and stops it with its helper processes if it began after the look did. A program that was already running on that port is never touched, and the screenshot is not taken from it. The tool takes the page's address only from the client's own `page :` line, and refuses a join that prints none, or two different ones. What the client prints is never shown or stored, because it can hold join credentials. If the join is stopped before it printed the page address, the tool cannot find the browser by its port, and the client's own `leave` and the body's end of life (the join's `--ttl`, the limit plus 30 seconds) are what stop it.

`bin/sdlca-look --check [account]` joins nothing and uses no network. It says, for each thing a look needs, `ok` or `MISSING` with a fix: `python3`, `timeout`, the Spawn client, `bun`, `playwright-core` in the kit's folder, the shots folder, the account if you give one (inside a turn, the turn's own) and the time limit. It exits 1 when something is missing. It also prints a `note` about the browser. That line is not a check: the Spawn client starts its own browser for a look, and nothing Spawn publishes says where it keeps one, so this tool does not look for it (and does not read the client's code or files). If the first look fails at the join, run `spawn client join <world> --render cpu` by hand and read what the client says. [Operations](operations.md#a-look-does-not-work) shows what to do when a look fails.

The tool takes the page's address from the `page :` line of the join's output, the line Spawn's guide shows in that output (read on 2026-11-18). The guide does not show the exact form of that line for a `--render cpu` join, and the client is Spawn's and can change, which is why the tool refuses a join whose page line it does not understand. If that happens on your first look, the join's own output (which you can read by running the join by hand, and which can hold credentials, so do not paste it) will show what changed.

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
3. How does it limit what the agent can do (a read-only mode, a sandbox, a tool allowlist)? The kit does not translate between tools. The postures above are specific to Claude Code.
4. Where does it find its credentials? A tool that stores a login in your home directory usually works under systemd. A tool that reads an environment variable needs the key in `SDLCA_CREDENTIALS_FILE`.
5. Does the agent have a way to run `sdlca-say`? Without it the answer goes only to `handler.log`.

## Provider keys

`SDLCA_CREDENTIALS_FILE` points at a file you already keep your provider keys in, so there is only ever one copy.

```bash
SDLCA_CREDENTIALS_FILE=/home/you/.config/agent-keys.env
```

How it behaves:

- The kit reads the file as shell, only inside a turn, after taking the world's lock and after the clone update. Every variable in it is exported to the agent command and to nothing else: the update of the clone has already run, so git never has these keys in its environment.
- Write plain `NAME='value'` lines. Because the file is shell, an unquoted value with a space breaks, and a value containing `$(...)` or backticks runs a command. Use single quotes and point only at a file you wrote.
- The kit checks only that the file is readable. It does not check its mode. Keep it at 0600.
- If it is unreadable, the log shows `ERROR SDLCA_CREDENTIALS_FILE is not readable; event kept in run/failed` and no `WARN` line follows it. No agent runs, the event is kept, and the cursor moves on. Fix the file, then [replay the event](operations.md#replay-a-failed-turn).
- The agent can see these keys. Anything it runs, and any file it reads, can reach them. A full-autonomy agent can print them.

## Extension keys

Optional extensions keep their keys in `accounts/<account>/credentials.d/<name>.env` and are listed in `accounts/<account>/extensions`. See [Optional extensions](extensions.md#day-zero-turn-an-extension-on-for-an-account).

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
      "git": "https://git.spawn.co/@alice/game-1.git",
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
| `git` | The git address that Spawn's listing gave for the world, recorded by `sdlca-worlds --apply` (the one above is only an illustration). The update before a turn fetches from this address only and refuses a clone whose remote or credential helper disagrees with it, so an entry without one is `skipped/unverified`. It is recorded only when it is https, with a host, no user information and no `.` or `..` in its path. One record per world, shared by every account that reaches it. A world recorded before the field existed gets it on the next `--apply`: run `bin/sdlca-as alice bin/sdlca-worlds --apply` under the agent's account, with `--only @owner/world` for one world. See [Several accounts and worlds](multi-account-and-worlds.md#the-world-registry). |
| `clone_path` | Where the clone lives. The agent starts here, and the kit brings it up to date just before a turn that came from the world's own chat. |
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
- `sdlca-look` joins only a world that is served to its account by this rule, by its address or an old address ([Seeing a world with sdlca-look](#seeing-a-world-with-sdlca-look)).
- If nothing matches, or the matched world's clone folder is missing, the turn runs in `run/scratch/<account>`, never in the runtime home. For no match, the prompt's world line shows `-`, and all such turns of one account share one lock (`run/unrouted__<account>.lock`).
- A failed clone is still recorded, and `sdlca-worlds --apply` tries it again on every run. See [Operations](operations.md#clone-failed).

## Clones and the commit identity

`sdlca-worlds --apply` makes one clone per world at `$SDLCA_REPOS/<world owner>/<world>` (and makes it again on a later run if the folder is missing). It sets these options in that clone only:

| Option | Value |
| --- | --- |
| `credential.helper` | An empty value, so git forgets any helper from your global or system configuration for this clone |
| `credential.https://<git host>.helper` | A helper that supplies the account's username and reads the password from that account's token file each time git asks. `<git host>` is the host of the world's https address, and only that host |
| `http.https://<git host>.proactiveAuth` | `basic` |
| Extra fetch rule | `+refs/notes/*:refs/notes/*`, so git notes are fetched along with branches by a plain `git fetch`. The kit's own update fetches one branch and does not fetch notes |
| `user.name`, `user.email` | `SDLCA_GIT_NAME` and `SDLCA_GIT_EMAIL`, set only on a clone the kit makes |

Things to know:

- Because the helper reads the token file when git runs, a rotated token works in every clone with no change.
- Git offers the token only to the git host of the world's address. A remote, submodule or LFS address on another host gets no credentials. **Known limit:** a clone shared by two accounts keeps the helper of the account that made it, so the update before a turn, which runs as the account that received the message, fetches with the other account's token. That fetch fails if that account loses standing in the world, as a push would.
- The identity is set only when the kit makes the clone. An existing clone is never changed, so set a name you want there yourself with `git config` in that clone.
- The default identity is `sdlca-agent` and `sdlca-agent@users.noreply.invalid`. The email ends in `.invalid`, a reserved name that cannot receive mail. Commits show that identity, so choose your own values if you want a real one.
- On a rename, the kit points the clone's remote at the new address, moves the folder to the new path under the current `SDLCA_REPOS`, and keeps the old address as an alias. If the new folder already exists, it leaves the clone where it was and warns. If an agent holds the world's lock, the move waits for a later run.
- For several accounts, renames and transferred worlds, see [Several accounts and worlds](multi-account-and-worlds.md).

### Updating a clone before each turn

A clone is only useful if it is current, and nothing else keeps it current. A read-only agent command cannot run git at all (the one in [`templates/account.env.example`](../templates/account.env.example) cannot), so it reads whatever was cloned earlier. A plain `git pull` is also the wrong tool for a bot: it is a fetch plus a merge, so it can make a merge commit, rebase local commits, or stop in the middle with conflict markers in files the world runs, and a push of that goes live in every open room. So the kit does the update itself, as trusted code, and only by **fast-forward**. The checked-out branch moves forward when that is a straight line from where it is. In every other case nothing changes and the kit says why. It never makes a merge commit, never rewrites history, never leaves conflict markers and never overwrites a file you changed, an untracked file or an ignored file. The kit cannot tell a read-only agent from a building one (`SDLCA_AGENT_CMD` is only a command string), and the update is safe in both cases.

When it runs: `sdlca-on-chat` runs [`lib/refresh.py`](../lib/refresh.py) once per turn, after it takes the world's lock and before the agent starts, for an event that matched a world. It does not run for a direct message (no world, so no clone to update), and it does not run when `SDLCA_REFRESH_TIMEOUT` is `0`. It updates only the clone of the world the message came from, and only the branch that is checked out: not other worlds, not other branches, not tags, not submodules, and not the git notes that the clone's extra fetch rule names. For a world you reach through a direct message, the agent is told that its clone may lag the latest push. It needs git 2.29 or newer.

**It trusts one address: the one that `sdlca-worlds` recorded.** The clone is a folder the agent may have written to, so the update never asks the clone where the world is. `sdlca-worlds` records the git address that Spawn lists for the world in `worlds.json` (see [The world registry](multi-account-and-worlds.md#the-world-registry)), outside the clone, and the update fetches from exactly that address (`git fetch -- <address> ...`) and not through the name of a remote (and a remote section that is called like the address makes the clone `untrusted`, because git would read the address as that remote's name). It also requires that the clone agrees: the branch's remote must have one address in the clone's settings, and it must be the recorded one, or the clone is `untrusted`. The addresses are compared by scheme, host, port and path. The scheme and the host are compared in lower case (`GIT.Spawn.CO` is `git.spawn.co`), a trailing slash or `.git` on the path does not count, and the port and the rest of the path are compared as written, so `:443` written out is not the same address as none. An address with user information, a query, a space or other odd character, or a `.` or `..` segment is never accepted, and neither is a host that merely starts or ends like the right one. A world with no usable recorded address is `unverified`: no git runs. Running `bin/sdlca-as <account> bin/sdlca-worlds --apply` records the address (`--only @owner/world` for one world).

What it does, in order. It stops at the first step that gives an answer:

1. The folder must exist, must not be a symbolic link, and must be the top of a git work tree (`not-git` or `untrusted` otherwise). Git must be version 2.29 or newer (`error` otherwise).
2. A branch must be checked out (`detached`), it must have commits and an upstream, that is `branch.<name>.remote` and `branch.<name>.merge` (`no-upstream`). A branch that exists but whose commit git cannot read is a damaged clone (`error`).
3. The folder and the clone's own git settings must hold nothing that can run a program, send git elsewhere or write through a link, and no credential helper scoped to any origin but the recorded one (`untrusted`, see below). This is checked now, and again just before step 5. The branch's remote must also have exactly one address in the clone's settings, and it must be the recorded address (`untrusted` otherwise, and the text names the two hosts and never a whole address). A remote that has no address in the clone's settings counts as no upstream (`no-upstream`).
4. It fetches that one branch from the recorded address into a ref of its own, `refs/sdlca/refresh-tip`, and into the tracking branch that the clone's own fetch rule names for it (`refs/remotes/origin/main`), in one fetch, and writes no `FETCH_HEAD` (`fetch`, or `timeout`). It writes the tracking branch itself because a fetch from an address does not, and the reflog of that branch is what `git rebase --fork-point` and the check for a world that moved back read. No tracking branch is written for a clone whose fetch rule maps the branch anywhere but under `refs/remotes/`. Nothing in the work tree changes.
5. It compares the clone's `HEAD` with the fetched tip. Equal is `current`. Ahead of the world (`ahead`) and both ahead and behind (`diverged`, which is also what a world that rewrote its history by force, or moved back to an older commit, looks like) change nothing. Behind is a fast-forward: after a second look at the clone's settings, and a look for lock files that would make git half-apply it, it runs `git merge --ff-only --no-overwrite-ignore`. That is `updated`, or `merge` if git refuses, for example because the update would overwrite a file you changed, an untracked file or an ignored one, in which case the tree stays exactly as it was. The one exception is a fast-forward that is stopped part way (see Time limits below).

It never runs `merge` without `--ff-only`, `rebase`, `reset`, `checkout`, `clean` or `stash`, and never forces anything. A change you have not committed is kept. If the update needs a file that you changed, or an untracked or ignored file stands in its way, the update is refused instead.

What each answer means. `sdlca-on-chat` writes one line, `WORLD <address> clone <status>/<code>: <text>`, to `handler.log`, and ends the prompt with a paragraph written by the kit:

| Log line | What happened | What the agent is told (the reason in the last paragraph of its prompt) |
| --- | --- | --- |
| `updated/ok: 3f2a1b9..8c0d4e1, 2 new commits` | The branch was fast-forwarded. | The branch that is checked out was brought up to date just before the turn. Other branches and any submodules were not updated. |
| `current/ok: already at 8c0d4e1` | The clone was already at the world's tip. | The same. |
| `skipped/unverified: no git address is recorded for this world, ...` | No git address is recorded for this world (or the recorded one is not an address the update accepts), so nothing about the clone was trusted and no git ran. | It could NOT be brought up to date: its git address has not been recorded, so it was not updated; the person can run `sdlca-worlds --apply`. |
| `skipped/ahead: 2 local commits are not pushed` | The clone has commits the world lacks, and the world has only moved forward. | It could NOT be brought up to date: it has commits that are not pushed yet. |
| `skipped/diverged: ...` | Both have moved on, or the world rewrote its history or moved back to an older commit (the update sees the last two in the reflog of the tracking branch, so that is a best effort). The text gives both counts, or says that the world moved back. | ... the clone and the world each have commits the other lacks, or the world rewrote its history. |
| `skipped/detached`, `skipped/no-upstream` | No branch is checked out, or the branch follows nothing (or has no commits, or its remote has no address in the clone's settings). | ... it is not on a branch that follows the world. |
| `skipped/untrusted: ...` | The folder, a link inside `.git`, the clone's remote or the clone's own git settings are not trusted. The text names the setting or the path, or, for a remote that is not the recorded address, the two hosts. The branch and the work tree were left as they were. | ... its git settings were not trusted, and the advice is not to run git in that clone. |
| `skipped/not-git: ...` | The folder is not the top of a git work tree (it is missing, or is a subfolder of another repository, or is not a repository). | ... the folder is not a git clone, or it is missing, and the advice is not to run git there. |
| `failed/fetch: git said: ...` | Git could not fetch from the recorded address: no network, a token Spawn refused, or the branch is gone. | ... the world could not be reached. |
| `failed/timeout: ...` | A git call other than the fast-forward took longer than `SDLCA_REFRESH_TIMEOUT` seconds and was stopped, or the handler stopped the whole update. | ... the update ran out of time. |
| `failed/merge: ...` | Git refused the fast-forward or did not move the branch, a lock file was in the way, the world holds a path that git refuses to check out, or the fast-forward ran out of time and was stopped part way. | ... something in the clone stopped the fast-forward, so some files may be changed or half updated: check `git status` before you trust or commit them. |
| `failed/error: ...` | Git is missing or older than 2.29, a branch's commit cannot be read, `lib/refresh.py` is missing or crashed, or an answer could not be read. | ... the update could not run. |
| (no line) | `SDLCA_REFRESH_TIMEOUT` is `0`, or the event matched no world. | Nothing is added. |

Every paragraph that says the clone could NOT be brought up to date says that what the agent reads in it may lag the latest push and that it should say so in its reply. It then ends with advice. For most codes: if it builds, run `git fetch` and then `git rebase --fork-point origin/main` before it pushes, and never force-push (a plain rebase can bring back commits that the world removed by rewriting its history, and `--fork-point` leaves them out). For `untrusted` and `not-git`: do not run git there, and tell the person that the clone needs a look. The wording is fixed, and nothing that git or a remote said is ever put in the prompt. The text after the colon in the log line is for you: it holds shas, counts, the name of a setting or a path, or the first line of git's own error with user information in URLs removed, control characters removed and the line cut to 120 characters.

**What makes a clone untrusted.** An agent that can edit files can change a clone's `.git/config`, and this update runs outside the agent's tool limits, so the kit reads the clone's own settings first: before git reads any object, again right before the fetch, and again right before the fast-forward. It reads `.git/config`, and `.git/config.worktree` when the clone turns on `extensions.worktreeConfig`, with `git config`, which runs nothing. It refuses to go on if it finds, whatever the value:

- any `filter.*` key (clean and smudge filters run on every file an update writes), `core.fsmonitor`, `core.sshCommand`, `core.gitProxy`, `core.askPass`, `core.alternateRefsCommand` or `core.worktree`;
- any `include.*` or `includeIf.*` key (they pull in settings that the check cannot see);
- `url.<base>.insteadOf` and `pushInsteadOf`, and `remote.<name>.proxy`, `.proxyAuthMethod`, `.uploadpack`, `.receivepack` or `.vcs`;
- `fetch.bundleURI` and any `bundle.*` key (a second place to download from);
- a promisor remote: `extensions.partialClone`, `remote.<name>.promisor`, `remote.<name>.partialCloneFilter` and any `promisor.*` key. With one of them git fetches an object that is missing, such as the commit the branch points to, from that remote on its own, even when the update only reads it, and with the token if a helper is scoped to that host. That is why the settings are checked before the first call that reads an object, and why every call also carries `GIT_NO_LAZY_FETCH=1` (git 2.44 and newer);
- a remote section whose name is an address, that is, a name with a colon, a slash or an at sign, such as `[remote "https://..."]`: git reads the word that `git fetch -- <address>` is given as the name of a remote first, so a remote called like the recorded address, with a url of its own, would take the fetch somewhere else. The log shows such a key as `remote.(a name that is not plain).<key>`, never with the name;
- `gpg.program` (and `gpg.<format>.program`), `uploadpack.packObjectsHook`, `merge.<name>.driver` and `branch.<name>.mergeOptions`;
- every `http.*` key except the ones the kit writes and a few that cannot send a request anywhere else. Allowed: `http.<url>.proactiveAuth` (with a URL in it, as `sdlca-worlds` writes it), `http.postBuffer`, `http.lowSpeedLimit`, `http.lowSpeedTime`, `http.maxRequests`, `http.minSessions`, `http.noEPSV`, `http.userAgent` and `http.version`. Anything else under `http.` can change where a request goes (`http.proxy`, `http.curloptResolve`, `http.followRedirects`), whom git trusts (`http.sslVerify`, `http.sslCAInfo`, `http.sslCAPath`) or what it sends (`http.extraHeader`, `http.cookieFile`), and a request that carries the token must not be changed that way. A proxy you need for every repository belongs in your own global git configuration or in the `https_proxy` environment variable (the name git's own documentation gives), which are yours and are not checked;
- a credential helper that is not what `sdlca-worlds` wrote, or that is scoped to another origin than the recorded address's. An empty `credential.helper` that is not scoped is fine. Any other helper that is not scoped to a host is not. A scoped one must be scoped to the origin (scheme, host and port, with no path, wildcard or user information in the scope) of the recorded address, which must itself be an https address, or plain http on this machine; a helper scoped to any other origin is refused, even an empty one, because a copy of the kit's helper line under another host's scope is how an agent would get the token sent there. It must be exactly the helper command that `sdlca-worlds` writes, reading the token file of this account (`SPAWN_TOKEN_FILE`) or a file named `token` in an account's folder under `$SDLCA_SPAWN_HOME/accounts`. A helper that reads any other file is refused, so a clone cannot make the kit send some other file to a host.

It also refuses a clone whose remote is not the recorded address (see above), and one whose remote has more than one address.

It also refuses a folder that is a symbolic link, or whose `.git` is a symbolic link or a file that points to a git folder somewhere else, and a clone where anything under `.git/logs` or `.git/refs` is a symbolic link or a file under `.git/logs` has more than one name. Git appends to a reflog in place, so a link there would be written through, and the update runs as you. The check names the key, spelled as `git config --local --list` prints it so that you can remove it, or the path, and never prints a value. Your own global and system git configuration is yours and is not checked. If you set one of these in a clone on purpose (a local Git LFS filter, `core.fsmonitor` from Scalar, an `include.path`, an `http.proxy`), that clone is skipped as untrusted: the agent still runs and is told, and you can remove the setting to get updates again. `core.hooksPath` is not on the list because the kit turns hooks off on the command line anyway.

**How the git calls are made.** There is no shell: git is started with an argument list, by its absolute path, found only through the absolute entries of `PATH` (an empty or relative entry would name a folder inside the clone). Git writes its output to temporary files and not to pipes, so a program that git started and left running cannot hold a call that has finished. Every call carries `-c core.hooksPath=/dev/null -c core.fsmonitor=false -c core.pager=cat -c gc.auto=0 -c maintenance.auto=false`, which beat both the clone's configuration and yours, plus `merge.autoStash=false` (so an update can never stash your work and re-apply it with conflict markers) and a fixed commit identity, `user.name=sdlca-refresh` and an `.invalid` email, which is what git writes in the reflog when it moves the branch, so the clone's own `user.name` is never written to a file. The kit never passes `credential.helper`, because the clone logs in through the helper that `sdlca-worlds` wrote into it, and an empty helper on the command line would erase that one. The fetch names the recorded address and not the remote, so `remote.<name>.proxy`, `.uploadpack` and the like of the remote that the branch follows do not reach it (the check still refuses them); `url.<base>.insteadOf`, which git applies to an address given on the command line as well, and a remote section called like the address (git reads the word it is given as a remote's name first) stay on the list for that reason. The environment is your own, with `PATH` cut to its absolute entries, `GIT_TERMINAL_PROMPT=0` (git never waits for a person), `LC_ALL=C`, `GIT_NO_LAZY_FETCH=1`, `GIT_ALLOW_PROTOCOL=https` unless you set `GIT_ALLOW_PROTOCOL` yourself (the recorded address is https in any case, and a clone whose remote is anything else is `untrusted` before a fetch), and without `GIT_ASKPASS`, `SSH_ASKPASS`, `GIT_SSH`, `GIT_SSH_COMMAND`, `GIT_PROXY_COMMAND`, `GIT_EXTERNAL_DIFF`, `GIT_DIR`, `GIT_COMMON_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY` and `GIT_ALTERNATE_OBJECT_DIRECTORIES`. Git is also told not to look for a repository above the clone's own folder. The handler runs the update before it reads `SDLCA_CREDENTIALS_FILE`, so provider keys are not in that environment.

**Time limits.** `SDLCA_REFRESH_TIMEOUT` is for each git call, not for the whole update, except that the fast-forward gets at least 600 seconds. When a call runs out of time, the kit stops git and everything in git's process group, asking first (`SIGTERM`, so that git removes its own lock files) and, after 3 seconds, by force. A program that git started and that put itself in another session or process group is not stopped. A fetch that is stopped logs `failed/timeout`. A fast-forward that is stopped logs `failed/merge`, with text that says so, because the world was reached: files that were already replaced stay replaced while the branch has not moved, `git status` shows them as changes, and every later update is refused until you have put them back (see [The clone was not brought up to date](operations.md#the-clone-was-not-brought-up-to-date)). Reaching that point takes a stuck file filter or a stalled disk, not a slow network. The handler also stops the whole update after four times `SDLCA_REFRESH_TIMEOUT` plus 660 seconds and logs `failed/timeout: the update was stopped by the handler`. That is a last resort so that a hung update cannot hold the world's lock for ever: a turn that waits for the lock counts that time against `SDLCA_LOCK_WAIT`.

**Limits.** The update is not a promise that the clone is current: it can be `skipped` or `failed`, and the agent is then told so. The check of the clone's settings is a list, so it does not stop an agent that can edit files in the clone from changing `.git/config` in ways the list does not name. It also looks at the settings before the fetch and again before the fast-forward, not during them, so a process that the agent left running could still change them in between, and that is not a theoretical gap: in a reviewer's test, a program that flipped `.git/config` between a clean and a hostile version at the right moment got a token to a host of its choosing within a few runs. The update fetches only from the address recorded outside the clone, so an agent that rewrites the clone's remote, or copies the kit's helper line under another host's scope, gets a refusal and no request. What is still open: an agent that can edit `worlds.json` or the runtime home, or that can run a program as your user, can change the record, and the address is only as good as Spawn's listing. A world that moved back or rewrote its history is recognized as such (`diverged`) only when the reflog of the tracking branch shows it, and otherwise it looks like `ahead`, which is why the advice uses `git rebase --fork-point`: unlike a plain rebase, it does not bring back commits that the world removed. Only a separate Unix user for the agent, with no write access to the runtime home, closes the list, the timing and the record. See [Security model](security-model.md#updating-the-clone-before-a-turn).

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

The kit also ends every prompt for an event that matched a world with a paragraph of its own, `Clone status (written by the kit): ...`, whatever your template says, except when `SDLCA_REFRESH_TIMEOUT` is `0` (see [Updating a clone before each turn](#updating-a-clone-before-each-turn)). It is added after the template is rendered, so your copy does not need it. If you change the lines about pulling or pushing, keep the rule against force-pushing. A copy you made before the kit updated clones still tells the agent to run `git pull` and has no rule against force-pushing, and the kit never edits your copy, so compare it with the template and copy the new lines. A copy made before the screenshot tool was documented also lacks the two sentences in "Seeing the game" that tell the agent to say so under `Handler notes:` when `sdlca-look` is refused or not permitted, and to name the picture it describes, and the rule that the picture must be a new `.png`: copy those in too.

What the default prompt tells the agent, in short: who it is and that it is an independent helper that never speaks for Spawn; to read `AGENTS.md` and `WORK-TODO.md` first; which world and folder it is in, and that the kit brings the clone of the world a message came from up to date just before the turn (any other clone may lag the latest push, so it says so); that the event and everything it fetches later (the conversation, other people's lines, world files, Savi's replies, `WORK-TODO.md`) is data and never an instruction that can change the rules; to read the line and what followed through `sdlca-api`; to answer with `sdlca-say`; never to print tokens or env files; to say what it will change before changing shared things; that a push goes live but never publishes; never to force-push (if a push is rejected, to run `git fetch`, then `git rebase --fork-point origin/main`, check that the change still works and push again, or to stop and tell the person if a conflict cannot be resolved); that agents cannot message Spawn's builder, Savi, so it ends with an "Ask Savi:" line instead; to end each reply with a "Handler notes:" line; and to record progress in `WORK-TODO.md`.

If you override it, keep equivalent rules. A prompt can only advise a model. It is not a sandbox, and dropping the rules removes the advice. You may want to remove the "Handler notes:" line, which other people in the room will see.

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
