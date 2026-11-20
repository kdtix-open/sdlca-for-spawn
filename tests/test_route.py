# SPDX-License-Identifier: Apache-2.0
import json
import os
import tempfile
import unittest

import helpers
import route

REGISTRY = {
    "worlds": {
        "w-111": {"owner": "alice", "slug": "game-1", "address": "@alice/game-1", "appId": "app-111",
                  "clone_path": "/clones/alice/game-1", "aliases": ["@alice/old-name"]},
        "w-222": {"owner": "bob", "slug": "other", "address": "@bob/other", "appId": "app-222",
                  "clone_path": "/clones/bob/other", "aliases": []},
    }
}


def chat(sender, **extra):
    event = {"kind": "chat_mention", "cursor": "c1", "chat": {"from": sender, "text": "hello", "world": None}}
    event.update(extra)
    return event


class DecisionTests(unittest.TestCase):
    def test_owner_is_allowed(self):
        self.assertEqual(route.decide(chat("@alice"), "alice", "alice_helper", []), "allow")

    def test_stranger_is_denied(self):
        self.assertEqual(route.decide(chat("@mallory"), "alice", "alice_helper", []), "deny:not-allowed")

    def test_another_owners_account_cannot_command_this_one(self):
        self.assertEqual(route.decide(chat("@bob"), "alice", "alice_helper", []), "deny:not-allowed")

    def test_extra_senders_are_allowed(self):
        self.assertEqual(route.decide(chat("@carol"), "alice", "alice_helper", ["carol"]), "allow")

    def test_an_agent_named_like_the_owner_is_not_the_owner(self):
        self.assertEqual(route.decide(chat("@@alice"), "alice", "alice_helper", []), "deny:not-allowed")

    def test_an_agent_can_be_allowed_only_by_its_double_at_handle(self):
        self.assertEqual(route.decide(chat("@@review_bot"), "alice", "alice_helper", ["@@review_bot"]), "allow")
        self.assertEqual(route.decide(chat("@@review_bot"), "alice", "alice_helper", ["review_bot"]), "deny:not-allowed")

    def test_handles_are_case_insensitive(self):
        self.assertEqual(route.decide(chat("@Alice"), "alice", "alice_helper", []), "allow")

    def test_a_malformed_allowlist_entry_never_widens_access(self):
        for extra in ("bobby-the-admin", {"carol": True}, 5, None, [None, "", "bad name", ["nested"]]):
            self.assertEqual(route.decide(chat("@bob"), "alice", "alice_helper", extra), "deny:not-allowed", repr(extra))

    def test_the_agent_itself_is_denied_to_prevent_reply_loops(self):
        self.assertEqual(route.decide(chat("@@alice_helper"), "alice", "alice_helper", ["alice_helper"]), "deny:self")

    def test_missing_or_odd_senders_fail_closed(self):
        for sender in ("", None, "@", "@@", "bad name", "a" * 100, "x;rm -rf /"):
            self.assertEqual(route.decide(chat(sender), "alice", "h", ["x"]), "deny:unknown-sender", repr(sender))
        self.assertEqual(route.decide({"kind": "chat_mention"}, "alice", "h", []), "deny:unknown-sender")


