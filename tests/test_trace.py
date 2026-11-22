# SPDX-License-Identifier: Apache-2.0
"""The trace: what gets written (and what never does), and what sdlca-trace makes of it."""
import datetime
import json
import os
import shutil
import tempfile
import unittest

import helpers

import sdlca_trace as tracelib

BIN = os.path.join(helpers.ROOT, "bin", "sdlca-trace")


def read_lines(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


class WriterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.file = os.path.join(self.tmp, "trace.jsonl")
        self.env = {"ACC": self.tmp, "SDLCA_TURN_ID": "t1700000000000-42"}

    def test_python_writer_cleans_values_and_keeps_numbers(self):
        old = dict(os.environ)
        os.environ.update(self.env)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old)))
        tracelib.emit("say.line", n=2, dur_ms=12.7, text='he said "sak_abc123" {x}\n', ok=True)
        (record,) = read_lines(self.file)
        self.assertEqual(record["turn"], "t1700000000000-42")
        self.assertEqual((record["n"], record["dur_ms"], record["ok"]), (2, 12, 1))
        self.assertNotIn('"', record["text"])
        self.assertNotIn("\n", record["text"])
        self.assertNotIn("{", record["text"])

    def test_off_switch_and_no_account_write_nothing(self):
        for env in ({"ACC": self.tmp, "SDLCA_TRACE": "0"}, {}):
            full = {"PATH": os.environ["PATH"]}
            full.update(env)
            result = helpers.run(["python3", "-I", "-B", "-c", "import sys; sys.path.insert(0, %r); import sdlca_trace; sdlca_trace.emit('x', a=1)" % os.path.join(helpers.ROOT, "lib")], env=full)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(os.path.exists(self.file))

    def test_the_file_is_started_again_when_it_is_large(self):
        with open(self.file, "w") as handle:
            handle.write("x" * (4 * 1024 * 1024 + 10))
        old = dict(os.environ)
        os.environ.update(self.env)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old)))
        tracelib.emit("a")
        self.assertTrue(os.path.exists(self.file + ".1"))
        self.assertEqual(len(read_lines(self.file)), 1)

    def test_bash_writer(self):
        script = ('. "$ROOT/lib/common.sh"; trace look.shot dur_ms=1500 rc=0 bytes=40000 note=\'a "quoted" $(touch /x) `id` {y}\' world=@alice/game-1; '
                  'trace "weird ev!" k=v; trace; SDLCA_TRACE=0 trace off a=1; ACC= trace nowhere a=1; echo done')
        result = helpers.run(["bash", "-c", script], env={"ROOT": helpers.ROOT, "ACC": self.tmp, "SDLCA_TURN_ID": "t1700000000001-7", "SDLCA_SPAWN_HOME": self.tmp})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("done", result.stdout)
        records = read_lines(self.file)
        self.assertEqual([r["ev"] for r in records], ["look.shot", "weird_ev_", ""])
        first = records[0]
        self.assertEqual((first["dur_ms"], first["bytes"], first["world"]), (1500, 40000, "@alice/game-1"))
        for bad in ('"', "$", "`", "{", "("):
            self.assertNotIn(bad, first["note"])
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "off")))


