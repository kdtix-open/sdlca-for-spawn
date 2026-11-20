#!/usr/bin/env -S python3 -I -B
# SPDX-License-Identifier: Apache-2.0
"""Read the owner's chat line as a presence command: /spawn, /spawn ttl <seconds>, or /leave.

usage: command.py  < event JSON      (environment: OWNER, and optionally SDLCA_PRESENCE_TTL)

Prints exactly one line: "join <seconds>", "leave", or "-" (not a command). Only the account's OWNER can give one: a line from
an allowed sender who is not the owner prints "-" and goes to the agent as before. Leading @mentions are dropped; the rest must be
exactly the command, nothing more, so a longer sentence that happens to start with /spawn is never a command. /spawn alone stays for
SDLCA_PRESENCE_TTL seconds (default 3600) because Spawn's client always has a time limit; /leave ends it sooner.
"""
import json
import os
import re
import sys

MIN_TTL, MAX_TTL = 10, 14400
HANDLE = re.compile(r"@{1,2}[A-Za-z0-9_]{1,40}")


def parse(text, default_ttl):
    words = text.strip().split()
    while words and HANDLE.fullmatch(words[0]):
        words.pop(0)
    words = [w.lower() for w in words]
    if words == ["/leave"]:
        return "leave"
    if words == ["/spawn"]:
        return "join %d" % default_ttl
    if len(words) == 3 and words[:2] == ["/spawn", "ttl"] and re.fullmatch(r"[0-9]{1,6}", words[2]):
        seconds = int(words[2])
        if MIN_TTL <= seconds <= MAX_TTL:
            return "join %d" % seconds
    return "-"


def main():
    try:
        event = json.load(sys.stdin)
        chat = event.get("chat") or {}
        sender = str(chat.get("from") or "").lower()
        owner = "@" + os.environ.get("OWNER", "").lower()
        default = os.environ.get("SDLCA_PRESENCE_TTL", "3600")
        default_ttl = int(default) if re.fullmatch(r"[0-9]{1,6}", default) and MIN_TTL <= int(default) <= MAX_TTL else 3600
        if event.get("kind") != "chat_mention" or not os.environ.get("OWNER") or sender != owner:
            print("-")
            return
        print(parse(str(chat.get("text") or ""), default_ttl))
    except (ValueError, AttributeError, RecursionError):
        print("-")


if __name__ == "__main__":
    main()
