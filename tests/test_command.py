# SPDX-License-Identifier: Apache-2.0
"""lib/command.py: the owner's presence commands, and nothing else, are commands."""
import json
import os
import unittest

import helpers

SCRIPT = os.path.join(helpers.ROOT, "lib", "command.py")


def run(text, sender="@alice", kind="chat_mention", env=None):
    event = json.dumps({"kind": kind, "chat": {"from": sender, "text": text}})
    full = {"OWNER": "alice"}
    full.update(env or {})
    result = helpers.run(["python3", "-I", "-B", SCRIPT], env=full, stdin=event)
    return result.stdout.strip()


class CommandTests(unittest.TestCase):
    def test_the_commands(self):
        self.assertEqual(run("/spawn"), "join 3600")
        self.assertEqual(run("@@alice_helper /spawn"), "join 3600")
        self.assertEqual(run("@@alice_helper /spawn ttl 600"), "join 600")
        self.assertEqual(run("/SPAWN TTL 600"), "join 600")
        self.assertEqual(run("@@a /leave"), "leave")
        self.assertEqual(run("/spawn", env={"SDLCA_PRESENCE_TTL": "900"}), "join 900")
        self.assertEqual(run("/spawn", env={"SDLCA_PRESENCE_TTL": "abc"}), "join 3600")

    def test_everything_else_goes_to_the_agent(self):
        for text in ("/spawn now please", "please /spawn", "/spawn ttl", "/spawn ttl 5", "/spawn ttl 99999", "/spawn ttl -1", "/spawn ttl 6e2", "/leave now", "hello", ""):
            self.assertEqual(run(text), "-", text)

    def test_only_the_owner_can_give_one(self):
        self.assertEqual(run("/spawn", sender="@carol"), "-")
        self.assertEqual(run("/spawn", sender="@@alice_helper"), "-")
        self.assertEqual(run("/spawn", env={"OWNER": ""}), "-")
        self.assertEqual(run("/spawn", kind="friend_request"), "-")

    def test_odd_input_is_not_a_command(self):
        result = helpers.run(["python3", "-I", "-B", SCRIPT], env={"OWNER": "alice"}, stdin="not json")
        self.assertEqual(result.stdout.strip(), "-")


if __name__ == "__main__":
    unittest.main()
