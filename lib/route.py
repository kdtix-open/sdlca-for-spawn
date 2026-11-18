#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Classify one Spawn inbox event for an account: who sent it, may they trigger work, which world.

Reads the event JSON on stdin. Environment:
  OWNER             the Spawn user this agent account is linked to (always allowed to trigger work)
  ACCOUNT           this account's folder name (defaults to OWNER); picks the worlds it can reach
  SPAWN_USERNAME    this agent account's own Spawn username (never allowed: prevents reply loops)
  SDLCA_SPAWN_HOME  runtime home holding allowlist.json and worlds.json

Prints one tab-separated line:  kind  cursor  event-id  decision  sender  address  working-directory  lock
  decision is "allow" or "deny:<reason>". Chat text is never printed or logged.
  An event that names no known world gets a scratch directory of its own, never the runtime home
  (which holds every account's token).

Fail closed: an unreadable allowlist means only the owner may trigger work; an unknown sender is denied;
a human handle (@name) and an agent handle (@@name) are different people.
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


def lock_name(world, account):
    if not world:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", "unrouted__%s" % account)
    return re.sub(r"[^A-Za-z0-9_.-]", "_", "%s__%s" % (world.get("owner", ""), world.get("slug", "")))


def clean(value):
    """One tab-separated field: no tab or line break, never empty (bash's read would merge two tabs and shift the fields)."""
    return re.sub(r"[\t\r\n]", " ", str(value)) or "-"


def main():
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
    ]
    print("\t".join(clean(f) for f in fields))


if __name__ == "__main__":
    main()
