# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the Python tests."""
import os
import signal
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))


def _environment(env):
    full = {"PATH": os.environ.get("PATH", ""), "HOME": tempfile.gettempdir(), "PYTHONDONTWRITEBYTECODE": "1"}
    full.update(env or {})
    return full


def run(args, env=None, stdin=None, cwd=None, timeout=None):
    """Run a command and wait for it. With a timeout, a hang is an ordinary test failure (subprocess.TimeoutExpired) and not a stalled suite."""
    return subprocess.run(args, input=stdin, capture_output=True, text=True, env=_environment(env), cwd=cwd, timeout=timeout)


def _default_interrupt():
    # A test run started in the background by a shell inherits "ignore Ctrl-C", and a program that was started with it ignores Ctrl-C too.
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def start(args, env=None, cwd=None):
    """Start a command and return it, for a test that has to send it a signal while it runs."""
    return subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=_environment(env), cwd=cwd,
                            preexec_fn=_default_interrupt)
