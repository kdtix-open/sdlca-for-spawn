# SPDX-License-Identifier: Apache-2.0
import os
import tempfile
import unittest

import helpers


class DirectRunTests(unittest.TestCase):
    """The commands are run directly (not as python3 script) by the agent and by people: the shebang must work."""

    def run_cmd(self, name, *args):
        with tempfile.TemporaryDirectory() as home:
            return helpers.run([os.path.join(helpers.ROOT, "bin", name), *args], env={"SDLCA_SPAWN_HOME": home})

    def test_the_python_commands_start_and_print_their_usage(self):
        for name in ("sdlca-say", "sdlca-worlds", "sdlca-allow"):
            result = self.run_cmd(name, "--help")
            self.assertIn("usage", (result.stdout + result.stderr).lower(), name)

    def test_the_shebang_isolates_the_interpreter(self):
        for name in ("sdlca-say", "sdlca-worlds", "sdlca-allow"):
            with open(os.path.join(helpers.ROOT, "bin", name)) as handle:
                self.assertEqual(handle.readline().strip(), "#!/usr/bin/env -S python3 -I -B", name)

    def test_allowlist_list_works_when_run_directly(self):
        result = self.run_cmd("sdlca-allow", "list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("members", result.stdout)


if __name__ == "__main__":
    unittest.main()
