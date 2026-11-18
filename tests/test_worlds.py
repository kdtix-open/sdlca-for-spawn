# SPDX-License-Identifier: Apache-2.0
import json
import os
import subprocess
import tempfile
import unittest

import helpers


def git(*args, cwd=None):
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "PATH": os.environ["PATH"], "HOME": tempfile.gettempdir()}
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)


class WorldsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.bare = os.path.join(t, "remote.git")
        git("init", "--bare", "-b", "main", self.bare)
        seed = os.path.join(t, "seed")
        git("init", "-b", "main", seed)
        with open(os.path.join(seed, "AGENTS.md"), "w") as handle:
            handle.write("# a world\n")
        git("add", ".", cwd=seed)
        git("commit", "-m", "born", cwd=seed)
        git("push", self.bare, "main", cwd=seed)
        self.origin = os.path.join(t, "origin")
        os.makedirs(os.path.join(self.origin, "api", "agent", "v1"))
        self.token = os.path.join(t, "token")
        with open(self.token, "w") as handle:
            handle.write("sak_test\n")
        self.home = os.path.join(t, "home")
        self.repos = os.path.join(t, "repos")
        self.env = {"SPAWN_TOKEN_FILE": self.token, "SPAWN_USERNAME": "alice_helper", "ACCOUNT": "alice", "SPAWN_ORIGIN": "file://" + self.origin, "SDLCA_ALLOW_FILE_ORIGIN": "1",
                    "SDLCA_SPAWN_HOME": self.home, "SDLCA_REPOS": self.repos}
        self.set_address("@alice/game-1")

    def tearDown(self):
        self.tmp.cleanup()

    def set_address(self, address):
        me = {"worlds": [{"worldId": "w-1", "appId": "a-1", "address": address, "git": "file://" + self.bare, "standing": "editor"}]}
        with open(os.path.join(self.origin, "api", "agent", "v1", "me"), "w") as handle:
            json.dump(me, handle)

    def worlds(self, *flags):
        result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-worlds"), *flags], env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def registry(self):
        with open(os.path.join(self.home, "worlds.json")) as handle:
            return json.load(handle)["worlds"]["w-1"]

    def test_dry_run_changes_nothing(self):
        out = self.worlds()
        self.assertIn("[dry-run] new world @alice/game-1", out)
        self.assertFalse(os.path.exists(self.repos))
        self.assertFalse(os.path.exists(os.path.join(self.home, "worlds.json")))

    def test_apply_clones_registers_and_sets_the_identity(self):
        self.worlds("--apply")
        clone = os.path.join(self.repos, "alice", "game-1")
        self.assertTrue(os.path.isfile(os.path.join(clone, "AGENTS.md")))
        self.assertEqual(self.registry()["clone_path"], clone)
        self.assertEqual(git("config", "user.name", cwd=clone).stdout.strip(), "sdlca-agent")
        # a local path is not an https url, so no credential helper is attached at all
        self.assertNotIn("alice_helper", git("config", "--local", "--list", cwd=clone).stdout)
        self.assertEqual(os.stat(os.path.join(self.home, "worlds.json")).st_mode & 0o777, 0o600)

    def test_a_rename_moves_the_clone_and_remembers_the_old_address(self):
        self.worlds("--apply")
        self.set_address("@alice/game-one")
        out = self.worlds("--apply")
        self.assertIn("RENAMED @alice/game-1 -> @alice/game-one", out)
        entry = self.registry()
        self.assertEqual(entry["address"], "@alice/game-one")
        self.assertEqual(entry["aliases"], ["@alice/game-1"])
        self.assertTrue(os.path.isdir(os.path.join(self.repos, "alice", "game-one", ".git")))
        self.assertFalse(os.path.exists(os.path.join(self.repos, "alice", "game-1")))

    def test_a_second_run_is_a_no_op(self):
        self.worlds("--apply")
        self.assertIn("ok @alice/game-1", self.worlds("--apply"))

    def test_unsafe_addresses_are_skipped(self):
        self.set_address("@alice/../../etc")
        out = self.worlds("--apply")
        self.assertIn("skipping", out)
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "etc")))

    def test_names_that_start_with_a_dot_or_a_dash_are_skipped(self):
        for address in ("@alice/.git", "@.git/game", "@alice/-rf", "@-x/game", "@alice/..", "@alice/.hidden", "@alice/game-1\n"):
            self.set_address(address)
            out = self.worlds("--apply")
            self.assertIn("skipping", out, address)
            self.assertFalse(os.path.exists(os.path.join(self.repos, "alice", ".git")), address)
            self.assertFalse(os.path.exists(os.path.join(self.repos, ".git")), address)

    def test_the_registry_records_which_accounts_reach_each_world(self):
        self.worlds("--apply")
        self.assertEqual(self.registry()["accounts"], ["alice"])
        self.env["ACCOUNT"] = "bob"
        self.worlds("--apply")
        self.assertEqual(self.registry()["accounts"], ["alice", "bob"])

    def test_an_account_inside_a_group_is_recorded_under_its_full_name(self):
        self.env["ACCOUNT"] = "sdlca-for-spawn/alice"
        self.worlds("--apply")
        self.assertEqual(self.registry()["accounts"], ["sdlca-for-spawn/alice"])

    def test_account_names_with_odd_shapes_are_refused(self):
        for bad in ("../x", "a/b/c", "/abs", "Up", "a b", ""):
            env = dict(self.env, ACCOUNT=bad)
            result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-worlds")], env=env)
            self.assertNotEqual(result.returncode, 0, repr(bad))

    def test_a_rename_waits_while_an_agent_is_working_in_the_world_and_then_moves(self):
        import fcntl
        self.worlds("--apply")
        os.makedirs(os.path.join(self.home, "run"), exist_ok=True)
        busy = open(os.path.join(self.home, "run", "alice__game-1.lock"), "w")
        fcntl.flock(busy, fcntl.LOCK_EX)
        try:
            self.set_address("@alice/game-one")
            out = self.worlds("--apply")
            self.assertIn("an agent is working", out)
            self.assertTrue(os.path.isdir(os.path.join(self.repos, "alice", "game-1", ".git")))
            self.assertFalse(os.path.exists(os.path.join(self.repos, "alice", "game-one")))
            self.assertEqual(self.registry()["address"], "@alice/game-one")
            self.assertIn("pending_move", self.registry())
        finally:
            busy.close()
        out = self.worlds("--apply")
        self.assertIn("moved", out)
        self.assertTrue(os.path.isdir(os.path.join(self.repos, "alice", "game-one", ".git")))
        self.assertEqual(self.registry()["clone_path"], os.path.join(self.repos, "alice", "game-one"))
        self.assertNotIn("pending_move", self.registry())

    def test_a_registry_that_cannot_be_read_is_never_overwritten(self):
        os.makedirs(self.home)
        for text in ("[]", "{ not json", "5"):
            path = os.path.join(self.home, "worlds.json")
            with open(path, "w") as handle:
                handle.write(text)
            for flags in (("--apply",), ()):
                result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-worlds"), *flags], env=self.env)
                self.assertNotEqual(result.returncode, 0, (text, flags))
                self.assertIn("not a valid JSON object", result.stderr)
            with open(path) as handle:
                self.assertEqual(handle.read(), text)
        self.assertFalse(os.path.exists(self.repos))

    def test_malformed_world_entries_from_the_server_are_skipped(self):
        me = {"worlds": [{"address": "@alice/x"}, {"worldId": 5, "address": "@alice/y"}, {"worldId": "w-1", "appId": "a-1", "address": "@alice/game-1", "git": "file://" + self.bare}]}
        with open(os.path.join(self.origin, "api", "agent", "v1", "me"), "w") as handle:
            json.dump(me, handle)
        out = self.worlds("--apply")
        self.assertEqual(out.count("skipping"), 2)
        self.assertEqual(self.registry()["address"], "@alice/game-1")

    def test_a_failed_clone_is_tried_again_on_the_next_run(self):
        self.set_address("@alice/game-1")
        me_path = os.path.join(self.origin, "api", "agent", "v1", "me")
        with open(me_path) as handle:
            me = json.load(handle)
        good = me["worlds"][0]["git"]
        me["worlds"][0]["git"] = "file://" + os.path.join(self.tmp.name, "does-not-exist.git")
        with open(me_path, "w") as handle:
            json.dump(me, handle)
        out = self.worlds("--apply")
        self.assertIn("clone failed", out)
        self.assertFalse(os.path.exists(os.path.join(self.repos, "alice", "game-1")))
        me["worlds"][0]["git"] = good
        with open(me_path, "w") as handle:
            json.dump(me, handle)
        out = self.worlds("--apply")
        self.assertIn("cloned", out)
        self.assertTrue(os.path.isfile(os.path.join(self.repos, "alice", "game-1", "AGENTS.md")))

    def test_a_world_an_agent_made_has_a_double_at_address(self):
        self.set_address("@@alice_helper/mine")
        self.worlds("--apply")
        self.assertTrue(os.path.isdir(os.path.join(self.repos, "alice_helper", "mine", ".git")))
        self.assertEqual(self.registry()["owner"], "alice_helper")

    def test_an_existing_clone_is_never_modified(self):
        clone = os.path.join(self.repos, "alice", "game-1")
        os.makedirs(os.path.dirname(clone))
        git("clone", "file://" + self.bare, clone)
        git("config", "user.name", "Someone Else", cwd=clone)
        self.worlds("--apply")
        self.assertEqual(git("config", "user.name", cwd=clone).stdout.strip(), "Someone Else")

    def test_requires_an_account(self):
        env = {k: v for k, v in self.env.items() if k != "SPAWN_TOKEN_FILE"}
        result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-worlds")], env=env)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
