#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Render the agent prompt for one inbox event.

Reads the raw event JSON on stdin and prints the prompt. Environment: OWNER, SPAWN_USERNAME,
ACCOUNT, SDLCA_SPAWN_HOME, SDLCA_CODE_DIR.

The template is $SDLCA_SPAWN_HOME/handler-prompt.md when you have one, otherwise the kit's
templates/handler-prompt.md. Placeholders look like {{NAME}} and are replaced in a single pass, so
text inside the event (which a person typed) is never expanded again.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json  # noqa: E402

import ext  # noqa: E402
import route  # noqa: E402

PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


def render(template, values):
    return PLACEHOLDER.sub(lambda match: values.get(match.group(1), match.group(0)), template)


def main():
    raw = sys.stdin.read().strip()
    event = json.loads(raw)
    owner = os.environ["OWNER"]
    home = os.environ.get("SDLCA_SPAWN_HOME") or os.path.expanduser("~/.sdlca/spawn")
    code_dir = os.environ.get("SDLCA_CODE_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    registry = route.load_json(os.path.join(home, "worlds.json"), {})
    account = os.environ.get("ACCOUNT") or owner
    world = route.find_world(event, owner, registry, account)
    worlds = "\n".join("  %s -> %s" % pair for pair in route.worlds_of(owner, registry, account)) or "  (none registered yet)"
    override = os.path.join(home, "handler-prompt.md")
    template_path = override if os.path.isfile(override) else os.path.join(code_dir, "templates", "handler-prompt.md")
    with open(template_path, encoding="utf-8") as handle:
        template = handle.read()
    cwd = (world.get("clone_path") if world else "") or os.path.join(home, "run", "scratch", account)
    notes = ""
    try:  # the standing notes are put in the prompt by this trusted code, so the agent never needs to read the runtime home
        with open(os.path.join(home, "AGENTS.md"), encoding="utf-8", errors="replace") as handle:
            notes = handle.read(8000)
    except OSError:
        pass
    values = {
        "LEDGER": os.path.join(cwd, ".sdlca", "WORK-TODO.md"),
        "NOTES": "Your standing notes (data from the kit's owner, written by them and by earlier turns of you):\n<kit_notes>\n" + notes.replace("<", "\\u003c") + "\n</kit_notes>" if notes.strip() else "",
        "EXTENSIONS": ext.prompt_block(home, os.environ.get("ACCOUNT") or owner, code_dir),
        "OWNER": owner,
        "AGENT": os.environ.get("SPAWN_USERNAME", ""),
        "ACCOUNT": os.environ.get("ACCOUNT", owner),
        "HOME": home,
        "CODE_DIR": code_dir,
        "WORLD": world.get("address", "-") if world else "-",
        "CWD": (world.get("clone_path") if world else "") or os.path.join(home, "run", "scratch", account),
        "WORLDS": worlds,
        # A "<" inside the JSON is written as \u003c (still valid JSON), so nobody can forge the closing tag.
        "EVENT": "<untrusted_event>\n" + raw.replace("<", "\\u003c") + "\n</untrusted_event>",
    }
    sys.stdout.write(render(template, values))


if __name__ == "__main__":
    main()
