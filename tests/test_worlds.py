# SPDX-License-Identifier: Apache-2.0
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

import helpers


def git(*args, cwd=None):
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "PATH": os.environ["PATH"], "HOME": tempfile.gettempdir(),
           # no configuration of the developer's (a $TMPDIR/.gitconfig or /etc/gitconfig that signs commits, say) may reach these calls
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True)


def read_file(path):
    with open(path) as handle:
        return handle.read()


class WorldsCase(unittest.TestCase):
    """A throwaway Spawn (a file:// origin that answers /api/agent/v1/me), a local git repository as the world, and the runtime home and the clones' folder."""

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
        self.gitconfig = os.path.join(t, "gitconfig")  # the tools' global git configuration: nothing here may read yours
        with open(self.gitconfig, "w"):
            pass
        self.env = {"SPAWN_TOKEN_FILE": self.token, "SPAWN_USERNAME": "alice_helper", "ACCOUNT": "alice", "SPAWN_ORIGIN": "file://" + self.origin, "SDLCA_ALLOW_FILE_ORIGIN": "1",
                    "SDLCA_SPAWN_HOME": self.home, "SDLCA_REPOS": self.repos, "GIT_CONFIG_GLOBAL": self.gitconfig, "GIT_CONFIG_NOSYSTEM": "1"}
        self.set_address("@alice/game-1")

    def tearDown(self):
        self.tmp.cleanup()

    def set_address(self, address, git_url=None):
        me = {"worlds": [{"worldId": "w-1", "appId": "a-1", "address": address, "git": git_url or "file://" + self.bare, "standing": "editor"}]}
        with open(os.path.join(self.origin, "api", "agent", "v1", "me"), "w") as handle:
            json.dump(me, handle)

    def worlds(self, *flags):
        result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-worlds"), *flags], env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def registry(self):
        with open(os.path.join(self.home, "worlds.json")) as handle:
            return json.load(handle)["worlds"]["w-1"]

    def registry_all(self):
        path = os.path.join(self.home, "worlds.json")
        if not os.path.exists(path):
            return {}
        with open(path) as handle:
            return json.load(handle)["worlds"]


