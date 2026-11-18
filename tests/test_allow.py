# SPDX-License-Identifier: Apache-2.0
import json
import os
import tempfile
import unittest

import helpers


class AllowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {"SDLCA_SPAWN_HOME": self.tmp.name}

    def tearDown(self):
        self.tmp.cleanup()

    def allow(self, *args):
        return helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-allow"), *args], env=self.env)

    def data(self):
        with open(os.path.join(self.tmp.name, "allowlist.json")) as handle:
            return json.load(handle)

    def test_add_and_remove_slack_members(self):
        self.assertEqual(self.allow("slack", "add", "dana", "U0123ABCD").returncode, 0)
        self.assertEqual(self.data()["slack"]["members"], [{"username": "dana", "id": "U0123ABCD"}])
        self.allow("slack", "add", "dana.renamed", "U0123ABCD")
        self.assertEqual(len(self.data()["slack"]["members"]), 1)
        self.allow("slack", "remove", "U0123ABCD")
        self.assertEqual(self.data()["slack"]["members"], [])

    def test_extra_spawn_senders_are_per_owner(self):
        self.allow("spawn", "add", "alice", "carol")
        self.allow("spawn", "add", "alice", "carol")
        self.assertEqual(self.data()["spawn"], {"alice": ["carol"]})
        self.allow("spawn", "remove", "alice", "carol")
        self.assertEqual(self.data()["spawn"], {"alice": []})

    def test_agents_can_be_named_with_a_double_at(self):
        self.assertEqual(self.allow("spawn", "add", "alice", "@@review_bot").returncode, 0)
        self.assertEqual(self.allow("spawn", "add", "alice", "@carol").returncode, 0)
        self.assertEqual(self.data()["spawn"], {"alice": ["@@review_bot", "@carol"]})
        self.assertNotEqual(self.allow("spawn", "add", "alice", "@@@x").returncode, 0)
        self.assertNotEqual(self.allow("spawn", "add", "@@alice", "x").returncode, 0)

    def test_rejects_malformed_ids_and_names(self):
        self.assertNotEqual(self.allow("slack", "add", "x", "not-an-id").returncode, 0)
        self.assertNotEqual(self.allow("spawn", "add", "alice", "Bad Name").returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "allowlist.json")))

    def test_file_is_private(self):
        self.allow("slack", "add", "dana", "U0123ABCD")
        self.assertEqual(os.stat(os.path.join(self.tmp.name, "allowlist.json")).st_mode & 0o777, 0o600)

    def test_list_works_on_a_fresh_home(self):
        result = self.allow("list")
        self.assertEqual(result.returncode, 0)
        self.assertIn("members", result.stdout)

    def test_a_trailing_line_break_is_not_accepted_in_an_id_or_a_name(self):
        self.assertNotEqual(self.allow("slack", "add", "x", "U0123ABCD\n").returncode, 0)
        self.assertNotEqual(self.allow("spawn", "add", "alice\n", "carol").returncode, 0)
        self.assertNotEqual(self.allow("spawn", "add", "alice", "carol\n").returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "allowlist.json")))

    def test_the_folder_and_the_file_it_creates_are_private(self):
        home = os.path.join(self.tmp.name, "fresh")
        self.env = {"SDLCA_SPAWN_HOME": home}
        self.assertEqual(self.allow("spawn", "add", "alice", "carol").returncode, 0)
        self.assertEqual(os.stat(home).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(os.path.join(home, "allowlist.json")).st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
