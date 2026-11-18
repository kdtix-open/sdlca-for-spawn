# SPDX-License-Identifier: Apache-2.0
"""scripts/check-secrets.sh finds what it promises to find, and leaves harmless look-alikes alone.

Every fake secret is built from pieces at run time, so this file itself holds nothing the scanner would flag.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

import helpers

SCRIPT = os.path.join(helpers.ROOT, "scripts", "check-secrets.sh")
BODY = "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0"  # 40 harmless characters


def hexlike(n):
    return ("0123456789abcdef" * 4)[:n]


# name -> the text of a file that must be refused
MUST_FIND = {
    "spawn-token": "token = " + "sak" + "_" + BODY[:30],
    "spawn-invite": "invite = " + "sbk" + "_" + hexlike(32),
    "spawn-invite-mixed-case": "invite = " + "sbk" + "_" + BODY[:30],
    "slack-bot": "t = " + "xox" + "b-" + "1234567890-abcdefghij",
    "slack-other": "t = " + "xox" + "e-" + "1234567890-abcdefghij",
    "slack-app": "t = " + "xapp" + "-1-A0123456789-abcdef",
    "slack-webhook": "u = https://" + "hooks.slack" + ".com/services/" + "T0123ABCD/B0123ABCD/" + BODY[:24],
    "github-classic": "t = " + "ghp" + "_" + BODY[:36],
    "github-fine": "t = " + "github" + "_pat_" + BODY[:36],
    "gitlab": "t = " + "glpat" + "-" + BODY[:24],
    "anthropic": "k = " + "sk" + "-ant-" + BODY[:30],
    "openai-project": "k = " + "sk" + "-proj-" + BODY[:30],
    "provider-legacy": "k = " + "sk" + "-" + BODY,
    "stripe-live": "k = " + "sk" + "_live_" + BODY[:28],
    "google": "k = " + "AI" + "za" + BODY[:35],
    "aws": "k = " + "AK" + "IA" + "ABCDEFGHIJKLMNOP",
    "aws-session": "k = " + "AS" + "IA" + "ABCDEFGHIJKLMNOP",
    "hugging-face": "k = " + "hf" + "_" + BODY[:34],
    "npm": "k = " + "npm" + "_" + BODY[:36],
    "jwt": "k = " + "ey" + "J" + BODY[:20] + "." + "ey" + "J" + BODY[:20] + "." + BODY[:10],
    "password-in-url": "u = https://" + "someone" + ":" + "hunter2hunter2" + "@" + "example.invalid/repo.git",
    "assigned-provider-key": "ANTHROPIC" + "_API_KEY=" + BODY[:30],
    "private-key": "-----BEGIN " + "OPENSSH PRIVATE" + " KEY-----",
    "pgp-private-key": "-----BEGIN PGP " + "PRIVATE KEY" + " BLOCK-----",
}

# things the docs and tests write on purpose: placeholders, short fixtures, prose about tokens
MUST_ALLOW = [
    "Tokens start with sak_ and invites with sbk_.",
    "SPAWN_TOKEN_FILE=/home/you/.sdlca/spawn/accounts/alice/token",
    "--invite sbk_<code-from-the-prompt>",
    "--invite 'sbk_PASTE_THE_CODE_HERE'",
    "export SDLCA_SLACK_BOT_TOKEN='xoxb-...'",
    "fake = sak_test_token and sak_short",
    "ANTHROPIC_API_KEY=... (your own key)",
    "git clone https://github.com/kdtix-open/sdlca-for-spawn.git",
    "https://git.spawn.co/@alice/game-1.git and https://www.spawn.co@elsewhere.example",
    "Authorization: Bearer <token>",
    "-----BEGIN and the word PRIVATE KEY in prose",
]


class CheckSecretsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        os.makedirs(os.path.join(self.repo, "scripts"))
        shutil.copy(SCRIPT, os.path.join(self.repo, "scripts", "check-secrets.sh"))
        subprocess.run(["git", "init", "-q", self.repo], check=True, capture_output=True,
                       env={"PATH": os.environ["PATH"], "HOME": self.tmp.name})

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, text):
        path = os.path.join(self.repo, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(text + "\n")

    def check(self):
        return helpers.run(["bash", os.path.join(self.repo, "scripts", "check-secrets.sh")], cwd=self.repo)

    def test_a_clean_tree_passes(self):
        self.put("notes.md", "nothing to see here")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no secrets found", result.stdout)

    def test_every_kind_of_secret_is_found_and_named(self):
        for name, text in MUST_FIND.items():
            with self.subTest(kind=name):
                self.put("cases/%s.txt" % name, text)
                result = self.check()
                self.assertEqual(result.returncode, 1, "%s was not found: %s" % (name, result.stdout))
                self.assertIn("cases/%s.txt:1" % name, result.stdout)
                os.remove(os.path.join(self.repo, "cases", "%s.txt" % name))

    def test_harmless_look_alikes_are_left_alone(self):
        self.put("docs/prose.md", "\n".join(MUST_ALLOW))
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_deliberate_fixture_can_carry_the_allow_marker(self):
        line = "u = https://" + "someone" + ":" + "hunter2hunter2" + "@" + "example.invalid/x.git"
        self.put("tests/fixture.py", line + "  # check-secrets:allow (made up)")
        self.assertEqual(self.check().returncode, 0)
        self.put("tests/fixture2.py", line)
        self.assertEqual(self.check().returncode, 1)

    def test_the_report_never_prints_the_secret_itself(self):
        self.put("leak.txt", MUST_FIND["spawn-token"])
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(BODY[:30], result.stdout + result.stderr)

    def test_files_git_would_ignore_are_not_scanned_but_untracked_ones_are(self):
        self.put(".gitignore", "ignored/\n")
        self.put("ignored/secret.txt", MUST_FIND["spawn-token"])
        self.assertEqual(self.check().returncode, 0)
        self.put("new-file.txt", MUST_FIND["spawn-token"])
        self.assertEqual(self.check().returncode, 1)


if __name__ == "__main__":
    unittest.main()