class WorldsTests(WorldsCase):
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

    # --only: a personal token reaches every world its person can reach, so a run can be limited to named worlds

    def set_worlds(self, *addresses):
        me = {"worlds": [{"worldId": "w-%d" % (i + 1), "appId": "a-%d" % (i + 1), "address": address, "git": "file://" + self.bare, "standing": "editor"}
                         for i, address in enumerate(addresses)]}
        with open(os.path.join(self.origin, "api", "agent", "v1", "me"), "w") as handle:
            json.dump(me, handle)

    def worlds_result(self, *flags):
        return helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-worlds"), *flags], env=self.env)

    def test_only_clones_and_records_just_the_named_world(self):
        self.set_worlds("@alice/game-1", "@zed/hollow-manor", "@bob/other")
        out = self.worlds("--apply", "--only", "@zed/hollow-manor")
        self.assertIn("new world @zed/hollow-manor", out)
        self.assertIn("--only: 1 world(s) named; 2 other world(s) this account can reach are left alone", out)
        self.assertNotIn("game-1", out)
        self.assertTrue(os.path.isdir(os.path.join(self.repos, "zed", "hollow-manor", ".git")))
        self.assertFalse(os.path.exists(os.path.join(self.repos, "alice")))
        self.assertFalse(os.path.exists(os.path.join(self.repos, "bob")))
        registry = self.registry_all()
        self.assertEqual(list(registry), ["w-2"])
        self.assertEqual(registry["w-2"]["accounts"], ["alice"])

    def test_only_in_a_dry_run_reports_just_that_world_and_writes_nothing(self):
        self.set_worlds("@alice/game-1", "@zed/hollow-manor")
        out = self.worlds("--only", "@zed/hollow-manor")
        self.assertIn("[dry-run] new world @zed/hollow-manor", out)
        self.assertNotIn("game-1", out.replace("--only: 1 world(s) named; 1 other", ""))
        self.assertFalse(os.path.exists(self.repos))
        self.assertFalse(os.path.exists(os.path.join(self.home, "worlds.json")))

    def test_only_can_be_given_more_than_once_and_as_one_argument(self):
        self.set_worlds("@alice/game-1", "@zed/hollow-manor", "@bob/other")
        self.worlds("--apply", "--only", "@alice/game-1", "--only=@bob/other")
        self.assertEqual(sorted(self.registry_all()), ["w-1", "w-3"])

    def test_only_with_a_world_the_account_cannot_reach_changes_nothing_and_lists_what_it_can(self):
        self.set_worlds("@alice/game-1", "@zed/hollow-manor")
        result = self.worlds_result("--apply", "--only", "@zed/typo", "--only", "@zed/hollow-manor")
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot reach @zed/typo", result.stderr)
        self.assertIn("@alice/game-1, @zed/hollow-manor", result.stderr)
        self.assertFalse(os.path.exists(self.repos))
        self.assertFalse(os.path.exists(os.path.join(self.home, "worlds.json")))

    def test_only_refuses_an_address_that_is_not_an_address(self):
        self.set_worlds("@alice/game-1")
        for bad in ("game-1", "@alice", "@alice/", "alice/game-1", "@alice/../x", "@.git/x", "@alice/-x", "--apply", ""):
            result = self.worlds_result("--only", bad)
            self.assertNotEqual(result.returncode, 0, repr(bad))
        self.assertNotEqual(self.worlds_result("--only").returncode, 0)  # no value
        self.assertFalse(os.path.exists(self.repos))

    def test_unknown_options_are_refused_instead_of_ignored(self):
        self.set_worlds("@alice/game-1")
        result = self.worlds_result("--aply")
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage: sdlca-worlds", result.stderr)
        self.assertFalse(os.path.exists(self.repos))

    def test_a_rename_is_followed_only_for_a_world_that_is_named(self):
        self.set_worlds("@alice/game-1", "@zed/hollow-manor")
        self.worlds("--apply")
        self.set_worlds("@alice/renamed", "@zed/hollow-manor")
        out = self.worlds("--apply", "--only", "@zed/hollow-manor")
        self.assertNotIn("RENAMED", out)
        self.assertEqual(self.registry_all()["w-1"]["address"], "@alice/game-1")
        self.assertTrue(os.path.isdir(os.path.join(self.repos, "alice", "game-1")))
        out = self.worlds("--apply", "--only", "@alice/renamed")
        self.assertIn("RENAMED @alice/game-1 -> @alice/renamed", out)
        self.assertTrue(os.path.isdir(os.path.join(self.repos, "alice", "renamed")))
        self.assertFalse(os.path.exists(os.path.join(self.repos, "alice", "game-1")))

    def test_a_listing_that_is_not_what_was_expected_stops_without_a_trace(self):
        for body in ('[]', '"text"', '{"worlds": "no"}', '{"worlds": [1, "x", null]}'):
            with open(os.path.join(self.origin, "api", "agent", "v1", "me"), "w") as handle:
                handle.write(body)
            result = self.worlds_result("--apply")
            self.assertFalse(os.path.exists(self.repos), body)
            if body in ('[]', '"text"'):
                self.assertEqual(result.returncode, 1, body)
                self.assertIn("not what this tool expects", result.stderr)
            else:
                self.assertEqual(result.returncode, 0, body + result.stderr)

    # a personal token, and what the account is allowed to do in each world

    def set_me(self, worlds, **extra):
        me = {"worlds": worlds}
        me.update(extra)
        with open(os.path.join(self.origin, "api", "agent", "v1", "me"), "w") as handle:
            json.dump(me, handle)

    def world_entry(self, address="@alice/game-1", **extra):
        entry = {"worldId": "w-1", "appId": "a-1", "address": address, "git": "file://" + self.bare}
        entry.update(extra)
        return entry

    def test_a_personal_token_gets_a_note_in_a_dry_run_and_nothing_is_changed(self):
        self.set_me([self.world_entry()], actorClass="human", handle="@alice")
        out = self.worlds()
        self.assertIn("[dry-run] NOTE: this token signs in as a PERSON (@alice), not as an agent", out)
        self.assertIn("will not route chat for your agent", out)
        self.assertFalse(os.path.exists(self.repos))
        self.assertFalse(os.path.exists(os.path.join(self.home, "worlds.json")))

    def test_apply_with_a_personal_token_needs_as_person_and_changes_nothing_without_it(self):
        self.set_me([self.world_entry()], actorClass="human", handle="@alice")
        result = self.worlds_result("--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--as-person", result.stderr)
        self.assertIn("push as @alice", result.stderr)
        self.assertFalse(os.path.exists(self.repos))
        self.assertFalse(os.path.exists(os.path.join(self.home, "worlds.json")))
        out = self.worlds("--apply", "--as-person")
        self.assertIn("NOTE: this token signs in as a PERSON", out)
        self.assertTrue(os.path.isdir(os.path.join(self.repos, "alice", "game-1", ".git")))

    def test_an_agent_token_or_an_answer_without_a_class_gets_no_note_and_needs_no_flag(self):
        for extra in ({"actorClass": "agent", "handle": "@@alice_helper"}, {}):
            self.set_me([self.world_entry()], **extra)
            self.assertNotIn("NOTE", self.worlds())
        self.set_me([self.world_entry()], actorClass="agent")
        self.assertIn("new world @alice/game-1", self.worlds("--apply"))

    def test_as_person_is_harmless_for_an_agent_token(self):
        self.set_me([self.world_entry()], actorClass="agent")
        self.assertIn("new world @alice/game-1", self.worlds("--apply", "--as-person"))

    def test_every_world_line_says_what_standing_the_account_has(self):
        self.set_me([self.world_entry(standing="editor")])
        self.assertIn("new world @alice/game-1 -> %s (standing: editor)" % os.path.join(self.repos, "alice", "game-1"), self.worlds())
        self.worlds("--apply")
        self.assertIn("(standing: editor)", self.worlds("--apply"))  # the "ok" line too

    def test_a_viewer_is_told_what_that_means_and_odd_standing_values_are_never_printed(self):
        self.set_me([self.world_entry(standing="viewer")])
        self.assertIn("(standing: viewer: can read and clone, cannot push)", self.worlds())
        for odd in (0, None, "", "editor; rm -rf /", "x" * 40, ["editor"], "Editor\n"):
            self.set_me([self.world_entry(standing=odd)])
            out = self.worlds()
            self.assertNotIn("standing", out, repr(odd))


