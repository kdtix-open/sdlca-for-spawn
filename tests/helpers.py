# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the Python tests."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))


def run(args, env=None, stdin=None, cwd=None):
    full = {"PATH": os.environ.get("PATH", ""), "HOME": tempfile.gettempdir(), "PYTHONDONTWRITEBYTECODE": "1"}
    full.update(env or {})
    return subprocess.run(args, input=stdin, capture_output=True, text=True, env=full, cwd=cwd)
