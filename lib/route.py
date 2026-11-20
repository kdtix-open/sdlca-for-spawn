#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Classify one Spawn inbox event for an account: who sent it, may they trigger work, which world.

Reads the event JSON on stdin. Environment:
  OWNER             the Spawn user this agent account is linked to (always allowed to trigger work)
  ACCOUNT           this account's folder name (defaults to OWNER); picks the worlds it can reach
  SPAWN_USERNAME    this agent account's own Spawn username (never allowed: prevents reply loops)
  SDLCA_SPAWN_HOME  runtime home holding allowlist.json and worlds.json

Prints one tab-separated line:  kind  cursor  event-id  decision  sender  address  working-directory  lock  git
  decision is "allow" or "deny:<reason>". Chat text is never printed or logged.
  An event that names no known world gets a scratch directory of its own, never the runtime home
  (which holds every account's token).
  git is the git address that sdlca-worlds recorded for the world (the "git" field of its entry in worlds.json,
  taken from Spawn's own listing and never from the clone), or "-" when there is none. The handler hands it to
  lib/refresh.py, which fetches from that address only. It is the last field, and a reader must name it: bash's read gives
  the rest of the line to its last variable.

Fail closed: an unreadable allowlist means only the owner may trigger work; an unknown sender is denied;
a human handle (@name) and an agent handle (@@name) are different people.

A second use, for sdlca-look:  route.py --serves <address>   (environment: OWNER, ACCOUNT, SDLCA_SPAWN_HOME)
  Exit 0 and print the world's current address when this account can reach a world whose address, or one of its old
  addresses (aliases), is exactly that text. Exit 1 and print nothing when it cannot (a registry file that is missing
  serves nothing). Exit 2 for a usage or setup error, for a registry file that is damaged (it cannot be read, is not
  JSON, or is not a JSON object), and when more than one world the account can reach answers to the text. A current
  address wins over an old one: a world that has the address now is the one that is found, whatever the order of the
  registry. It never looks at ids or at part of a text: the caller acts as the account on the strength of the answer.
"""
import json
import os
import re
import sys

HANDLE = re.compile(r"@{1,2}[A-Za-z0-9_.-]{1,64}")  # used with fullmatch: "$" would also accept a trailing newline
SAFE_ID = re.compile(r"[A-Za-z0-9_-]{1,80}")


def load_json(path, default):
    """A JSON object from a file, or the default when it is missing, unreadable, or not an object."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return default
    return data if isinstance(data, dict) else default


def sender_of(event):
    """The sender's handle exactly as Spawn writes it ("@name" for a person, "@@name" for an agent),
    lower-cased, or '' if it is missing or odd-looking."""
    raw = str((event.get("chat") or {}).get("from") or "")
    return raw.lower() if HANDLE.fullmatch(raw) else ""


def normalize_extra(entry):
    """An allowlist entry: "carol" or "@carol" means the person; "@@helper" means an agent."""
    entry = str(entry).strip().lower()
    if not entry:
        return ""
    handle = entry if entry.startswith("@") else "@" + entry
    return handle if HANDLE.fullmatch(handle) else ""


def decide(event, owner, agent, extra_senders):
    sender = sender_of(event)
    if not sender:
        return "deny:unknown-sender"
    if sender == "@@" + agent.lower():
        return "deny:self"
    allowed = {"@" + owner.lower()}
    if isinstance(extra_senders, list):
        allowed |= {h for h in (normalize_extra(e) for e in extra_senders) if h}
    return "allow" if sender in allowed else "deny:not-allowed"


def structured_haystack(event):
    """Fields that name the world. The chat text and message are excluded on purpose, so what a
    person types can never steer which world's clone the agent works in."""
    chat = event.get("chat") or {}
    return " ".join(str(part) for part in (event.get("relatedGameId"), event.get("actionData"), chat.get("world"), chat.get("key")) if part)


def tokens(text):
    """Whole-word views of the structured fields, so that "@alice/game" never matches "@alice/game-2".
    Addresses are compared as whole tokens that may contain @ and /; ids are compared as whole tokens
    that may not (an id inside "room:<id>/dev/main" or "world=<id>&room=main" is split out)."""
    address_tokens = set(re.split(r"[^A-Za-z0-9_.@/-]+", text))
    id_tokens = set(re.split(r"[^A-Za-z0-9_-]+", text))
    return address_tokens, id_tokens


def serves(world, account, owner):
    """True when this account can reach the world. Entries written by sdlca-worlds list the accounts that
    reach them; older entries fall back to the address owner."""
    accounts = world.get("accounts")
    if isinstance(accounts, list):
        return account in accounts
    return world.get("owner") == owner


def world_entries(registry):
    """(id, entry) for every well-formed registry entry. A damaged one is skipped instead of stopping every event."""
    worlds = registry.get("worlds") if isinstance(registry, dict) else None
    return [(i, w) for i, w in (worlds.items() if isinstance(worlds, dict) else []) if isinstance(w, dict)]


def find_world(event, owner, registry, account=None):
    """The world an event is about, by exact id first and then by exact address or alias; None if unknown."""
    account = account or owner
    address_tokens, id_tokens = tokens(structured_haystack(event))
    by_address = None
    for world_id, world in world_entries(registry):
        if not serves(world, account, owner):
            continue
        app_id = str(world.get("appId") or "")
        ids = {world_id, world_id.replace("-", ""), app_id, app_id.replace("-", "")}
        if any(i and i in id_tokens for i in ids):
            return world
        names = {world.get("address"), *(world.get("aliases") or [])}
        if by_address is None and any(n and n in address_tokens for n in names):
            by_address = world
    return by_address


def worlds_of(owner, registry, account=None):
    """(address, clone_path) of every world this account can reach."""
    account = account or owner
    return [
        (w.get("address", ""), w.get("clone_path", ""))
        for _, w in world_entries(registry)
        if serves(w, account, owner)
    ]


class AmbiguousAddress(Exception):
    """More than one world that the account can reach answers to the same address."""


class DamagedRegistry(Exception):
    """worlds.json exists, and cannot be read as a JSON object."""


def world_by_address(address, owner, registry, account=None):
    """The entry of a world this account can reach whose current address, or one of its old addresses (aliases), is exactly this
    text; None when there is none. Unlike find_world it never looks at ids and never at part of a text, because a caller that
    joins a world as the account decides on the strength of the answer. The comparison is exact (case included).

    A world's old address can be a world's current address again (a name that was given up and taken by another world). The world that
    has the address NOW wins, so the answer does not depend on the order of the registry; an old address is used only when no world
    has it as its current one. Two worlds that answer in the same way (two with that current address, or none and two with that old
    one) are ambiguous, and raise AmbiguousAddress: the caller must not guess which one to act in."""
    account = account or owner
    if not isinstance(address, str) or not address:
        return None
    current, old = [], []
    for _, world in world_entries(registry):
        if not serves(world, account, owner):
            continue
        aliases = world.get("aliases")
        if world.get("address") == address:
            current.append(world)
        elif address in (aliases if isinstance(aliases, list) else []):
            old.append(world)
    for found in (current, old):
        if len(found) > 1:
            raise AmbiguousAddress(address)
        if found:
            return found[0]
    return None


def read_registry(path):
    """The registry as a dict. A file that is not there is an empty registry (nothing is served). One that is there and cannot be read, is not
    JSON, or is not a JSON object is damaged (DamagedRegistry): that must not look like "nothing is served", because the person is then told to
    run a command that refuses a damaged file as well, when what they have to do is mend the file."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        raise DamagedRegistry(path)
    if not isinstance(data, dict):
        raise DamagedRegistry(path)
    return data


def lock_name(world, account):
    if not world:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", "unrouted__%s" % account)
    return re.sub(r"[^A-Za-z0-9_.-]", "_", "%s__%s" % (world.get("owner", ""), world.get("slug", "")))


def recorded_git(world):
    """The git address recorded for a world, or "" when the world is unknown, has none, or it is not text. Only a string counts: the value
    is handed to code that fetches from it, so a number or a list in a hand-edited registry must read as "none recorded"."""
    git = world.get("git") if world else None
    return git if isinstance(git, str) else ""


def clean(value):
    """One tab-separated field: no tab or line break, never empty (bash's read would merge two tabs and shift the fields)."""
    return re.sub(r"[\t\r\n]", " ", str(value)) or "-"


def serves_main(args):
    """The --serves command (see the top of this file). Every way of not answering "yes" prints nothing on standard output."""
    owner = os.environ.get("OWNER", "")
    account = os.environ.get("ACCOUNT") or owner
    home = os.environ.get("SDLCA_SPAWN_HOME") or os.path.expanduser("~/.sdlca/spawn")
    if len(args) != 2 or args[0] != "--serves" or not owner or not account:
        print("usage: route.py --serves <address>   (environment: OWNER, ACCOUNT, SDLCA_SPAWN_HOME)", file=sys.stderr)
        return 2
    path = os.path.join(home, "worlds.json")
    try:
        world = world_by_address(args[1], owner, read_registry(path), account)
        if world is None:
            return 1
        current = world.get("address")
        print(clean(current if isinstance(current, str) and current else args[1]))  # a world found by an old address is joined by its current one
    except DamagedRegistry:
        print("route.py --serves: %s is damaged (it cannot be read, or it is not a JSON object); fix it or move it aside, and then run sdlca-worlds --apply" % path, file=sys.stderr)
        return 2
    except AmbiguousAddress:
        print("route.py --serves: more than one world that this account can reach has that address (one as its address, or more as an old one); "
              "fix %s so that only one does" % path, file=sys.stderr)
        return 2
    except Exception as error:  # nothing else may print a traceback into a caller's output
        print("route.py --serves: %s" % type(error).__name__, file=sys.stderr)
        return 2
    return 0


def main():
    if len(sys.argv) > 1:
        sys.exit(serves_main(sys.argv[1:]))
    event = json.load(sys.stdin)
    owner = os.environ["OWNER"]
    account = os.environ.get("ACCOUNT") or owner
    agent = os.environ.get("SPAWN_USERNAME", "")
    home = os.environ.get("SDLCA_SPAWN_HOME") or os.path.expanduser("~/.sdlca/spawn")
    allow = load_json(os.path.join(home, "allowlist.json"), {})
    spawn_section = allow.get("spawn") if isinstance(allow.get("spawn"), dict) else {}
    registry = load_json(os.path.join(home, "worlds.json"), {})
    world = find_world(event, owner, registry, account)
    event_id = str(event.get("id") or "")
    fields = [
        event.get("kind") or "-",
        event.get("cursor", "") or "-",
        event_id if SAFE_ID.fullmatch(event_id) else "-",
        decide(event, owner, agent, spawn_section.get(owner)) if event.get("kind") == "chat_mention" else "n/a",
        sender_of(event) or "-",
        world.get("address", "-") if world else "-",
        (world.get("clone_path") if world else "") or os.path.join(home, "run", "scratch", account),
        lock_name(world, account),
        recorded_git(world),
    ]
    print("\t".join(clean(f) for f in fields))


if __name__ == "__main__":
    main()
