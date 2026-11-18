#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Advance an inbox cursor file monotonically.

usage: cursor.py <cursor-file> <new-cursor>

A Spawn inbox cursor is an opaque string; today it is base64url JSON holding createdAt and id.
When both the stored and the new cursor decode, the file only moves forward, so two handlers that
finish out of order cannot send the listener back to an older event after a restart. If either does
not decode, the new value is written as given.
"""
import base64
import fcntl
import json
import os
import sys
import tempfile
from datetime import datetime, timezone


def decode(cursor):
    """Return a sortable key for a cursor, or None when it does not look like one we understand."""
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        data = json.loads(raw)
        stamp = datetime.fromisoformat(str(data["createdAt"]))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return (stamp, str(data.get("id", "")))
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


def should_advance(old, new):
    if not old:
        return True
    old_key, new_key = decode(old), decode(new)
    if old_key is None or new_key is None:
        return True
    return new_key > old_key


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    path, new = argv[1], argv[2].strip()
    if not new:
        return
    # One lock around read, compare and replace, so two handlers that finish together cannot undo each other.
    lock = os.open(path + ".lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                old = handle.read().strip()
        except OSError:
            old = ""
        if not should_advance(old, new):
            return
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), prefix=".cursor.")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(new)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        os.close(lock)


if __name__ == "__main__":
    main(sys.argv)