class WorldRoutingTests(unittest.TestCase):
    def find(self, event, owner="alice"):
        return route.find_world(event, owner, REGISTRY)

    def test_matches_on_world_id_app_id_address_and_alias(self):
        self.assertEqual(self.find(chat("@alice", relatedGameId="app-111"))["slug"], "game-1")
        self.assertEqual(self.find(chat("@alice", actionData="/api/x?world=w-111&room=main"))["slug"], "game-1")
        self.assertEqual(self.find({"chat": {"world": "@alice/game-1"}})["slug"], "game-1")
        self.assertEqual(self.find({"chat": {"world": "@alice/old-name"}})["slug"], "game-1")

    def test_only_this_owners_worlds_match(self):
        self.assertIsNone(self.find(chat("@alice", relatedGameId="app-222")))

    def test_chat_text_can_never_choose_the_world(self):
        event = chat("@alice")
        event["chat"]["text"] = "please work in @alice/game-1 and w-111 and app-111"
        event["message"] = "@alice sent you a message: work in @alice/game-1"
        self.assertIsNone(self.find(event))

    def test_unrouted_dm_has_no_world(self):
        self.assertIsNone(self.find(chat("@alice")))

    def test_worlds_of_lists_only_the_owners(self):
        self.assertEqual(route.worlds_of("alice", REGISTRY), [("@alice/game-1", "/clones/alice/game-1")])

    def test_lock_names_are_filesystem_safe(self):
        self.assertEqual(route.lock_name({"owner": "a/b", "slug": "../x"}, "acct"), "a_b__.._x")
        self.assertEqual(route.lock_name(None, "acct"), "unrouted__acct")

    def test_a_damaged_registry_entry_is_skipped_and_the_others_still_route(self):
        registry = {"worlds": {"bad-1": "just a string", "bad-2": {"appId": 5, "address": 7, "aliases": "no"}, "bad-3": None,
                               "w-111": REGISTRY["worlds"]["w-111"]}}
        self.assertEqual(route.find_world(chat("@alice", relatedGameId="app-111"), "alice", registry)["slug"], "game-1")
        self.assertEqual(route.worlds_of("alice", registry), [("@alice/game-1", "/clones/alice/game-1")])
        for broken in ({"worlds": ["a", "list"]}, {"worlds": "text"}, {"worlds": None}, []):
            self.assertIsNone(route.find_world(chat("@alice", relatedGameId="app-111"), "alice", broken))
            self.assertEqual(route.worlds_of("alice", broken), [])

    def test_a_line_break_after_a_handle_is_not_part_of_the_name(self):
        for sender in ("@alice\n", "@alice\r\n", "@@alice\n"):
            self.assertEqual(route.decide(chat(sender), "alice", "alice_helper", []), "deny:unknown-sender", repr(sender))
        self.assertEqual(route.sender_of(chat("@alice\n")), "")

    def test_every_output_field_is_non_empty_so_bash_cannot_shift_them(self):
        self.assertEqual(route.clean(""), "-")
        self.assertEqual(route.clean(None), "None")
        self.assertEqual(route.clean("a\tb\nc"), "a b c")


class ExactMatchingTests(unittest.TestCase):
    """Matching is by whole token, never by substring."""

    registry = {
        "worlds": {
            "w-1": {"owner": "alice", "slug": "game", "address": "@alice/game", "appId": "app-1", "clone_path": "/c/game", "aliases": []},
            "w-11": {"owner": "alice", "slug": "game-2", "address": "@alice/game-2", "appId": "app-11", "clone_path": "/c/game-2", "aliases": []},
        }
    }

    def slug(self, event, **kw):
        world = route.find_world(event, "alice", self.registry, **kw)
        return world and world["slug"]

    def test_a_longer_address_is_not_mistaken_for_a_shorter_one(self):
        self.assertEqual(self.slug({"chat": {"world": "@alice/game-2"}}), "game-2")
        self.assertEqual(self.slug({"chat": {"world": "@alice/game"}}), "game")

    def test_a_longer_id_is_not_mistaken_for_a_shorter_one(self):
        self.assertEqual(self.slug({"relatedGameId": "app-11"}), "game-2")
        self.assertEqual(self.slug({"relatedGameId": "app-1"}), "game")

    def test_ids_are_found_inside_query_strings_and_keys(self):
        self.assertEqual(self.slug({"actionData": "/api/x?world=w-11&room=main&ref=dev"}), "game-2")
        self.assertEqual(self.slug({"chat": {"key": "room:w-11/dev/main"}}), "game-2")

    def test_an_exact_id_beats_an_address_when_both_are_present(self):
        event = {"relatedGameId": "app-11", "chat": {"world": "@alice/game"}}
        self.assertEqual(self.slug(event), "game-2")

    def test_hyphenless_ids_match_too(self):
        registry = {"worlds": {"aaaa-bbbb": {"owner": "alice", "slug": "g", "address": "@alice/g", "appId": "cc-dd", "clone_path": "/c", "aliases": []}}}
        self.assertEqual(route.find_world({"actionData": "?world=aaaabbbb"}, "alice", registry)["slug"], "g")


