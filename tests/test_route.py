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
        self.assertEqual(fields, ["chat_mention", "c1", "-", "allow", "@alice", "@alice/game-1", "/clones/alice/game-1", "alice__game-1"])

    def test_an_unrouted_event_gets_a_scratch_directory_never_the_runtime_home(self):
        fields, home = self.run_main(chat("@alice"))
        self.assertEqual(fields[5:], ["-", home + "/run/scratch/alice", "unrouted__alice"])

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
        self.assertEqual(len(fields), 8)
        self.assertEqual(fields[6], home + "/run/scratch/alice")

    def test_fields_never_contain_tabs_or_newlines(self):
        reg = {"worlds": {"w": {"owner": "alice", "slug": "s", "address": "@alice/s", "appId": "a", "clone_path": "/p\tq\nr", "aliases": []}}}
        fields, _ = self.run_main(chat("@alice", relatedGameId="a"), registry=reg)
        self.assertEqual(len(fields), 8)


if __name__ == "__main__":
    unittest.main()
