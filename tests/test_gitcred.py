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
