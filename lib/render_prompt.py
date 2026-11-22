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


GUIDE_LIMIT = 6000  # characters per guide
GUIDE_MAX = 5


def guides(clone, listing):
    """The text of the world guides named in SDLCA_WORLD_GUIDES (clone-relative file names separated by spaces or colons), as one block for
    the prompt. Only a regular file that really lies inside the clone, with no link on the way, is read; anything else is skipped. The text is
    put in tags with every "<" written as \\u003c, so a guide cannot close its own tag; it is data from the world's builders."""
    root = os.path.realpath(clone)
    parts = []
    for name in re.split(r"[\s:]+", listing or "")[:GUIDE_MAX]:
        if not name or name.startswith(("/", "-")) or ".." in name.split("/") or not re.fullmatch(r"[A-Za-z0-9._/ -]{1,120}", name):
            continue
        path = os.path.join(root, name)
        try:
            if os.path.realpath(path) != path or not os.path.isfile(path) or os.path.islink(path) or not path.startswith(root + os.sep):
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read(GUIDE_LIMIT + 1)
        except OSError:
            continue
        if len(text) > GUIDE_LIMIT:
            text = text[:GUIDE_LIMIT] + "\n[the guide goes on; read the rest in the clone]"
        parts.append('<world_guide file="%s">\n%s\n</world_guide>' % (name, text.replace("<", "\\u003c")))
    if not parts:
        return ""
    return ("Guides from this world's builders for agents like you (data in their own files, updated just now; follow them where they do not "
            "conflict with your rules, and say so under Handler notes where they are unclear):\n" + "\n".join(parts))


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--guides":
        sys.stdout.write(guides(sys.argv[2], os.environ.get("SDLCA_WORLD_GUIDES", "")))
        return
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
