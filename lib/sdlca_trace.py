# SPDX-License-Identifier: Apache-2.0
"""One line of JSON for the account's trace file, the same shape as lib/common.sh's trace(): when (ts, ms), which turn, what happened, and the facts.

The file is $ACC/trace.jsonl (the account's folder; SDLCA_TRACE=0 turns it off). Only whole numbers and short plain text go in: a value is cut to
200 characters and every character outside letters, digits and . _ : @ / - and space becomes an underscore, so a chat line, a token or a quote cannot
get into it. It never fails its caller. `sdlca-trace` reads it (docs/observability.md).
"""
import json
import os
import re
import time

UNSAFE = re.compile(r"[^A-Za-z0-9._:@/ -]")
MAX_BYTES = 4 * 1024 * 1024


def emit(event, **fields):
    folder = os.environ.get("ACC")
    if not folder or os.environ.get("SDLCA_TRACE") == "0":
        return
    record = {"ts": int(time.time() * 1000), "turn": os.environ.get("SDLCA_TURN_ID") or "-", "ev": UNSAFE.sub("_", str(event))[:60]}
    for key, value in fields.items():
        key = re.sub(r"[^A-Za-z0-9_]", "_", str(key))
        if isinstance(value, bool):
            value = int(value)
        record[key] = int(value) if isinstance(value, (int, float)) and value == value and abs(value) < 1e15 else UNSAFE.sub("_", str(value))[:200]
    path = os.path.join(folder, "trace.jsonl")
    try:
        if os.path.getsize(path) > MAX_BYTES:
            os.replace(path, path + ".1")
    except OSError:
        pass
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    except OSError:
        pass
