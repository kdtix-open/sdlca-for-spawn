# Operations

This page is for someone who already has the SDLCA agent kit working and now has to keep it running for weeks: start and stop it, read its logs, upgrade it, and fix it when something goes wrong. It was checked against the kit's code on 2026-11-17, its parts about the git address, `sdlca-look` and the Claude Code option on 2026-11-18, and its part about `sdlca-body` on 2026-11-20. The examples use an account for the owner `alice`; replace the name with yours. For a first install, see [Getting started](getting-started.md).

## Daily commands

Each account has its own systemd user service, named `sdlca-listener@<account>.service`. Only one-word account names work as instances: a grouped account (`group/name`) cannot be one, because an instance name cannot contain a slash (see [Grouped accounts](configuration.md#grouped-accounts-and-sdlca-token)).

| Task | Command |
| --- | --- |
| Start now and at every login | `systemctl --user enable --now sdlca-listener@alice.service` |
| See the status | `systemctl --user status sdlca-listener@alice.service` |
| Follow the service journal | `journalctl --user -u sdlca-listener@alice.service -f` |
| Read the last hour of the journal | `journalctl --user -u sdlca-listener@alice.service --since "1 hour ago"` |
| Follow the handler log | `tail -f ~/.sdlca/spawn/accounts/alice/handler.log` |
| Restart | `systemctl --user restart sdlca-listener@alice.service` |
| Stop, but start again at next login | `systemctl --user stop sdlca-listener@alice.service` |
| Stop and do not start at login | `systemctl --user disable --now sdlca-listener@alice.service` |
| List the listeners | `systemctl --user list-units 'sdlca-listener@*'` |
| Keep user services running after logout | `loginctl enable-linger "$USER"` |
| Check that lingering is on | `loginctl show-user "$USER" --property=Linger` |

A restart or stop ends a turn that is running at that moment. See [Restart and upgrade](#restart-and-upgrade).

## Running without systemd

The kit ships a systemd unit only. A launchd setup for macOS is planned (see the [roadmap](community/roadmap.md)). On macOS or anywhere else you can run the listener under any supervisor that does the following:

- Runs `bin/sdlca-listen <account>` as your user, one process per account, with `umask 077`.
- Gives it a `PATH` that finds `bun`, `spawn` and your agent tool. The kit adds `~/.bun/bin` and `~/.local/bin` by itself.
- Restarts it a few seconds after it exits, but not when it exits with status 78. That status means a configuration error, and restarting would only repeat it.
- Stops everything it started when you stop it, so a running turn does not outlive the listener.

For a quick test, run `bin/sdlca-listen alice` in a terminal and `tail -f` the handler log in another. The listener writes to `listener.log`, not to the terminal.

## Systemd unit settings

[`systemd/sdlca-listener@.service.in`](../systemd/sdlca-listener@.service.in) is rendered by `scripts/install.sh` into `~/.config/systemd/user/`.

| Setting | Value | What it does for you |
| --- | --- | --- |
| `ExecStart` | `<kit folder>/bin/sdlca-listen %i` | One instance per account. `%i` is the account name. |
| `Restart`, `RestartSec` | `always`, `5` | The listener comes back five seconds after an exit. |
| `RestartSteps`, `RestartMaxDelaySec` | `6`, `300` | While the listener keeps failing (for example because Spawn refuses the token), the delay grows from 5 seconds to 5 minutes. These two settings need systemd 254 or newer. |
| `RestartPreventExitStatus` | `78` | No restart loop when the agent command is not configured. |
| `UMask` | `0077` | Files the kit writes are private to you. |
| `NoNewPrivileges` | `yes` | The service and everything it starts cannot gain privileges, for example through a setuid program such as `sudo`. |
| `KillMode` | `control-group` | Stopping or restarting the service ends everything it started, including a running agent turn and any stray process the agent left behind. |
| `TimeoutStopSec` | `30` | After 30 seconds systemd forces whatever is left to stop. |
| `WantedBy` | `default.target` | Start with your user manager. |

The unit does not wait for the network: `network-online.target` is not available to the user manager. A listener that cannot connect is restarted as described above.

Do not edit the rendered file, because `scripts/install.sh` writes it again each time. Use a drop-in, which systemd keeps separate:

```bash
systemctl --user edit sdlca-listener@alice.service
```

For example, to use a runtime home in another place, add this and restart:

```ini
[Service]
Environment=SDLCA_SPAWN_HOME=/srv/sdlca/spawn
```

Set the same variable in your shell when you run kit commands by hand, or they will use the default home.

## Logs and what they contain

| Where | What is in it |
| --- | --- |
| The systemd journal (`journalctl --user -u ...`) | Systemd's own start, stop and restart messages, plus anything `sdlca-listen` prints before it hands over to Spawn's client. Start-up errors appear here, such as the status 78 message. |
| `accounts/alice/listener.log` | The output of the friend-request catch-up at start (`friend accept: ...`) and the Spawn client's status lines (what `spawn events` prints on standard error). The event JSON the client prints on standard output is discarded. |
| `accounts/alice/handler.log` | One metadata line per event the kit handles (and one more about the update of the world's clone), plus everything the agent command prints. |
| `run/failed/<event-id>.json` | Not a log, but kept events, which the handler deletes after `SDLCA_FAILED_KEEP_DAYS` days (30 by default): see [Replay a failed turn](#replay-a-failed-turn). |
| Your agent tool's own logs | Wherever that tool keeps them. The kit does not manage them. |

The lines the kit writes to `handler.log` start with a UTC time. They never contain chat text or tokens.

| Line | Meaning |
| --- | --- |
| `event sender=@alice world=@alice/game-1` | An allowed message started a turn. The sender is a handle as Spawn writes it (`@name` for a person, `@@name` for an agent). A dash for `world` means no world was matched, and the agent starts in `run/scratch/alice`. |
| `WORLD @alice/game-1 clone updated/ok: 3f2a1b9..8c0d4e1, 2 new commits` | Before the agent started, the handler brought the world's clone up to date, by fast-forward only. This line follows the `event` line of every turn that matched a world, and says what happened as `<status>/<code>: <text>`. `current/ok` and `updated/ok` mean the clone is current. `skipped/...` means the kit chose to change nothing: `unverified`, `ahead`, `diverged`, `detached`, `no-upstream`, `untrusted` or `not-git`. `failed/...` means the update was tried and did not work: `fetch`, `timeout`, `merge` or `error`. For any other status the agent was told that the clone may lag the latest push, and the turn still ran. The text can hold a host, or the first line of git's own error, which is for you and is never put in the prompt. If `lib/refresh.py` itself crashed, its traceback is in the lines just above this one. No line is written for a direct message, or when `SDLCA_REFRESH_TIMEOUT` is `0`. See [The clone was not brought up to date](#the-clone-was-not-brought-up-to-date) and [Updating a clone before each turn](configuration.md#updating-a-clone-before-each-turn). |
| `DENIED sender=@mallory reason=not-allowed` | A message was ignored. Reasons are `not-allowed`, `self` and `unknown-sender` (shown as `sender=-`). See [DENIED lines](#denied-lines). |
| `SKIP event <id> was already handled` | The same event arrived again after its turn had finished (for example a replay after a crash), so the agent did not run again. With `(another copy finished first)` added, two copies of the event arrived at the same moment and the other one ran. |
| `RATE-LIMITED more than 20 agent runs in an hour; event kept in run/failed` | The hourly cap (`SDLCA_MAX_RUNS_PER_HOUR`) was reached. The agent did not run. See [Replay a failed turn](#replay-a-failed-turn). |
| `WARN agent exited with status 127; event kept in run/failed` | The agent command ended with a non-zero status. 124 means the time limit stopped it, and 137 means it had to be killed after ignoring the stop signal. 125 means `timeout` could not read `SDLCA_AGENT_TIMEOUT`. 126 and 127 mean the command could not be run or was not found. If the agent command itself exits with 74, 75 or 76, which the handler uses for its own outcomes, the line says status 1. |
| `WARN the world was busy for too long; event kept in run/failed` | Another turn held the world's lock for longer than `SDLCA_LOCK_WAIT`, so the agent did not run. |
| `ERROR SDLCA_AGENT_CMD is not set; event left unhandled` | The env file lost its agent command after the listener started. The cursor does not move, so the event comes again after the next listener start. |
| `ERROR SDLCA_CREDENTIALS_FILE is not readable; event kept in run/failed` | The credentials file is missing or unreadable. The agent does not run, and no `WARN` line follows. The event is kept in `run/failed` and the cursor moves on. |
| `ERROR the run cap could not be checked (status 2; ...); event left unhandled` | `SDLCA_MAX_RUNS_PER_HOUR` is not a whole number, or `runs.log` cannot be written. The agent did not run and the cursor does not move. Fix the value or the file's permissions. |
| `WARN handled.ids could not be read (status 2); treating the event as new` | The file of finished event ids cannot be opened (for example it is a folder, or its mode is wrong). The agent ran anyway, because a repeated turn is better than a lost one. Fix the file. |
| `WARN could not record event <id> as handled` | The turn finished but its id could not be saved, so a replay of the same event would run again. Look at the permissions of `handled.ids`. |
| `ERROR the prompt could not be rendered; event left unhandled` | The prompt could not be built, for example because `handler-prompt.md` cannot be read. The cursor does not move. |
| `ERROR event could not be parsed; skipped` | The event was not usable JSON. The kit skips it and does not move the cursor. |
| `WARN friend accept failed` | Accepting the owner's friend request failed. The lines just before it explain why. |
| `friend accept: friends` | The result of accepting a friend request. It has no time in front. |
| `SAVI-EVENT kind=savi_finished` | Spawn's builder, Savi, finished or needs the owner. The kit only logs it. `savi_needs_you` is the other kind. |

There is no "turn finished" line. A turn that ends with status 0 adds nothing after the agent's own output.

Treat the logs as private. `handler.log` receives the agent's own output, which can hold chat text and file contents. `listener.log` holds only the Spawn client's status lines and the friend-request catch-up, because the kit discards the client's standard output, where Spawn documents one JSON line per event with the chat text ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17). The files in `run/failed` hold the raw events, so they hold chat text. The kit creates all of these with mode 0600.

The kit never rotates or deletes logs. To trim one, wait until no turn is running and empty it. This is safe because the kit only appends:

```bash
: > ~/.sdlca/spawn/accounts/alice/handler.log
```

You can also use `logrotate` with `copytruncate`. The kit ships no configuration for it.

## Restart and upgrade

### Check that no turn is running

A restart ends a running turn, and the cursor does not move for it. The turn then runs again after the restart. See [Cursor and replay](#cursor-and-replay). Each world's lock file is held while a turn runs, so you can test the locks:

```bash
shopt -s nullglob
for f in ~/.sdlca/spawn/run/*.lock; do
  if flock -n "$f" true; then echo "idle  $f"; else echo "BUSY  $f"; fi
done
```

`BUSY` means a turn is running for that world. Nothing printed means there are no lock files yet. You can also list the handlers with `pgrep -af sdlca-on-chat`.

### Upgrade the kit

```bash
cd ~/repos/kdtix-open/sdlca-for-spawn
git pull --ff-only
scripts/install.sh
systemctl --user restart sdlca-listener@alice.service
systemctl --user status sdlca-listener@alice.service
```

Run the last two commands once per account. Read the [changelog](../CHANGELOG.md) first. `scripts/install.sh` is safe to repeat. It never overwrites your env files, allowlist, `AGENTS.md`, `WORK-TODO.md` or prompt override. It refreshes the dependencies, writes the unit again and reloads systemd. A service that is already running keeps its old definition until you restart it. Where systemd is present, the script stops with a message, before it writes the unit, if the kit's folder path has a space or a character that is special to systemd or `sed` (letters, digits and `. _ / + @ : -` are fine). Move the kit to a plain path and run it again.

A kit that records git addresses (see [Several accounts and worlds](multi-account-and-worlds.md#what-sdlca-worlds-does)) needs one more step the first time you run it over worlds that were recorded earlier: until each world has its address, the update before a turn says `skipped/unverified` for it, runs no git, and the agent is told the clone may lag the latest push. Run `bin/sdlca-as alice bin/sdlca-worlds --apply` once for each account, under the agent's account, after the restart (or `--only @owner/world` for one world), and look at the dry run first. Recording an address changes only the registry (`worlds.json`), and never a clone's files or settings. The same run still does what `--apply` always does: it follows a rename (it points the clone's remote at the new address and moves the folder) and it clones a world whose clone is missing, and the dry run shows both (`RENAMED`, `new world`).

**Action needed if you set up an account before the examples passed `--setting-sources user`.** `scripts/install.sh` never overwrites an env file, so an account whose `SDLCA_AGENT_CMD` runs Claude Code with `-p` and has no `--setting-sources user` still runs it in print mode with the world's own `.claude/settings.json` hooks and `.mcp.json` servers loaded, and a world that someone else can push to could run a command on this machine before any tool rule applies ([the hole, and how it was tested](security-model.md#a-worlds-own-settings-can-run-code)). Open `~/.sdlca/spawn/accounts/<account>/env` for each account, put `--setting-sources user` right after `-p` in that command, and check the line with [a test by hand](configuration.md#test-a-command-by-hand). The edit applies to the next event, with no restart, because the handler reads the env file for every event. The kit does not check the command for you, and an agent tool other than Claude Code needs the same look: find out which of the folder's files it loads, and whether it asks first when it runs without a person.

If an upgrade goes wrong, check out the commit you had before (`git reflog` and `git log --oneline` list them), run `scripts/install.sh` again and restart.

### Upgrade Spawn's client

Update it the way you installed it, for example `bun add -g @spawnco/client`, then restart the listeners. Spawn's client fetches its own code from Spawn when it starts (see the package's launcher script, listed on the [npm page](https://www.npmjs.com/package/@spawnco/client), checked 2026-11-17), so a restart also picks up Spawn's changes. Spawn changes its client, its rules and its terms often. After an upgrade, send a test message and read [Rules we follow for Spawn](compliance/spawn-rules.md) for the date it was last checked.

### Change settings

Most edits to the account env apply to the next event. A change to what only the listener process reads needs a restart. [Configuration](configuration.md#when-a-change-takes-effect) has the table.

## Cursor and replay

The *cursor* is a bookmark: the newest inbox event the kit has finished handling. It lives in `accounts/alice/cursor`.

How it behaves:

- **Spawn defines the value.** It is an opaque string. Today it decodes to a time and an id. The kit uses that only to compare two cursors, and writes any value it cannot read as it is.
- **It is written after the event is handled.** That means after the agent command ends, whatever its exit status, and after a denial, a skipped duplicate, a rate-limited or lock-starved event, or a friend request. It is written atomically, through a temporary file and a rename, with mode 0600, and an empty value is never written.
- **It is not written** when the agent command is unset, when the run cap could not be checked, when the prompt could not be rendered, or when the event cannot be parsed.
- **It never moves backwards.** If two turns finish out of order, the newer cursor stays. A small lock file, `cursor.lock`, makes two handlers that finish together take turns.
- **It is read only when the listener starts.** The kit passes it to Spawn's client as `--since`, so the stream resumes after it. While the listener runs, the client tracks its own position and reconnects by itself.
- **No cursor file means "start from now".** Spawn's documentation says a stream without a starting cursor starts from the present ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17). Messages sent while the listener was down are then not delivered.

### At least once, not exactly once

Delivery is at least once. If the listener stops between the start of a turn and the cursor write, the event comes again after the next start. If the turn had not finished, the agent runs it again. That happens when:

- you restart or stop the service during a turn;
- the machine loses power, reboots or runs out of memory;
- the handler stops for any other reason before the agent command ends.

A turn that had finished is not run again: the kit records the id of every event whose agent command exited with status 0 (in `handled.ids`, the newest 500) and skips a repeat with a `SKIP` line. A failed turn is not repeated either. If the agent exits with an error or hits the time limit, the cursor still moves, and the event is kept so you can [replay it by hand](#replay-a-failed-turn).

One more limit: the cursor is a single mark. If two turns for different worlds overlap and the newer one finishes first, a crash before the older one finishes can skip the older one. Whether Spawn's client starts the next handler while an earlier one runs is Spawn's behavior, and we have not confirmed it.

### What a replay looks like

If a restart cut a turn short, `handler.log` shows two `event` lines for the same message, the second after the restart:

```text
2026-11-17T18:04:11Z event sender=@alice world=@alice/game-1
2026-11-17T18:09:40Z event sender=@alice world=@alice/game-1
```

In chat, the owner sees a second answer to the same question. Its wording differs, because the model runs again. The second turn may also repeat work the first one did, such as commits. The kit brings the clone up to date before each turn, but only by fast-forward, and a commit that the first turn made and did not push stays in the clone (the second turn's `WORLD` line then says `skipped/ahead`), so check `git log` in the clone if the result looks doubled.

If the turn had finished before the restart, the second line is instead `SKIP event <id> was already handled` and nothing runs.

### Replay a failed turn

When a turn fails, times out, is refused by the hourly cap, waits too long for its world's lock or cannot read the credentials file, the kit saves the raw event as `run/failed/<event-id>.json` in the runtime home (a name like `event-<time>` when the event has no id) and moves the cursor past it. Nothing replays it by itself. After you fix the cause, run it once more by hand:

```bash
SPAWN_EVENT="$(cat ~/.sdlca/spawn/run/failed/<event-id>.json)" bin/sdlca-on-chat alice
```

A replay counts against the hourly cap, and a turn that finishes is recorded in `handled.ids`, like any other, so replaying the same file again is skipped. The kit deletes a saved file once it is more than `SDLCA_FAILED_KEEP_DAYS` days old (30 by default; `0` keeps it forever). That happens when the next allowed event reaches the handler, so replay a saved event before then, or copy the file if you want to keep it. The `run/failed` folder is shared by all accounts, so an allowed event on any account removes every account's saved files that are more than that account's `SDLCA_FAILED_KEEP_DAYS` days old. To keep files longer, set the same larger value (or `0`) in every account's env file, or copy the file out. You can delete a file yourself sooner: it holds the chat text. The cursor only ever holds the newest event, so only a saved event can be replayed this way. To have anything else done again, send the message again.

## Timeouts and locks

| What | Value | Effect |
| --- | --- | --- |
| One agent turn | `SDLCA_AGENT_TIMEOUT`, 1800 seconds by default | After the limit the kit sends the agent command SIGTERM, then SIGKILL 10 seconds later if it is still running (`timeout -k 10`). It logs `WARN agent exited with status 124` (137 if SIGKILL was needed) and keeps the event in `run/failed`. The clock starts after the turn gets the world's lock. |
| Waiting for a world's lock | `SDLCA_LOCK_WAIT`, 3600 seconds by default | Later turns for the same world wait for the earlier one. After the wait the agent does not run, the log shows `WARN the world was busy for too long`, and the event is kept in `run/failed`. |
| Updating a world's clone | `SDLCA_REFRESH_TIMEOUT`, 60 seconds by default, for each git call. The fast-forward gets at least 600 seconds. The whole update is stopped after four times the value plus 660 seconds. | The kit stops git and everything in its process group: `SIGTERM` first, so git removes its own lock files, and `SIGKILL` 3 seconds later if something is still running. A program that put itself in another process group is not stopped. A fetch that runs out of time logs `failed/timeout`, a fast-forward that is stopped logs `failed/merge`, and the handler stopping the whole update logs `failed/timeout: the update was stopped by the handler`. The agent is told, and the turn goes on. The clock runs while the world's lock is held, before the agent starts, and it is not part of `SDLCA_AGENT_TIMEOUT`. A turn that is waiting for the lock counts the update's time against `SDLCA_LOCK_WAIT`. `0` turns the update off. |
| Agent turns per hour | `SDLCA_MAX_RUNS_PER_HOUR`, 20 by default | Past the cap the agent does not run, the log shows `RATE-LIMITED`, and the event is kept in `run/failed`. `0` turns the cap off. |
| Calls made with curl | `SDLCA_HTTP_TIMEOUT`, 30 seconds | `sdlca-api` and `sdlca-friends` give up after that. |
| `sdlca-say` | 30 seconds per request | On HTTP 429 or a 5xx answer it waits and retries up to five more times. See [Rate limits](#rate-limits-and-429-errors). |
| `sdlca-worlds` | 30 seconds for the account request, 600 seconds for each `git clone` | It stops with an error if Spawn does not answer the account request. A clone that runs out of time is reported as `clone failed`. |
| `sdlca-body` | At most 120 seconds for each call (300 for the picture's upload), however slowly Spawn answers. Waiting for a sculpt: `--wait`, 900 seconds by default, with a check every `SDLCA_BODY_POLL` seconds (10 by default) | A call that runs out is reported as no answer. A wait that runs out exits with status 3 and prints the `--job` command, and the sculpt keeps running at Spawn. See [Giving an agent a body](#giving-an-agent-a-body). |
| Restart after an exit | 5 seconds, growing to 5 minutes while it keeps failing | Set by the unit. Not for status 78. |
| Stop | 30 seconds | Then systemd forces the rest to stop. |

### The per-world lock

Each world has a lock file in `run/`, named `<world owner>__<world>.lock`. A turn holds it from just before the agent starts until the agent command ends. Two turns for the same world never run together, so two agents never edit one clone at once. Messages with no matching world share one lock per account, named `unrouted__<account>.lock` (a slash in a grouped account's name becomes an underscore). The kernel releases a lock when the process that holds it ends, so there are no stale locks to clean up. The kit lets turns for different worlds run at the same time, if Spawn's client starts them that way.

**A background process no longer holds the lock.** The agent command does not inherit the lock's file descriptor, so a development server or file watcher that the agent leaves running cannot keep the world locked. Such a process can still run on and touch the clone while a later turn works there, because the lock covers only the agent command itself. A restart of the service ends everything it started:

```bash
systemctl --user restart sdlca-listener@alice.service
```

If a later turn seems stuck, the cause is an agent command that has not ended yet, up to `SDLCA_AGENT_TIMEOUT`. A turn that waits longer than `SDLCA_LOCK_WAIT` gives up and keeps its event in `run/failed`. If you have `fuser` or `lsof`, you can name the holder, for example `fuser -v ~/.sdlca/spawn/run/alice__game-1.lock`. To avoid stray processes, tell the agent in `AGENTS.md` not to leave background processes running.

## Troubleshooting

Find the symptom, then follow the link or the fix. Every line the kit writes is listed under [Logs](#logs-and-what-they-contain).

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Service shows `failed` with `status=78` and does not restart | `SDLCA_AGENT_CMD` is unset or empty in the account env. The listener exits with 78 on purpose and the unit does not restart on 78. | Set it (see [Configuration](configuration.md#the-agent-command)), then `systemctl --user start sdlca-listener@alice.service`. |
| Service keeps restarting (after 5 seconds at first, then after longer waits up to 5 minutes) | A start-up check fails. The journal says which: `the spawn client is not installed`, `token file is not readable`, `is writable by group or others`, `unknown account`, `invalid account name`. | Fix what the message says. See [Token file and permission errors](#token-file-and-permission-errors). |
| Service keeps restarting, journal shows only `status=127` | `bun` or `spawn` is not on the service's `PATH`. Spawn's launcher needs `bun`. The message is in `listener.log`. | Add `PATH="$PATH:<folder>"` to the account env, where the folder is the output of `dirname "$(command -v bun)"` in your normal shell. Restart. |
| `listener.log` shows `self signed certificate in certificate chain` and no event arrives | A proxy or VPN that inspects TLS re-signs the traffic, and Spawn's client does not trust its certificate authority. | [Self signed certificate in certificate chain](#self-signed-certificate-in-certificate-chain) |
| I message the agent and nothing happens | Several possible causes. | [Nothing happens when I message](#nothing-happens-when-i-message) |
| `DENIED sender=... reason=...` | The sender is not allowed, or is the agent itself. | [DENIED lines](#denied-lines) |
| `WARN agent exited with status 127; event kept in run/failed` | The agent command was not found. Under systemd the `PATH` is short, so a tool in `~/.nvm` or `/opt` is invisible. | Install the tool in `~/.local/bin` or `~/.bun/bin`, or add its folder to `PATH` in the account env. Then [replay the event](#replay-a-failed-turn). |
| `WARN agent exited with status 124; event kept in run/failed` | The turn passed `SDLCA_AGENT_TIMEOUT` and was stopped. | Raise the limit or give smaller tasks, then [replay the event](#replay-a-failed-turn). Status 125 means the limit value is not valid. |
| `RATE-LIMITED ...` or `WARN the world was busy for too long` | The hourly cap on agent turns was reached, or an earlier turn held the world's lock for longer than `SDLCA_LOCK_WAIT`. The agent did not run. | Wait, or raise `SDLCA_MAX_RUNS_PER_HOUR` or `SDLCA_LOCK_WAIT`, then [replay the event](#replay-a-failed-turn). |
| `SKIP event ... was already handled` | The event came again after its turn had finished, or two copies of it arrived at the same moment (two listeners for one account will do that). | Nothing. This is the duplicate guard working. If you see it often, check that only one listener runs for the account. |
| An `event` line but no reply in chat | The agent finished without posting, or the post failed. | [The agent never answers](#the-agent-never-answers) |
| An `event` line, then nothing for later messages about the same world | A turn is still running and holds the world's lock. Later turns wait for it. | [The per-world lock](#the-per-world-lock) |
| `sdlca-say: HTTP 429`, or `curl: (22) ... error: 429` | Spawn's rate limits. | [Rate limits and 429 errors](#rate-limits-and-429-errors) |
| `clone failed (it will be tried again next run): ...` | The clone could not be made. | [Clone failed](#clone-failed) |
| `WORLD ... clone skipped/...` or `WORLD ... clone failed/...` | The kit could not bring the world's clone up to date before the turn. The agent was told, and the turn still ran. | [The clone was not brought up to date](#the-clone-was-not-brought-up-to-date) |
| I renamed a world and the agent still uses the old name | The kit only notices renames when you run `sdlca-worlds`. | [A rename is not detected](#a-rename-is-not-detected) |
| `sdlca-look` refuses, fails, or says the time limit passed, or the agent says it could not look | A world the account does not serve, another account named inside a turn, a missing browser, a join that does not finish, or a posture that does not allow the tool. | [A look does not work](#a-look-does-not-work) |
| `token file is not readable` or `writable by group or others` | File mode or ownership. | [Token file and permission errors](#token-file-and-permission-errors) |
| The same question was answered twice after a restart | At-least-once delivery: the restart cut the first turn short, so the event came again. A turn that had finished is skipped. | [Duplicate answers after a crash](#duplicate-answers-after-a-crash) |
| The agent works in `run/scratch/<account>` instead of a world's clone | No world matched the event (the log says `world=-`), or the matched world's clone folder is missing. | [How an event is matched to a world](configuration.md#how-an-event-is-matched-to-a-world), then check `worlds.json` and the clone folder. |
| `ERROR SDLCA_CREDENTIALS_FILE is not readable` | The path is wrong or the file is not readable by you. | Fix the path or mode, then [replay the event](#replay-a-failed-turn). It was kept in `run/failed`. |
| After the token was revoked or the agent unlinked, nothing works and the service keeps restarting | Spawn refuses the token. If Spawn's client exits, the unit restarts it, again and again, because it restarts after any exit except 78. The wait between restarts grows to 5 minutes. | Stop the service, then follow [Rotating a token](#rotating-a-token). |
| `ERROR event could not be parsed; skipped` | The event was not usable JSON. | Normally nothing. If it repeats, report it with the log line but without chat text. |

### Nothing happens when I message

Work down this list and stop at the first step that explains it.

1. **Is the listener running?** `systemctl --user status sdlca-listener@alice.service` should say `active (running)`. If not, use the first rows of the table above.
2. **Is the message addressed to the agent?** Spawn creates an event only for a line that mentions the agent's handle, replies to one of its lines, or messages it directly ([Spawn's short guide](https://www.spawn.co/llms.txt), retrieved 2026-11-17). In a world's chat, mention `@@alice_helper` with two at signs, in a world the agent was added to.
3. **Did the owner's own account send it?** Messages from anyone else are ignored. See [DENIED lines](#denied-lines).
4. **Read the end of `handler.log`.** A `DENIED` line explains itself. `SKIP`, `RATE-LIMITED`, `WARN` and `ERROR` lines are described in the logs table. No new line at all means the event never reached the kit. Also look at `listener.log` for the client's own messages, such as a refused connection.
5. **Check the token and the network.** `bin/sdlca-as alice bin/sdlca-api GET /api/agent/v1/me` should print JSON. An error ending in `401` means Spawn refused the token (see [Rotating a token](#rotating-a-token)). Then read `listener.log` and the journal for connection errors.
6. **Is the cursor ahead of your message?** A cursor restored from a backup or copied from another machine can be newer than your message. Stop the listener, delete `accounts/alice/cursor`, and start it again. The listener then starts from now.
7. **See what the kit would decide.** The commands in [Configuration](configuration.md#test-a-command-by-hand) show the decision and the world for a made-up event, without running an agent.

### DENIED lines

A `DENIED` line means the kit ignored a message. It sends no reply, on purpose, so nobody can probe the agent. It logs only the sender's name.

| Reason | Meaning | What to do |
| --- | --- | --- |
| `not-allowed` | The sender is neither the owner nor on the allowlist. | If it is the owner, compare `sender=` with `OWNER` in the account env: the owner is `@` followed by that name, so `@alice` for `OWNER=alice`. A sender written `@@alice` is an agent that shares the name, and is not the owner. To allow another person, run `bin/sdlca-allow spawn add alice carol`. It applies from the next message. If you do not know the sender, do nothing. |
| `self` | The sender is the agent's own account (`@@` followed by `SPAWN_USERNAME`). | Normal and harmless. The kit ignores the agent's own lines so that it cannot answer itself in a loop. |
| `unknown-sender` | The event had no usable sender: it was missing, was not written as `@name` or `@@name`, was longer than 64 characters or had odd characters. The log shows `sender=-`. | Usually nothing. If it keeps happening for messages you expect to work, open an issue and leave out chat text. |

An allowlist that is missing, is not valid JSON, or is JSON but not an object allows only the owner.

### The agent never answers

The `event` line proves the kit started a turn. Read what came after it in `handler.log`.

1. **A `WARN agent exited with status N` line.** 127 means the command was not found and 124 means the time limit. Any other number is the agent tool's own error code, so read the agent's own lines just above it. A missing provider key is common: put it in `SDLCA_CREDENTIALS_FILE`, because systemd does not read your shell profile. The event is kept, so you can [replay it](#replay-a-failed-turn) once it is fixed.
2. **No `WARN` line, so the agent ended normally, but nothing reached chat.** The agent may have printed its answer instead of posting it. Read the agent's final text in `handler.log`. If you chose a restricted posture, the agent may not be allowed to run `sdlca-say`. The allowlist rules must name the kit's real path. Test your posture as shown in [Configuration](configuration.md#test-a-command-by-hand).
3. **The post failed.** `sdlca-say` prints `sdlca-say: HTTP <code>`. A 403 can mean the agent has no standing in that room: Spawn lets an agent post in a world's room only if it builds the world, or one of its bodies stands in the room ([Spawn's short guide](https://www.spawn.co/llms.txt), retrieved 2026-11-17). A 403 on a direct message can mean the person's settings do not accept messages from the agent. Chat lines are also checked by Spawn's moderation. Spawn's API description lists these causes ([Spawn's API description](https://www.spawn.co/openapi.json), retrieved 2026-11-17). A 429 is covered under [Rate limits](#rate-limits-and-429-errors).
4. **The turn is waiting.** An `event` line with nothing after it for a long time means an earlier turn holds the world's lock. After `SDLCA_LOCK_WAIT` the turn gives up and the log says so. See [The per-world lock](#the-per-world-lock).
5. **The agent is still working.** A turn can run up to `SDLCA_AGENT_TIMEOUT`, 30 minutes by default.

### Rate limits and 429 errors

Spawn limits how fast an account can call it. For chat, the published limits are 1 to 200 characters per line, 20 lines per minute, and 5 lines in any 10 seconds into the same room, or to the same person for direct messages ([Spawn's API description](https://www.spawn.co/openapi.json), retrieved 2026-11-17). Spawn tells clients to follow its retry hint: "Follow Retry-After on 429 or 503." ([Spawn's short guide](https://www.spawn.co/llms.txt), retrieved 2026-11-17).

What the kit does and what you can do:

- **`sdlca-say: HTTP 429`.** `sdlca-say` already retries up to five more times on a 429 (and on a 5xx answer). On a 429 it waits the server's `Retry-After` value, or the `retry_after_ms` value in the answer, or three seconds when there is neither, plus one second (at most 30). A value that is not a plain number of seconds, or is negative, counts as missing. If it still fails it gives up. The lines it already posted stay, and the rest of the reply is lost. It also spaces lines 2.2 seconds apart (Spawn allows about 5 in 10 seconds) and sends at most 8 lines per reply (never fewer than 2): a longer reply ends with a line saying how many were not sent. If you still hit the limit, raise `SDLCA_SAY_PAUSE` in the account env and ask for shorter answers. The default prompt already asks for about three chunks and for long material to go into a file.
- **`curl: (22) The requested URL returned error: 429`** from `sdlca-api` or `sdlca-friends`. These do not retry. Wait, then try again. The agent should wait too. A failed friend accept is logged as `WARN friend accept failed`, and the kit tries again at the next friend-request event or the next listener start.
- **A 429 from `sdlca-worlds`** appears as `sdlca-worlds: could not read the account's worlds: HTTP Error 429`. During onboarding the account and the env file already exist at that point and the invite is used up. Do not run onboarding again. Run `bin/sdlca-as alice bin/sdlca-worlds --apply` later.
- **`sdlca-body` while it waits for a sculpt.** A 429 or a server error on one of the checks is asked about again: after the time Spawn names (at most 60 seconds), or ten seconds for a 429 that names none, and never sooner than `SDLCA_BODY_POLL` seconds. A 429 or a server error on a call that makes something (the picture, the sculpt, wearing a body, resetting it) is not retried. See [Giving an agent a body](#giving-an-agent-a-body).
- **Do not get around a limit with another account.** Spawn's terms do not allow it. See [Rules we follow for Spawn](compliance/spawn-rules.md).

### Clone failed

`sdlca-worlds --apply` prints `clone failed (it will be tried again next run): ` followed by the first 200 characters of git's error. Common causes are no network, a token that Spawn refused, no free disk space, a folder you cannot write to, or a clone that took longer than 600 seconds.

A failed clone is still written to `worlds.json`, and every later `--apply` tries it again for as long as the clone folder is missing. Until the clone exists, turns for that world run in `run/scratch/<account>`, without a warning. To retry:

1. Fix the cause. Check the token with `bin/sdlca-as alice bin/sdlca-api GET /api/agent/v1/me`.
2. Run `bin/sdlca-as alice bin/sdlca-worlds --apply`. It reports `ok` for the world and then `cloned`, or the same error again.

If a failed attempt left an empty folder at the clone path, the kit skips the clone because the path exists. Remove that folder first. `sdlca-worlds` never changes the files or settings of a clone that already exists, apart from following a rename (it points the remote at the new address and moves the folder). (The fast-forward that the handler does before a turn is separate: see [The clone was not brought up to date](#the-clone-was-not-brought-up-to-date).)

### The clone was not brought up to date

Before each turn that came from a world's own chat, the kit tries to bring that world's clone up to date by fast-forward only, and logs one `WORLD <address> clone <status>/<code>: <text>` line. If the status is `skipped` or `failed`, the agent is told that the clone may lag the latest push, and the turn runs anyway, so none of this is urgent. The text after the colon says what to look at. It is the kit's own words, a count, the name of a setting or a path, or the first line of git's error. [Configuration](configuration.md#updating-a-clone-before-each-turn) explains every code. In the commands below `<clone>` is the world's folder: the `clone_path` of the world in `worlds.json`, which is also the `Working directory` line of the agent's prompt. A state the kit does not change, such as `ahead` or `diverged`, shows up again on every turn until somebody acts. What to do:

| Code | Likely cause | Fix |
| --- | --- | --- |
| `skipped/unverified` | No git address is recorded for this world, so the kit does not trust the clone and ran no git at all (the text says `no git address is recorded for this world`). The usual cause is a world that `sdlca-worlds` recorded before it kept the address, or one whose listing gave no usable address (it must be https, with a host and no user information). The text can also say that the recorded address is not one the update accepts: someone edited `worlds.json` by hand. | Run `bin/sdlca-as alice bin/sdlca-worlds --apply` under the agent's account, with `--only @owner/world` for one world (see [Several accounts and worlds](multi-account-and-worlds.md#what-sdlca-worlds-does)). It records the address from Spawn's listing, which changes only `worlds.json` (the same run also follows a rename and clones a missing clone, so look at the dry run first). It prints a `WARNING` for a world whose listing gives no usable address: then there is nothing to record, and the clone is not updated until Spawn gives one. |
| `skipped/ahead` | The clone has commits that were never pushed, from an earlier build or a push that was refused. (If the world went back to an older commit, the update says `diverged` when it can tell.) | Look: `git -C <clone> log --branches --not --remotes`. If they are yours, push them, or discard them yourself. If you do not know them, find out whether the world went back before you push: a push would bring those commits back. The kit never does either. |
| `skipped/diverged` | The clone and the world both have commits the other lacks. The world may also have rewritten its history by force, or moved back to an older commit (the text says so). | Look at both sides: `git -C <clone> log --oneline --left-right HEAD...@{upstream}`. A line that starts with `<` is a commit only the clone has, and `>` a commit only the world has. To keep the clone's commits, run `git -C <clone> rebase --fork-point origin/main` (a plain rebase would bring back commits that the world removed), then push without force. If the clone holds no work of its own, `git -C <clone> fetch` and then `git -C <clone> reset --hard @{upstream}` makes it match the world. That discards the clone's commits and uncommitted changes, so copy out anything you want first, and do it between turns. |
| `skipped/detached`, `skipped/no-upstream` | No branch is checked out, or the checked-out branch follows no remote branch (or has no commits, or follows a remote that has no address in the clone's settings, as `branch.<name>.remote = .` does). | Check out the branch that follows the world, for example `git -C <clone> switch main`, or run `git -C <clone> branch --set-upstream-to=origin/main`. |
| `skipped/untrusted` | Either the clone's remote is not the address recorded for the world (the text says `the clone's remote origin points to host a, not to host b, where the address recorded for this world is`, or that both point to the same host but the scheme, port or path differs, or that the remote has more than one address, or that it points to `an address that is not a plain URL`, which is what an ssh address, a local path or an address with user information is), or the text names a setting in the clone's own git configuration that can run a program, send git or the token elsewhere or change whom it trusts (shown as `git config --local --list` prints it, so you can copy it, and including a credential helper scoped to any host but the recorded one, a promisor remote such as `extensions.partialclone` or `remote.<name>.promisor`, and a remote section whose name is an address, which the text shows as `remote.(a name that is not plain).<key>`: find it with `git -C <clone> config --local --list`), or a path under `.git/logs` or `.git/refs` that is a link, or the folder is a symbolic link, or its `.git` is a symbolic link or a file that points elsewhere. | If you did not set it, someone with write access to the clone did: look at `git -C <clone> config --local --list` and at `.git/config.worktree`, and remove the setting with `git -C <clone> config --local --unset-all <key>` (a link is removed with `rm`, after you have looked at where it points). For a remote that differs, find out which side is right before you change anything: the record is the address Spawn listed the last time `sdlca-worlds --apply` visited the world (`git` in `worlds.json`), and Spawn's listing is the truth. If the remote is wrong, put it right with `git -C <clone> remote set-url origin <the recorded address>`. If Spawn moved the world and the record is stale, run `bin/sdlca-as alice bin/sdlca-worlds --apply` and then set the remote to the new address. If you set a setting on purpose, the clone stays unupdated until you remove it. A clone that you made yourself (the kit uses it as it is) is updated only when its remote is the recorded address and it carries the kit's credential helper, so one whose remote is ssh, git or a local path is `untrusted` too: point its `origin` at the recorded https address. |
| `skipped/not-git` | The folder is missing, or is not a clone (or is a subfolder of another repository). The agent then ran in `run/scratch/<account>` if the folder was missing. | Run `bin/sdlca-as alice bin/sdlca-worlds --apply` to clone again. Remove an empty leftover folder first (see [Clone failed](#clone-failed)). |
| `failed/fetch` | Git could not fetch. Read the text. Common causes: no network; a token Spawn refused ([Token file and permission errors](#token-file-and-permission-errors), [Rotating a token](#rotating-a-token)); the branch the clone follows no longer exists on the world; the account lost standing ([When standing is lost](multi-account-and-worlds.md#when-standing-is-lost)). `could not read Username ... terminal prompts disabled` means the clone has no credential helper, for example because it was not made by `sdlca-worlds`. | Fix what the text says. (A clone whose remote is not the recorded https address never gets this far: it is `untrusted` before anything is fetched.) For a clone without the helper, move it aside and run `bin/sdlca-as alice bin/sdlca-worlds --apply` to make it again, after saving any work in it. |
| `failed/timeout` | A git call other than the fast-forward took longer than `SDLCA_REFRESH_TIMEOUT` seconds (a stalled network, usually), or the handler stopped the whole update. | Raise `SDLCA_REFRESH_TIMEOUT` if the network is just slow. |
| `failed/merge` | Something in the clone stopped the fast-forward: a file you changed, or an untracked or ignored file that the update would overwrite; a merge in the clone that is unfinished; a lock file from an earlier git command that was cut short (the text names it, for example `.git/index.lock`); or the world holds a path that git refuses to check out (the text says `invalid path`); or the fast-forward ran out of time and was stopped part way (the text says so). | For a file in the way, commit, stash or move your change, then the next turn updates the clone. For a merge that is unfinished, finish or abort it. For a lock file, check that no git is running in the clone and remove the named file. For a path that git refuses, someone has to remove it from the world, and until then the clone is not updated. For a stopped fast-forward, see below. |
| `failed/error` | Git is not installed or not on `PATH` (under systemd the `PATH` is short: see [Troubleshooting](#troubleshooting)), git is older than 2.29, the branch points to a commit that git cannot read (a damaged clone), `lib/refresh.py` is missing, or the update crashed. | Install or upgrade git, or fix `PATH`. A crash prints its traceback in `handler.log`, in the lines just above the `WORLD` line. If the file is missing, repeat the upgrade (`git status` in the kit's folder). |

**A fast-forward that was stopped.** If `failed/merge` says the fast-forward ran out of time, the branch did not move, but some files may already have been replaced, and `git status` shows them as changes you made. Do not commit them. If the clone holds no work of your own, put the files back with `git -C <clone> checkout -- .`, then look at what the update had already added: `git -C <clone> clean -n` lists untracked files, and `git -C <clone> clean -f` removes them (only when the list holds nothing of yours). The next turn then fast-forwards. If you have work there, compare with `git -C <clone> diff` first. The cause is a file filter that hangs or a disk that stalls, so find it before the next update, or the same thing happens again.

To run the update by hand, when no turn is running, use `bin/sdlca-as <account> python3 -I -B lib/refresh.py <clone> <git address>` from the kit's folder (`sdlca-as` gives it the account's environment, which it uses to recognize the clone's credential helper; the address is the `git` field of the world in `worlds.json`, and without one, or with `-`, the answer is `skipped/unverified`). It prints one line, and it is the real update, so a clone that is behind is fast-forwarded. `SDLCA_REFRESH_TIMEOUT=0` in the account env turns the update off for that account, and nothing is logged then, even if `lib/refresh.py` is missing.

### A rename is not detected

The kit follows a world's id, not its name, but it learns about a rename only when `sdlca-worlds` runs. That happens at onboarding and when you run it. Nothing runs it in the background.

```bash
bin/sdlca-as alice bin/sdlca-worlds            # shows [dry-run] RENAMED @alice/old -> @alice/new
bin/sdlca-as alice bin/sdlca-worlds --apply    # moves the clone and remembers the old name
```

Before you run it, events that carry the world's app id still find the right clone. Events that carry only the new address may run in `run/scratch/<account>`, because the registry still has the old address. If an agent holds the world's lock when you run `--apply`, the kit updates the remote and the registry but leaves the folder where it is, prints a warning, and moves the folder on a later run (the entry shows `pending_move` until then). If the sync reports a new world instead of a rename, Spawn gave the world a new id, so the kit treats it as a different world. See [Several accounts and worlds](multi-account-and-worlds.md).

### A look does not work

`sdlca-look` joins a world, saves one screenshot and leaves (see [Seeing a world with sdlca-look](configuration.md#seeing-a-world-with-sdlca-look)). Start with the check. It joins nothing, uses no network and starts no program of Spawn's client, and says `ok` or `MISSING` with a fix for each thing a look needs:

```bash
bin/sdlca-look --check alice
```

It exits 1 when something is missing. Do what each `MISSING` line says, then run it again. The `note` line about the browser is not a check: the Spawn client starts its own browser for a look, and this tool cannot see it. If a look fails at the join, run `spawn client join <world> --render cpu` by hand once and read what the client says (its output can hold join credentials, so do not paste it).

To try a look by hand, as a person (the world must be one the account serves, and you will see the agent's body come and go in the world, as everyone in the room does):

```bash
bin/sdlca-look alice @alice/game-1 /tmp/look-test.png 8
```

It prints `saved <path>` when the picture is written, and then it leaves. Read the picture yourself before you trust what the agent says about one. The output must be a name that does not exist yet: the tool never replaces a file, so pick a new name for every look.

If you join by hand instead (`spawn client join <@owner/world> --render cpu`), the body stays in the world, visible to everyone in the room and counted against the account's body budget, until it ends: run `spawn client leave` afterwards (`spawn client status` shows the sessions that are live, and `--name <session>` picks a session that you named).

To see that the agent is **allowed** to run the tool, which `--check` does not show, ask the agent for a look through your own command, as the account (it uses your provider account and may cost a little, and the body appears in the world):

```bash
bin/sdlca-as alice bash -c 'printf "Run %s/bin/sdlca-look alice @alice/game-1 /tmp/try-look-1.png 8 and say whether it worked.\n" "$SDLCA_CODE_DIR" | bash -c "$SDLCA_AGENT_CMD"'
```

Use a new name for the picture every time. If the agent says the tool was not permitted, the allow rule is missing or does not match how the agent wrote the command: see the posture in [Configuration](configuration.md#the-postures).

| What it says | What it means | What to do |
| --- | --- | --- |
| `this account (alice) does not serve @owner/world` | The address is not listed for the account in `worlds.json`, not even as an old address. A tool that joins as the account only joins a world it serves. | Run `bin/sdlca-as alice bin/sdlca-worlds --apply --only @owner/world` (the account must have standing in the world), then try again. |
| `inside an agent turn only the turn's own account (alice) may be named` | The agent named another account. The handler sets `SDLCA_TURN_ACCOUNT` for the agent command, and the tool refuses any other name. | The prompt tells the agent its own account name. Nothing to fix unless it keeps happening: then read the agent's lines in `handler.log`. |
| `every picture was blank when the time limit of N seconds ... ran out` | The software renderer draws nothing until the world has loaded, and this world had not finished loading in the time the look had (a look waits for it and tries again every `SDLCA_LOOK_POLL` seconds). The body left. | Raise `SDLCA_LOOK_TIMEOUT` (a heavy world on a slow machine can need several minutes). A `--render gpu` join would be faster on a machine whose graphics card the client can use; the tool does not offer it yet. |
| `the join did not finish within the time limit of N seconds` or `the screenshot did not finish within the time limit` | A look has `SDLCA_LOOK_TIMEOUT` seconds (default 240) for the join and the pictures together. The body left and the browser was stopped. | Run the join by hand as the message says to read the client's own message (it can print join credentials, so keep that output to yourself). The client fetches its own code the first time it runs and keeps it in `~/.cache/spawnco-client/`, so the first join can be slow. Raise `SDLCA_LOOK_TIMEOUT` only if the join is just slow. |
| `join failed; run 'spawn client join ...' by hand` | The client refused or failed. The tool does not repeat the client's message, because it can hold join credentials. | Run the command it names, by hand. A refusal for a seat or a budget is Spawn's limit on bodies: Spawn's figure for an unlinked agent account is two at a time, and a linked account's may differ ([the rules we follow](compliance/spawn-rules.md)), so wait for the other to leave. |
| `the join did not print a page address`, or `printed more than one page address` | The client's `page :` line is missing (the body has no eye, or the client changed its output), or there were two with different addresses. | Run the join by hand and look for the `page :` line. If the client changed its wording, the tool needs a change: open an issue and leave out any credential. |
| `the page address names port N, which a program that was already running ... holds` | The address does not belong to a browser that this join started, so the tool refused to attach to it. | Normally nothing. It protects a browser or a server of yours that listens on a local port. If it keeps happening on a quiet machine, report it. |
| `a browser that the join started is still running (process ids: ...)` | After `leave`, the tool could not stop something the join left behind. | Stop those processes by hand. A join that hangs before it prints its page line is the case the tool cannot see into: it finds the browser by the page's port, which it learns from that line, so it then relies on `spawn client leave` to end the browser. After such a failure, look for a headless Chromium that is still running (`ps -ef | grep -i chrom`) and stop it by hand. |
| `something still answers at ... and this look cannot see which program holds it` | Something still accepts connections at the page's port, and the tool cannot tell which program (it needs `/proc`, so it is Linux only, and it sees only your own programs). | If it is a browser the join started, stop it by hand. |
| `the output must be a .png under /tmp ...`, `the output must be an absolute path` | The output path rules (an absolute path to a `.png` under `/tmp`, `$TMPDIR` or `$SDLCA_SPAWN_HOME/shots`, no `..`). | Use a path that follows them. |
| `refusing to write to <path>: something is there already` | The output must be new: a file, a link or a folder already has that name. The tool never replaces anything. | Give a name that does not exist yet. |
| `could not save the picture at <path>` | Something appeared at the path while the look ran (a link, a file) or its folder was replaced by a link. The picture is made in a private folder and placed at the path at the very end, as a new file that never follows a link, so nothing was written through it. | Look at what is at the path, then look again under a new name. |
| `the screenshot tool finished but made no picture` | The screenshot tool said it worked and left no file. | Run the look by hand and read the tool's own lines above this one. |

When the agent says a look was refused or not permitted, the cause is usually the posture: the agent's command must allow the tool (`"Bash($SDLCA_CODE_DIR/bin/sdlca-look *)"`, as in the read-only with sight example). Test it by hand as shown in [Configuration](configuration.md#test-a-command-by-hand). The prompt tells the agent to say so under `Handler notes:` and to work from the files in the clone.

### Token file and permission errors

Every command that takes an account checks its files first.

| Message | Cause | Fix |
| --- | --- | --- |
| `token file is not readable: <path>` | The file is missing, the path in `SPAWN_TOKEN_FILE` is wrong, or your user cannot read it, for example because it was made with `sudo` and belongs to root. | Run `ls -l <path>`. Fix the path in the env file, or `chown "$USER" <path>` and `chmod 600 <path>`. |
| `<path>/env is writable by group or others; run: chmod 600 '<path>/env'` | Another user or group can write to the env file. The kit reads that file as shell, so it refuses. | Run `chmod 600 <path>/env`. |
| `unknown account: <path>/env not found (create one with sdlca-onboard for an agent, or sdlca-token init for a personal token)` | The account name is misspelled, or the command is looking in the wrong runtime home. A service does not see variables from your shell, so a custom `SDLCA_SPAWN_HOME` must be set in the unit (see [Systemd unit settings](#systemd-unit-settings)). | Fix the name or set the variable. |
| `invalid account name '<name>' (words of lowercase letters, digits, underscore or hyphen, starting with a letter or digit; at most one slash, as in group/name)` | The name has other characters or capitals, or more than one slash. | Use the folder name exactly as it is under `accounts/`, with `group/name` for a grouped account. |
| `OWNER is not set in <path>/env` (or `SPAWN_USERNAME`, or `SPAWN_TOKEN_FILE`) | A required line is missing. | Add it. See [The account env file](configuration.md#the-account-env-file). |

The kit does not check the token file's own mode. Keep it at 0600 anyway. If you move the token file, leave a symbolic link at the old path. Each clone's git credential helper reads the token from the path that was current when the clone was made.

### Duplicate answers after a crash

This is at-least-once delivery working as designed. A stop, restart or crash during a turn stops the cursor from moving, so the turn runs again. A turn that had already finished is skipped (look for a `SKIP` line). See [Cursor and replay](#cursor-and-replay). There is nothing to repair. Check `git log` in the world's clone if the agent may have repeated work. To avoid it, restart the listener only when [no turn is running](#check-that-no-turn-is-running).

### Self signed certificate in certificate chain

**Symptom.** The Spawn client refuses the connection with `self signed certificate in certificate chain`, and no events arrive. Look in `accounts/alice/listener.log`.

**Cause.** A proxy or VPN that inspects TLS is re-signing the traffic with its own certificate authority, and the client does not trust it.

**Effect.** The listener keeps retrying by itself, so it does not stop, but it receives nothing until the client trusts the proxy. This is a reliability problem. Do not switch certificate checking off: the connection carries the account's token. Trust only an authority that really belongs to your organization.

**Remedy.** Make the client trust the proxy's certificate authority. For Bun, the usual setting is `NODE_EXTRA_CA_CERTS`, pointing at a file that holds the authority's certificate. Put it in the account env, which the listener passes on to the client, and restart the listener:

```bash
NODE_EXTRA_CA_CERTS=/home/you/proxy-ca.pem
```

**We have not verified that Bun honors `NODE_EXTRA_CA_CERTS`.** Check Bun's documentation for your version before you rely on it, and send a test message afterwards. The kit's own `curl` and `git` calls use your system's certificate store rather than this setting, so they may need the authority added there.

## Rotating a token

Rotate when the token may have leaked, when Spawn refuses it (an error ending in `401`), when you lost the token file, or on a schedule you choose. Spawn shows a token once and keeps only a hash of it, so you cannot read it back. The way to a new token is a reconnect code. The owner creates it on the agent's row in their agents list in Spawn. It works once, expires after ten minutes, and gives the same account a new token while it revokes the older ones ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17).

The kit has no rotate command. (For a personal token that you made by hand, revoke it on Spawn's settings page, make a new one, stop the listener if one runs, and store it with `bin/sdlca-token add <account>`, which replaces the old token file. See [Grouped accounts and sdlca-token](configuration.md#grouped-accounts-and-sdlca-token).) For an agent account, these steps use Spawn's own client. **The `--reconnect` option comes from Spawn's documentation and we have not run it. Run `spawn login --help` first and use what your version says.**

```bash
# 1. Stop the listener
systemctl --user stop sdlca-listener@alice.service
# 2. The owner makes a reconnect code in Spawn. Then, within ten minutes:
(cd ~ && SPAWN_TOKEN_FILE=~/.sdlca/spawn/accounts/alice/token spawn login --reconnect sbk_<code>)
# 3. Keep the file private
chmod 600 ~/.sdlca/spawn/accounts/alice/token
# 4. Check the new token
bin/sdlca-as alice bin/sdlca-api GET /api/agent/v1/me
# 5. Start the listener
systemctl --user start sdlca-listener@alice.service
```

`spawn login` adds a git credential helper for Spawn's git host to your global git configuration. `sdlca-onboard` removes it again, but this manual path does not. Look, and remove it if it was not there before you started:

```bash
git config --global --get-all credential.https://git.spawn.co.helper
git config --global --unset-all credential.https://git.spawn.co.helper
```

Run the second command only if the first one printed something you did not set yourself. If you had your own helper under that key, leave it.

Clones need no change, because their helper reads the token file each time git runs.

To stop a leaked token right away, you can revoke it, then reconnect as above. Spawn documents `POST /api/agent/v1/token/revoke`, which takes no body, ends the calling token everywhere (git included) and leaves the account in place. The owner can also revoke tokens and unlink agents on Spawn's settings page for tokens ([Spawn's API description](https://www.spawn.co/openapi.json), retrieved 2026-11-17). We have not run the call:

```bash
bin/sdlca-as alice bin/sdlca-api POST /api/agent/v1/token/revoke
```

If the token file is lost and the agent is linked, the owner's reconnect code is the way back. Spawn says an unlinked agent has nobody to reconnect it ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), read 2026-11-17), so [back up](#backups) the token file.

## Adding an account

Every owner gets their own agent account, token, cursor, logs and listener. The owner makes the invite, as in [Getting started](getting-started.md#step-2-create-the-agent-account).

```bash
bin/sdlca-onboard --owner bob --invite sbk_<code-from-the-prompt> --username bob_helper
${EDITOR:-nano} ~/.sdlca/spawn/accounts/bob/env          # set SDLCA_AGENT_CMD
systemctl --user enable --now sdlca-listener@bob.service
```

- The agent's username must be new on Spawn. Use a different one for each account.
- `sdlca-onboard` is for agent accounts made from an invite. To keep a token that a person made by hand, use `bin/sdlca-token` instead, with a one-word or `group/name` account name (see [Grouped accounts and sdlca-token](configuration.md#grouped-accounts-and-sdlca-token)). Each person should make and keep their own token.
- The allowlist, `worlds.json`, `AGENTS.md` and `WORK-TODO.md` are shared by all accounts in one runtime home. Extra senders are listed per owner, so carol can be allowed on alice's account and not on bob's. Each world in `worlds.json` lists the accounts that can reach it.
- Accounts share one Linux user, so an agent turn for one owner can read the other owner's token and notes. If owners must be kept apart, run each in its own Linux user account, each with its own runtime home. See [Security model](security-model.md).
- One account per person who consents. Do not create extra accounts to get around Spawn's limits.

## Removing an account

The kit has no remove command. For the owner `bob`:

1. Stop the listener: `systemctl --user disable --now sdlca-listener@bob.service`.
2. If you want the token to stop working, revoke it first (see [Rotating a token](#rotating-a-token)), or ask the owner to unlink the agent in Spawn. The owner's agents list has an unlink action ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17).
3. Remove the extra senders you allowed for that owner: `bin/sdlca-allow spawn remove bob carol`, once for each name. `remove` matches the entry exactly as stored (`carol` and `@carol` are two entries), so run `bin/sdlca-allow list` first and remove each spelling you see. An empty entry for `bob` stays in the file and does no harm.
4. Delete the account folder, which holds the token, env, cursor, `handled.ids`, `runs.log` and logs: `rm -rf ~/.sdlca/spawn/accounts/bob` (for a grouped account, the `<group>/<name>` folder). Also delete its scratch folder, `~/.sdlca/spawn/run/scratch/bob`. Saved events in `~/.sdlca/spawn/run/failed` are not sorted by account and hold chat text, so delete the ones you do not need.
5. Decide about the clones. `worlds.json` is shared and keyed by world, so leave its entries unless you also delete the clones. Each entry keeps the account's name in its `accounts` list, which is harmless. Check each clone for unpushed work first (`git -C <clone> status`).

This does not delete the agent account on Spawn. That is done in Spawn.

## Putting the agent's body in a world from chat

The owner can mention the agent with `/spawn` (stays for `SDLCA_PRESENCE_TTL` seconds, 3600 by default), `/spawn ttl 600` (10 to 14400 seconds) or `/leave`. The handler runs `spawn client join <the world the message came from> --render none` itself, so no agent turn is started, and a second `/spawn` replaces the first. Only the owner's line counts, and only when it is exactly the command. It needs a world the account serves (a direct message has none). The log has a `PRESENCE` line; the client's own output is thrown away because a join can print a credential. Spawn's client always has a time limit, which is why `/spawn` alone is not forever.

## Giving an agent a body

This section is the short version. [Giving an agent a body: day zero and day n+1](giving-an-agent-a-body.md) tells it as two stories, with the output you will see.

An agent that is in a world is a player there, and Spawn dresses a player in a body. A new agent account has Spawn's default body. `sdlca-body` makes a body of your own from a picture and puts it on the agent, or puts a body that already exists on an agent. You run it yourself, from your own shell. It is not for the agent: it spends the linked person's money and puts a picture on Spawn (see [Why an agent must not run sdlca-body](security-model.md#why-an-agent-must-not-run-sdlca-body)).

You need the kit account of the agent (the name you give `sdlca-as`), which must be an agent's own account that is linked to a person, because that person pays for the sculpt. You also need a picture of the body: PNG, JPEG or WebP, at most 4 MB. Use only a picture you have the right to upload. Spawn reviews it like any other upload, Spawn's terms apply to you (rules 22 and 23 of [the rules we follow for Spawn](compliance/spawn-rules.md)), and the body is shown to everyone who sees the agent in a world. Spawn decides whether it can sculpt the picture, and says so if it cannot.

1. **Look first.** Without `--apply` the tool changes nothing and only reads from Spawn. It checks the picture on your machine and prints the plan: the agent, who pays, the picture (its type, size and a fingerprint), whether the picture carries embedded text or camera data, and whether any bytes follow the end of the picture (a phone's "motion photo" keeps a video there). Whatever the picture carries is sent along as it is.

   ```bash
   bin/sdlca-body alice ~/Pictures/agent-body.png
   ```

2. **Do it.** Add `--apply`. The tool uploads the picture as a draft, starts the sculpt (the step that is paid for), waits for it, wears the result and reads the agent's profile back to check that it names a body. The sculpt takes minutes (about four, in the one real run we did). The tool prints the sculpt's id as soon as it starts.

   ```bash
   bin/sdlca-body alice ~/Pictures/agent-body.png --apply
   ```

3. **If the wait runs out** (after 15 minutes unless you pass `--wait <seconds>`, from 1 to 7200), or if you stop the tool with Ctrl-C, close its terminal or send it a stop signal, the sculpt keeps running at Spawn and nothing is lost. The tool exits with status 3 after a wait that ran out, or 130 after a stop, and prints the command that carries on. It waits for that same sculpt and wears it, and makes nothing again. Every other way the run can stop once the sculpt has started, such as a refused or failed wear, prints that command too:

   ```bash
   bin/sdlca-body alice --job <the id the tool printed> --apply
   ```

4. **Take it off.** After the upload the tool prints a character id (and again, as a ready command, when the body is worn). This puts the agent back on the default body:

   ```bash
   bin/sdlca-body alice --reset <the character id> --apply
   ```

5. **Share the body with another agent, without a new sculpt.** The costly step happens once, so what is left is to get the model onto the other agent. Spawn's guide describes one road: carry the model file to Spawn, then wear the address that the carry answers. We tried it on the real Spawn on 2026-11-20, with the agents of two different people, and the result is mixed:

   - **Worked: the carried address as a body for one join.** The second agent stood in a world wearing the shared body. Spawn's client takes the address with `--body`, and it needs the whole https address, not the `/cdn/...` form.
   - **Did not work: the same address as the agent's own profile body.** `sdlca-body --wear` was refused with `body_not_carried`, both for the address printed after a sculpt and for an address that `--carry` printed after a full carry through a world where the agent is an editor. Spawn's published description says the body must be "your own carried" file, and we have not found out what more it needs. One untried idea is a world that the agent owns, which would mean making a world under the agent's handle. Until that is known, a second agent gets a body on its profile by a sculpt of its own.

   ```bash
   # 1. get the model's file (the address is the one printed after the sculpt)
   curl -L -o body.glb https://www.spawn.co/magic/character-robot-character-ABCD1234.glb
   # 2. carry it to Spawn from an agent that is an editor of a world; it prints the address to use
   bin/sdlca-body bob --carry body.glb --world @bob/den --apply
   # 3. any agent can then stand in a world wearing it for one join (do not paste what the join prints: it can hold a credential)
   bin/sdlca-as bob spawn client join @bob/den --body https://www.spawn.co/cdn/value.<hash>.glb --ttl 600
   # 4. to try the profile body, which Spawn refused in our test
   bin/sdlca-body bob --wear https://www.spawn.co/cdn/value.<hash>.glb --apply
   ```

   `--carry` takes a rigged glTF binary (a `.glb`, at most 25 MB) and a world where the agent is an editor, an admin or the owner. A file up to 4.4 MB goes in one call. A bigger one goes by Spawn's road for large files: a request for a storage address, a PUT of the bytes to that address (another host, which never gets the token), and a call that tells the asset door where they are. The signed storage address is never printed. Spawn may answer that it is still placing the file, and the tool asks again. Carrying the same file twice costs nothing. The dry run reads from Spawn and sends nothing.

Things to know:

- **A second paid sculpt is what the tool is built to prevent.** Just before it asks for the sculpt, the tool records it in `body-sculpt.json` in the account's folder (see [Files in the runtime home](configuration.md#files-in-the-runtime-home)). While that file exists, a picture run for the account, a dry run too, refuses and says what to do: carry on with `--job` when the id is known, or look at your characters on spawn.co when it is not. The file is removed when the body is worn or the sculpt has failed. To start over on purpose, delete it.
- **When the answer to the request for the sculpt is lost or unclear**, because the connection dropped, Spawn answered with a server error, or gave an answer without a usable id, or you pressed Ctrl-C at that moment, the tool says that Spawn may have started the sculpt anyway and keeps the record. Look at your characters on spawn.co first, so that the sculpt is not made, and paid for, twice. A refusal (a status such as 400 or 403) means that nothing started, and the record is removed.
- **Only the checks on a running sculpt are asked again**, every `SDLCA_BODY_POLL` seconds (10 unless you set it), after the time Spawn names when it limits the rate (at most 60 seconds), and after ten seconds when it names none. No call lasts longer than two minutes (the picture's upload, five), and a check is cut short at the end of `--wait`.
- **Carrying puts the file where anyone who knows its address can fetch it.** The file is stored with that world's assets under a name that is its own hash, Spawn screens it, and the tool says so in its plan. Carry only a file you may upload.
- **A ready-made body ships with the kit.** `templates/bodies/kdtix-agent-body.glb` needs no sculpt: carry it with `--carry` and join with `--body`, as in step 5. Its folder's README says where it came from.
- **A body is shown while the agent is in a world.** The kit's agent is in a world only while `sdlca-look` takes a screenshot, so that is when you can see it. Staying in a room is planned and not built.
- **The picture is sent exactly as it is, under a fixed file name.** The name of your file and the folders it sits in are not sent. The tool decides what a file is from its first bytes, so a file that only starts like a picture is accepted: the plan names what follows the picture, but read what you send.
- **What the messages mean.** `this is not an agent account`: you named an account that holds a person's token. `generation lane ... closed`: Spawn will not make a body for this agent, and the words after it are Spawn's. `Spawn did not accept the picture as a draft`: Spawn's review refused it, and nothing was sculpted. `the sculpt did not finish`: Spawn could not make a body from that picture, nothing was worn, and you can try another picture. `body_not_carried`: Spawn did not take that address as the agent's own body (see step 5 above).

## Backups

The runtime home holds the only copy of each token, and the only copy of your settings. Spawn shows a token once.

**Back up:** `accounts/<account>/token` and `env`, `allowlist.json`, `worlds.json`, `AGENTS.md`, `WORK-TODO.md`, `handler-prompt.md` if you made one, any systemd drop-ins you wrote, and the credentials file you point `SDLCA_CREDENTIALS_FILE` at.

**Skip:** logs (including `runs.log`), `handled.ids`, the `run/` folder (lock files, scratch folders and saved events) and `shots/`. Leave out the `cursor` too. A restored old cursor makes the kit replay events, and no cursor starts from now.

**Clones:** Spawn's git remote holds what was pushed. Unpushed commits and uncommitted changes live only in the clone. Check with `git -C <clone> status` and `git -C <clone> log --branches --not --remotes`.

```bash
( umask 077; tar -czf ~/sdlca-backup-$(date +%F).tar.gz \
    --exclude='*.log' --exclude='handled.ids' --exclude='cursor' --exclude='run' --exclude='shots' \
    -C ~ .sdlca/spawn )
```

The archive contains tokens. Treat it like a password file: encrypt it with a tool you trust before you copy it off the machine, and never put it in a repository.

To restore, extract it into your home folder, run `chmod -R go-rwx ~/.sdlca`, run `scripts/install.sh`, and start the listeners. A restored token only works if it was not rotated or revoked since the backup. Then check it with `bin/sdlca-as <account> bin/sdlca-api GET /api/agent/v1/me`.

## Uninstalling

The short version for one trial account is in [Getting started](getting-started.md#remove-everything). The full version:

```bash
# 1. Stop every listener and stop it starting at login
for a in $(ls ~/.sdlca/spawn/accounts); do systemctl --user disable --now "sdlca-listener@$a.service"; done   # grouped accounts have no listener
# 2. Back up anything you want to keep (see Backups)
# 3. Delete the clones you no longer need, after checking for unpushed work
grep clone_path ~/.sdlca/spawn/worlds.json
# 4. Delete the runtime home, the unit and the kit
rm -rf ~/.sdlca/spawn
rm -f ~/.config/systemd/user/sdlca-listener@.service
systemctl --user daemon-reload
rm -rf ~/repos/kdtix-open/sdlca-for-spawn
```

Then, where they apply:

- `loginctl disable-linger "$USER"`, only if you turned lingering on just for the kit.
- Remove Spawn's client the way you installed it, for example `bun remove -g @spawnco/client`. It has its own files (for example `~/.spawn` and `~/.cache/spawnco-client`), which are not the kit's.
- In Spawn, ask each owner to unlink the agent, so the account does not stay linked to a person's allowance.

Your global git configuration needs no clean-up, because the kit never leaves anything in it. If you ever ran `spawn login` by hand, check the helper as shown under [Rotating a token](#rotating-a-token).

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