class GitAddressTests(WorldsCase):
    """sdlca-worlds records, outside the clone, the git address that Spawn lists for each world: the update before a turn holds a clone to it.
    Spawn's addresses are https, so the tests give the listing https addresses and send them to the local repository through the tools' own
    global git configuration (the URL rewriting of git), and nothing reaches a network."""

    A = "https://git.spawn.co/@alice/game-1.git"
    B = "https://git.spawn.co/@alice/game-one.git"

    def map_to_bare(self, *urls):
        for url in urls:
            git("config", "--file", self.gitconfig, "--add", "url.%s.insteadOf" % ("file://" + self.bare), url)

    def remote_of(self, clone):
        return git("config", "--local", "remote.origin.url", cwd=clone).stdout.strip()

    def clone_path(self, name="game-1"):
        return os.path.join(self.repos, "alice", name)

    def test_a_new_world_records_the_git_address_from_the_listing(self):
        self.map_to_bare(self.A)
        self.set_address("@alice/game-1", self.A)
        out = self.worlds("--apply")
        self.assertEqual(self.registry()["git"], self.A)
        self.assertEqual(self.remote_of(self.clone_path()), self.A)  # the clone's remote and the record are the same address
        self.assertIn("cloned", out)
        self.assertNotIn("WARNING", out)
        self.assertEqual(sorted(self.registry()), ["accounts", "address", "aliases", "appId", "clone_path", "git", "owner", "slack_channel_ids", "slug", "standing"])
        self.assertEqual(os.stat(os.path.join(self.home, "worlds.json")).st_mode & 0o777, 0o600)

    def test_a_dry_run_records_nothing_and_says_what_apply_would_do(self):
        self.map_to_bare(self.A)
        self.set_address("@alice/game-1", self.A)
        self.worlds("--apply")
        with open(os.path.join(self.home, "worlds.json")) as handle:
            registry = json.load(handle)
        del registry["worlds"]["w-1"]["git"]  # an entry from before the field existed
        with open(os.path.join(self.home, "worlds.json"), "w") as handle:
            json.dump(registry, handle)
        before = read_file(os.path.join(self.home, "worlds.json"))
        out = self.worlds()
        self.assertIn("[dry-run] recording the git address of @alice/game-1 (host git.spawn.co)", out)
        self.assertEqual(read_file(os.path.join(self.home, "worlds.json")), before)
        self.assertNotIn("git", self.registry())

    def test_a_world_recorded_before_the_field_existed_gets_it_on_apply_and_keeps_everything_else(self):
        self.map_to_bare(self.A)
        self.set_address("@alice/game-1", self.A)
        self.worlds("--apply")
        with open(os.path.join(self.home, "worlds.json")) as handle:
            registry = json.load(handle)
        entry = registry["worlds"]["w-1"]
        del entry["git"]
        entry.update(slack_channel_ids=["C1"], aliases=["@alice/old"], extra_key="kept", standing="viewer")
        with open(os.path.join(self.home, "worlds.json"), "w") as handle:
            json.dump(registry, handle)
        before = dict(entry)
        out = self.worlds("--apply")
        self.assertIn("recording the git address of @alice/game-1 (host git.spawn.co)", out)
        after = self.registry()
        self.assertEqual(after.pop("git"), self.A)
        self.assertEqual(after.pop("standing"), "editor")  # refreshed, as it always was
        before.pop("standing")
        self.assertEqual(after, before)  # every other key is as it was
        self.assertNotIn("recording", self.worlds("--apply"))  # and a second run has nothing more to record

    def test_the_address_comes_from_the_listing_and_never_from_the_clone(self):
        self.map_to_bare(self.A)
        self.set_address("@alice/game-1", self.A)
        self.worlds("--apply")
        clone = self.clone_path()
        git("remote", "set-url", "origin", "https://evil.example/stolen.git", cwd=clone)  # what an agent that can edit the clone's settings would do
        with open(os.path.join(self.home, "worlds.json")) as handle:
            registry = json.load(handle)
        registry["worlds"]["w-1"]["git"] = "https://evil.example/stolen.git"  # and, if the record were the clone's, this is what it would hold
        with open(os.path.join(self.home, "worlds.json"), "w") as handle:
            json.dump(registry, handle)
        config = read_file(os.path.join(clone, ".git", "config"))
        out = self.worlds("--apply")
        self.assertEqual(self.registry()["git"], self.A)  # the listing wins
        self.assertIn("updating the git address of @alice/game-1 (host git.spawn.co)", out)
        self.assertEqual(read_file(os.path.join(clone, ".git", "config")), config)  # and an existing clone is never modified
        self.assertEqual(self.remote_of(clone), "https://evil.example/stolen.git")

    def test_an_address_that_cannot_carry_the_helper_is_not_recorded_and_is_never_printed(self):
        secret = "hunter2"
        for url in ("http://git.spawn.co/@alice/game-1.git", "https://" + "bob:" + secret + "@git.spawn.co/@alice/game-1.git",  # check-secrets:allow
                    "https://bob@git.spawn.co/@alice/game-1.git", "https:///@alice/game-1.git", "https://git.spawn.co:notaport/@alice/game-1.git",
                    "https://git.spawn.co/@alice/game-1.git?token=" + secret, "ssh://git@git.spawn.co/@alice/game-1.git", "file://" + self.bare):
            with self.subTest(url=url.replace(secret, "***")):
                shutil.rmtree(self.repos, ignore_errors=True)
                shutil.rmtree(self.home, ignore_errors=True)
                self.map_to_bare(url)
                self.set_address("@alice/game-1", url)
                out = self.worlds("--apply")
                self.assertNotIn("git", self.registry())
                self.assertIn("WARNING Spawn lists no git address for @alice/game-1 that the kit can hold a clone to (it must be https, with a host and no user information); "
                              "none is recorded, so the update before a turn skips this world", out)
                self.assertNotIn(secret, out)
                self.assertNotIn(url, out)
                self.assertNotIn("(host ", out)  # no part of an address that was refused is printed, not even its host

    def test_a_listing_with_no_address_or_one_that_is_not_text_records_none_and_does_not_crash(self):
        for listed in (None, "", 5, ["https://git.spawn.co/@alice/game-1.git"], {"a": 1}, True):
            with self.subTest(listed=listed):
                shutil.rmtree(self.repos, ignore_errors=True)
                shutil.rmtree(self.home, ignore_errors=True)
                me = {"worlds": [{"worldId": "w-1", "appId": "a-1", "address": "@alice/game-1", "git": listed, "standing": "editor"}]}
                with open(os.path.join(self.origin, "api", "agent", "v1", "me"), "w") as handle:
                    json.dump(me, handle)
                out = self.worlds("--apply")
                self.assertIn("WARNING Spawn lists no git address for @alice/game-1", out)
                self.assertNotIn("git", self.registry())
                self.assertFalse(os.path.exists(self.clone_path()))  # nothing to clone from

    def test_an_address_that_was_recorded_and_is_no_longer_usable_is_removed(self):
        self.map_to_bare(self.A, "http://git.spawn.co/@alice/game-1.git")
        self.set_address("@alice/game-1", self.A)
        self.worlds("--apply")
        self.assertEqual(self.registry()["git"], self.A)
        self.set_address("@alice/game-1", "http://git.spawn.co/@alice/game-1.git")
        out = self.worlds("--apply")
        self.assertNotIn("git", self.registry())  # a stale address is not one to hold a clone to
        self.assertIn("none is recorded and the one recorded before is removed, so the update before a turn skips this world", out)

    def test_a_change_of_the_address_without_a_rename_updates_the_record_and_leaves_the_clone_alone(self):
        other = "https://git2.spawn.co/@alice/game-1.git"
        self.map_to_bare(self.A, other)
        self.set_address("@alice/game-1", self.A)
        self.worlds("--apply")
        self.set_address("@alice/game-1", other)
        out = self.worlds("--apply")
        self.assertIn("updating the git address of @alice/game-1 (host git2.spawn.co)", out)
        self.assertNotIn("RENAMED", out)
        self.assertEqual(self.registry()["git"], other)
        self.assertEqual(self.remote_of(self.clone_path()), self.A)  # only a rename moves a clone's remote

    def test_a_rename_updates_the_record_together_with_the_remote(self):
        self.map_to_bare(self.A, self.B)
        self.set_address("@alice/game-1", self.A)
        self.worlds("--apply")
        self.set_address("@alice/game-one", self.B)
        out = self.worlds("--apply")
        self.assertIn("RENAMED @alice/game-1 -> @alice/game-one", out)
        self.assertEqual(self.registry()["git"], self.B)
        self.assertEqual(self.remote_of(self.clone_path("game-one")), self.B)  # the clone moved, and its remote and the record agree
        self.assertNotIn("WARNING", out)

    def test_a_rename_that_cannot_update_the_remote_says_so_and_still_records_what_the_listing_says(self):
        self.map_to_bare(self.A, self.B)
        self.set_address("@alice/game-1", self.A)
        self.worlds("--apply")
        git("remote", "rename", "origin", "elsewhere", cwd=self.clone_path())  # the person renamed the remote: there is no origin to point at the new address
        self.set_address("@alice/game-one", self.B)
        out = self.worlds("--apply")
        self.assertIn("WARNING could not point the remote of the clone at", out)
        self.assertEqual(self.registry()["git"], self.B)  # the listing is the truth: the update will refuse this clone, as it should

    # what is recorded is the address as Spawn listed it, character for character

    def test_the_address_is_recorded_exactly_as_listed_for_a_new_world_and_for_one_that_exists(self):
        """The update compares the scheme and the host in lower case, but the path as written, and it fetches from the record as it stands. So a
        recorder that changed the case of a path would make the clone untrusted."""
        for listed in ("https://git.spawn.co/@Alice/Game-1.git", "https://Git.Spawn.CO/@Alice/Game-1.git", "https://git.spawn.co/@alice/Game-1",
                       "https://git.spawn.co:8443/@alice/game-1.git/"):
            with self.subTest(listed=listed):
                shutil.rmtree(self.repos, ignore_errors=True)
                shutil.rmtree(self.home, ignore_errors=True)
                self.map_to_bare(listed)
                self.set_address("@alice/game-1", listed)
                self.worlds("--apply")
                self.assertEqual(self.registry()["git"], listed)  # a new world
                with open(os.path.join(self.home, "worlds.json")) as handle:
                    registry = json.load(handle)
                del registry["worlds"]["w-1"]["git"]
                with open(os.path.join(self.home, "worlds.json"), "w") as handle:
                    json.dump(registry, handle)
                self.worlds("--apply")
                self.assertEqual(self.registry()["git"], listed)  # a world that was there before the field

    def test_an_address_with_a_dot_segment_is_not_recorded_because_the_update_would_not_accept_it(self):
        for listed in ("https://git.spawn.co/secret-segment/../game-1.git", "https://git.spawn.co/a/%2e%2e/game-1.git", "https://git.spawn.co/./game-1.git",
                       "https://git.spawn.co/%2E/game-1.git", "https://git.spawn.co/@alice/game-1.git/.."):
            with self.subTest(listed=listed):
                shutil.rmtree(self.repos, ignore_errors=True)
                shutil.rmtree(self.home, ignore_errors=True)
                self.map_to_bare(listed)
                self.set_address("@alice/game-1", listed)
                out = self.worlds("--apply")
                self.assertNotIn("git", self.registry())
                self.assertIn("WARNING Spawn lists no git address for @alice/game-1 that the kit can hold a clone to (it has a . or .. segment in its path); none is recorded", out)
                self.assertNotIn("segment-secret", out)
                self.assertNotIn("(host ", out)

    def test_a_rename_to_an_address_the_kit_does_not_use_leaves_the_remote_alone(self):
        """The clone's remote is moved to the new address only when it is one the kit would record: not to one with user information, http or ssh."""
        for unusable in ("https://" + "tok:en" + "@git.spawn.co/@alice/game-one.git",  # check-secrets:allow (a made-up value)
                         "ssh://git@git.spawn.co/@alice/game-one.git", "http://git.spawn.co/@alice/game-one.git", "https://git.spawn.co/a/../game-one.git"):
            with self.subTest(unusable=unusable.split("@")[-1]):
                shutil.rmtree(self.repos, ignore_errors=True)
                shutil.rmtree(self.home, ignore_errors=True)
                self.map_to_bare(self.A, unusable)
                self.set_address("@alice/game-1", self.A)
                self.worlds("--apply")
                self.set_address("@alice/game-one", unusable)
                out = self.worlds("--apply")
                self.assertIn("RENAMED @alice/game-1 -> @alice/game-one", out)
                self.assertIn("WARNING the remote of the clone at", out)
                self.assertIn("was left as it was", out)
                self.assertNotIn("tok:en", out)
                self.assertEqual(self.remote_of(self.clone_path("game-one")), self.A)  # still the address that was recorded and listed before
                self.assertNotIn("git", self.registry())  # the stale record is removed, so the update says unverified and does not hold the clone to it
                self.assertIn("the one recorded before is removed", out)

    def test_a_change_or_removal_says_which_other_accounts_share_the_record(self):
        other = "https://git2.spawn.co/@alice/game-1.git"
        self.map_to_bare(self.A, other, "http://git.spawn.co/@alice/game-1.git")
        self.set_address("@alice/game-1", self.A)
        self.worlds("--apply")
        out = self.worlds("--apply")
        self.assertNotIn("shared", out)  # one account, and nothing changed
        with open(os.path.join(self.home, "worlds.json")) as handle:
            registry = json.load(handle)
        registry["worlds"]["w-1"]["accounts"] = ["alice", "bob", "carol"]
        with open(os.path.join(self.home, "worlds.json"), "w") as handle:
            json.dump(registry, handle)
        self.set_address("@alice/game-1", other)
        out = self.worlds("--apply")
        self.assertIn("updating the git address of @alice/game-1 (host git2.spawn.co) (this record is shared with the accounts bob, carol, whose updates it changes too)", out)
        self.set_address("@alice/game-1", "http://git.spawn.co/@alice/game-1.git")
        out = self.worlds("--apply")
        self.assertIn("the one recorded before is removed, so the update before a turn skips this world (this record is shared with the accounts bob, carol", out)
        self.assertEqual(self.registry()["accounts"], ["alice", "bob", "carol"])  # the other accounts are still listed

    def test_only_records_just_the_named_worlds_and_leaves_the_others_without_one(self):
        urls = ["https://git.spawn.co/@alice/game-1.git", "https://git.spawn.co/@zed/hollow-manor.git", "https://git.spawn.co/@bob/other.git"]
        self.map_to_bare(*urls)
        me = {"worlds": [{"worldId": "w-%d" % (i + 1), "appId": "a-%d" % (i + 1), "address": address, "git": url, "standing": "editor"}
                         for i, (address, url) in enumerate(zip(("@alice/game-1", "@zed/hollow-manor", "@bob/other"), urls))]}
        with open(os.path.join(self.origin, "api", "agent", "v1", "me"), "w") as handle:
            json.dump(me, handle)
        self.worlds("--apply")  # all three are known, with their addresses
        with open(os.path.join(self.home, "worlds.json")) as handle:
            registry = json.load(handle)
        for entry in registry["worlds"].values():
            del entry["git"]  # as if they were all recorded before the field existed
        with open(os.path.join(self.home, "worlds.json"), "w") as handle:
            json.dump(registry, handle)
        out = self.worlds("--apply", "--only", "@zed/hollow-manor")
        self.assertEqual(out.count("recording the git address"), 1)
        self.assertIn("recording the git address of @zed/hollow-manor", out)
        recorded = self.registry_all()
        self.assertEqual(recorded["w-2"]["git"], urls[1])
        self.assertNotIn("git", recorded["w-1"])
        self.assertNotIn("git", recorded["w-3"])
        out = self.worlds("--apply", "--only", "@alice/game-1", "--only", "@bob/other")
        self.assertEqual(out.count("recording the git address"), 2)
        self.assertEqual({k: v.get("git") for k, v in self.registry_all().items()}, {"w-1": urls[0], "w-2": urls[1], "w-3": urls[2]})

    def test_a_dry_run_with_only_reports_just_that_world(self):
        self.map_to_bare(self.A)
        self.set_address("@alice/game-1", self.A)
        out = self.worlds("--only", "@alice/game-1")
        self.assertIn("[dry-run] new world @alice/game-1", out)
        self.assertNotIn("recording the git address", out)  # a new world's address is part of "new world": nothing more to say
        self.assertFalse(os.path.exists(os.path.join(self.home, "worlds.json")))

    def test_the_record_is_written_with_the_registry_and_survives_a_second_run_unchanged(self):
        self.map_to_bare(self.A)
        self.set_address("@alice/game-1", self.A)
        self.worlds("--apply")
        first = read_file(os.path.join(self.home, "worlds.json"))
        out = self.worlds("--apply")
        self.assertEqual(read_file(os.path.join(self.home, "worlds.json")), first)
        self.assertNotIn("git address", out)
        self.assertIn("ok @alice/game-1", out)


