# SPDX-License-Identifier: Apache-2.0
"""Split a long reply into ordered chat lines that fit Spawn's 200-character limit."""
import textwrap

LINE_LIMIT = 200
# Room kept for the "(i/n) " marker: "(100/120) " is ten characters, so twelve leaves slack.
MARKER_ROOM = 12


def chunk(text, limit=LINE_LIMIT):
    """Return the lines to post, in order. A reply that fits in one line is returned unchanged.

    Whitespace is collapsed, because a chat line has no use for line breaks. Longer replies are
    wrapped on word boundaries and numbered "(1/3)", "(2/3)", ... so they read in order.
    """
    flat = " ".join(str(text).split())
    if not flat:
        return []
    if len(flat) <= limit:
        return [flat]
    parts = textwrap.wrap(flat, limit - MARKER_ROOM, break_long_words=True, break_on_hyphens=False)
    total = len(parts)
    return ["(%d/%d) %s" % (index, total, part) for index, part in enumerate(parts, 1)]
