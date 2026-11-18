# SPDX-License-Identifier: Apache-2.0
"""lib/dedupe.py, lib/ratelimit.py and lib/safeurl.read_token: the small state and guard helpers."""
import os
import tempfile
import time
import unittest

import helpers
import safeurl

DEDUPE = os.path.join(helpers.ROOT, "lib", "dedupe.py")
RATELIMIT = os.path.join(helpers.ROOT, "lib", "ratelimit.py")


def py(script, *args):
    return helpers.run(["python3", "-I", "-B", script, *args])


class DedupeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "handled.ids")

    def tearDown(self):
        self.tmp.cleanup()

    def test_an_id_is_unseen_until_it_is_added(self):
        self.assertEqual(py(DEDUPE, "seen", self.path, "evt-1").returncode, 1)
        self.assertEqual(py(DEDUPE, "add", self.path, "evt-1").returncode, 0)
        self.assertEqual(py(DEDUPE, "seen", self.path, "evt-1").returncode, 0)
        self.assertEqual(py(DEDUPE, "seen", self.path, "evt-2").returncode, 1)

    def test_the_file_is_private_and_holds_each_id_once(self):
        for _ in range(3):
            py(DEDUPE, "add", self.path, "evt-1")
        with open(self.path) as handle:
            self.assertEqual(handle.read().split(), ["evt-1"])
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)

    def test_only_the_newest_500_ids_are_kept(self):
        with open(self.path, "w") as handle:
            handle.write("".join("old-%d\n" % i for i in range(600)))
        py(DEDUPE, "add", self.path, "new-1")
        with open(self.path) as handle:
            ids = handle.read().split()
        self.assertEqual(len(ids), 500)
        self.assertEqual(ids[-1], "new-1")
        self.assertNotIn("old-0", ids)

    def test_a_damaged_file_is_read_leniently(self):
        with open(self.path, "wb") as handle:
            handle.write(b"evt-1\n\xff\xfe broken \xc3\n evt-3 \n")
        self.assertEqual(py(DEDUPE, "seen", self.path, "evt-1").returncode, 0)
        self.assertEqual(py(DEDUPE, "seen", self.path, "evt-3").returncode, 0)
        self.assertEqual(py(DEDUPE, "seen", self.path, "evt-9").returncode, 1)
        self.assertEqual(py(DEDUPE, "add", self.path, "evt-9").returncode, 0)
        self.assertEqual(py(DEDUPE, "seen", self.path, "evt-9").returncode, 0)

    def test_a_file_that_cannot_be_opened_is_could_not_tell_not_unseen(self):
        result = py(DEDUPE, "seen", self.tmp.name, "evt-1")  # a directory
        self.assertEqual(result.returncode, 2)

    def test_bad_calls_and_odd_ids_are_could_not_tell(self):
        for args in (("seen",), ("seen", self.path), ("forget", self.path, "evt-1"), ("seen", self.path, "bad id"),
                     ("seen", self.path, "evt-1\n"), ("seen", self.path, "x" * 81), ("add", self.path, "")):
            self.assertEqual(py(DEDUPE, *args).returncode, 2, repr(args))
        self.assertFalse(os.path.exists(self.path))


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "runs.log")

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_cap_is_enforced_inside_the_window(self):
        self.assertEqual(py(RATELIMIT, self.path, "2", "3600").returncode, 0)
        self.assertEqual(py(RATELIMIT, self.path, "2", "3600").returncode, 0)
        self.assertEqual(py(RATELIMIT, self.path, "2", "3600").returncode, 1)
        with open(self.path) as handle:
            self.assertEqual(len(handle.read().split()), 2)  # the refused call recorded nothing

    def test_old_runs_fall_out_of_the_window(self):
        with open(self.path, "w") as handle:
            handle.write("%.3f\n%.3f\n" % (time.time() - 7200, time.time() - 7100))
        self.assertEqual(py(RATELIMIT, self.path, "2", "3600").returncode, 0)

    def test_a_limit_of_zero_turns_the_cap_off(self):
        for _ in range(5):
            self.assertEqual(py(RATELIMIT, self.path, "0", "3600").returncode, 0)

    def test_damaged_lines_never_count_against_the_cap(self):
        with open(self.path, "wb") as handle:
            handle.write(b"nan\ninf\n-inf\n\xff\xfe\nnot a number\n%.3f\n" % (time.time() + 86400))  # the last is in the future
        self.assertEqual(py(RATELIMIT, self.path, "1", "3600").returncode, 0)
        self.assertEqual(py(RATELIMIT, self.path, "1", "3600").returncode, 1)

    def test_a_bad_call_or_an_unusable_file_is_could_not_tell_not_a_refusal(self):
        self.assertEqual(py(RATELIMIT, self.path, "many", "3600").returncode, 2)
        self.assertEqual(py(RATELIMIT, self.path, "2").returncode, 2)
        self.assertEqual(py(RATELIMIT, self.tmp.name, "2", "3600").returncode, 2)  # a directory


class ReadTokenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "token")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, data):
        with open(self.path, "wb") as handle:
            handle.write(data)

    def test_a_plain_token_is_read_without_its_trailing_newline(self):
        self.write(b"sak_abc.DEF-123_xyz\n")
        self.assertEqual(safeurl.read_token(self.path), "sak_abc.DEF-123_xyz")

    def test_odd_content_is_refused_and_the_message_never_holds_the_token(self):
        for data in (b'sak_a"b', b"sak_a\\b", b"sak_a b", b"sak_line1\nsak_line2", b"sak_\xc3\xa9", b"sak_\xff", b"", b"  \n", b"x" * 4097):
            self.write(data)
            with self.assertRaises(SystemExit) as caught:
                safeurl.read_token(self.path)
            message = str(caught.exception)
            self.assertIn("does not hold a plain token", message, repr(data))
            self.assertNotIn("sak_", message)

    def test_a_visible_ascii_token_of_any_shape_is_accepted(self):
        self.write(b"!#$%&'()*+,-./0123456789:;<=>?@AZ[]^_`az{|}~")
        self.assertEqual(safeurl.read_token(self.path), "!#$%&'()*+,-./0123456789:;<=>?@AZ[]^_`az{|}~")


if __name__ == "__main__":
    unittest.main()