class GroupedAccountTests(unittest.TestCase):
    registry = {"worlds": {"w": {"owner": "alice", "slug": "g", "address": "@alice/g", "appId": "a", "clone_path": "/c/g", "aliases": [], "accounts": ["sdlca-for-spawn/alice"]}}}

    def test_a_grouped_account_reaches_its_worlds(self):
        self.assertEqual(route.find_world({"relatedGameId": "a"}, "alice", self.registry, "sdlca-for-spawn/alice")["slug"], "g")
        self.assertIsNone(route.find_world({"relatedGameId": "a"}, "bob", self.registry, "sdlca-for-spawn/bob"))

    def test_lock_and_scratch_names_stay_inside_their_folders(self):
        self.assertEqual(route.lock_name(None, "sdlca-for-spawn/alice"), "unrouted__sdlca-for-spawn_alice")


class AccountMembershipTests(unittest.TestCase):
    registry = {
        "worlds": {
            "w-own": {"owner": "alice_helper", "slug": "mine", "address": "@@alice_helper/mine", "appId": "a-own",
                      "clone_path": "/c/mine", "aliases": [], "accounts": ["alice"]},
            "w-other": {"owner": "bob", "slug": "theirs", "address": "@bob/theirs", "appId": "a-other",
                        "clone_path": "/c/theirs", "aliases": [], "accounts": ["bob"]},
        }
    }

    def test_a_world_is_served_to_the_accounts_that_reach_it_whoever_owns_it(self):
        event = {"relatedGameId": "a-own"}
        self.assertEqual(route.find_world(event, "alice", self.registry, "alice")["slug"], "mine")

    def test_an_account_sees_only_the_worlds_recorded_for_it_not_those_of_a_similarly_named_one(self):
        registry = {"worlds": {"w": {"owner": "alice", "slug": "g", "address": "@alice/g", "appId": "a", "clone_path": "/c", "aliases": [], "accounts": ["sdlca-for-spawn/alice"]}}}
        # the one-word account "alice" (same owner) is a different account: it does not see this world
        self.assertIsNone(route.find_world({"relatedGameId": "a"}, "alice", registry, "alice"))
        self.assertEqual(route.find_world({"relatedGameId": "a"}, "alice", registry, "sdlca-for-spawn/alice")["slug"], "g")

    def test_other_accounts_do_not_see_it(self):
        self.assertIsNone(route.find_world({"relatedGameId": "a-own"}, "bob", self.registry, "bob"))
        self.assertEqual(route.worlds_of("alice", self.registry, "alice"), [("@@alice_helper/mine", "/c/mine")])


