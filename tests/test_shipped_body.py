# SPDX-License-Identifier: Apache-2.0
"""The one body file that ships with the kit: it is the one the maintainers decided on, it is what its README says it is, and no other model file slips in."""
import hashlib
import os
import unittest

import helpers

import body

ROOT = helpers.ROOT
SHIPPED = os.path.join(ROOT, "templates", "bodies", "kdtix-agent-body.glb")
README = os.path.join(ROOT, "templates", "bodies", "README.md")
SKIP = {".git", "node_modules", "design"}  # design/ is private material that is never committed
MODEL_SUFFIXES = (".glb", ".gltf")


def read(path):
    with open(path, "rb") as handle:
        return handle.read()


class ShippedBodyTests(unittest.TestCase):
    def test_it_is_the_only_model_file_in_the_repository(self):
        found = []
        for folder, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in SKIP]
            found += [os.path.relpath(os.path.join(folder, name), ROOT) for name in files if name.lower().endswith(MODEL_SUFFIXES)]
        self.assertEqual(sorted(found), ["templates/bodies/kdtix-agent-body.glb"],
                         "A maintainer decided on 2026-11-20 that this is the only generated model the kit ships until the question has been reviewed further "
                         "(see templates/bodies/README.md). Change this test only when that review has happened.")

    def test_it_is_a_complete_rigged_model_that_the_tool_will_carry(self):
        data = body.read_model(SHIPPED)  # a glTF binary whose header names its own length
        self.assertGreaterEqual(body.glb_skins(data) or 0, 1, "a body needs a skeleton")
        self.assertLessEqual(len(data), body.MAX_MODEL_BYTES)

    def test_its_readme_names_its_hash_its_size_and_the_decision(self):
        data = read(SHIPPED)
        text = read(README).decode("utf-8")
        self.assertIn(hashlib.sha256(data).hexdigest(), text)
        self.assertIn("{:,}".format(len(data)) + " bytes", text)
        for words in ("2026-11-20", "No other generated model is shipped", "Spawn was not asked", "tests/test_shipped_body.py"):
            self.assertIn(words, text)

    def test_the_address_in_the_readme_is_the_one_named_by_the_hash(self):
        digest = hashlib.sha256(read(SHIPPED)).hexdigest()
        self.assertIn("https://www.spawn.co/cdn/value.%s.glb" % digest, read(README).decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
