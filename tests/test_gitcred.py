# SPDX-License-Identifier: Apache-2.0
import os
import subprocess
import tempfile
import unittest

import helpers
import gitcred

SPAWN_GIT = "https://git.spawn.co/@alice/game-1.git"


def run_git(args, cwd, stdin=None, extra=None):
    env = {"PATH": os.environ["PATH"], "HOME": cwd, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
    env.update(extra or {})
    return subprocess.run(["git", *args], cwd=cwd, input=stdin, capture_output=True, text=True, env=env)


class CloneConfigTests(unittest.TestCase):
    def test_the_helper_is_attached_to_the_git_host_of_the_url_only(self):
        config = gitcred.clone_config(SPAWN_GIT, "alice_helper", "/p/token")
        self.assertEqual(config[0], "credential.helper=")
        scoped = [c for c in config if c.startswith("credential.https://git.spawn.co.helper=")]
        self.assertEqual(len(scoped), 1)
        self.assertIn("username=alice_helper", scoped[0])
        self.assertIn("/p/token", scoped[0])
        self.assertIn("http.https://git.spawn.co.proactiveAuth=basic", config)
        self.assertIn("remote.origin.fetch=+refs/notes/*:refs/notes/*", config)
        self.assertFalse([c for c in config if c.startswith("credential.helper=") and c != "credential.helper="])

    def test_a_port_stays_part_of_the_scope(self):
        config = gitcred.clone_config("https://git.example.invalid:8443/x.git", "u", "/t")
        self.assertTrue(any(c.startswith("credential.https://git.example.invalid:8443.helper=") for c in config))

    def test_urls_that_are_not_plain_https_get_no_helper(self):
        for url in ("file:///tmp/x.git", "/tmp/x.git", "http://git.spawn.co/x.git", "ssh://git@git.spawn.co/x.git", "https://user:pw@git.spawn.co/x.git", "https:///x"):  # check-secrets:allow (a made-up password, to prove it is refused)
            config = gitcred.clone_config(url, "u", "/t")
            self.assertEqual(config, ["credential.helper=", "remote.origin.fetch=+refs/notes/*:refs/notes/*"], url)

    def test_paths_with_spaces_and_quotes_are_quoted(self):
        command = gitcred.helper_command("alice", "/tmp/odd dir/tok'en")
        self.assertTrue(command.startswith("!"))
        out = subprocess.run(["sh", "-c", command[1:] + " get"], capture_output=True, text=True, env={"PATH": os.environ["PATH"]})  # git strips the "!"
        self.assertIn("username=alice", out.stdout)
        self.assertIn("password=\n", out.stdout)  # the file does not exist, so there is no password; nothing else ran
        self.assertIn("/tmp/odd dir/tok'en", out.stderr)  # cat was asked for exactly the odd path, as one argument


class AddressTests(unittest.TestCase):
    """One parser for a git address, and the one test of whether the clone's credential helper (and so a recorded address) may go with it."""

    def test_a_plain_address_is_split_and_nothing_else_is_accepted(self):
        url = gitcred.parse_url("HTTPS://Git.Spawn.CO:8443/@alice/game-1.git")
        self.assertEqual((url.scheme, url.host, url.port, url.path, url.authority), ("https", "git.spawn.co", "8443", "/@alice/game-1.git", "Git.Spawn.CO:8443"))
        self.assertEqual(gitcred.parse_url("https://git.spawn.co"), ("https", "git.spawn.co", "", "", "git.spawn.co"))
        self.assertEqual(gitcred.parse_url("file:///tmp/world.git").path, "/tmp/world.git")
        self.assertEqual(gitcred.parse_url("https://[::1]:8443/x").host, "[::1]")
        for bad in ("https://" + "user:pw" + "@git.spawn.co/x", "https://user@git.spawn.co/x", "https://git.spawn.co@evil.example/x",  # check-secrets:allow
                    "https://evil.example\\@git.spawn.co/x", "https://git.spawn.co/x?y", "https://git.spawn.co/x#y", "https://git.spawn.co/x y", "https://git.spawn.co/x\n",
                    "https://git.spawn.co\t/x", "https://git.spawn.co:abc/x", "https://git.spawn.co:0/x", "https://git.spawn.co:65536/x", "https://git.spawn.co:/x",
                    "https:///x", "https://-host/x", "https://.host/x", "https://exämple.com/x", "https://[::1/x", "file://:8443/x", "/tmp/x", "git@git.spawn.co:x", "x://",
                    "", "x" * 3000, None, 5, ["https://git.spawn.co/x"], b"https://git.spawn.co/x"):
            with self.subTest(bad=repr(bad)[:50]):
                self.assertIsNone(gitcred.parse_url(bad))

    def test_the_scope_of_the_helper_is_the_https_origin_as_written(self):
        self.assertEqual(gitcred.credential_scope(SPAWN_GIT), "https://git.spawn.co")
        self.assertEqual(gitcred.credential_scope("https://Git.Example.Invalid:8443/x.git"), "https://Git.Example.Invalid:8443")
        self.assertEqual(gitcred.credential_scope("HTTPS://git.spawn.co"), "https://git.spawn.co")

    def test_an_address_that_cannot_carry_the_helper_has_no_scope(self):
        for url in ("file:///tmp/x.git", "/tmp/x.git", "http://git.spawn.co/x.git", "ssh://git@git.spawn.co/x.git", "https://user@git.spawn.co/x.git", "https:///x",
                    "https://" + "user:pw" + "@git.spawn.co/x.git", "https://git.spawn.co:notaport/x.git", "https://git.spawn.co/x y.git", "https://git.spawn.co/x\n", "", None, 5):  # check-secrets:allow
            with self.subTest(url=repr(url)):
                self.assertIsNone(gitcred.credential_scope(url))

    def test_the_helper_is_written_exactly_when_there_is_a_scope(self):
        for url in (SPAWN_GIT, "https://git.example.invalid:8443/x.git", "file:///tmp/x.git", "http://git.spawn.co/x.git", "https://user@git.spawn.co/x.git",
                    "https://git.spawn.co:notaport/x.git", "https://git.spawn.co/x y.git"):
            config = gitcred.clone_config(url, "u", "/t")
            self.assertEqual(len(config) == 4, gitcred.credential_scope(url) is not None, url)
            self.assertEqual(config[0], "credential.helper=")
            self.assertEqual(config[-1], "remote.origin.fetch=+refs/notes/*:refs/notes/*")


    def test_the_length_limit_is_exact_and_a_backslash_in_the_path_is_refused(self):
        base = "https://git.spawn.co/"
        self.assertIsNotNone(gitcred.parse_url(base + "a" * (gitcred.URL_LIMIT - len(base))))  # 2048 characters: the longest that is looked at
        self.assertIsNone(gitcred.parse_url(base + "a" * (gitcred.URL_LIMIT - len(base) + 1)))  # one more is not
        self.assertIsNone(gitcred.parse_url("https://git.spawn.co/a\\b"))
        self.assertIsNone(gitcred.parse_url("https://git.spawn.co\\a/b"))

    def test_a_dot_segment_is_found_however_it_is_spelled(self):
        for path in ("/a/../b", "/a/./b", "/..", "/.", "/a/..", "/a/%2e%2e/b", "/a/%2E%2E/b", "/a/%2e./b", "/a/.%2E/b", "/%2e", "/a/%2E", "/a/../", "/a/./.git"):
            with self.subTest(path=path):
                self.assertTrue(gitcred.has_dot_segment(path), path)
        for path in ("", "/", "/@alice/game-1.git", "/a/.hidden/b", "/a/..b/c", "/a/b../c", "/a/...", "/a/.git", "/a/%2e%2ex", "/a/%252e%252e/b", "/@alice/a.b.git/"):
            with self.subTest(path=path):
                self.assertFalse(gitcred.has_dot_segment(path), path)

    def test_the_two_programs_agree_on_what_is_recorded(self):
        """sdlca-worlds records an address only when gitcred.recordable says so, and lib/refresh.py holds a clone only to one that
        refresh.recorded_address accepts. Nothing recordable may be refused by the update (it would show up as "unverified" for no reason a person
        could see), and an https address that the update refuses must not be recordable."""
        import refresh
        for url in (SPAWN_GIT, "https://git.spawn.co/a/../game-1.git", "https://git.spawn.co/a/%2e%2e/game-1.git", "https://git.spawn.co/./game-1.git",
                    "https://Git.Spawn.CO:8443/@Alice/Game-1", "https://git.spawn.co", "https://git.spawn.co/", "https://[::1]:8443/x.git", "https://127.0.0.1/x.git",
                    "http://git.spawn.co/x.git", "ssh://git@git.spawn.co/x.git", "file:///tmp/x.git", "https://user@git.spawn.co/x.git", "https:///x.git",
                    "https://git.spawn.co/x.git?y", "https://git.spawn.co/x y", "", None, 5):
            with self.subTest(url=repr(url)):
                if gitcred.recordable(url):
                    self.assertIsNotNone(refresh.recorded_address(url))
                    self.assertIsNotNone(gitcred.credential_scope(url))
                if gitcred.credential_scope(url) is not None and refresh.recorded_address(url) is None:
                    self.assertFalse(gitcred.recordable(url))
        self.assertTrue(gitcred.recordable(SPAWN_GIT))
        self.assertFalse(gitcred.recordable("https://git.spawn.co/a/../game-1.git"))
        self.assertIsNotNone(gitcred.credential_scope("https://git.spawn.co/a/../game-1.git"))  # the helper alone would have gone with it: that is the gap this closes


class GitBehaviorTests(unittest.TestCase):
    """What git itself does with these settings (nothing here touches the network)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        token = os.path.join(self.tmp.name, "token")
        with open(token, "w") as handle:
            handle.write("sak_" + "not_a_real_token_just_a_test\n")
        run_git(["init", "-q", "."], self.repo)
        for setting in gitcred.clone_config(SPAWN_GIT, "alice_helper", token):
            key, _, value = setting.partition("=")
            run_git(["config", "--local", "--add", key, value], self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def fill(self, host):
        return run_git(["credential", "fill"], self.repo, stdin="protocol=https\nhost=%s\n\n" % host)

    def test_spawns_git_host_gets_the_account_and_token(self):
        result = self.fill("git.spawn.co")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("username=alice_helper", result.stdout)
        self.assertIn("password=sak_" + "not_a_real_token_just_a_test", result.stdout)

    def test_any_other_host_gets_nothing(self):
        for host in ("evil.example.invalid", "git.spawn.co.evil.invalid", "spawn.co", "www.spawn.co"):
            result = self.fill(host)
            self.assertNotEqual(result.returncode, 0, host)
            self.assertNotIn("sak_" + "not_a_real_token", result.stdout + result.stderr, host)

    def test_proactive_auth_is_scoped_the_same_way(self):
        ours = run_git(["config", "--get-urlmatch", "http.proactiveAuth", "https://git.spawn.co/@alice/game-1.git"], self.repo)
        other = run_git(["config", "--get-urlmatch", "http.proactiveAuth", "https://evil.example.invalid/x.git"], self.repo)
        self.assertEqual(ours.stdout.strip(), "basic")
        self.assertEqual(other.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