def event(turn, ev, ts, **fields):
    record = {"ts": ts, "turn": turn, "ev": ev}
    record.update(fields)
    return record


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "spawn")
        self.acc = os.path.join(self.home, "accounts", "alice")
        os.makedirs(self.acc)
        self.env = {"SDLCA_SPAWN_HOME": self.home}
        self.t0 = 1_700_000_000_000

    def write(self, records, name="trace.jsonl"):
        with open(os.path.join(self.acc, name), "w") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")

    def slow_turn(self, turn="t1700000000000-100", t0=None):
        t0 = t0 or self.t0
        return [
            event(turn, "turn.start", t0, kind="chat_mention", world="@alice/game-1", sender="@alice", event="e1"),
            event(turn, "lock.acquired", t0 + 20, wait_ms=15000),
            event(turn, "refresh", t0 + 900, dur_ms=800, status="current", rc=0),
            event(turn, "agent.start", t0 + 1000),
            event(turn, "look.start", t0 + 3000, world="@alice/game-1"),
            event(turn, "look.join", t0 + 20000, dur_ms=17000, rc=0),
            event(turn, "shot.wait", t0 + 30000, dur_ms=10000),
            event(turn, "shot.place", t0 + 40000, dur_ms=9000, reached="0.2,24.0,-1.4"),
            event(turn, "shot.aim", t0 + 60000, dur_ms=20000),
            event(turn, "shot.screenshot", t0 + 62000, dur_ms=2000),
            event(turn, "look.shot", t0 + 90000, dur_ms=70000, rc=0, bytes=4000),
            event(turn, "look.shot", t0 + 160000, dur_ms=70000, rc=0, bytes=300000),
            event(turn, "look.end", t0 + 161000, total_ms=158000, rc=0),
            event(turn, "say.total", t0 + 170000, lines=3, dur_ms=7800, paused_ms=4400),
            event(turn, "agent.end", t0 + 180000, dur_ms=179000, rc=0),
            event(turn, "turn.end", t0 + 180500, total_ms=180500, status=0),
        ]

    def run_trace(self, *args):
        return helpers.run([BIN, "alice"] + list(args), env=self.env, timeout=60)

    def test_a_slow_turn_is_explained(self):
        self.write(self.slow_turn())
        result = self.run_trace()
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        for words in ("total 180.5 s", "lock wait 15.0 s", "agent 179.0 s", "look (whole)", "look: join the world", "pictures: 2 attempts, 1 blank",
                      "looks are 88% of the agent's time", "came back blank", "waited 15 s for the world's lock", "deliberate pause"):
            self.assertIn(words, out)

    def test_json_output_and_selecting_turns(self):
        self.write(self.slow_turn("t1700000000000-1") + self.slow_turn("t1700000500000-2", t0=self.t0 + 500000))
        result = self.run_trace("--json", "--last", "1")
        lines = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([l["turn"] for l in lines], ["t1700000500000-2"])
        self.assertEqual(lines[0]["pictures"], {"attempts": 2, "blank": 1, "failed": 0})
        one = self.run_trace("--json", "--turn", "t1700000000000-1")
        self.assertEqual(json.loads(one.stdout)["turn"], "t1700000000000-1")
        self.assertEqual(self.run_trace("--turn", "t1700000000009-9").returncode, 1)

    def test_events_outside_a_turn_are_not_a_turn_and_junk_lines_are_skipped(self):
        self.write([event("-", "look.end", self.t0, total_ms=5)] + self.slow_turn())
        with open(os.path.join(self.acc, "trace.jsonl"), "a") as handle:
            handle.write("not json\n[1,2]\n")
        result = self.run_trace("--json")
        self.assertEqual(len(result.stdout.splitlines()), 1)

    def test_an_empty_trace_says_so(self):
        result = self.run_trace()
        self.assertEqual(result.returncode, 1)
        self.assertIn("no turns", result.stderr)

    def test_odd_arguments_are_refused(self):
        self.write(self.slow_turn())
        for args in (["--last", "0"], ["--last", "x"], ["--turn", "../x"], ["--bogus"], ["--last"]):
            self.assertEqual(self.run_trace(*args).returncode, 2, args)
        self.assertEqual(helpers.run([BIN, "../x"], env=self.env).returncode, 2)

    def test_transcripts_add_the_agents_own_tool_times_without_content(self):
        turn = self.slow_turn()
        self.write(turn)
        folder = os.path.join(self.tmp, "projects", "-some-clone")
        os.makedirs(folder)
        base = datetime.datetime.fromtimestamp((self.t0 + 1000) / 1000, datetime.timezone.utc)

        def at(seconds):
            return (base + datetime.timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")

        rows = [
            {"type": "user", "timestamp": at(0), "message": {"content": "SECRET CHAT TEXT sak_notreal"}},
            {"type": "assistant", "timestamp": at(2), "message": {"content": [{"type": "tool_use", "id": "a", "name": "Bash", "input": {"command": "/k/bin/sdlca-look alice @alice/game-1 /tmp/x.png"}}]}},
            {"type": "user", "timestamp": at(160), "message": {"content": [{"type": "tool_result", "tool_use_id": "a", "content": "PRIVATE OUTPUT"}]}},
            {"type": "assistant", "timestamp": at(162), "message": {"content": [{"type": "tool_use", "id": "b", "name": "Edit", "input": {"file_path": "/x"}}]}},
            {"type": "user", "timestamp": at(163), "message": {"content": [{"type": "tool_result", "tool_use_id": "b", "content": "ok"}]}},
        ]
        with open(os.path.join(folder, "s.jsonl"), "w") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        env = dict(self.env)
        result = helpers.run([BIN, "alice", "--transcripts", os.path.join(self.tmp, "projects")], env=env, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Bash: sdlca-look", result.stdout)
        self.assertIn("158.0 s", result.stdout)
        self.assertIn("Edit", result.stdout)
        self.assertNotIn("SECRET CHAT TEXT", result.stdout + result.stderr)
        self.assertNotIn("PRIVATE OUTPUT", result.stdout + result.stderr)
        self.assertNotIn("sak_", result.stdout)


if __name__ == "__main__":
    unittest.main()
