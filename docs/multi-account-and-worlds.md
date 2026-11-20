# Several accounts and worlds

This page is for someone who runs the SDLCA agent kit for more than one person or account, or who wants to know where the kit keeps its files and what happens to the local clones when a world is renamed, lost or moved. You will learn what an account is, how to keep several tokens together in a group, how the world registry and the clones work, and how to avoid the mistakes that are easy to make. It was checked against the kit's code on 2026-11-17, and its parts about the git address and `sdlca-look` on 2026-11-18.

The kit is an unofficial community project. It is not made, reviewed or supported by Spawn. For the first install, see [Getting started](getting-started.md). For the bigger picture, see [Architecture](architecture.md).

## Accounts

In the kit, an *account* is a token plus an env file. It is a folder, `accounts/<account>/`, under the runtime home, and it has its own cursor and logs and, when its name is one word, its own listener. Three names are easy to mix up:

| Name | Where it is set | What it is | Example |
| --- | --- | --- | --- |
| Account | The folder name, and the argument of every `sdlca-*` command | The kit's label for one token and its settings. One word, or `group/name` (at most one slash). Each word is lowercase letters, digits, underscore or hyphen, starts with a letter or digit, and is at most 64 characters. | `alice`, `sdlca-for-spawn` or `sdlca-for-spawn/alice` |
| `OWNER` | The account's env file | The Spawn user who may command this account. Also the key for extra allowed senders in `allowlist.json`. | `alice` |
| `SPAWN_USERNAME` | The account's env file | The Spawn username the token belongs to. The kit ignores messages from `@@<SPAWN_USERNAME>`, which prevents reply loops, and uses the name in the clones' credential helper. | `alice_helper` |

### One account per person

The usual setup is one account per person the agent works for. `sdlca-onboard --owner alice ...` creates the account `alice`: an agent account on Spawn, linked to `alice` by alice's invite code, with its token in `accounts/alice/token`. It always names the account after the owner. Do this once for each person, and start one listener for each.

All accounts on one machine share one runtime home. That means they share:

- `worlds.json`, the registry of worlds and clones;
- `allowlist.json`, where the extra senders are listed under each owner's name;
- `AGENTS.md` and `WORK-TODO.md`, the notes every agent turn reads and writes;
- `handler-prompt.md`, if you made one;
- one Unix user, so every agent turn can read every account's token file.

