# SPDX-License-Identifier: Apache-2.0
"""sdlca-asset: the command an agent may run to upload a finished model. Against the same stand-in Spawn as sdlca-body."""
import os
import unittest

import helpers
import test_body as tb

BIN = os.path.join(helpers.ROOT, "bin", "sdlca-asset")


class AssetTests(tb.CarryTests):
    def asset(self, *args, env=None):
        return helpers.run([BIN] + list(args), env=self.merged(env), timeout=90)

    def test_the_default_uploads_and_prints_the_address_without_body_hints(self):
        self.answer("PUT", self.assets + self.name, (201, self.carried()))
        result = self.asset("alice", "@alice/game-1", self.path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(self.address, result.stdout)
        self.assertNotIn("--wear", result.stdout)
        self.assertNotIn("sdlca-body <account>", result.stdout)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me"), ("PUT", self.assets + self.name)])
        self.assertNoToken(result)

    def test_a_model_without_a_skeleton_is_fine_for_a_prop(self):
        self.glb = tb.glb_bytes(extra=500, skins=0)
        with open(self.path, "wb") as handle:
            handle.write(self.glb)
        import hashlib
        self.sha = hashlib.sha256(self.glb).hexdigest()
        self.name = "value.%s.glb" % self.sha
        self.address = "https://www.spawn.co/cdn/" + self.name
        self.answer("PUT", self.assets + self.name, (201, self.carried()))
        result = self.asset("alice", "@alice/game-1", self.path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(self.address, result.stdout)

    def test_a_dry_run_changes_nothing(self):
        result = self.asset("alice", "@alice/game-1", self.path, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me")])

    def test_an_agent_turn_may_name_only_its_own_account(self):
        result = self.asset("alice", "@alice/game-1", self.path, env={"SDLCA_TURN_ACCOUNT": "bob"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("only the turn's own account", result.stderr)
        self.assertEqual(self.sequence(), [])
        ok = self.asset("alice", "@alice/game-1", self.path, "--dry-run", env={"SDLCA_TURN_ACCOUNT": "alice"})
        self.assertEqual(ok.returncode, 0, ok.stderr)

    def test_odd_arguments_are_refused_before_anything_is_asked(self):
        for args in (("alice",), ("alice", "@alice/game-1"), ("alice", "game-1", self.path), ("alice", "@alice/game-1", "-x"),
                     ("alice", "@alice/game-1", self.path, "--apply"), ("../x", "@alice/game-1", self.path)):
            result = self.asset(*args)
            self.assertNotEqual(result.returncode, 0, args)
        self.assertEqual(self.sequence(), [])

    def test_only_a_real_model_is_taken(self):
        not_a_model = os.path.join(self.folder, "notes.glb")
        with open(not_a_model, "wb") as handle:
            handle.write(b"just text, not a model\n")
        result = self.asset("alice", "@alice/game-1", not_a_model)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.sequence(), [])

    def test_a_world_that_is_not_the_agents_is_refused(self):
        result = self.asset("alice", "@alice/elsewhere", self.path)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([c for c in self.sequence() if c[0] == "PUT"], [])

    def test_a_forged_asset_mode_does_not_let_a_turn_change_a_body(self):
        env = self.merged({"SDLCA_TURN_ACCOUNT": "alice", "SDLCA_ASSET_MODE": "1", "ACC": self.account, "ACCOUNT": "alice", "SPAWN_TOKEN_FILE": self.token_file})
        for args in (["--reset", "char-1", "--apply"], ["--wear", "muse", "--apply"], [self.picture, "--apply"]):
            result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "lib", "body.py")] + args, env=env, timeout=60)
            self.assertNotEqual(result.returncode, 0, args)
            self.assertIn("an agent turn may not change a body", result.stdout + result.stderr)
        self.assertEqual(self.sequence(), [])

    def test_help(self):
        result = self.asset("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: sdlca-asset", result.stdout)


# CarryTests' own tests would run again under this subclass; only the asset tests belong here.
for name in [n for n in dir(tb.CarryTests) if n.startswith("test_")]:
    setattr(AssetTests, name, None)

if __name__ == "__main__":
    unittest.main()
