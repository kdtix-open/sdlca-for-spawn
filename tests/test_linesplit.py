# SPDX-License-Identifier: Apache-2.0
import unittest

import helpers  # noqa: F401  (puts lib/ on sys.path)
from linesplit import LINE_LIMIT, chunk


class ChunkTests(unittest.TestCase):
    def test_empty_input_yields_no_lines(self):
        self.assertEqual(chunk(""), [])
        self.assertEqual(chunk("  \n\t "), [])

    def test_short_text_is_one_unnumbered_line(self):
        self.assertEqual(chunk("hello   world\n"), ["hello world"])

    def test_text_that_exactly_fits_stays_one_line(self):
        text = "x" * LINE_LIMIT
        self.assertEqual(chunk(text), [text])

    def test_long_text_is_numbered_and_every_line_fits(self):
        text = " ".join("word%d" % i for i in range(400))
        lines = chunk(text)
        self.assertGreater(len(lines), 2)
        for index, line in enumerate(lines, 1):
            self.assertLessEqual(len(line), LINE_LIMIT)
            self.assertTrue(line.startswith("(%d/%d) " % (index, len(lines))))

    def test_no_words_are_lost_or_reordered(self):
        text = " ".join("w%d" % i for i in range(300))
        lines = chunk(text)
        rebuilt = " ".join(line.split(") ", 1)[1] for line in lines)
        self.assertEqual(rebuilt, text)

    def test_a_single_huge_word_is_still_split_to_fit(self):
        lines = chunk("y" * 1000)
        self.assertTrue(all(len(line) <= LINE_LIMIT for line in lines))
        self.assertGreater(len(lines), 1)

    def test_over_a_hundred_lines_still_fit(self):
        lines = chunk(" ".join(["ab"] * 9000))
        self.assertGreater(len(lines), 100)
        self.assertTrue(all(len(line) <= LINE_LIMIT for line in lines))


if __name__ == "__main__":
    unittest.main()