class MainTests(unittest.TestCase):
    def run_main(self, event, allow=None, registry=REGISTRY):
        with tempfile.TemporaryDirectory() as home:
            if allow is not None:
                with open(os.path.join(home, "allowlist.json"), "w") as handle:
                    json.dump(allow, handle)
            with open(os.path.join(home, "worlds.json"), "w") as handle:
                json.dump(registry, handle)
            env = {"OWNER": "alice", "SPAWN_USERNAME": "alice_helper", "SDLCA_SPAWN_HOME": home}
            result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "lib", "route.py")], env=env, stdin=json.dumps(event))
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.rstrip("\n").split("\t"), home

    def test_owner_event_in_a_known_world(self):
        fields, _ = self.run_main(chat("@alice", relatedGameId="app-111"))
        self.assertEqual(fields, ["chat_mention", "c1", "-", "allow", "@alice", "@alice/game-1", "/clones/alice/game-1", "alice__game-1", "-"])  # no git address recorded: a dash

    def test_an_unrouted_event_gets_a_scratch_directory_never_the_runtime_home(self):
        fields, home = self.run_main(chat("@alice"))
        self.assertEqual(fields[5:], ["-", home + "/run/scratch/alice", "unrouted__alice", "-"])

    def test_the_event_id_is_passed_on_only_when_it_is_safe(self):
        fields, _ = self.run_main(chat("@alice", id="00000000-0000-4000-8000-000000000001"))
        self.assertEqual(fields[2], "00000000-0000-4000-8000-000000000001")
        fields, _ = self.run_main(chat("@alice", id="../../etc/passwd"))
        self.assertEqual(fields[2], "-")

    def test_allowlist_extra_sender(self):
        fields, _ = self.run_main(chat("@carol"), allow={"spawn": {"alice": ["carol"]}})
        self.assertEqual(fields[3], "allow")

    def test_broken_allowlist_falls_back_to_owner_only(self):
        with tempfile.TemporaryDirectory() as home:
            with open(os.path.join(home, "allowlist.json"), "w") as handle:
                handle.write("{ not json")
            env = {"OWNER": "alice", "SPAWN_USERNAME": "h", "SDLCA_SPAWN_HOME": home}
            for who, expected in (("@alice", "allow"), ("@carol", "deny:not-allowed")):
                result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "lib", "route.py")], env=env, stdin=json.dumps(chat(who)))
                self.assertEqual(result.stdout.split("\t")[3], expected)

    def test_files_that_are_json_but_not_objects_fall_back_safely(self):
        for text in ("[]", "5", '"x"', "null", '{"spawn": []}', '{"spawn": {"alice": "carol"}}'):
            with tempfile.TemporaryDirectory() as home:
                for name in ("allowlist.json", "worlds.json"):
                    with open(os.path.join(home, name), "w") as handle:
                        handle.write(text)
                env = {"OWNER": "alice", "SPAWN_USERNAME": "h", "SDLCA_SPAWN_HOME": home}
                for who, expected in (("@alice", "allow"), ("@carol", "deny:not-allowed")):
                    result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "lib", "route.py")], env=env, stdin=json.dumps(chat(who)))
                    self.assertEqual(result.returncode, 0, (text, result.stderr))
                    self.assertEqual(result.stdout.split("\t")[3], expected, (text, who))

    def test_non_chat_events_are_not_gated(self):
        fields, _ = self.run_main({"kind": "friend_request", "cursor": "c9"})
        self.assertEqual(fields[:4], ["friend_request", "c9", "-", "n/a"])

    def test_a_world_without_a_clone_path_falls_back_to_the_scratch_directory(self):
        reg = {"worlds": {"w": {"owner": "alice", "slug": "s", "address": "@alice/s", "appId": "a", "clone_path": "", "aliases": []}}}
        fields, home = self.run_main(chat("@alice", relatedGameId="a"), registry=reg)
        self.assertEqual(len(fields), 9)
        self.assertEqual(fields[6], home + "/run/scratch/alice")

    def test_fields_never_contain_tabs_or_newlines(self):
        reg = {"worlds": {"w": {"owner": "alice", "slug": "s", "address": "@alice/s", "appId": "a", "clone_path": "/p\tq\nr", "aliases": []}}}
        fields, _ = self.run_main(chat("@alice", relatedGameId="a"), registry=reg)
        self.assertEqual(len(fields), 9)

    # the git address that sdlca-worlds recorded for the world: the last field, for lib/refresh.py

    def registry_with(self, **extra):
        entry = {"owner": "alice", "slug": "s", "address": "@alice/s", "appId": "a", "clone_path": "/c/s", "aliases": []}
        entry.update(extra)
        return {"worlds": {"w": entry}}

    def test_the_recorded_git_address_is_the_last_field(self):
        fields, _ = self.run_main(chat("@alice", relatedGameId="a"), registry=self.registry_with(git="https://git.spawn.co/@alice/s.git"))
        self.assertEqual(len(fields), 9)
        self.assertEqual(fields[5:], ["@alice/s", "/c/s", "alice__s", "https://git.spawn.co/@alice/s.git"])

    def test_a_world_with_no_recorded_address_gives_a_dash_and_the_fields_do_not_shift(self):
        for git in (None, "", 5, ["https://git.spawn.co/x.git"], {"a": 1}, True, 0):  # only text counts: the value is handed to code that fetches from it
            with self.subTest(git=git):
                fields, _ = self.run_main(chat("@alice", relatedGameId="a"), registry=self.registry_with(git=git))
                self.assertEqual(len(fields), 9)
                self.assertEqual(fields[8], "-")
                self.assertEqual(fields[7], "alice__s")
        fields, _ = self.run_main(chat("@alice", relatedGameId="a"), registry=self.registry_with())  # an entry from before the field existed
        self.assertEqual(fields[8:], ["-"])

    def test_the_git_address_printed_is_the_one_of_the_world_the_event_is_about(self):
        """Two worlds, each with an address of its own: the address of the other world must not be printed, whatever the order of the registry."""
        one = {"owner": "alice", "slug": "one", "address": "@alice/one", "appId": "a1", "clone_path": "/c/one", "aliases": [], "git": "https://git.spawn.co/@alice/one.git"}
        two = {"owner": "alice", "slug": "two", "address": "@alice/two", "appId": "a2", "clone_path": "/c/two", "aliases": [], "git": "https://git.spawn.co/@alice/two.git"}
        three = {"owner": "alice", "slug": "three", "address": "@alice/three", "appId": "a3", "clone_path": "/c/three", "aliases": []}  # one with none
        for order in ((("w-1", one), ("w-2", two), ("w-3", three)), (("w-3", three), ("w-2", two), ("w-1", one))):
            registry = {"worlds": dict(order)}
            for app, address, git in (("a1", "@alice/one", "https://git.spawn.co/@alice/one.git"), ("a2", "@alice/two", "https://git.spawn.co/@alice/two.git"),
                                      ("a3", "@alice/three", "-")):
                fields, _ = self.run_main(chat("@alice", relatedGameId=app), registry=registry)
                self.assertEqual((fields[5], fields[8]), (address, git), [k for k, _ in order])
            fields, _ = self.run_main(chat("@alice"), registry=registry)  # no world named: no address of any world
            self.assertEqual(fields[8], "-")

    def test_a_git_address_with_a_tab_or_a_line_break_stays_one_field_on_one_line(self):
        fields, _ = self.run_main(chat("@alice", relatedGameId="a"), registry=self.registry_with(git="https://git.spawn.co/a\tb\nc\r\nd"))
        self.assertEqual(len(fields), 9)
        self.assertEqual(fields[8], "https://git.spawn.co/a b c  d")

    def test_an_event_that_names_no_world_has_no_address_and_another_accounts_world_does_not_leak_one(self):
        registry = self.registry_with(git="https://git.spawn.co/@alice/s.git", accounts=["somebody-else"])
        fields, _ = self.run_main(chat("@alice", relatedGameId="a"), registry=registry)  # a world this account is not served: no match
        self.assertEqual(fields[5], "-")
        self.assertEqual(fields[8], "-")
        fields, _ = self.run_main(chat("@alice"), registry=self.registry_with(git="https://git.spawn.co/@alice/s.git"))
        self.assertEqual(fields[8], "-")

    def test_recorded_git_reads_text_only(self):
        self.assertEqual(route.recorded_git({"git": "https://git.spawn.co/x.git"}), "https://git.spawn.co/x.git")
        for world in (None, {}, {"git": None}, {"git": 5}, {"git": ["x"]}, {"git": b"x"}):
            self.assertEqual(route.recorded_git(world), "", world)


