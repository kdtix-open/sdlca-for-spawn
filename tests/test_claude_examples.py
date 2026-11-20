# SPDX-License-Identifier: Apache-2.0
"""Every example of the Claude Code command in the kit's templates and docs must pass --setting-sources user.

In print mode (-p) Claude Code skips the question about trusting a folder, and with its default settings it loads the folder's own
.claude/settings.json (hooks) and .mcp.json (MCP servers). The kit runs the agent inside world clones that other people can push to,
so those files would run a command on the machine before any tool rule applies. --setting-sources user loads only the user's own
settings (docs/security-model.md has the facts and the date). This test keeps an example from being added, or edited, without it.

What counts as an example: the word claude (alone, or at the end of a path such as ~/.local/bin/claude) followed, on the same line, by a
standalone -p or --print, with any options between them (claude --model <id> -p ...). A command that a backslash wraps onto the next
lines is read as one line. Where the search looks: the starter files (templates/), every page of the documentation (docs/), the scripts
(scripts/), the issue forms and the other files under .github/, and the Markdown files at the top. Binary files (a picture, a model) are
not read. The two issue forms were brought in line on 2026-11-20, with a person's approval (AGENTS.md, rule 3).
"""
import os
import re
import unittest

import helpers

ROOT = helpers.ROOT
# The examples this test reads: the starter files, every page of the documentation, the scripts, the files under .github/ and the Markdown files at the top.
SKIP_DIRS = {".git", "node_modules", "design", "__pycache__"}
BINARY = (".glb", ".gltf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".zip", ".gz", ".ktx2")  # never text, so never read as text
# The word claude as a command: not part of another word, a model id (claude-sonnet-5-5), a folder (.claude/) or an address (claude.ai), and with
# an optional path before it. Whatever follows it, up to the end of the example, is looked at for -p or --print.
CLAUDE = re.compile(r"(?<![\w.-])(?:[\"']?[\w$~{}./-]*/)?claude(?![\w-]|\.\w)")
PRINT = re.compile(r"(?<![\w-])(?:-p|--print)(?![\w-])")
# The value of --setting-sources, with or without quotes around it.
SOURCES = re.compile(r"--setting-sources(?:\s+|=)[\"']?([^\s`'\"]*)")


def example_files():
    for folder in ("templates", "docs", "scripts", ".github"):
        for base, dirs, names in os.walk(os.path.join(ROOT, folder)):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(names):
                if not name.lower().endswith(BINARY):
                    yield os.path.join(base, name)
    for name in sorted(os.listdir(ROOT)):
        if name.endswith(".md") and os.path.isfile(os.path.join(ROOT, name)):
            yield os.path.join(ROOT, name)


def logical_lines(text):
    """(number of the first line, the line) where a backslash at the end of a line joins the next one: a shell command wrapped over several lines."""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        start, joined = index + 1, lines[index]
        while joined.rstrip().endswith("\\") and index + 1 < len(lines):
            index += 1
            joined = joined.rstrip()[:-1] + " " + lines[index].strip()
        yield start, joined
        index += 1


def examples(text):
    """(line number, the example) for every use of the command in print mode. An example runs from `claude` to the end of the line, or
    to the backtick or the single quote that closes it, which is where the docs and the env file put the end of a command. It is one
    only when a standalone -p or --print comes in it."""
    for number, line in logical_lines(text):
        for match in CLAUDE.finditer(line):
            end = len(line)
            for stop in ("`", "'"):
                found = line.find(stop, match.end())
                if found != -1:
                    end = min(end, found)
            if PRINT.search(line, match.end(), end):
                yield number, line[match.start():end]


def problem(example):
    """Why an example is wrong, or None. It must carry --setting-sources once, and its value must be exactly user (a list such as
    user,project would load the folder's own settings again)."""
    values = SOURCES.findall(example)
    if not values:
        return "it does not pass --setting-sources user"
    if values != ["user"]:
        return "it passes --setting-sources %s, and the only value that keeps a world's own settings out is user" % " and ".join(values)
    return None


class ExampleTests(unittest.TestCase):
    def test_every_example_of_the_claude_command_passes_setting_sources_user(self):
        found = []
        for path in example_files():
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            for number, example in examples(text):
                why = problem(example)
                if why:
                    found.append("%s:%d: %s: %s" % (os.path.relpath(path, ROOT), number, why, example))
        self.assertEqual(found, [], "\n" + "\n".join(found))

    def test_the_search_really_finds_the_examples(self):
        """A test that finds nothing passes by itself. These files hold examples of the command, and the search must see them."""
        counts = {}
        for path in example_files():
            with open(path, encoding="utf-8") as handle:
                counts[os.path.relpath(path, ROOT)] = len(list(examples(handle.read())))
        self.assertGreaterEqual(counts["templates/account.env.example"], 4)  # read-only, read-only with sight, builder, full autonomy
        self.assertGreaterEqual(counts["docs/configuration.md"], 6)
        self.assertGreaterEqual(counts["docs/getting-started.md"], 3)  # read-only, read-only with sight, builder
        self.assertGreaterEqual(counts[".github/ISSUE_TEMPLATE/bug_report.yml"], 1)  # the two issue forms
        self.assertGreaterEqual(counts[".github/ISSUE_TEMPLATE/agent_behavior.yml"], 1)
        self.assertGreaterEqual(sum(counts.values()), 14)

    def test_the_checker_flags_what_it_must(self):
        bad = [
            'claude -p --allowedTools "Read"',
            "claude -p",
            "claude --print --permission-mode bypassPermissions",
            "claude -p --setting-sources project",
            "claude -p --setting-sources user,project",
            "claude -p --setting-sources local,user",
            "claude -p --setting-sources user --setting-sources project",
            "claude -p --setting-sources",
            "claude -p --setting-sources users",
            "claude -p --setting-sources=project",
            "claude -p --setting-sources ''",
            'claude -p --setting-sources "user,project"',
            "claude -p --setting-sources 'project'",
            'claude --model sonnet -p --allowedTools "Read"',
            "claude --permission-mode bypassPermissions -p",
        ]
        for example in bad:
            self.assertIsNotNone(problem(example), example)
        good = [
            "claude -p --setting-sources user",
            "claude -p --setting-sources user --allowedTools \"Read\"",
            "claude -p --allowedTools \"Read\" --setting-sources user",
            "claude -p --setting-sources=user --permission-mode bypassPermissions",
            "claude --print --setting-sources user",
            'claude -p --setting-sources "user" --allowedTools "Read"',
            "claude -p --setting-sources='user'",
            "claude --model sonnet -p --setting-sources user",
        ]
        for example in good:
            self.assertIsNone(problem(example), example)

    def test_the_search_sees_every_way_of_writing_the_command(self):
        """An example with another option before -p, a path in front of claude, or a command wrapped over lines is still an example. Each of these is
        found, and each is refused for lacking --setting-sources user."""
        spellings = (
            "SDLCA_AGENT_CMD='claude --model claude-sonnet-5-5 -p --allowedTools \"Read\"'",
            "claude --permission-mode acceptEdits --print",
            'claude --allowedTools "Read" -p',
            "/home/u/.local/bin/claude -p",
            "~/.local/bin/claude -p",
            '"$HOME/.local/bin/claude" -p',
            'claude "$@" -p',
            "claude --dangerously-skip-permissions -p",
            "env FOO=1 claude -p",
            "claude   -p",
            "| Pinned | `claude --model <model-id> -p --allowedTools \"Read\"` | Read files |",
            "SDLCA_AGENT_CMD='claude \\\n  -p \\\n  --allowedTools \"Read\"'",
            "SDLCA_AGENT_CMD='claude \\\n  --model x \\\n  --print'",
        )
        for spelling in spellings:
            with self.subTest(spelling=spelling):
                found = list(examples(spelling))
                self.assertEqual(len(found), 1, "the search does not see this example")
                self.assertEqual(found[0][0], 1)
                self.assertIsNotNone(problem(found[0][1]))
        wrapped = "SDLCA_AGENT_CMD='claude \\\n  -p \\\n  --setting-sources user \\\n  --allowedTools \"Read\"'"
        self.assertEqual([problem(example) for _, example in examples(wrapped)], [None])  # the option on a wrapped line counts
        later = "one\ntwo\n" + wrapped
        self.assertEqual([number for number, _ in examples(later)], [3])  # and the line number is the first line of the command

    def test_what_is_not_an_example_is_left_alone(self):
        for text in ("claude --help", "`claude --help` says that `-p` skips the question", "see claude.ai for -p", "code.claude.com/docs/en/headless -p",
                     "~/.claude/settings.json -p", ".claude/settings.json and -p", "claude-sonnet-5-5 -p", "Claude Code -p", "claude-code --print",
                     "the claudex tool -p", "Assisted-by: Claude Code claude-sonnet-5-5"):
            with self.subTest(text=text):
                self.assertEqual(list(examples(text)), [], text)

    def test_the_search_cuts_an_example_where_the_docs_end_it(self):
        text = (
            "SDLCA_AGENT_CMD='claude -p --setting-sources user --allowedTools \"Read\"'\n"
            "| Read-only | `claude -p --setting-sources user --allowedTools \"Read\"` | Read files | a second `claude -p` is another example |\n"
            "(for example `claude -p`, `codex exec`)\n"
            "Print mode (`-p`) skips the question about trusting a folder; claude --help says so.\n"
            "The flag takes a comma-separated list, and claude -p --setting-sources user is the safe one.\n"
        )
        found = [(number, example) for number, example in examples(text)]
        self.assertEqual([number for number, _ in found], [1, 2, 2, 3, 5])
        self.assertEqual([problem(example) is None for _, example in found], [True, True, False, False, True])
        self.assertEqual(found[1][1], 'claude -p --setting-sources user --allowedTools "Read"')
        self.assertEqual(found[2][1], "claude -p")

    def test_read_only_with_sight_is_the_read_only_example_plus_the_one_rule_everywhere(self):
        """The posture that lets the agent see is the read-only one plus the sdlca-look rule and nothing else, in the starter file and in both pages
        that show it. A rule that is added, dropped or changed in one place and not in the others is how a posture gets wider than the page says."""
        rule = '"Bash($SDLCA_CODE_DIR/bin/sdlca-look *)"'
        read_only, sight = set(), set()
        for name in ("templates/account.env.example", "docs/getting-started.md", "docs/configuration.md"):
            with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
                found = [example for _, example in examples(handle.read())]
            here_read_only = {e for e in found if '"Read"' in e and "sdlca-api GET" in e and "sdlca-look" not in e and "git" not in e}
            here_sight = {e for e in found if "sdlca-look" in e and "sdlca-api GET" in e and "git" not in e}
            self.assertTrue(here_read_only, name + " has no read-only example")
            self.assertTrue(here_sight, name + " has no read-only with sight example")
            read_only |= here_read_only
            sight |= here_sight
        self.assertEqual(len(read_only), 1, read_only)  # one command, spelled the same in every place
        self.assertEqual(sight, {next(iter(read_only)) + " " + rule})

    def test_the_look_time_limit_and_the_model_tip_are_documented_where_they_are_needed(self):
        for name, wanted in (("templates/account.env.example", ("SDLCA_LOOK_TIMEOUT",)), ("docs/configuration.md", ("SDLCA_LOOK_TIMEOUT", "--model <model-id>")),
                             ("docs/operations.md", ("sdlca-look --check",))):
            with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
                text = handle.read()
            for needle in wanted:
                self.assertIn(needle, text, name)

    def test_examples_for_other_tools_are_left_alone(self):
        """--setting-sources is a Claude Code option. A tool that has no such option must not be told to take it."""
        with open(os.path.join(ROOT, "docs", "configuration.md"), encoding="utf-8") as handle:
            lines = [line for line in handle.read().splitlines() if re.search(r"codex exec|opencode run|cursor-agent|gemini -p", line)]
        self.assertGreaterEqual(len(lines), 4)  # the four unverified examples
        for line in lines:
            self.assertNotIn("--setting-sources", line)
            self.assertEqual(list(examples(line)), [], line)  # and none of them is mistaken for a Claude Code example


if __name__ == "__main__":
    unittest.main()
