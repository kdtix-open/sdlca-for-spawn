# SPDX-License-Identifier: Apache-2.0
import base64
import json
import os
import tempfile
import unittest

import helpers
from cursor import should_advance


def make(created_at, ident="x"):
    raw = json.dumps({"createdAt": created_at, "id": ident}).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


OLD = make("2026-11-12T23:03:40.247384+00:00")
NEW = make("2026-11-13T02:06:21.000000+00:00")


class CursorTests(unittest.TestCase):
    def test_empty_store_accepts_anything(self):
        self.assertTrue(should_advance("", OLD))

    def test_moves_forward_only(self):
        self.assertTrue(should_advance(OLD, NEW))
        self.assertFalse(should_advance(NEW, OLD))
        self.assertFalse(should_advance(NEW, NEW))

    def test_ties_on_time_break_on_id(self):
        self.assertTrue(should_advance(make("2026-11-13T00:00:00+00:00", "a"), make("2026-11-13T00:00:00+00:00", "b")))

    def test_opaque_values_are_written_as_given(self):
        self.assertTrue(should_advance("not-a-cursor", NEW))
        self.assertTrue(should_advance(OLD, "also-opaque"))

    def test_cli_writes_atomically_with_private_mode_and_never_goes_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cursor")
            for value in (OLD, NEW, OLD):
                result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "lib", "cursor.py"), path, value])
                self.assertEqual(result.returncode, 0, result.stderr)
            with open(path) as handle:
                self.assertEqual(handle.read(), NEW)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertFalse(os.path.exists(path + ".tmp"))

    def test_a_time_with_and_without_a_zone_can_be_compared(self):
        naive = make("2026-11-13T02:00:00")
        aware = make("2026-11-13T03:00:00+00:00")
        self.assertTrue(should_advance(naive, aware))
        self.assertFalse(should_advance(aware, naive))

    def test_writers_that_finish_together_never_rewind_the_cursor(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cursor")
            values = [make("2026-11-13T02:%02d:00+00:00" % minute) for minute in range(40)]
            script = os.path.join(helpers.ROOT, "lib", "cursor.py")
            env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
            procs = [subprocess.Popen(["python3", "-I", "-B", script, path, value], env=env) for value in reversed(values)]
            for proc in procs:
                self.assertEqual(proc.wait(), 0)
            with open(path) as handle:
                self.assertEqual(handle.read(), values[-1])
            leftovers = [name for name in os.listdir(tmp) if name.startswith(".cursor.")]
            self.assertEqual(leftovers, [])

    def test_a_cursor_file_with_bad_bytes_is_replaced_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cursor")
            with open(path, "wb") as handle:
                handle.write(b"\xff\xfe not a cursor")
            result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "lib", "cursor.py"), path, NEW])
            self.assertEqual(result.returncode, 0, result.stderr)
            with open(path) as handle:
                self.assertEqual(handle.read(), NEW)


if __name__ == "__main__":
    unittest.main()