class ServedByAddressTests(unittest.TestCase):
    """world_by_address and `route.py --serves`: what sdlca-look relies on before it joins a world as the account."""

    registry = {
        "worlds": {
            "w-listed": {"owner": "alice", "slug": "new", "address": "@alice/new", "appId": "a1", "aliases": ["@alice/old", "@alice/older"], "accounts": ["alice"]},
            "w-legacy": {"owner": "alice", "slug": "legacy", "address": "@alice/legacy", "appId": "a2", "aliases": []},
            "w-agent": {"owner": "helper", "slug": "made", "address": "@@helper/made", "appId": "a3", "aliases": [], "accounts": ["alice", "sdlca-for-spawn/alice"]},
            "w-bobs": {"owner": "bob", "slug": "other", "address": "@bob/other", "appId": "a4", "aliases": ["@bob/before"], "accounts": ["bob"]},
            "w-damaged": "not an object",
        }
    }

    def address_of(self, address, account="alice", owner="alice"):
        world = route.world_by_address(address, owner, self.registry, account)
        return world.get("address") if world else None

    def test_the_current_address_and_every_old_one_find_the_world(self):
        for address in ("@alice/new", "@alice/old", "@alice/older"):
            self.assertEqual(self.address_of(address), "@alice/new", address)

    def test_an_older_entry_with_no_list_of_accounts_is_served_to_the_owner_only(self):
        self.assertEqual(self.address_of("@alice/legacy"), "@alice/legacy")
        self.assertIsNone(self.address_of("@alice/legacy", account="alice-two", owner="alice-two"))

    def test_a_world_an_agent_made_is_served_to_the_accounts_that_were_recorded_for_it(self):
        self.assertEqual(self.address_of("@@helper/made"), "@@helper/made")
        self.assertEqual(self.address_of("@@helper/made", account="sdlca-for-spawn/alice"), "@@helper/made")
        self.assertIsNone(self.address_of("@@helper/made", account="sdlca-for-spawn/bob", owner="bob"))

    def test_another_accounts_world_is_not_served_even_by_an_old_address(self):
        for address in ("@bob/other", "@bob/before"):
            self.assertIsNone(self.address_of(address), address)
            self.assertEqual(self.address_of(address, account="bob", owner="bob"), "@bob/other", address)

    def test_only_an_exact_address_counts_never_an_id_a_part_or_another_spelling(self):
        for address in ("a1", "w-listed", "@alice/ne", "@alice/new-2", "@alice/news", "@Alice/new", "@alice/New", " @alice/new", "@alice/new\n", "@alice", "", "@@alice/new", "alice/new"):
            self.assertIsNone(self.address_of(address), repr(address))

    def test_a_damaged_entry_or_a_value_that_is_not_text_never_matches(self):
        for address in (None, 5, ["@alice/new"], {"a": 1}, b"@alice/new"):
            self.assertIsNone(route.world_by_address(address, "alice", self.registry, "alice"), repr(address))
        registry = {"worlds": {"w": {"owner": "alice", "address": None, "aliases": "@alice/x", "accounts": ["alice"]}}}
        self.assertIsNone(route.world_by_address("@alice/x", "alice", registry, "alice"))
        self.assertIsNone(route.world_by_address("None", "alice", registry, "alice"))
        for registry in (None, [], {}, {"worlds": []}, {"worlds": "x"}):
            self.assertIsNone(route.world_by_address("@alice/new", "alice", registry, "alice"), repr(registry))

    def test_the_account_defaults_to_the_owner(self):
        self.assertEqual(route.world_by_address("@alice/legacy", "alice", self.registry)["slug"], "legacy")

    def run_serves(self, *args, registry=None, env=None, raw=None):
        with tempfile.TemporaryDirectory() as home:
            if raw is not None:
                with open(os.path.join(home, "worlds.json"), "w") as handle:
                    handle.write(raw)
            elif registry is not False:
                with open(os.path.join(home, "worlds.json"), "w") as handle:
                    json.dump(self.registry if registry is None else registry, handle)
            full = {"OWNER": "alice", "ACCOUNT": "alice", "SDLCA_SPAWN_HOME": home}
            full.update(env or {})
            return helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "lib", "route.py"), *args], env=full, stdin="")

    def test_the_command_prints_the_current_address_and_exits_0_for_a_served_world(self):
        for address, printed in (("@alice/new", "@alice/new"), ("@alice/old", "@alice/new"), ("@@helper/made", "@@helper/made")):
            result = self.run_serves("--serves", address)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, printed + "\n", ""), address)

    def test_the_command_exits_1_and_prints_nothing_for_a_world_that_is_not_served(self):
        for address in ("@bob/other", "@alice/never", "@alice/ne", ""):
            result = self.run_serves("--serves", address)
            self.assertEqual((result.returncode, result.stdout), (1, ""), address)

    def test_the_command_uses_the_account_in_the_environment(self):
        result = self.run_serves("--serves", "@bob/other", env={"OWNER": "bob", "ACCOUNT": "bob"})
        self.assertEqual((result.returncode, result.stdout), (0, "@bob/other\n"))
        result = self.run_serves("--serves", "@@helper/made", env={"ACCOUNT": "sdlca-for-spawn/alice"})
        self.assertEqual((result.returncode, result.stdout), (0, "@@helper/made\n"))
        result = self.run_serves("--serves", "@@helper/made", env={"ACCOUNT": "sdlca-for-spawn/carol"})
        self.assertEqual((result.returncode, result.stdout), (1, ""))

    def test_a_missing_registry_or_one_with_odd_contents_serves_nothing(self):
        for kwargs in ({"registry": False}, {"raw": '{"worlds": []}'}, {"raw": '{"worlds": {"w": 5}}'}, {"raw": "{}"}):
            result = self.run_serves("--serves", "@alice/new", **kwargs)
            self.assertEqual((result.returncode, result.stdout), (1, ""), kwargs)
            self.assertNotIn("Traceback", result.stderr)

    def test_a_damaged_registry_is_not_mistaken_for_one_that_serves_nothing(self):
        """The person is told to run sdlca-worlds --apply when a world is not served, and that command refuses a file that is not a JSON object.
        So a damaged file must say that it is damaged (exit 2), and not "not served" (exit 1)."""
        for raw in ("", "not json", "[]", "5", '"x"', "null", '{"worlds": ', "\ufeff{}x"):
            result = self.run_serves("--serves", "@alice/new", raw=raw)
            self.assertEqual((result.returncode, result.stdout), (2, ""), repr(raw))
            self.assertIn("is damaged", result.stderr)
            self.assertIn("worlds.json", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        with tempfile.TemporaryDirectory() as home:  # a file that cannot be read at all, here a folder in its place
            os.mkdir(os.path.join(home, "worlds.json"))
            result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "lib", "route.py"), "--serves", "@alice/new"],
                                 env={"OWNER": "alice", "ACCOUNT": "alice", "SDLCA_SPAWN_HOME": home}, stdin="")
            self.assertEqual((result.returncode, result.stdout), (2, ""))
            self.assertIn("is damaged", result.stderr)

    def test_a_world_that_has_the_address_now_wins_over_one_that_used_to_have_it_in_either_order(self):
        """alice gave up @alice/foo (it is an old address of the world that is @alice/bar now), and another world took the name @alice/foo."""
        renamed = {"owner": "alice", "slug": "bar", "address": "@alice/bar", "appId": "a1", "aliases": ["@alice/foo"], "accounts": ["alice"]}
        taken = {"owner": "alice", "slug": "foo", "address": "@alice/foo", "appId": "a2", "aliases": [], "accounts": ["alice"]}
        for order in ((("w-1", renamed), ("w-2", taken)), (("w-2", taken), ("w-1", renamed))):
            registry = {"worlds": dict(order)}
            self.assertEqual(route.world_by_address("@alice/foo", "alice", registry, "alice")["appId"], "a2", [k for k, _ in order])
            result = self.run_serves("--serves", "@alice/foo", registry=registry)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "@alice/foo\n", ""), [k for k, _ in order])
            self.assertEqual(route.world_by_address("@alice/bar", "alice", registry, "alice")["appId"], "a1")
        # the old address still works when nobody has it now
        only = {"worlds": {"w-1": renamed}}
        self.assertEqual(route.world_by_address("@alice/foo", "alice", only, "alice")["appId"], "a1")
        # a world that this account cannot reach does not take the name from the one it can reach
        theirs = dict(taken, accounts=["bob"])
        for order in ((("w-1", renamed), ("w-2", theirs)), (("w-2", theirs), ("w-1", renamed))):
            self.assertEqual(route.world_by_address("@alice/foo", "alice", {"worlds": dict(order)}, "alice")["appId"], "a1")

    def test_two_worlds_that_answer_in_the_same_way_are_ambiguous_and_never_guessed_between(self):
        one = {"owner": "alice", "slug": "one", "address": "@alice/one", "appId": "a1", "aliases": ["@alice/x"], "accounts": ["alice"]}
        two = {"owner": "alice", "slug": "two", "address": "@alice/two", "appId": "a2", "aliases": ["@alice/x"], "accounts": ["alice"]}
        twin = {"owner": "alice", "slug": "one", "address": "@alice/one", "appId": "a3", "aliases": [], "accounts": ["alice"]}
        for registry, address in (({"worlds": {"w-1": one, "w-2": two}}, "@alice/x"), ({"worlds": {"w-1": one, "w-3": twin}}, "@alice/one")):
            with self.assertRaises(route.AmbiguousAddress):
                route.world_by_address(address, "alice", registry, "alice")
            result = self.run_serves("--serves", address, registry=registry)
            self.assertEqual((result.returncode, result.stdout), (2, ""), address)
            self.assertIn("more than one world", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        # an address that only one of them answers to is not ambiguous
        self.assertEqual(route.world_by_address("@alice/two", "alice", {"worlds": {"w-1": one, "w-2": two}}, "alice")["appId"], "a2")

    def test_a_wrong_use_exits_2_and_prints_nothing_on_standard_output(self):
        cases = (
            (("--serves",), {}),
            (("--serves", "@alice/new", "extra"), {}),
            (("--other", "@alice/new"), {}),
            (("@alice/new",), {}),
            (("--serves", "@alice/new"), {"OWNER": ""}),
        )
        for args, env in cases:
            result = self.run_serves(*args, env=env)
            self.assertEqual((result.returncode, result.stdout), (2, ""), (args, env))
            self.assertIn("usage: route.py --serves", result.stderr)

    def test_the_address_printed_is_one_line_even_if_the_registry_holds_a_line_break(self):
        registry = {"worlds": {"w": {"owner": "alice", "address": "@alice/a\nb\tc", "aliases": ["@alice/x"], "accounts": ["alice"]}}}
        result = self.run_serves("--serves", "@alice/x", registry=registry)
        self.assertEqual((result.returncode, result.stdout), (0, "@alice/a b c\n"))

    def test_asking_with_no_arguments_still_reads_an_event_from_standard_input(self):
        with tempfile.TemporaryDirectory() as home:
            env = {"OWNER": "alice", "SPAWN_USERNAME": "alice_helper", "SDLCA_SPAWN_HOME": home}
            result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "lib", "route.py")], env=env, stdin=json.dumps(chat("@alice")))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(result.stdout.rstrip("\n").split("\t")), 9)


if __name__ == "__main__":
    unittest.main()
