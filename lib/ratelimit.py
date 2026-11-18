#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""A simple cap on how many agent runs an account may start in a time window.

usage: ratelimit.py <file> <limit> <window-seconds>

Exit 0 and record the run when fewer than <limit> runs happened in the window; exit 1 (and record
nothing) when the cap is reached. A limit of 0 turns the cap off. Exit 2 means "could not tell" (a bad call, or a
file that cannot be opened).
"""
import fcntl
import math
import os
import sys
import time


def main(argv):
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    path = argv[1]
    try:
        limit, window = int(argv[2]), float(argv[3])
    except ValueError:
        sys.exit(2)
    if limit <= 0:
        return
    now = time.time()
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        stamps = []
        for line in handle.read().decode("utf-8", "replace").splitlines():
            try:
                stamp = float(line)
            except ValueError:
                continue
            if math.isfinite(stamp) and 0 <= now - stamp < window:  # damaged or future lines never count
                stamps.append(stamp)
        if len(stamps) >= limit:
            sys.exit(1)
        stamps.append(now)
        handle.seek(0)
        handle.truncate()
        handle.write(("\n".join("%.3f" % s for s in stamps) + "\n").encode("utf-8"))


if __name__ == "__main__":
    try:
        main(sys.argv)
    except OSError:  # exit 2 is "could not tell"; 0 (go) and 1 (cap reached) are the answers
        sys.exit(2)
