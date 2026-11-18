#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check that every relative link and heading anchor in the Markdown files resolves.

usage: check-links.py [file-or-directory ...]     (default: the whole repository)

It follows GitHub's rules for heading anchors, ignores code blocks, and does not touch the network:
links that start with a scheme (https:, mailto:) are not checked. Exit status 1 if anything is broken.
"""
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "node_modules", "design", "__pycache__"}
LINK = re.compile(r"!?\[(?:[^\]\\]|\\.)*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^ {0,3}(```|~~~)")


def slug(text):
    """GitHub's heading anchor: lower-case, drop punctuation, spaces become hyphens."""
    text = re.sub(r"<[^>]+>", "", text)  # inline html
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links keep their text
    text = text.strip().lower()
    out = []
    for ch in text:
        category = unicodedata.category(ch)
        if ch in " -":
            out.append("-")
        elif ch == "_" or category[0] in "LN" or category in ("Mn", "Mc"):
            out.append(ch)
    return "".join(out)


def anchors_of(path, cache={}):
    if path in cache:
        return cache[path]
    seen, found, in_fence = {}, set(), False
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            match = HEADING.match(line)
            if not match:
                continue
            base = slug(match.group(2))
            count = seen.get(base, 0)
            seen[base] = count + 1
            found.add(base if count == 0 else "%s-%d" % (base, count))
    cache[path] = found
    return found


def markdown_files(targets):
    for target in targets:
        if os.path.isfile(target):
            yield target
            continue
        for folder, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in sorted(files):
                if name.endswith(".md"):
                    yield os.path.join(folder, name)


def problems_in(path):
    base = os.path.dirname(path)
    in_fence = False
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            line = re.sub(r"`[^`]*`", "", line)  # inline code
            for target in LINK.findall(line):
                if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("{{"):
                    continue
                file_part, _, anchor = target.partition("#")
                resolved = path if not file_part else os.path.normpath(os.path.join(base, file_part))
                if not os.path.exists(resolved):
                    yield number, "missing file: %s" % target
                elif anchor and resolved.endswith(".md") and os.path.isfile(resolved):
                    if anchor.lower() not in anchors_of(resolved):
                        yield number, "missing anchor: %s" % target


def main(argv):
    targets = argv[1:] or [ROOT]
    broken = 0
    for path in markdown_files(targets):
        for number, message in problems_in(path):
            print("%s:%d: %s" % (os.path.relpath(path, ROOT), number, message))
            broken += 1
    if broken:
        print("%d broken link(s)" % broken)
        return 1
    print("links ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