This has a consequence you should decide on. A note the agent writes in `WORK-TODO.md` for alice's turn is read by bob's next turn, and could appear in bob's chat. If your owners should not see each other's work, or do not trust each other, give each owner a separate runtime home (set `SDLCA_SPAWN_HOME`) or, better, a separate Unix user. See [Security model](security-model.md#hardening-checklist).

A word about Spawn's terms. [Spawn's terms](https://www.spawn.co/terms-of-service) (read on 2026-11-17) restrict letting other people use your account and acting as an intermediary or service bureau. We have not asked Spawn how that applies to one machine that serves several people. The safe default is that each person runs the kit for their own accounts. See [the rules we follow for Spawn](compliance/spawn-rules.md).

### A coordinator account

An account does not have to be one person's agent. Nothing in the kit insists that the token was made by `sdlca-onboard`, or that the account is named after its owner. That allows a *coordinator account*: one account, named for example `sdlca-for-spawn`, whose token a person minted for their own scripts, run by one listener that works across the worlds that token can reach.

Spawn's agent guide says that a person who wants a token for their own scripts can mint one in their settings, that it acts as that person, and that doors meant for agent accounts alone refuse it ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17). A coordinator account is a kit account whose token came that way. Spawn's own tokens page (in settings, seen 2026-11-17) says much the same: a personal token is for your own scripts, and agents make their own.

What this means:

- **One token acts as one Spawn account.** The kit can reach only the worlds that account can reach. The kit does not widen that. Spawn lists the account's worlds, and `sdlca-worlds` records them. A coordinator that works across several people's worlds therefore holds several tokens, one per person: see [grouped accounts](#grouped-accounts-and-the-sdlca-token-command).
- **To work in other people's worlds, their creators must let the account in.** According to Spawn's guide, a world's creator can invite an account into the crew, or approve its request to build, and a person's own prompt can add an agent as an editor on one world (retrieved 2026-11-17). The kit does not ask, accept or approve for you. After the account has standing, run `sdlca-worlds --apply` so the world is cloned and routed.
- **The account's own handle is the person's.** Chat lines the kit posts through this token, and the pushes it makes, appear under that person's name, not under an agent name. Keep the agent's replies signed as the agent (the default prompt tells it to), so nobody takes an agent's words for a person's.
- **`OWNER` is a choice you make.** It is the Spawn user whose messages may start work, and the key for extra senders in `allowlist.json`.

Check these before you rely on it:

- The automated tests use stand-ins for Spawn, so they do not cover a person-minted token. If you run one, tell us what you find.
- Spawn's guide describes such tokens as being for a person's own scripts. It does not say whether an AI agent counts. Read [the rules we follow for Spawn](compliance/spawn-rules.md) and, if in doubt, ask Spawn. The route the guide describes for agents is an agent account linked to a person by an invite code, which is what `sdlca-onboard` does.
- The reply-loop guard looks for the agent form of the handle, `@@name`. An account that writes as a person writes as `@name`. Try one message and watch `handler.log` for a second `event` line that you did not cause.
- The default prompt says the account is `@@<SPAWN_USERNAME>`, and one prompt override is shared by all accounts in a runtime home. If that is wrong for this account, use a separate runtime home for it.

To make a coordinator account with one token, after you have run `scripts/install.sh`, use `sdlca-token` (described in the next section) with the account's real owner:

```bash
bin/sdlca-token add sdlca-for-spawn --owner alice        # asks for the token; nothing is shown
${EDITOR:-nano} ~/.sdlca/spawn/accounts/sdlca-for-spawn/env   # set SDLCA_AGENT_CMD (docs/security-model.md first)
bin/sdlca-as sdlca-for-spawn bin/sdlca-worlds            # dry run: lists what this token can reach
bin/sdlca-as sdlca-for-spawn bin/sdlca-worlds --apply    # clone and record those worlds
systemctl --user enable --now sdlca-listener@sdlca-for-spawn.service
```

`sdlca-token add` writes `OWNER`, `SPAWN_USERNAME` (the owner's name unless you pass `--username`) and `SPAWN_TOKEN_FILE` into the env file. It does not set `SDLCA_AGENT_CMD`: you choose that yourself, and the listener refuses to start without it. The kit refuses an env file that group or others can write, and `sdlca-token` makes both files private to you.

### Grouped accounts and the sdlca-token command

Because one personal token acts as one Spawn account, a coordinator for several people holds one token per person, and each is its own kit account. The kit keeps them together as *grouped accounts*. A grouped account has a name of the form `group/name`, and its folder is `accounts/<group>/<name>/`, with its own `env` and `token`. For example, a coordinator group named `sdlca-for-spawn` can hold one personal token for each Spawn account that chooses to use it:

```text
accounts/sdlca-for-spawn/alice/    env, token
accounts/sdlca-for-spawn/bob/      env, token
accounts/sdlca-for-spawn/carol/    env, token
```

Read [Personal tokens that belong to other people](#personal-tokens-that-belong-to-other-people) before you store a token that is not your own.

`bin/sdlca-token` creates and checks these accounts without putting a token on a command line, in your shell history or in a chat:

| Command | What it does |
| --- | --- |
| `init <account> --owner <spawn-username> [--username <spawn-username>]` | Makes the account's folders (mode 0700) and its env file. No token yet. |
| `add <account> --owner <spawn-username> [--username <spawn-username>] [--stdin]` | Does what `init` does, then asks for the token without echoing it, or reads one line from standard input with `--stdin`. It refuses a one-time invite code (`sbk_...`), a value shorter than 16 characters and a value with a space, double quote, backslash or character outside visible ASCII, stores the token with mode 0600 through a temporary file, and never prints it. A token that does not start with `sak_` is stored, with a note. Adding again to an existing account replaces the token and keeps the env file, so `--owner` is not needed. |
| `path <account>` | Prints the path of the account's token file, for your own scripts. |
| `verify <account>` | Asks Spawn who the token belongs to (`GET /api/agent/v1/me`, through `sdlca-api`). Prints the username, handle, account kind, who it is linked to and the number of worlds. Says plainly when the token signs in as a person. Never prints the token. |
| `list` | Shows every account, its owner and whether a token is stored. Never shows a token. |

For example:

```bash
bin/sdlca-token add sdlca-for-spawn/alice --owner alice          # asks for the token; nothing is shown
bin/sdlca-token verify sdlca-for-spawn/alice                     # who does Spawn say this token is?
bin/sdlca-as sdlca-for-spawn/alice bin/sdlca-worlds --apply      # clone the worlds that account can reach
bin/sdlca-token list
```

How the rest of the kit treats a grouped name:

- `ACCOUNT`, which `sdlca-as` sets, is the full `group/name`, and the `accounts` lists in the registry use it.
- Lock and scratch names are made safe. In a lock name the slash becomes an underscore (`run/unrouted__sdlca-for-spawn_alice.lock`), and the scratch folder is `run/scratch/sdlca-for-spawn/alice`.
- The sender allowlist is keyed by `OWNER`, so accounts with the same `OWNER` share their extra senders.
- **A grouped account cannot be a systemd listener.** A systemd instance name cannot contain a slash. Grouped accounts are for scripts and tools (`sdlca-as`, `sdlca-api`, `sdlca-worlds`, `sdlca-look`), and listeners use one-word account names. We have not tried `sdlca-listen` with a grouped name under another supervisor.

### Personal tokens that belong to other people

A personal token acts as the person who made it. Chat lines, pushes and everything else it does appear under that person's name. Spawn's terms bar letting other people use your account ([Spawn's terms](https://www.spawn.co/terms-of-service), section 3, read on 2026-11-17; see [the rules we follow for Spawn](compliance/spawn-rules.md)). So:

- **Each person should mint and keep their own token.** Name it for the machine that uses it (for example "my laptop") when you make it, so you can revoke each token on its own. Do not ask anyone to send you a token, and do not send yours to anyone else. The kit never asks.
- **For another person's account, the safer route is the one the kit already uses:** a separate agent account, linked to that person with their own one-time invite (`sdlca-onboard`).
- **For an AI agent or a coordinator that works in several owners' worlds, prefer one agent account** that each owner adds as an editor, through a build invite or the crew request flow. It shows as an agent, needs one token instead of one per person, is revoked by unlinking, and does not let a machine act as a person.
- **Keep personal tokens for a person's own scripts.** `sdlca-token verify` prints the account kind, and says so when a token is a person's.

**Make personal tokens by hand.** Spawn publishes no API for minting them: a person makes one on Spawn's settings page. Replaying a logged-in browser session, or calling the website's own internal requests, is outside the documented doors that Spawn allows. Its terms allow automation only through the APIs and tools it publishes, and bar probing undocumented interfaces ([rule 6](compliance/spawn-rules.md#use-only-spawns-documented-doors)). A session cookie works like the account's password, and the internal requests change with each Spawn release. The kit never uses or stores browser cookies. If you want to mint tokens by script, ask Spawn for an API.

## The runtime home

Everything the kit keeps is under `$SDLCA_SPAWN_HOME`, by default `~/.sdlca/spawn`. [Configuration](configuration.md#files-in-the-runtime-home) has the full table of modes and writers. This is the shape:

```text
~/.sdlca/spawn/                      mode 0700
|-- accounts/
|   `-- <account>/                   one folder per account, mode 0700 (a grouped account is <group>/<name>/)
|       |-- env                      the account's settings, read as shell, mode 0600
|       |-- token                    the account's Spawn token, mode 0600 (the env file records the path)
|       |-- cursor                   newest inbox event handled
|       |-- cursor.lock              an empty file used as a lock while the cursor is written
|       |-- handled.ids              ids of events that finished (newest 500)
|       |-- runs.log                 start times of recent agent runs, for the hourly cap
|       |-- handler.log              handler lines, plus everything the agent prints
|       `-- listener.log             the Spawn client's status lines
|-- worlds.json                      the world registry, shared by all accounts
|-- worlds.json.lock                 held by sdlca-worlds while it writes the registry
|-- allowlist.json                   who besides each owner may trigger work
|-- AGENTS.md                        notes the agent reads each turn, shared by all accounts
|-- WORK-TODO.md                     the agent's ledger, shared by all accounts
|-- handler-prompt.md                optional prompt override, shared by all accounts
|-- run/
|   |-- <world owner>__<world>.lock  one lock per world
|   |-- unrouted__<account>.lock     one lock per account, for events with no world (a slash in the name becomes _)
|   |-- scratch/<account>/           where turns with no world start
|   `-- failed/<event-id>.json       events that failed or were refused, kept for replay (deleted after SDLCA_FAILED_KEEP_DAYS days, 30 by default)
`-- shots/                           where sdlca-look may save a screenshot; nothing writes here by itself
```

The clones live outside it, at `$SDLCA_REPOS/<world owner>/<world>`. [Clone paths and SDLCA_REPOS](#clone-paths-and-sdlca_repos) says more.

## The world registry

`worlds.json` records which worlds the accounts can reach and where their clones are. Entries are keyed by the world's id, which Spawn never changes, and not by its name, which can change. That is what lets the kit survive a rename.

```json
{
  "worlds": {
    "<world id>": {
      "appId": "<app id>",
      "owner": "alice",
      "slug": "game-1",
      "address": "@alice/game-1",
      "git": "https://git.spawn.co/@alice/game-1.git",
      "clone_path": "/home/you/spawn-worlds/alice/game-1",
      "aliases": ["@alice/old-name"],
      "accounts": ["alice", "sdlca-for-spawn/bob"],
      "slack_channel_ids": [],
      "standing": "editor"
    }
  }
}
```

| Field | Meaning |
| --- | --- |
| Key | Spawn's world id. Never a name. |
| `appId` | Spawn's app id for the world. Events name the world through it as well. |
| `owner`, `slug` | The two parts of the address. The owner is the world's owner, which is not always an account's owner. For a world an agent made, `@@agent/world`, the owner is `agent`. |
| `address` | The current address. |
| `git` | The git address that Spawn's listing gave for the world the last time `sdlca-worlds --apply` visited it (the example above is only an illustration; the real one is whatever Spawn lists). The update before each turn (`lib/refresh.py`) fetches from this address and from no other, and refuses a clone whose remote or credential helper disagrees with it. It is recorded only when it is an https address with a host, no user information and no `.` or `..` segment in its path (the form the clone's credential helper can be attached to, and one that the update can compare). If Spawn lists none, or one that is not usable, the field is left out, and one recorded before is removed. There is one record per world, shared by every account in `accounts`: if the accounts that reach a world did not get the same address from Spawn, the one that ran `--apply` last decides, and the tool says which other accounts share the record when it changes or removes it. The field is optional: an entry without it is a world that was recorded before the field existed, or one with no usable address, and the update then says `unverified` and runs no git. It is always taken from Spawn's listing, never from the clone. |
| `clone_path` | Where the clone lives. The agent starts here. |
| `aliases` | Old addresses, added when the kit sees a rename. Events that still use one are routed to the world. |
| `accounts` | The accounts that reach this world, by full name (`group/name` for a grouped account). This list decides which accounts the world is served to: an account is served a world only when its own full name is in the list (its `OWNER` is not consulted). Entries from older versions without the list fall back to comparing the owner part of the address with the account's `OWNER`. |
| `pending_move` | Present only after a rename whose folder move had to wait because an agent was working in the world. A later `--apply` moves the folder, if the new place is free, and removes this field. |
| `slack_channel_ids` | Reserved for the planned [Slack bridge](slack-bridge.md). Nothing reads it. |
| `standing` | The account's role in the world as Spawn last reported it. Informational. |

### What sdlca-worlds does

`sdlca-worlds` is the only program that writes the registry. Run it under `sdlca-as`, which supplies the account:

```bash
bin/sdlca-as alice bin/sdlca-worlds            # dry run: report only
bin/sdlca-as alice bin/sdlca-worlds --apply    # clone, follow renames, save
bin/sdlca-as alice bin/sdlca-worlds --only @bob/game --apply    # only the world you name
```

A personal token reaches every world its person can reach, which can be many (and mostly other people's). Run the dry run first, then use `--only @owner/world` (once for each world, with the address exactly as the dry run prints it) so that only those worlds are cloned and recorded. Each line also says your standing in the world (owner, admin, editor or viewer): a viewer can read and clone but cannot push, and only an admin can invite others to build. Every other world is left alone: not cloned, not recorded, and not renamed even if it was renamed on Spawn. If the account cannot reach a world you name, nothing is changed and the reachable addresses are listed.

Under a personal token (a person's own account, not an agent's) the tool prints a note, and `--apply` needs `--as-person`. Clones made with that token push as that person, and a chat listener cannot run on that account, so those worlds do not route chat for your agent: the registry lists the world only for the account that ran the tool, and an existing clone is never re-pointed to another account's token later. To give your agent a world, run the tool under the agent's own account, once the agent has standing in the world.

It asks Spawn for the account's worlds (the `/api/agent/v1/me` call, with the account's token) and then, for each world:

1. Skips it, with a message, if its address does not look like `@owner/world` or `@@agent/world`, if either part starts with a dot or a hyphen (which covers `.` and `..`), or if it has no world id that is a string.
2. Records it if it is new, with its clone path set to `$SDLCA_REPOS/<owner>/<world>`.
3. Refreshes its `standing` if it is already known.
4. Follows a rename if the world kept its id but changed its address (see [Renames](#renames)).
5. Records the git address that Spawn lists for the world (the `git` field), when it is one the clone's credential helper can be attached to and the update can compare (https, a host, no user information, no `.` or `..` in the path), and says `recording the git address of <world> (host <host>)` or `updating ...` when that changes the registry, and which other accounts share the record. It prints the host and never the address. If the listing has none, or an unusable one, it records none, removes one recorded before, and prints a `WARNING` that says the update before a turn will skip that world. Recording is a change to the registry only: the clone's files and settings are not touched for it. (A rename, in step 4, does move the clone's remote to the new address, but only when the new address is one that is recorded; for any other the remote is left as it was, and the tool says so.)
6. With `--apply`, adds the account to the world's `accounts` list and makes the clone if its folder does not exist. The clone has a 600-second time limit. A failed clone is reported as `clone failed (it will be tried again next run)` and is tried again on every later `--apply`.
7. With `--apply`, writes the file through a temporary file and a rename, with mode 0600.

Without `--apply` nothing is written. The dry run prints lines such as `[dry-run] new world @alice/game-1 -> /home/you/spawn-worlds/alice/game-1`, and `[dry-run] recording the git address of @alice/game-1 (host git.spawn.co)` for a world that was recorded before the field existed.

**A world recorded before the `git` field existed.** Its entry has no address, so the update before a turn says `unverified` (see [Operations](operations.md#the-clone-was-not-brought-up-to-date)) and runs no git until it has one. Give it one by running the tool under the AGENT's account (the one whose clone it is):

```bash
bin/sdlca-as alice bin/sdlca-worlds --apply                         # every world that account reaches
bin/sdlca-as alice bin/sdlca-worlds --apply --only @alice/game-1    # just one
```

Look at the dry run first. Recording an address changes only the registry. The tool does not check the clone's remote for it, and does not change it: if the clone's remote differs from what Spawn lists, the next update says `untrusted` and names both hosts, and you decide which one is right. The same run still does what `--apply` always does, so the dry run may also show `RENAMED` (the clone's remote is pointed at the new address and the folder is moved) or `new world` (a missing clone is made): read it before you run `--apply`.

What it never does:

- **It does not run by itself.** `sdlca-onboard` runs it once. After that, run it yourself whenever the account gains standing in a new world, and after a rename. Until you do, events about a new world are not matched and the agent starts in its scratch folder.
- **It never deletes a clone you already have, and never changes its files or settings,** except to point its remote at the new address and move it for a rename.
- **It never removes a registry entry,** even when the account has lost access to the world. See [When standing is lost](#when-standing-is-lost).
- **It never pulls or pushes.** Before a turn that came from a world's own chat, the handler brings that world's clone up to date, by fast-forward only (see [Updating a clone before each turn](configuration.md#updating-a-clone-before-each-turn)), and the agent pushes during a turn.

With `--apply`, it holds a lock on `worlds.json.lock` while it works, so two runs (or onboarding and a manual run) do not overwrite each other's registry. A rename's folder move does not pull the ground out from under an agent: if an agent holds that world's lock, the move waits. The entry gets a `pending_move` field, `sdlca-worlds` prints `WARNING an agent is working in ...`, and a later `--apply` moves the folder. A hand edit of `worlds.json` takes no lock, so make it only while nothing is running.

### How an event finds its world

The handler compares the ids, addresses and aliases in the registry with four structured fields of the event. It never reads the chat text. The rules, and what happens when nothing matches, are in [Architecture](architecture.md#routing-rules). Two things matter here:

- Because ids come first, a rename does not break routing. The new address and the old one both lead to the same world.
- A world is served only to the accounts named in its `accounts` list. A second account (for example `sdlca-for-spawn/alice` for a world that `alice` registered) is added by running `bin/sdlca-as sdlca-for-spawn/alice bin/sdlca-worlds --apply` under that account, once Spawn lists the world among that account's worlds. Until then its events about that world run in the scratch folder.
- Matching is by whole token, so `@alice/game` never matches `@alice/game-2`.

## Clone paths and SDLCA_REPOS

A clone lives at `$SDLCA_REPOS/<world owner>/<world>`. The default for `SDLCA_REPOS` is `~/repos`, so a world `@alice/game-1` is cloned to `~/repos/alice/game-1`.

- Set `SDLCA_REPOS` in your shell when you run `sdlca-onboard`, because onboarding does not load the account's env file. For later runs under `sdlca-as`, you can also put it in the account env file.
- Changing it later affects only clones made afterward. An existing clone keeps the path recorded in `worlds.json`. A rename moves the clone to the new path under whatever `SDLCA_REPOS` is then.

**Keep Spawn clones in their own folder.** Spawn owner names and GitHub organization names can be the same, or nearly: a Spawn owner `kdtix_open` and a GitHub organization `kdtix-open` differ by one character, and an owner `alice` can be identical to an organization `alice`. Some people keep their git checkouts under `~/repos/<organization>/<repository>`, which is the same shape as the kit's default. The kit makes a clone only if the folder does not exist, and it never checks what an existing folder holds. If a world's path already holds another repository, the kit takes that folder to be the clone. The agent then works there, and a push goes to whatever remote that repository has. To avoid this, point the kit at a root of its own:

```bash
export SDLCA_REPOS="$HOME/spawn-worlds"
```

This also gives you a way to adopt a clone you already made: put it at the expected path and the kit will use it as it is, without touching its remote, its identity or its credentials. The agent will work in it. But the update before a turn brings it up to date only when its remote is the address recorded for the world and it carries the kit's credential helper for that address (see [Operations](operations.md#the-clone-was-not-brought-up-to-date)); a clone that was made some other way is `untrusted` or fails to fetch until you make that so, or remove the clone and let `sdlca-worlds --apply` make it again.

## Credentials and identity in the clones

`sdlca-worlds` sets these options in each clone it makes, and only in that clone:

| Option | Value |
| --- | --- |
| `credential.helper` | An empty value first, so that git forgets any helper from your global or system configuration |
| `credential.https://<git host>.helper` | A helper that supplies the account's username and reads the password from that account's token file each time git asks. It is attached to the git host in the world's https URL only |
| `http.https://<git host>.proactiveAuth` | `basic`, for that same host only |
| `remote.origin.fetch` | An extra rule, `+refs/notes/*:refs/notes/*`, so git notes are fetched with branches |
| `user.name`, `user.email` | `SDLCA_GIT_NAME` and `SDLCA_GIT_EMAIL`, by default `sdlca-agent` and `sdlca-agent@users.noreply.invalid` |

What follows from that:

- **Your global git configuration is not touched** by any of this. One caveat: while `sdlca-onboard` runs Spawn's `spawn login`, Spawn's client adds a credential helper to the global configuration, and onboarding puts the earlier state back when it ends.
- **The token is not copied into the clone.** The helper reads the token file when git runs, so a rotated token works in every clone with no change. The clone's configuration holds the file's path and the username. The kit's own update before a turn (`lib/refresh.py`) fetches through this same helper, and it accepts only the exact form that `sdlca-worlds` writes, scoped to the origin of the world's recorded git address: if someone edits the helper in the clone's configuration, or scopes one to another host, the update is skipped as `untrusted` until the edit is undone.
- **The helper is limited to the git host of the world's URL.** Git offers the token to that host and to no other. A remote, submodule or large-file URL on another host gets no credentials, and a world whose URL is not plain https gets no helper at all. A test checks this with `git credential fill`. The limit is on what git offers, not on who can read the token: an agent that can read the token file, or run arbitrary `git` commands (which can run other programs through configuration and aliases), can still reach it. See [Security model](security-model.md#residual-risks).
- **A shared clone uses the credentials of the account that made it.** If two accounts reach one world, there is one clone, and its helper points at the token of whichever account ran `--apply` first. If that account loses standing, pushes from the clone fail even though the other account still has it, and so does the update that the handler runs before each turn (it logs `failed/fetch`). To switch, delete the clone (after checking for unpushed work) and run `--apply` under the account you want, or change the clone's `credential.helper` yourself.
- **The commit identity is set only on clones the kit makes.** An existing clone keeps its identity. Set `SDLCA_GIT_NAME` and `SDLCA_GIT_EMAIL` before the clone is made, or change one clone with `git -C <clone> config user.name ...`. The default address ends in `.invalid`, a reserved name that cannot receive mail. Choose your own if you want one that can.
- **Deleting a clone deletes the commits you have not pushed.** Spawn's git remote keeps only what was pushed.

## Renames

A world keeps its id when its name changes. When `sdlca-worlds` sees the same id with a new address, it prints `RENAMED <old> -> <new>`. With `--apply` it then:

1. adds the old address to the world's `aliases`;
2. points the clone's `origin` at the new git URL, and records the new git URL in the entry (`git`) in the same run. If git cannot update the remote (for example because the remote is not called `origin`), it prints a `WARNING`, still records what Spawn lists, and the update then refuses the clone as `untrusted` until its remote is put right;
3. moves the clone's folder to `$SDLCA_REPOS/<new owner>/<new slug>`, if that folder does not exist and no agent is working in the world. If the new folder does exist, the kit leaves the clone where it was, prints a warning and keeps the old path. If an agent holds the world's lock, the entry gets `pending_move` and the folder moves on a later `--apply`;
4. updates `owner`, `slug`, `address` and `clone_path` (the path changes when the folder moves).

Until you run `--apply`, the old folder stays, and the clone's remote and the recorded git address are the old ones, so the update before each turn can log `failed/fetch` if Spawn no longer answers at the old address. Routing keeps working, because ids come first. The lock file name comes from the owner and the slug, so a renamed world gets a new lock file. The move first tries the world's lock, so it does not happen while an agent holds it.

## When standing is lost

An account's access to a world can end: a creator removes it from the crew, the person who linked it unlinks it, or the world is deleted. Spawn's guide says that unlinking by the person who linked an agent ends its standing on every world of theirs, while its own worlds and its account stay (retrieved 2026-11-17).

What the kit does about it: nothing, automatically. It does not watch for the unlink event, and `sdlca-worlds` never removes an entry. So:

- A world that was lost stays in `worlds.json`, with the last `standing` it saw, and its clone stays on disk.
- If events about it still arrive, they still route to the clone. Spawn refuses a `git push` from an account that cannot write to the world ([Spawn's agent guide](https://www.spawn.co/llms-full.txt), retrieved 2026-11-17), and it may refuse a `git pull` as well. The update that the handler makes before each turn then logs `failed/fetch`, the agent is told that the clone may lag the latest push, and the turn still runs.
- A dry run of `sdlca-worlds` lists every world Spawn still shows to the account. A world that is missing from the list has been lost.

To clean up, stop the listener, then:

1. Check the clone for commits you have not pushed (`git -C <clone> log --branches --not --remotes`).
2. Copy out or push anything you want, if you still can.
3. Remove the world's entry from `worlds.json`, or only the account's name from its `accounts` list if another account still reaches the world. The file is JSON, so keep it valid: if `sdlca-worlds` cannot read it as a JSON object, it stops with "is not a valid JSON object" and changes nothing (a dry run does the same), so fix the file or move it aside and run again. Keep a copy before you edit.
4. Delete the clone if you no longer need it.

If the token itself is refused, that is a different problem. See [Operations](operations.md#rotating-a-token).

## When a world is transferred

We have not found a description of world transfers in Spawn's agent guide, so we cannot say what Spawn does. Here is what the kit does with what it can see:

- If the world keeps its id and its address changes, which would include a new owner in the address, the kit treats it as a rename. The folder moves to `$SDLCA_REPOS/<new owner>/<world>`, and the old address becomes an alias.
- If the account no longer has standing after the transfer, the world drops out of the account's list and the section above applies.
- If Spawn gives the world a new id, the kit sees a new world. The old entry stays until you remove it.

Check one world after the first transfer you see, and tell us what you find: a note in the [Discussions](https://github.com/kdtix-open/sdlca-for-spawn/discussions) helps the next person.

## A checklist for a new account

1. Run `scripts/install.sh` once per machine.
2. Create the account with `sdlca-onboard` (or with `sdlca-token add` for a coordinator or grouped account, after reading [Personal tokens that belong to other people](#personal-tokens-that-belong-to-other-people)).
3. Set `SDLCA_AGENT_CMD` in the account's env file. Read [Security model](security-model.md) first.
4. Set `SDLCA_REPOS` to a folder of its own, before the first clone.
5. Run `bin/sdlca-as <account> bin/sdlca-worlds --apply` whenever the account gains access to a new world.
6. Start the listener (a one-word account only), then send a first message.

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
