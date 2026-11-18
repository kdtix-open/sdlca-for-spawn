# SPDX-License-Identifier: Apache-2.0
import os
import tempfile
import unittest

import helpers

SCRIPT = os.path.join(helpers.ROOT, "scripts", "check-links.py")


class LinkCheckTests(unittest.TestCase):
    def check(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in files.items():
                path = os.path.join(tmp, name)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as handle:
                    handle.write(text)
            result = helpers.run(["python3", "-I", "-B", SCRIPT, tmp])
            return result.returncode, result.stdout

    def test_good_links_pass(self):
        code, out = self.check({
            "a.md": "# Title\n\nSee [b](docs/b.md) and [section](docs/b.md#second-part) and [here](#title).\n",
            "docs/b.md": "# B\n\n## Second part\n\n## Second part\n",
        })
        self.assertEqual((code, out.strip()), (0, "links ok"))

    def test_missing_files_and_anchors_are_reported(self):
        code, out = self.check({"a.md": "[x](nope.md) [y](#nowhere) [z](b.md#absent)\n", "b.md": "# B\n"})
        self.assertEqual(code, 1)
        self.assertIn("missing file: nope.md", out)
        self.assertIn("missing anchor: #nowhere", out)
        self.assertIn("missing anchor: b.md#absent", out)

    def test_github_slugs(self):
        code, out = self.check({"a.md": "# What it is, and why (really)\n\n[ok](#what-it-is-and-why-really)\n"})
        self.assertEqual(code, 0, out)

    def test_duplicate_headings_get_numeric_suffixes(self):
        code, out = self.check({"a.md": "# A\n## Same\n## Same\n[two](#same-1)\n"})
        self.assertEqual(code, 0, out)

    def test_code_blocks_urls_and_inline_code_are_ignored(self):
        code, out = self.check({"a.md": "```\n[x](missing.md)\n```\n`[y](missing.md)` and [web](https://example.invalid/x) and [mail](mailto:a@example.invalid)\n"})
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
