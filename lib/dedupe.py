#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Remember which inbox events were already handled, so a replay after a restart does not run them twice.

usage:
  dedupe.py seen <file> <event-id>    exit 0 if the id is recorded, 1 if not
  dedupe.py add  <file> <event-id>    record it (the newest 500 ids are kept)

Exit 2 means "could not tell" (a bad call, or a file that cannot be opened); a caller should treat that as "not seen".
"""
import fcntl
import os
import re
import sys

KEEP = 500
EVENT_ID = re.compile(r"[A-Za-z0-9_-]{1,80}")


def read_ids(handle):
    handle.seek(0)
    return [line.strip() for line in handle.read().decode("utf-8", "replace").splitlines() if line.strip()]


def main(argv):
    if len(argv) != 4 or argv[1] not in ("seen", "add") or not EVENT_ID.fullmatch(argv[3]):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    mode, path, event_id = argv[1:]
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        ids = read_ids(handle)
        if mode == "seen":
            sys.exit(0 if event_id in ids else 1)
        if event_id not in ids:
            ids.append(event_id)
        handle.seek(0)
        handle.truncate()
        handle.write(("\n".join(ids[-KEEP:]) + "\n").encode("utf-8"))


if __name__ == "__main__":
    try:
        main(sys.argv)
    except OSError:  # exit 2 is "could not tell"; 0 and 1 are the answers
        sys.exit(2)