class ProxyTests(unittest.TestCase):
    """With a proxy named in the environment, a plain-http origin (this machine, for tests and development) must not send the token through it."""

    def test_a_proxy_in_the_environment_is_never_used_for_a_plain_http_origin(self):
        hits = {"origin": [], "proxy": []}

        def handler(name):
            class Answer(BaseHTTPRequestHandler):
                def do_GET(self):
                    hits[name].append((self.path, self.headers.get("Authorization")))
                    body = b'{"worlds": []}'
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

                def log_message(self, *args):
                    pass

            return Answer

        servers = [HTTPServer(("127.0.0.1", 0), handler(name)) for name in ("origin", "proxy")]
        for server in servers:
            threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                token = os.path.join(tmp, "token")
                with open(token, "w") as handle:
                    handle.write("sak_test\n")
                proxy = "http://127.0.0.1:%d" % servers[1].server_port
                env = {"SPAWN_TOKEN_FILE": token, "SPAWN_USERNAME": "alice_helper", "ACCOUNT": "alice", "SPAWN_ORIGIN": "http://127.0.0.1:%d" % servers[0].server_port,
                       "SDLCA_SPAWN_HOME": os.path.join(tmp, "home"), "SDLCA_REPOS": os.path.join(tmp, "repos"), "http_proxy": proxy, "HTTP_PROXY": proxy}
                result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-worlds")], env=env)
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(hits["proxy"], [], "the token went to the proxy")
        self.assertEqual(hits["origin"], [("/api/agent/v1/me", "Bearer sak_test")])


if __name__ == "__main__":
    unittest.main()
