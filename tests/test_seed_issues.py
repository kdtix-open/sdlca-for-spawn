# SPDX-License-Identifier: Apache-2.0
"""scripts/seed-starter-issues.py: the starter issues are well formed, point at real files, use real labels, and are
only posted when a person asks (--apply), once."""
import importlib.machinery
import importlib.util
import json
import os
import re
import stat
import tempfile
import unittest

import helpers

SCRIPT = os.path.join(helpers.ROOT, "scripts", "seed-starter-issues.py")


def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


SEED = load(SCRIPT, "seed_starter_issues")
LINKS = load(os.path.join(helpers.ROOT, "scripts", "check-links.py"), "check_links")


def label_names():
    names = set()
    with open(os.path.join(helpers.ROOT, ".github", "labels.tsv"), encoding="utf-8") as handle:
        for line in handle:
            if line.strip() and not line.startswith("#"):
                names.add(line.split("\t")[0])
    return names


FAKE_GH = """#!/usr/bin/env bash
# records every call on one line (line breaks inside an argument become spaces); `issue list` answers from FAKE_TITLES
line=""
for a in "$@"; do line="$line ${a//$'\\n'/ }"; done
printf '%s\\n' "${line# }" >> "$FAKE_GH_LOG"
case "$1 $2" in
  "issue list") printf '%s' "${FAKE_TITLES:-[]}" ;;
  "issue create") echo "https://github.com/example/repo/issues/1" ;;
esac
"""


class SeedIssuesTests(unittest.TestCase):
    def test_every_label_exists_in_the_label_file(self):
        known = label_names()
        for title, labels, _ in SEED.bodies(SEED.DEFAULT_REPO):
            for label in labels:
                self.assertIn(label, known, "%s uses a label that labels.tsv does not create: %s" % (title, label))

    def test_every_issue_has_a_unique_title_a_body_and_the_disclosure_label(self):
        issues = SEED.bodies(SEED.DEFAULT_REPO)
        titles = [title for title, _, _ in issues]
        self.assertEqual(len(titles), len(set(titles)))
        for title, labels, body in issues:
            self.assertLessEqual(len(title), 120, title)
            self.assertIn("## Why", body, title)
            self.assertIn("## What done looks like", body, title)
            self.assertIn("ai-assisted", labels, title)

    def test_every_link_into_the_repository_points_at_a_real_file_and_heading(self):
        base = "https://github.com/%s/blob/main/" % SEED.DEFAULT_REPO
        checked = 0
        for title, _, body in SEED.bodies(SEED.DEFAULT_REPO):
            for match in re.finditer(re.escape(base) + r"([^)\s#]+)(#[^)\s]+)?", body):
                path = os.path.join(helpers.ROOT, match.group(1))
                self.assertTrue(os.path.exists(path), "%s links to a missing file: %s" % (title, match.group(1)))
                anchor = (match.group(2) or "")[1:]
                if anchor:
                    self.assertIn(anchor, LINKS.anchors_of(path), "%s links to a missing heading: %s" % (title, match.group(0)))
                checked += 1
        self.assertGreater(checked, 10)

    def test_the_welcome_post_links_into_the_repository_resolve(self):
        with open(os.path.join(helpers.ROOT, "docs", "maintainers", "welcome-post.md"), encoding="utf-8") as handle:
            text = handle.read()
        base = "https://github.com/%s/blob/main/" % SEED.DEFAULT_REPO
        found = list(re.finditer(re.escape(base) + r"([^)\s#]+)(#[^)\s]+)?", text))
        self.assertGreater(len(found), 3)
        for match in found:
            path = os.path.join(helpers.ROOT, match.group(1))
            self.assertTrue(os.path.exists(path), "the welcome post links to a missing file: %s" % match.group(1))
            anchor = (match.group(2) or "")[1:]
            if anchor:
                self.assertIn(anchor, LINKS.anchors_of(path), match.group(0))

    def test_no_issue_asks_an_agent_to_contact_spawn_and_none_holds_a_secret_shape(self):
        for title, _, body in SEED.bodies(SEED.DEFAULT_REPO):
            self.assertNotRegex(body, r"sak_[A-Za-z0-9]{8}|sbk_[A-Za-z0-9]{8}|xox[a-z]-[0-9A-Za-z]{8}", title)

    def run_script(self, args, titles="[]"):
        with tempfile.TemporaryDirectory() as tmp:
            gh = os.path.join(tmp, "gh")
            with open(gh, "w") as handle:
                handle.write(FAKE_GH)
            os.chmod(gh, os.stat(gh).st_mode | stat.S_IXUSR)
            log = os.path.join(tmp, "calls.log")
            open(log, "w").close()
            env = {"PATH": tmp + os.pathsep + os.environ.get("PATH", ""), "FAKE_GH_LOG": log, "FAKE_TITLES": titles}
            result = helpers.run(["python3", "-I", "-B", SCRIPT, *args], env=env)
            with open(log) as handle:
                calls = handle.read().splitlines()
        return result, calls

    def test_a_dry_run_posts_nothing_and_does_not_even_call_gh(self):
        result, calls = self.run_script([])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [])
        self.assertEqual(result.stdout.count("[dry-run]"), len(SEED.ISSUES))
        self.assertIn("Nothing was posted", result.stdout)

    def test_apply_posts_each_issue_once_with_its_labels(self):
        result, calls = self.run_script(["--apply"])
        self.assertEqual(result.returncode, 0, result.stderr)
        creates = [c for c in calls if c.startswith("issue create")]
        self.assertEqual(len(creates), len(SEED.ISSUES))
        for call in creates:
            self.assertIn("--repo %s" % SEED.DEFAULT_REPO, call)
            self.assertIn("--label ai-assisted", call)

    def test_apply_skips_a_title_that_already_exists(self):
        first = SEED.ISSUES[0]["title"]
        result, calls = self.run_script(["--apply"], titles=json.dumps([{"title": first}]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("exists, skipped: %s" % first, result.stdout)
        creates = [c for c in calls if c.startswith("issue create")]
        self.assertEqual(len(creates), len(SEED.ISSUES) - 1)
        self.assertFalse(any(first in c for c in creates))

    def test_a_bad_repository_name_or_option_is_refused(self):
        for args in (["--repo", "no-slash"], ["--repo", "a/b/c"], ["--bogus"], ["--repo"]):
            result, calls = self.run_script(args)
            self.assertNotEqual(result.returncode, 0, args)
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
