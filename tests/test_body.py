# SPDX-License-Identifier: Apache-2.0
"""sdlca-body against a stand-in Spawn that listens on this machine: no network, no real account, no real picture."""
import contextlib
import hashlib
import io
import json
import os
import signal
import stat
import struct
import tempfile
import threading
import time
import unittest
import zlib
from email.parser import BytesParser
from email.policy import HTTP
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

import helpers

import body

TOKEN = "sak_fake_token_xyz123"
BIN = os.path.join(helpers.ROOT, "bin", "sdlca-body")
ME = {
    "actorClass": "agent",
    "handle": "@@alice_helper",
    "name": "sdlca",
    "characterModelUrl": None,
    "looks": [{"key": "muse", "name": "Muse"}, {"key": "claude-crab", "name": "Crab"}, {"key": "codex", "name": "Codex"}],
    "linked": True,
    "linkedTo": "alice",
    "budget": {"paidBy": "@alice", "lanes": {"generation": {"state": "open"}, "compute": {"state": "open"}}},
}
DRAFT = {"characterId": "char-1", "resultAssetId": "asset-1", "historyId": "hist-1", "status": "ready"}
JOB_STARTED = {"jobId": "job-1", "characterId": "char-1", "resultAssetId": "asset-1", "status": "queued"}
MODEL = "https://www.spawn.co/magic/character-robot-character-0123abcd.glb"  # the form Spawn gave in the one real run
EQUIPPED = {"success": True, "characterId": "char-1", "modelUrl": MODEL}
DONE = {"jobId": "job-1", "status": "completed", "modelUrl": MODEL}
RUNNING = {"jobId": "job-1", "status": "processing", "stage": "mesh"}


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def png_bytes(width=8, height=6, extra=(), trailing=b""):
    raw = b"".join(b"\x00" + b"\x10\x20\x30" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + b"".join(chunk(kind, data) for kind, data in extra) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"") + trailing)


def jpeg_bytes(trailing=b"", scans=1, segments=()):
    out = b"\xff\xd8"
    for marker, payload in segments:
        out += b"\xff" + bytes([marker]) + struct.pack(">H", len(payload) + 2) + payload
    for number in range(scans):
        out += b"\xff\xda" + struct.pack(">H", 4) + b"\x01\x00"
        out += b"\x12\x34\xff\x00\x56\xff\xd0\x78"  # coded data with a stuffed 0xFF and a restart marker
        if number + 1 < scans:
            out += b"\xff\xc4" + struct.pack(">H", 4) + b"\x00\x00"
    return out + b"\xff\xd9" + trailing


def webp_bytes(trailing=b""):
    return b"RIFF" + struct.pack("<I", 4 + 8 + 4) + b"WEBP" + b"VP8 " + struct.pack("<I", 4) + b"abcd" + trailing


def glb_bytes(extra=0, skins=1, version=2, length_delta=0):
    document = {"asset": {"version": "2.0"}, "nodes": [{}], "skins": [{"joints": [0]} for _ in range(skins)]}
    js = json.dumps(document).encode()
    js += b" " * (-len(js) % 4)
    chunks = struct.pack("<I4s", len(js), b"JSON") + js
    if extra:
        padded = extra + (-extra % 4)
        chunks += struct.pack("<I4s", padded, b"BIN\x00") + b"\x00" * padded
    return b"glTF" + struct.pack("<II", version, 12 + len(chunks) + length_delta) + chunks


WORLD_ID = "11111111-2222-3333-4444-555555555555"
WORLD = {"appId": "app-1", "worldId": WORLD_ID, "address": "@alice/game-1", "standing": "editor", "name": "game-1"}
ME_WORLD = dict(ME, worlds=[WORLD])


class Fake(BaseHTTPRequestHandler):
    """The stand-in. answers[(method, path)] is a list of steps (status, payload[, headers]): each call takes the next one, and the last one
    repeats. A status of "drop" closes the connection without an answer, "hold" keeps the request open until `release` is set, and "endless"
    answers a chunked 200 whose trailer never ends. A payload that is bytes is sent as it is."""

    calls = []
    answers = {}
    release = threading.Event()

    def handle_any(self, method):
        length = int(self.headers.get("Content-Length") or 0)
        data = self.rfile.read(length) if length else b""
        Fake.calls.append((method, self.path, self.headers.get("Authorization"), self.headers.get("Content-Type"), data))
        steps = Fake.answers.get((method, self.path))
        if not steps:
            status, payload, headers = 404, {"error": "no such door in the stand-in"}, {}
        else:
            step = steps[0] if len(steps) == 1 else steps.pop(0)
            status, payload, headers = (step[0], step[1], step[2] if len(step) > 2 else {})
        if status == "drop":
            self.close_connection = True
            return
        if status == "hold":
            Fake.release.wait(30)
            self.close_connection = True
            return
        if status == "endless":
            self.close_connection = True
            try:
                self.wfile.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n{}\r\n0\r\n")
                end = time.monotonic() + 20
                while time.monotonic() < end and not Fake.release.is_set():
                    self.wfile.write(b"X-Trailer: " + b"a" * 100 + b"\r\n")
                    time.sleep(0.002)
            except OSError:
                pass
            return
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.handle_any("GET")

    def do_POST(self):
        self.handle_any("POST")

    def do_PATCH(self):
        self.handle_any("PATCH")

    def do_PUT(self):
        self.handle_any("PUT")

    def log_message(self, *args):
        pass


class Elsewhere(BaseHTTPRequestHandler):
    """Another host: a redirect that was followed, or a proxy that was used, would bring the token here."""

    hits = []

    def do_POST(self):
        Elsewhere.hits.append(self.headers.get("Authorization"))
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    do_GET = do_POST

    def log_message(self, *args):
        pass


def serve(handler):
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def wait_for(predicate, timeout=30):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return False


class BodyCase(unittest.TestCase):
    def setUp(self):
        Fake.calls = []
        Fake.answers = {}
        Fake.release = threading.Event()
        Elsewhere.hits = []
        self.server = serve(Fake)
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "spawn")
        self.account = os.path.join(self.home, "accounts", "alice")
        os.makedirs(self.account)
        token = os.path.join(self.account, "token")
        with open(token, "w") as handle:
            handle.write(TOKEN + "\n")
        os.chmod(token, 0o600)
        env = os.path.join(self.account, "env")
        with open(env, "w") as handle:
            handle.write("OWNER=alice\nSPAWN_USERNAME=alice_helper\nSPAWN_TOKEN_FILE=%s\n" % token)
        os.chmod(env, 0o600)
        self.token_file = token
        self.marker = os.path.join(self.account, "body-sculpt.json")
        self.env = {"SDLCA_SPAWN_HOME": self.home, "SPAWN_ORIGIN": "http://127.0.0.1:%d" % self.server.server_port, "SDLCA_BODY_POLL": "1"}
        self.folder = os.path.join(self.tmp.name, "Alex Example", "Pics")
        os.makedirs(self.folder)
        self.picture = os.path.join(self.folder, "my-agent-body.png")
        self.image = png_bytes()
        with open(self.picture, "wb") as handle:
            handle.write(self.image)

    def tearDown(self):
        Fake.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def merged(self, env):
        merged = dict(self.env)
        merged.update(env or {})
        return merged

    def body(self, *args, env=None, timeout=90):
        return helpers.run([BIN, "alice", *args], env=self.merged(env), timeout=timeout)

    def start(self, *args, env=None):
        return helpers.start([BIN, "alice", *args], env=self.merged(env))

    def answer(self, method, path, *steps):
        Fake.answers[(method, path)] = list(steps)

    def script_full_run(self, job_steps=None):
        self.answer("GET", "/api/agent/v1/me", (200, ME), (200, dict(ME, characterModelUrl=MODEL)))  # the first answer, then the profile read back after the equip
        self.answer("POST", "/api/character/picture", (200, DRAFT))
        self.answer("POST", "/api/character/convert", (200, JOB_STARTED))
        self.answer("GET", "/api/character/jobs/job-1", *(job_steps or [(200, DONE)]))
        self.answer("POST", "/api/character/equip", (200, EQUIPPED))

    def sequence(self):
        return [(method, path) for method, path, *_ in Fake.calls]

    def count(self, method, path):
        return self.sequence().count((method, path))

    def recorded(self):
        try:
            with open(self.marker) as handle:
                return json.load(handle)
        except FileNotFoundError:
            return None

    def fresh(self):
        """Forget what the stand-in saw, and the record of a sculpt, so that one test can run the tool again."""
        Fake.calls = []
        try:
            os.unlink(self.marker)
        except FileNotFoundError:
            pass

    def assertNoToken(self, result):
        self.assertNotIn(TOKEN, result.stdout)
        self.assertNotIn(TOKEN, result.stderr)


class PlanTests(BodyCase):
    def test_a_dry_run_asks_once_who_the_agent_is_and_changes_nothing(self):
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        result = self.body(self.picture)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me")])
        self.assertIn("dry run", result.stdout)
        self.assertIn("Add --apply", result.stdout)
        self.assertIn("@@alice_helper", result.stdout)
        self.assertIn("PNG, 8 x 6", result.stdout)
        self.assertIn("sha256", result.stdout)
        self.assertIn("Spawn's default body", result.stdout)
        self.assertIn("right to upload", result.stdout)
        self.assertFalse(os.path.exists(self.marker))
        self.assertNoToken(result)

    def test_a_picture_that_carries_text_data_says_so_in_the_plan(self):
        with open(self.picture, "wb") as handle:
            handle.write(png_bytes(extra=[(b"tEXt", b"Author\x00someone")]))
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.assertIn("tEXt", self.body(self.picture).stdout)

    def test_bytes_after_the_end_of_the_picture_are_named_in_the_plan(self):
        with open(self.picture, "wb") as handle:
            handle.write(png_bytes(trailing=b"a video would be here"))
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.assertIn("21 bytes after the end of the picture", self.body(self.picture).stdout)

    def test_an_agent_that_already_wears_a_made_body_is_told_it_will_be_replaced(self):
        self.answer("GET", "/api/agent/v1/me", (200, dict(ME, characterModelUrl=MODEL)))
        self.assertIn("a new one replaces it", self.body(self.picture).stdout)


class MakeTests(BodyCase):
    def test_a_picture_becomes_a_body_that_is_worn(self):
        self.script_full_run([(200, {"jobId": "job-1", "status": "queued"}), (200, RUNNING), (200, DONE)])
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.sequence(), [
            ("GET", "/api/agent/v1/me"), ("POST", "/api/character/picture"), ("POST", "/api/character/convert"),
            ("GET", "/api/character/jobs/job-1"), ("GET", "/api/character/jobs/job-1"), ("GET", "/api/character/jobs/job-1"),
            ("POST", "/api/character/equip"), ("GET", "/api/agent/v1/me"),
        ])
        for method, path, auth, *_ in Fake.calls:
            self.assertEqual(auth, "Bearer " + TOKEN, path)
        self.assertEqual(json.loads(Fake.calls[2][4]), {"sourceAssetId": "asset-1"})
        self.assertEqual(json.loads(Fake.calls[6][4]), {"jobId": "job-1"})
        self.assertIn("done: the body is worn", result.stdout)
        self.assertIn("sdlca-body alice --reset char-1 --apply", result.stdout)
        self.assertIn("curl -L -o body.glb " + MODEL, result.stdout)
        self.assertIn("--carry body.glb --world <@owner/world> --apply", result.stdout)
        self.assertIn("Spawn refuses this address as it is", result.stdout)
        self.assertIn("stage mesh", result.stdout)
        self.assertIn("job job-1", result.stdout)
        self.assertFalse(os.path.exists(self.marker), "the record of the sculpt is removed once the body is worn")
        self.assertNoToken(result)

    def test_the_picture_goes_up_as_it_is_under_a_fixed_name(self):
        self.script_full_run()
        self.assertEqual(self.body(self.picture, "--apply").returncode, 0)
        _, _, _, content_type, raw = Fake.calls[1]
        message = BytesParser(policy=HTTP).parsebytes(b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + raw)
        parts = list(message.iter_parts())
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0].get_param("name", header="content-disposition"), "image")
        self.assertEqual(parts[0].get_filename(), "body.png")
        self.assertEqual(parts[0].get_content_type(), "image/png")
        self.assertEqual(parts[0].get_payload(decode=True), self.image)
        for private in (b"Example", b"my-agent-body", b"Pics", self.tmp.name.encode()):
            self.assertNotIn(private, raw)

    def test_a_jpeg_and_a_webp_go_up_with_their_own_type_whatever_the_file_is_called(self):
        for kind, data, content_type, ext in (("jpeg", jpeg_bytes(), "image/jpeg", "jpg"), ("webp", webp_bytes(), "image/webp", "webp")):
            self.fresh()
            self.script_full_run()
            path = os.path.join(self.folder, "named-like-a." + ("png" if kind == "jpeg" else "jpg"))
            with open(path, "wb") as handle:
                handle.write(data)
            self.assertEqual(self.body(path, "--apply").returncode, 0, kind)
            _, _, _, content_type_header, raw = Fake.calls[1]
            message = BytesParser(policy=HTTP).parsebytes(b"Content-Type: " + content_type_header.encode() + b"\r\n\r\n" + raw)
            part = list(message.iter_parts())[0]
            self.assertEqual(part.get_content_type(), content_type)
            self.assertEqual(part.get_filename(), "body." + ext)

    def test_trouble_while_waiting_is_asked_again_but_nothing_that_makes_is_repeated(self):
        self.script_full_run([(503, {"error": "busy"}), ("drop", None), (429, {"error": "slow down"}, {"Retry-After": "0"}), (200, DONE)])
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for door in (("POST", "/api/character/picture"), ("POST", "/api/character/convert"), ("POST", "/api/character/equip")):
            self.assertEqual(self.count(*door), 1, door)
        self.assertEqual(self.count("GET", "/api/character/jobs/job-1"), 4)

    def test_a_sculpt_that_is_still_running_when_the_wait_ends_is_left_running_and_can_be_resumed(self):
        self.script_full_run([(200, RUNNING)])
        result = self.body(self.picture, "--apply", "--wait", "1")
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("sdlca-body alice --job job-1 --apply", result.stderr)
        self.assertIn("keeps running at Spawn", result.stderr)
        self.assertIn("last status was 'processing'", result.stderr)
        self.assertNotIn(("POST", "/api/character/equip"), self.sequence())
        self.assertEqual(self.count("POST", "/api/character/convert"), 1)
        self.assertEqual(self.recorded()["job"], "job-1", "the record keeps the job id, for the next run")

    def test_when_no_check_is_answered_the_state_of_the_sculpt_is_said_to_be_unknown(self):
        self.script_full_run([("drop", None)])
        result = self.body(self.picture, "--apply", "--wait", "1")
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("so its state is not known", result.stderr)
        self.assertIn("--job job-1 --apply", result.stderr)

    def test_a_sculpt_that_failed_is_not_worn_and_its_record_is_removed(self):
        self.script_full_run([(200, {"jobId": "job-1", "status": "failed", "error": "the picture has no body in it"})])
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("did not finish", result.stderr)
        self.assertIn("the picture has no body in it", result.stderr)
        self.assertNotIn("--job", result.stderr, "nothing can be carried on after a failed sculpt")
        self.assertNotIn(("POST", "/api/character/equip"), self.sequence())
        self.assertFalse(os.path.exists(self.marker))

    def test_a_failed_status_with_no_error_text_stops_at_once(self):
        self.script_full_run([(200, {"jobId": "job-1", "status": "failed"})])
        started = time.monotonic()
        result = self.body(self.picture, "--apply", "--wait", "60")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertLess(time.monotonic() - started, 20)
        self.assertNotIn(("POST", "/api/character/equip"), self.sequence())

    def test_a_refused_upload_stops_there_and_says_why(self):
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.answer("POST", "/api/character/picture", (403, {"error": "agent_lane_closed", "verdict": "Generation is a person's."}))
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("HTTP 403 agent_lane_closed: Generation is a person's.", result.stderr)
        self.assertNotIn(("POST", "/api/character/convert"), self.sequence())
        self.assertFalse(os.path.exists(self.marker))

    def test_a_draft_that_spawn_flagged_is_not_sculpted(self):
        for draft in ({"resultAssetId": "asset-1", "status": "rejected"}, {"resultAssetId": "asset-1", "status": "ready", "error": "blocked by review"}):
            self.fresh()
            self.answer("GET", "/api/agent/v1/me", (200, ME))
            self.answer("POST", "/api/character/picture", (200, draft))
            result = self.body(self.picture, "--apply")
            self.assertEqual(result.returncode, 1, draft)
            self.assertIn("did not accept the picture", result.stderr)
            self.assertNotIn(("POST", "/api/character/convert"), self.sequence())
            self.assertFalse(os.path.exists(self.marker))

    def test_the_draft_s_status_is_shown(self):
        self.script_full_run()
        self.assertIn("status ready", self.body(self.picture, "--apply").stdout)


class ConvertTests(BodyCase):
    """The one call that costs money: what the person is told, and what is recorded, whatever happens to it."""

    def setUp(self):
        super().setUp()
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.answer("POST", "/api/character/picture", (200, DRAFT))

    def test_a_server_error_may_mean_that_the_sculpt_started(self):
        for status in (500, 502, 504, 408):
            self.fresh()
            self.answer("POST", "/api/character/convert", (status, {"error": "gateway gave up"}))
            result = self.body(self.picture, "--apply")
            self.assertEqual(result.returncode, 1, status)
            self.assertIn("may have started it anyway", result.stderr, status)
            self.assertIn("recorded this in", result.stderr, status)
            self.assertEqual(self.count("POST", "/api/character/convert"), 1, status)
            self.assertEqual(self.recorded()["state"], "unknown", status)
            self.assertNotIn(("GET", "/api/character/jobs/job-1"), self.sequence())

    def test_a_dropped_connection_may_mean_that_the_sculpt_started(self):
        self.answer("POST", "/api/character/convert", ("drop", None))
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("may have started it anyway", result.stderr)
        self.assertEqual(self.count("POST", "/api/character/convert"), 1)
        self.assertEqual(self.recorded()["state"], "unknown")

    def test_an_answer_without_a_usable_job_id_may_mean_that_the_sculpt_started(self):
        for answer in ({"id": "job-1"}, {"jobId": "job.1"}, {"jobId": 12345}, {"jobId": "a b"}, {}):
            self.fresh()
            self.answer("POST", "/api/character/convert", (200, answer))
            result = self.body(self.picture, "--apply")
            self.assertEqual(result.returncode, 1, answer)
            self.assertIn("gave no usable job id", result.stderr, answer)
            self.assertIn("may have started it anyway", result.stderr, answer)
            self.assertEqual(self.recorded()["state"], "unknown", answer)
            self.assertEqual(self.count("POST", "/api/character/convert"), 1)

    def test_a_refusal_means_that_nothing_started_and_nothing_stays_recorded(self):
        for status in (400, 403, 409, 422, 429):
            self.fresh()
            self.answer("POST", "/api/character/convert", (status, {"error": "no"}))
            result = self.body(self.picture, "--apply")
            self.assertEqual(result.returncode, 1, status)
            self.assertIn("Spawn refused the sculpt: HTTP %d" % status, result.stderr)
            self.assertNotIn("may have started", result.stderr)
            self.assertFalse(os.path.exists(self.marker), status)
            self.assertEqual(self.count("POST", "/api/character/convert"), 1)

    def test_ctrl_c_while_the_answer_is_pending_says_that_the_sculpt_may_have_started(self):
        self.answer("POST", "/api/character/convert", ("hold", None))
        process = self.start(self.picture, "--apply")
        self.assertTrue(wait_for(lambda: ("POST", "/api/character/convert") in self.sequence()))
        process.send_signal(signal.SIGINT)
        out, err = process.communicate(timeout=30)
        Fake.release.set()
        self.assertEqual(process.returncode, 130, out + err)
        self.assertIn("may have started it anyway", err)
        self.assertEqual(self.recorded()["state"], "unknown")


class AfterTheSculptStartsTests(BodyCase):
    """Once the sculpt exists, every way to stop that is not the sculpt failing says how to carry on."""

    def test_an_equip_that_fails_says_how_to_carry_on(self):
        for step in ((500, {"error": "boom"}), (429, {"error": "slow"}), ("drop", None), (200, {"success": False}), (200, b"not json at all"), (403, {"error": "no"})):
            self.fresh()
            self.script_full_run()
            self.answer("POST", "/api/character/equip", step)
            result = self.body(self.picture, "--apply")
            self.assertEqual(result.returncode, 1, step)
            self.assertIn("sdlca-body alice --job job-1 --apply", result.stderr, step)
            self.assertEqual(self.count("POST", "/api/character/equip"), 1, step)
            self.assertEqual(self.recorded()["job"], "job-1", step)

    def test_a_refused_check_says_how_to_carry_on(self):
        self.script_full_run([(401, {"error": "unauthorized"})])
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("sdlca-body alice --job job-1 --apply", result.stderr)

    def test_a_sculpt_that_is_not_shown_at_first_is_waited_for(self):
        self.script_full_run([(404, {"error": "Job not found"}), (404, {"error": "Job not found"}), (200, DONE)])
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("does not show the sculpt yet", result.stdout)

    def test_ctrl_c_and_a_stop_signal_while_waiting_say_how_to_carry_on(self):
        for sent in (signal.SIGINT, signal.SIGTERM):
            self.fresh()
            self.script_full_run([(200, RUNNING)])
            process = self.start(self.picture, "--apply")
            self.assertTrue(wait_for(lambda: ("GET", "/api/character/jobs/job-1") in self.sequence()))
            process.send_signal(sent)
            out, err = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 130, (sent, out, err))
            self.assertIn("sdlca-body alice --job job-1 --apply", out + err)
            self.assertEqual(self.recorded()["job"], "job-1")

    def test_a_note_on_a_running_sculpt_is_shown_and_not_taken_for_a_failure(self):
        self.script_full_run([(200, {"jobId": "job-1", "status": "processing", "error": "retrying after a hiccup"}), (200, DONE)])
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Spawn says: retrying after a hiccup", result.stdout)

    def test_a_profile_that_does_not_show_the_body_is_not_reported_as_done(self):
        self.script_full_run()
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("does not show one yet", result.stdout)
        self.assertNotIn("done: the body is worn", result.stdout)


class RecordTests(BodyCase):
    """The record in the account's folder that stops a second paid sculpt."""

    def test_a_started_sculpt_blocks_a_new_picture_run_with_no_call_to_spawn(self):
        with open(self.marker, "w") as handle:
            json.dump({"state": "started", "job": "job-7", "character": "char-7", "at": "2026-11-19T12:00:00Z"}, handle)
        for args in ((self.picture,), (self.picture, "--apply")):
            result = self.body(*args)
            self.assertEqual(result.returncode, 1, args)
            self.assertIn("a sculpt is already recorded for this account (job job-7, started 2026-11-19T12:00:00Z)", result.stderr)
            self.assertIn("sdlca-body alice --job job-7 --apply", result.stderr)
            self.assertIn("delete " + self.marker, result.stderr)
        self.assertEqual(Fake.calls, [])

    def test_an_unconfirmed_sculpt_blocks_a_new_picture_run_too(self):
        with open(self.marker, "w") as handle:
            json.dump({"state": "unknown", "job": None, "at": "2026-11-19T12:00:00Z"}, handle)
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("may have started a sculpt that Spawn did not confirm", result.stderr)
        self.assertIn("spawn.co", result.stderr)
        self.assertEqual(Fake.calls, [])

    def test_the_record_does_not_stop_the_other_modes(self):
        with open(self.marker, "w") as handle:
            json.dump({"state": "started", "job": "job-7"}, handle)
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.answer("POST", "/api/character/reset", (200, {"success": True}))
        self.assertEqual(self.body("--reset", "char-1", "--apply").returncode, 0)

    def test_a_record_that_was_tampered_with_is_cleaned_before_it_is_printed(self):
        with open(self.marker, "w") as handle:
            json.dump({"state": "started", "job": "../../x", "at": "now\x1b[31m\r\nSECOND"}, handle)
        result = self.body(self.picture)
        self.assertEqual(result.returncode, 1)
        for bad in ("\x1b", "\r", "../../x"):
            self.assertNotIn(bad, result.stderr)
        with open(self.marker, "w") as handle:
            handle.write("not json at all")
        self.assertEqual(self.body(self.picture).returncode, 1)
        self.assertEqual(Fake.calls, [])

    def test_the_record_is_private_and_a_second_begin_fails(self):
        marker = body.Marker(self.account)
        marker.begin("char-1")
        self.assertEqual(stat.S_IMODE(os.stat(self.marker).st_mode), 0o600)
        with self.assertRaises(body.Refuse):
            marker.begin("char-2")
        marker.update(state="started", job="job-1")
        self.assertEqual(self.recorded()["job"], "job-1")
        self.assertEqual(self.recorded()["character"], "char-1")
        marker.clear_if("job-9")
        self.assertTrue(os.path.exists(self.marker), "another job's end leaves it alone")
        marker.clear_if("job-1")
        self.assertFalse(os.path.exists(self.marker))

    def test_a_link_planted_at_the_record_is_not_written_through(self):
        target = os.path.join(self.tmp.name, "victim")
        with open(target, "w") as handle:
            handle.write("keep me")
        os.symlink(target, self.marker)
        with self.assertRaises(body.Refuse):
            body.Marker(self.account).begin("char-1")
        with open(target) as handle:
            self.assertEqual(handle.read(), "keep me")

    def test_without_the_account_folder_a_picture_run_will_not_start(self):
        env = {"PATH": os.environ.get("PATH", ""), "SPAWN_TOKEN_FILE": self.token_file, "SPAWN_ORIGIN": self.env["SPAWN_ORIGIN"], "ACCOUNT": "alice"}
        result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "lib", "body.py"), self.picture, "--apply"], env=env, timeout=60)
        self.assertEqual(result.returncode, 1)
        self.assertIn("account's folder is not known", result.stderr)
        self.assertEqual(Fake.calls, [])


class RefusalTests(BodyCase):
    def test_a_persons_account_is_refused_before_anything_is_uploaded(self):
        self.answer("GET", "/api/agent/v1/me", (200, dict(ME, actorClass="person")))
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not an agent account", result.stderr)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me")])

    def test_an_answer_that_does_not_say_what_the_account_is_is_refused_too(self):
        self.answer("GET", "/api/agent/v1/me", (200, {"handle": "@x"}))
        self.assertEqual(self.body(self.picture, "--apply").returncode, 1)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me")])

    def test_a_closed_generation_lane_stops_a_picture_and_shows_what_spawn_says(self):
        closed = json.loads(json.dumps(ME))
        closed["budget"]["lanes"]["generation"] = {"state": "closed", "why": "Your person's allowance is used up.", "ask": "https://www.spawn.co/@alice"}
        self.answer("GET", "/api/agent/v1/me", (200, closed))
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("generation lane closed", result.stderr)
        self.assertIn("allowance is used up", result.stderr)
        self.assertNotIn("link the agent to a person", result.stderr, "the agent is linked, so that advice would be wrong")
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me")])
        unlinked = dict(closed, linkedTo=None, linked=False)
        unlinked["budget"] = {"lanes": {"generation": {"state": "closed"}}}
        self.answer("GET", "/api/agent/v1/me", (200, unlinked))
        self.assertIn("link the agent to a person", self.body(self.picture, "--apply").stderr)

    def test_advice_to_set_the_agent_up_again_is_given_only_for_a_refused_token(self):
        for status, advised in ((401, True), (403, True), (500, False), (429, False)):
            self.answer("GET", "/api/agent/v1/me", (status, {"error": "no"}))
            result = self.body(self.picture, "--apply")
            self.assertEqual(result.returncode, 1, status)
            self.assertIn("would not say who this account is", result.stderr)
            self.assertEqual("sdlca-onboard" in result.stderr, advised, status)
        self.assertEqual(set(self.sequence()), {("GET", "/api/agent/v1/me")})

    def test_a_file_that_is_not_a_picture_never_leaves_the_machine(self):
        cases = {
            "text": b"sak_looks_like_a_token\n",
            "empty": b"",
            "too big": b"\x89PNG\r\n\x1a\n" + b"\x00" * (4 * 1024 * 1024),
            "pdf": b"%PDF-1.7 stuff",
        }
        for name, data in cases.items():
            path = os.path.join(self.folder, name.replace(" ", "-") + ".png")
            with open(path, "wb") as handle:
                handle.write(data)
            with self.assertRaises(body.Refuse, msg=name):
                body.read_image(path)
        for name, path in (("folder", self.folder), ("missing", os.path.join(self.folder, "nope.png")), ("device", "/dev/null")):
            with self.assertRaises(body.Refuse, msg=name):
                body.read_image(path)
        exactly = os.path.join(self.folder, "exactly.png")
        with open(exactly, "wb") as handle:
            handle.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * (4 * 1024 * 1024 - 8))
        self.assertEqual(len(body.read_image(exactly)[0]), 4 * 1024 * 1024)  # a picture of exactly 4 MB is allowed
        result = self.body(os.path.join(self.folder, "text.png"), "--apply")  # the whole tool, once
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a PNG, JPEG or WebP", result.stderr)
        self.assertNotIn("sak_looks_like_a_token", result.stdout + result.stderr)
        folder = self.body(self.folder, "--apply")  # a folder: a plain refusal, never a crash
        self.assertEqual(folder.returncode, 1)
        self.assertIn("not a plain file", folder.stderr)
        self.assertNotIn("Traceback", folder.stderr)
        self.assertEqual(Fake.calls, [])

    def test_a_file_that_only_starts_like_a_picture_is_accepted(self):
        path = os.path.join(self.folder, "starts-like.png")
        with open(path, "wb") as handle:
            handle.write(b"\x89PNG\r\n\x1a\n" + b"this is only text")
        data, found = body.read_image(path)
        self.assertEqual(found[0], "PNG")
        self.assertIsNone(body.png_size(data))

    def test_a_named_pipe_does_not_hang_it(self):
        fifo = os.path.join(self.folder, "pipe.png")
        os.mkfifo(fifo)
        result = self.body(fifo, "--apply", timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a plain file", result.stderr)
        self.assertEqual(Fake.calls, [])

    def test_inside_an_agent_turn_it_will_not_run_and_each_layer_says_so(self):
        result = self.body(self.picture, "--apply", env={"SDLCA_TURN_ACCOUNT": "alice"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("agent turn", result.stderr)
        unknown = helpers.run([BIN, "nobody", self.picture], env=self.merged({"SDLCA_TURN_ACCOUNT": "alice"}), timeout=30)  # the wrapper refuses before it looks the account up
        self.assertEqual(unknown.returncode, 1)
        self.assertIn("agent turn", unknown.stderr)
        self.assertNotIn("unknown account", unknown.stderr)
        with self.assertRaisesRegex(body.Refuse, "agent turn"):  # and the module, if the wrapper were skipped (not for some other reason)
            body.run([self.picture], {"SDLCA_TURN_ACCOUNT": "x"})
        self.assertEqual(Fake.calls, [])

    def test_an_unknown_account_and_an_unsafe_origin_are_refused(self):
        result = helpers.run([BIN, "nobody", self.picture], env=self.env, timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown account", result.stderr)
        for origin in ("https://www.spawn.co@elsewhere.example", "http://example.com", "ftp://x", "file:///tmp"):
            result = self.body(self.picture, "--apply", env={"SPAWN_ORIGIN": origin})
            self.assertEqual(result.returncode, 1, origin)
            self.assertIn("refusing to send a token", result.stderr, origin)
        for origin in ("http://[", "https://[::1", "https://www.spawn.co\uff20evil.example"):
            result = self.body(self.picture, "--apply", env={"SPAWN_ORIGIN": origin})
            self.assertEqual(result.returncode, 1, origin)
            self.assertNotIn("unexpected", result.stderr, origin)
        self.assertEqual(Fake.calls, [])

    def test_a_token_file_that_holds_something_else_is_refused_without_printing_it(self):
        with open(self.token_file, "w") as handle:
            handle.write('sak_has a space "and quote"\n')
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not hold a plain token", result.stderr)
        self.assertNotIn("has a space", result.stdout + result.stderr)
        self.assertEqual(Fake.calls, [])

    def test_no_kind_of_redirect_is_followed_on_any_door_and_the_token_never_reaches_another_host(self):
        elsewhere = serve(Elsewhere)
        location = {"Location": "http://127.0.0.1:%d/steal" % elsewhere.server_port}
        try:
            for door, code in (("me", 302), ("me", 308), ("picture", 303), ("picture", 307), ("me", 301)):
                self.fresh()
                self.answer("GET", "/api/agent/v1/me", (code, {}, location) if door == "me" else (200, ME))
                self.answer("POST", "/api/character/picture", (code, {}, location))
                result = self.body(self.picture, "--apply")
                self.assertEqual(result.returncode, 1, (door, code))
                self.assertIn("redirect", result.stderr, (door, code))
                self.assertNotIn(("POST", "/api/character/convert"), self.sequence())
        finally:
            elsewhere.shutdown()
            elsewhere.server_close()
        self.assertEqual(Elsewhere.hits, [])

    def test_the_environments_proxy_is_never_used_for_a_plain_http_origin(self):
        proxy = serve(Elsewhere)
        try:
            self.answer("GET", "/api/agent/v1/me", (200, ME))
            address = "http://127.0.0.1:%d" % proxy.server_port
            result = self.body(self.picture, env={"http_proxy": address, "HTTP_PROXY": address})
        finally:
            proxy.shutdown()
            proxy.server_close()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Elsewhere.hits, [])
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me")])


class TokenTests(BodyCase):
    def test_the_token_is_never_printed_even_when_spawn_echoes_it_and_terminal_codes_are_removed(self):
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        evil = "you sent %s \x1b[31mred\x1b[0m\r\nSECOND LINE \u202e" % TOKEN
        self.answer("POST", "/api/character/picture", (400, {"error": "bad\x07", "verdict": evil}))
        result = self.body(self.picture, "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(TOKEN, result.stdout + result.stderr)
        self.assertIn("[token]", result.stderr)
        for bad in ("\x1b", "\x07", "\r", "\u202e"):
            self.assertNotIn(bad, result.stdout + result.stderr)
        self.assertEqual(len(result.stderr.strip().splitlines()), 1)

    def test_the_token_is_taken_out_of_every_field_of_a_normal_answer_too(self):
        echoing = dict(ME, handle=TOKEN, name="n-" + TOKEN, linkedTo=TOKEN, budget={"paidBy": TOKEN, "lanes": {"generation": {"state": "open"}}})
        self.answer("GET", "/api/agent/v1/me", (200, echoing))
        dry = self.body(self.picture)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertNoToken(dry)
        self.assertIn("[token]", dry.stdout)
        self.fresh()
        self.script_full_run([(200, {"jobId": "job-1", "status": "processing", "stage": TOKEN}), (200, DONE)])
        self.answer("GET", "/api/agent/v1/me", (200, echoing))
        self.answer("POST", "/api/character/picture", (200, dict(DRAFT, status="ready-" + TOKEN)))
        self.answer("POST", "/api/character/equip", (200, dict(EQUIPPED, modelUrl="https://www.spawn.co/magic/" + TOKEN + ".glb")))
        full = self.body(self.picture, "--apply")
        self.assertEqual(full.returncode, 0, full.stdout + full.stderr)
        self.assertNoToken(full)

    def test_an_id_that_is_the_token_is_refused_and_not_printed(self):
        with mock.patch.object(body, "SECRETS", [TOKEN]):
            with self.assertRaises(body.Refuse) as caught:
                body.need_id({"jobId": TOKEN, "x": TOKEN}, "jobId", "the sculpt")
            self.assertNotIn(TOKEN, str(caught.exception))
            self.assertIsNone(body.need_id({"characterId": "ab-" + TOKEN}, "characterId", "the upload", required=False))

    def test_a_closed_stdout_does_not_stop_the_run(self):
        class Broken(io.TextIOBase):
            def write(self, text):
                raise BrokenPipeError()

            def flush(self):
                raise BrokenPipeError()

            def fileno(self):
                return 1

        with mock.patch("sys.stdout", Broken()), mock.patch("os.open", return_value=7), mock.patch("os.dup2") as dup2:
            body.emit("a line")
            body.say("another")
        self.assertTrue(dup2.called)

    def test_an_unforeseen_failure_prints_its_kind_and_never_its_text(self):
        def explode(argv, env):
            raise RuntimeError("secret text sak_abc that must not be printed")

        captured = io.StringIO()
        with mock.patch.object(body, "run", explode), contextlib.redirect_stderr(captured):
            self.assertEqual(body.main(["x.png"], {}), 1)
        self.assertIn("RuntimeError", captured.getvalue())
        self.assertNotIn("sak_abc", captured.getvalue())
        self.assertNotIn("Traceback", captured.getvalue())


class HostileServerTests(BodyCase):
    def test_a_call_whose_answer_never_ends_is_cut_off_at_its_limit(self):
        self.answer("GET", "/api/agent/v1/me", ("endless", None))
        client = body.Client(self.env["SPAWN_ORIGIN"], TOKEN)
        started = time.monotonic()
        with self.assertRaises(body.NetworkError) as caught:
            client.call("GET", "/api/agent/v1/me", limit=1)
        self.assertLess(time.monotonic() - started, 15)
        self.assertIn("no complete answer in time", str(caught.exception))
        Fake.release.set()

    def test_a_check_that_never_ends_cannot_run_past_the_wait(self):
        self.script_full_run([("endless", None)])
        started = time.monotonic()
        result = self.body(self.picture, "--apply", "--wait", "2", timeout=90)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertLess(time.monotonic() - started, 40)
        self.assertIn("--job job-1 --apply", result.stderr)
        Fake.release.set()

    def test_the_deadline_stops_a_stuck_call_and_leaves_no_timer_or_handler_behind(self):
        before = signal.getsignal(signal.SIGALRM)
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            with body.hard_deadline(0.2):
                time.sleep(10)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
        self.assertEqual(signal.getsignal(signal.SIGALRM), before)

    def test_an_answer_nested_thousands_of_levels_deep_is_a_plain_failure_not_a_crash(self):
        self.answer("GET", "/api/agent/v1/me", (200, b"[" * 100000))
        result = self.body(self.picture)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("unexpected", result.stderr)
        self.assertIn("not JSON", result.stderr)

    def test_an_answer_that_is_too_big_or_not_an_object_is_refused(self):
        self.answer("GET", "/api/agent/v1/me", (200, b'{"a": "' + b"x" * (body.MAX_ANSWER_BYTES + 10) + b'"}'))
        self.assertIn("larger than this tool reads", self.body(self.picture).stderr)
        self.answer("GET", "/api/agent/v1/me", (200, b'["not", "an", "object"]'))
        self.assertIn("not a JSON object", self.body(self.picture).stderr)

    def test_text_from_spawn_is_cleaned_wherever_it_is_printed(self):
        hostile = "\x1b]0;PWN\x07\x1b[2J bad \u202e text\r\nline two"
        me = dict(ME, handle=hostile, name=hostile, linkedTo=hostile, characterModelUrl=None)
        me["budget"] = {"paidBy": hostile, "lanes": {"generation": {"state": "open"}}}
        self.answer("GET", "/api/agent/v1/me", (200, me))
        result = self.body(self.picture)
        for bad in ("\x1b", "\x07", "\r", "\u202e"):
            self.assertNotIn(bad, result.stdout + result.stderr)


class WaitTests(unittest.TestCase):
    """The waiting loop against a stub that answers from a script: no server, and no real waiting."""

    class Stub:
        origin = "https://www.spawn.co"

        def __init__(self, *steps):
            self.steps = list(steps)
            self.calls = 0

        def call(self, method, path, body=None, content_type=None, limit=None):
            self.calls += 1
            step = self.steps.pop(0) if len(self.steps) > 1 else self.steps[0]
            if isinstance(step, BaseException):
                raise step
            return step

    def wait(self, stub, wait=1000, grace=0):
        out = io.StringIO()
        with mock.patch.object(body.time, "sleep") as sleep, contextlib.redirect_stdout(out):
            try:
                result = body.wait_for_job(stub, "job-1", wait, 1, grace)
            except (body.Refuse, body.TimedOut) as stop:
                result = stop
        return result, [call.args[0] for call in sleep.call_args_list], out.getvalue()

    def test_every_word_for_a_failure_stops_at_once_without_an_error_text(self):
        for status in ("failed", "Failure", "internal_error", "canceled_by_user", "moderation_blocked", "timed_out", "error", "rejected", "aborted", " FAILED ", "expired"):
            result, sleeps, _ = self.wait(self.Stub({"status": status}))
            self.assertIsInstance(result, body.Refuse, status)
            self.assertTrue(result.final, status)
            self.assertEqual(sleeps, [], status)

    def test_every_word_for_done_is_accepted(self):
        for status in ("completed", "Completed", " completed ", "complete", "succeeded", "success", "finished", "done"):
            result, _, _ = self.wait(self.Stub({"status": status}))
            self.assertIsInstance(result, dict, status)

    def test_a_message_on_a_sculpt_that_has_not_failed_is_shown_once_and_the_wait_goes_on(self):
        busy = {"status": "weird", "error": "retrying"}
        result, sleeps, output = self.wait(self.Stub(busy, busy, {"status": "completed"}))
        self.assertIsInstance(result, dict)
        self.assertEqual(len(sleeps), 2)
        self.assertEqual(output.count("Spawn says: retrying"), 1)

    def test_no_such_sculpt_is_put_down_to_a_slow_start_only_while_the_grace_lasts(self):
        missing = body.ApiError(404, None, "Job not found")
        result, _, _ = self.wait(self.Stub(missing, missing, missing, {"status": "completed"}), grace=3)
        self.assertIsInstance(result, dict)
        result, _, _ = self.wait(self.Stub(missing), grace=3)
        self.assertIsInstance(result, body.Refuse)
        self.assertFalse(result.final, "in a fresh run the sculpt probably exists: the resume hint is added")
        result, _, _ = self.wait(self.Stub(missing), grace=0)
        self.assertIsInstance(result, body.Refuse)
        self.assertTrue(result.final, "for an id the person typed, a 404 is the answer")

    def test_a_rate_limit_waits_for_the_time_spawn_names_or_a_default(self):
        slow = body.ApiError(429, None, None, None)
        _, sleeps, _ = self.wait(self.Stub(slow, {"status": "completed"}))
        self.assertEqual(sleeps, [body.RATE_LIMIT_PAUSE])
        named = body.ApiError(429, None, None, 3.0)
        _, sleeps, _ = self.wait(self.Stub(named, {"status": "completed"}))
        self.assertEqual(sleeps, [3.0])
        server = body.ApiError(503, None, None, None)
        _, sleeps, _ = self.wait(self.Stub(server, {"status": "completed"}))
        self.assertEqual(sleeps, [1])

    def test_the_end_of_the_wait_says_what_was_last_seen(self):
        result, _, _ = self.wait(self.Stub({"status": "processing", "stage": "mesh"}), wait=0)
        self.assertIsInstance(result, body.TimedOut)
        self.assertEqual(result.last, ("processing", "mesh"))
        result, _, _ = self.wait(self.Stub(body.NetworkError("no")), wait=0)
        self.assertIsInstance(result, body.TimedOut)
        self.assertIsNone(result.last)


class OtherModeTests(BodyCase):
    def test_job_carries_on_without_making_anything(self):
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.answer("GET", "/api/character/jobs/job-1", (200, {"jobId": "job-1", "status": "processing"}), (200, {"jobId": "job-1", "status": "completed"}))
        self.answer("POST", "/api/character/equip", (200, EQUIPPED))
        dry = self.body("--job", "job-1")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me"), ("GET", "/api/character/jobs/job-1")])
        self.assertIn("status processing", dry.stdout)
        self.assertIn("only read from Spawn", dry.stdout)
        Fake.calls = []
        result = self.body("--job", "job-1", "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.sequence()[:2], [("GET", "/api/agent/v1/me"), ("GET", "/api/character/jobs/job-1")])
        self.assertIn(("POST", "/api/character/equip"), self.sequence())
        self.assertNotIn(("POST", "/api/character/picture"), self.sequence())
        self.assertNotIn(("POST", "/api/character/convert"), self.sequence())

    def test_job_ends_the_record_it_belongs_to_and_uses_its_character_for_the_undo_hint(self):
        with open(self.marker, "w") as handle:
            json.dump({"state": "started", "job": "job-1", "character": "char-9"}, handle)
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.answer("GET", "/api/character/jobs/job-1", (200, DONE))
        self.answer("POST", "/api/character/equip", (200, {"success": True, "modelUrl": MODEL}))
        result = self.body("--job", "job-1", "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("--reset char-9 --apply", result.stdout)
        self.assertFalse(os.path.exists(self.marker))

    def test_a_job_spawn_does_not_know_is_reported_and_there_is_nothing_to_carry_on_with(self):
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.answer("GET", "/api/character/jobs/job-9", (404, {"error": "Job not found"}))
        result = self.body("--job", "job-9", "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Job not found", result.stderr)
        self.assertNotIn("carry on with", result.stderr)
        self.assertNotIn(("POST", "/api/character/equip"), self.sequence())

    def test_wear_puts_an_existing_body_on_the_agent(self):
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.answer("PATCH", "/api/agent/v1/me", (200, {"ok": True, "body": {"look": None, "modelUrl": MODEL}, "note": "ok"}))
        dry = self.body("--wear", MODEL)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me")])
        self.assertIn("muse, claude-crab, codex", dry.stdout)
        self.assertIn("a dry run cannot ask it", dry.stdout)
        Fake.calls = []
        result = self.body("--wear", MODEL, "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me"), ("PATCH", "/api/agent/v1/me")])
        self.assertEqual(json.loads(Fake.calls[1][4]), {"body": MODEL})
        self.assertIn("done: Spawn says the agent now wears", result.stdout)

    def test_the_dry_run_says_so_when_spawn_lists_no_looks(self):
        self.answer("GET", "/api/agent/v1/me", (200, dict(ME, looks=None)))
        self.assertIn("Spawn listed none in its answer", self.body("--wear", "muse").stdout)

    def test_wear_takes_a_look_key_too_and_explains_a_refusal(self):
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.answer("PATCH", "/api/agent/v1/me", (200, {"ok": True, "body": {"look": "muse", "modelUrl": MODEL}}))
        result = self.body("--wear", "muse", "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(Fake.calls[1][4]), {"body": "muse"})
        self.assertIn('the look "muse"', result.stdout)
        for code, words in (("body_not_carried", "--carry <file.glb> --world"), ("body_no_rig", "no skeleton")):
            self.answer("PATCH", "/api/agent/v1/me", (400, {"error": code}))
            refused = self.body("--wear", MODEL, "--apply")
            self.assertEqual(refused.returncode, 1, code)
            self.assertIn(code, refused.stderr)
            self.assertIn(words, refused.stderr)

    def test_a_dropped_connection_on_wear_or_reset_says_it_may_have_gone_through(self):
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.answer("PATCH", "/api/agent/v1/me", ("drop", None))
        self.answer("POST", "/api/character/reset", ("drop", None))
        for args in (("--wear", MODEL, "--apply"), ("--reset", "char-1", "--apply")):
            result = self.body(*args)
            self.assertEqual(result.returncode, 1, args)
            self.assertIn("may have gone through anyway", result.stderr)
            self.assertNotIn("while the", result.stderr)

    def test_reset_takes_a_made_body_off(self):
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.answer("POST", "/api/character/reset", (200, {"success": True}))
        dry = self.body("--reset", "char-1")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me")])
        Fake.calls = []
        result = self.body("--reset", "char-1", "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(Fake.calls[1][4]), {"characterId": "char-1"})
        self.assertIn("done: Spawn says the reset went through", result.stdout)

    def test_a_call_that_makes_something_is_made_once_whatever_spawn_answers(self):
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        for status in (500, 502, 429):
            for args, door in ((("--wear", MODEL, "--apply"), ("PATCH", "/api/agent/v1/me")), (("--reset", "char-1", "--apply"), ("POST", "/api/character/reset"))):
                Fake.calls = []
                self.answer(door[0], door[1], (status, {"error": "no"}))
                self.assertEqual(self.body(*args).returncode, 1)
                self.assertEqual(self.count(*door), 1, (status, door))
        for status in (200, 500):
            for answer in ({"ok": False}, {"success": False}, {}):
                Fake.calls = []
                self.answer("PATCH", "/api/agent/v1/me", (status, answer))
                self.assertEqual(self.body("--wear", MODEL, "--apply").returncode, 1)
                self.assertEqual(self.count("PATCH", "/api/agent/v1/me"), 1)


class CarryTests(BodyCase):
    """Carrying a model file to Spawn through a world, the road a body needs before another agent can wear it."""

    def setUp(self):
        super().setUp()
        self.answer("GET", "/api/agent/v1/me", (200, ME_WORLD))
        self.glb = glb_bytes(extra=1000)
        self.sha = hashlib.sha256(self.glb).hexdigest()
        self.name = "value.%s.glb" % self.sha
        self.path = os.path.join(self.folder, "body.glb")
        with open(self.path, "wb") as handle:
            handle.write(self.glb)
        self.assets = "/api/sdk/v1/%s/assets/" % WORLD_ID
        self.address = "https://www.spawn.co/cdn/" + self.name

    def carried(self, status="carried"):
        return {"status": status, "name": self.name, "url": self.address, "sha256": self.sha, "bytes": len(self.glb)}

    def big(self, extra=4_600_000):
        self.glb = glb_bytes(extra=extra)
        self.sha = hashlib.sha256(self.glb).hexdigest()
        self.name = "value.%s.glb" % self.sha
        self.address = "https://www.spawn.co/cdn/" + self.name
        with open(self.path, "wb") as handle:
            handle.write(self.glb)

    def storage(self):
        return "http://127.0.0.1:%d/storage/upload-1?sig=SIGNEDSECRET123" % self.server.server_port

    def script_big(self, final=None):
        self.answer("POST", self.assets + "upload-target", (200, {"status": "upload", "name": self.name, "contentType": "model/gltf-binary", "uploadUrl": self.storage(),
                                                                  "tempPath": "user-uploads/u1/carry/c1", "maxBytes": 26214400, "expiresAtMs": 1}))
        self.answer("PUT", "/storage/upload-1?sig=SIGNEDSECRET123", (200, b""))
        self.answer("PUT", self.assets + self.name, *(final or [(201, self.carried())]))

    def test_a_dry_run_reads_once_and_says_what_it_would_do(self):
        result = self.body("--carry", self.path, "--world", "@alice/game-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me")])
        for words in ("sha256 " + self.sha[:16], "it has a skeleton (1 skin)", "@alice/game-1 (the agent is editor there)", "in one call", "publicly" if False else "public address", "only read from Spawn"):
            self.assertIn(words, result.stdout)
        self.assertNoToken(result)

    def test_a_small_file_goes_in_one_call(self):
        self.answer("PUT", self.assets + self.name, (201, self.carried()))
        result = self.body("--carry", self.path, "--world", "@alice/game-1", "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me"), ("PUT", self.assets + self.name)])
        _, _, auth, content_type, data = Fake.calls[1]
        self.assertEqual((auth, content_type, data), ("Bearer " + TOKEN, "model/gltf-binary", self.glb))
        self.assertIn("done: Spawn carried the file", result.stdout)
        self.assertIn(self.address, result.stdout)
        self.assertIn("--wear %s --apply" % self.address, result.stdout)
        self.assertNoToken(result)

    def test_a_big_file_goes_by_address_and_the_token_never_reaches_the_storage(self):
        self.big()
        self.script_big()
        result = self.body("--carry", self.path, "--world", "@alice/game-1", "--apply", timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me"), ("POST", self.assets + "upload-target"),
                                           ("PUT", "/storage/upload-1?sig=SIGNEDSECRET123"), ("PUT", self.assets + self.name)])
        _, _, auth, _, ask = Fake.calls[1]
        self.assertEqual(auth, "Bearer " + TOKEN)
        self.assertEqual(json.loads(ask), {"name": self.name, "sizeBytes": len(self.glb)})
        _, _, storage_auth, storage_type, stored = Fake.calls[2]
        self.assertIsNone(storage_auth, "the storage host is another host: no token goes with the file")
        self.assertEqual(storage_type, "model/gltf-binary")
        self.assertEqual(stored, self.glb)
        _, _, final_auth, _, final = Fake.calls[3]
        self.assertEqual((final_auth, json.loads(final)), ("Bearer " + TOKEN, {"tempPath": "user-uploads/u1/carry/c1"}))
        self.assertIn(self.address, result.stdout)
        self.assertNotIn("SIGNEDSECRET123", result.stdout + result.stderr, "the signed address is never printed")
        self.assertIn("by address", self.body("--carry", self.path, "--world", "@alice/game-1").stdout)

    def test_a_file_that_is_already_there_is_not_sent_again(self):
        self.big()
        self.answer("POST", self.assets + "upload-target", (200, {"status": "exists", "name": self.name, "url": self.address}))
        result = self.body("--carry", self.path, "--world", "@alice/game-1", "--apply", timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me"), ("POST", self.assets + "upload-target")])
        self.assertIn("done: Spawn has the file", result.stdout)

    def test_a_file_that_is_still_being_placed_is_asked_for_again(self):
        self.big()
        self.script_big(final=[(503, {"error": "store_busy"}), (200, self.carried("exists"))])
        result = self.body("--carry", self.path, "--world", "@alice/game-1", "--apply", timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.count("PUT", self.assets + self.name), 2)
        self.assertEqual(self.count("PUT", "/storage/upload-1?sig=SIGNEDSECRET123"), 1, "the bytes go to the storage once")
        self.assertIn("still placing the file", result.stdout)

    def test_a_storage_that_refuses_is_reported_without_the_signed_address(self):
        self.big()
        self.script_big()
        self.answer("PUT", "/storage/upload-1?sig=SIGNEDSECRET123", (403, b"denied for SIGNEDSECRET123"))
        result = self.body("--carry", self.path, "--world", "@alice/game-1", "--apply", timeout=120)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Spawn's storage refused the file", result.stderr)
        self.assertIn("costs nothing", result.stderr)
        self.assertNotIn("SIGNEDSECRET123", result.stdout + result.stderr)
        self.assertNotIn(("PUT", self.assets + self.name), self.sequence())

    def test_an_answer_that_is_not_what_was_asked_for_is_refused(self):
        for answer in ({"status": "carried", "name": self.name, "url": "https://evil.example/cdn/" + "x"}, {"status": "weird", "url": self.address},
                       {"status": "carried", "url": "https://www.spawn.co/cdn/value.0000.glb"}, {"status": "carried"}):
            self.answer("PUT", self.assets + self.name, (201, answer))
            result = self.body("--carry", self.path, "--world", "@alice/game-1", "--apply")
            self.assertEqual(result.returncode, 1, answer)
            self.assertIn("not what was asked for", result.stderr)

    def test_an_upload_address_that_cannot_be_trusted_is_never_used(self):
        self.big()
        for bad in ("http://storage.example.com/x", "https://10.0.0.5/x", "https://[::1]/x", "https://localhost/x", "https://user@storage.example.com/x",
                    "https://storage/x", "https://storage.example.com/a b", "ftp://storage.example.com/x", ""):
            self.fresh()
            self.answer("POST", self.assets + "upload-target", (200, {"status": "upload", "contentType": "model/gltf-binary", "uploadUrl": bad, "tempPath": "u/c"}))
            result = self.body("--carry", self.path, "--world", "@alice/game-1", "--apply", timeout=120)
            self.assertEqual(result.returncode, 1, bad)
            self.assertIn("upload address that this tool will not use", result.stderr, bad)
            self.assertEqual(self.sequence(), [("GET", "/api/agent/v1/me"), ("POST", self.assets + "upload-target")], bad)

    def test_an_upload_answer_with_unusable_parts_is_refused(self):
        self.big()
        good = {"status": "upload", "contentType": "model/gltf-binary", "uploadUrl": self.storage(), "tempPath": "u/c", "maxBytes": 26214400}
        for change in ({"tempPath": "../../x y"}, {"tempPath": None}, {"contentType": "text/html; evil"}, {"contentType": None}, {"status": "other"}, {"maxBytes": 10}):
            self.fresh()
            self.answer("POST", self.assets + "upload-target", (200, dict(good, **change)))
            result = self.body("--carry", self.path, "--world", "@alice/game-1", "--apply", timeout=120)
            self.assertEqual(result.returncode, 1, change)
            self.assertNotIn(("PUT", "/storage/upload-1?sig=SIGNEDSECRET123"), self.sequence(), change)

    def test_the_agent_must_be_an_editor_of_a_world_it_can_see(self):
        viewer = dict(ME, worlds=[dict(WORLD, standing="viewer")])
        self.answer("GET", "/api/agent/v1/me", (200, viewer))
        result = self.body("--carry", self.path, "--world", "@alice/game-1", "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertIn("only a viewer", result.stderr)
        self.answer("GET", "/api/agent/v1/me", (200, ME_WORLD))
        unknown = self.body("--carry", self.path, "--world", "@nobody/else", "--apply")
        self.assertEqual(unknown.returncode, 1)
        self.assertIn("does not reach the world @nobody/else", unknown.stderr)
        self.assertIn("@alice/game-1", unknown.stderr)
        self.answer("GET", "/api/agent/v1/me", (200, dict(ME, worlds=[dict(WORLD, worldId="../x")])))
        self.assertEqual(self.body("--carry", self.path, "--world", "@alice/game-1", "--apply").returncode, 1)
        self.assertNotIn("PUT", [method for method, _ in self.sequence()])

    def test_a_file_that_is_not_a_complete_model_never_leaves_the_machine(self):
        cases = {"text": b"not a model at all, and long enough to pass the length check", "version one": glb_bytes(version=1), "cut short": glb_bytes(extra=100)[:-40],
                 "bytes after": glb_bytes(extra=100) + b"more", "wrong length": glb_bytes(length_delta=4), "empty": b"",
                 "wrong magic": b"JSON" + struct.pack("<II", 2, 24) + b"\x00" * 12}
        for name, data in cases.items():
            path = os.path.join(self.folder, name.replace(" ", "-") + ".glb")
            with open(path, "wb") as handle:
                handle.write(data)
            result = self.body("--carry", path, "--world", "@alice/game-1", "--apply")
            self.assertEqual(result.returncode, 1, name)
        big = os.path.join(self.folder, "huge.glb")
        with open(big, "wb") as handle:
            handle.write(glb_bytes())
            handle.truncate(body.MAX_MODEL_BYTES + 1)
        self.assertEqual(self.body("--carry", big, "--world", "@alice/game-1", "--apply").returncode, 1)
        self.assertEqual(Fake.calls, [])

    def test_a_model_without_a_skeleton_is_flagged_in_the_plan(self):
        with open(self.path, "wb") as handle:
            handle.write(glb_bytes(skins=0))
        self.assertIn("body_no_rig", self.body("--carry", self.path, "--world", "@alice/game-1").stdout)
        self.assertEqual(body.glb_skins(glb_bytes(skins=2)), 2)
        self.assertIsNone(body.glb_skins(b"glTF" + struct.pack("<II", 2, 20) + struct.pack("<I4s", 4, b"BIN\x00")))

    def test_the_signed_address_is_taken_out_of_everything_printed_from_the_moment_it_is_used(self):
        self.answer("PUT", "/storage/upload-1?sig=SIGNEDSECRET123", (200, b""))
        client = body.Client(self.env["SPAWN_ORIGIN"], TOKEN)
        address = self.storage()
        with mock.patch.object(body, "SECRETS", [TOKEN]):
            client.put_storage(address, b"bytes", "model/gltf-binary")
            self.assertIn(address, body.SECRETS)
            self.assertEqual(body.clean("failed at " + address + " badly"), "failed at [token] badly")
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                body.say("the address was " + address)
            self.assertNotIn("SIGNEDSECRET123", captured.getvalue())
        self.assertIsNone(Fake.calls[-1][2], "no Authorization header went with the file")

    def test_the_storage_check_allows_only_what_a_signed_address_should_be(self):
        https_origin = "https://www.spawn.co"
        self.assertEqual(body.storage_target("https://storage.example.com/x?sig=1", https_origin), "https://storage.example.com/x?sig=1")
        for bad in ("http://127.0.0.1:9/x", "http://localhost/x", "https://127.0.0.1/x", "https://localhost/x", "https://a.local/x", "https://x.internal/x", "x" * 5000):
            with self.assertRaises(body.Refuse, msg=bad):
                body.storage_target(bad, https_origin)
        self.assertEqual(body.storage_target("http://127.0.0.1:9/x", "http://127.0.0.1:5"), "http://127.0.0.1:9/x")
        with self.assertRaises(body.Refuse):
            body.storage_target("http://evil.example/x", "http://127.0.0.1:5")

    def test_the_carry_is_asked_again_only_while_spawn_is_placing_the_file(self):
        self.answer("PUT", self.assets + self.name, (500, {"error": "boom"}))
        result = self.body("--carry", self.path, "--world", "@alice/game-1", "--apply")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.count("PUT", self.assets + self.name), 1)
        self.answer("PUT", self.assets + self.name, ("drop", None))
        dropped = self.body("--carry", self.path, "--world", "@alice/game-1", "--apply")
        self.assertEqual(dropped.returncode, 1)
        self.assertIn("costs nothing", dropped.stderr)


class CommandLineTests(BodyCase):
    def test_wrong_command_lines_are_refused_before_any_call(self):
        cases = [
            [], ["--apply"], [self.picture, "--job", "job-1"], ["--job", "job-1", "--wear", "muse"], [self.picture, self.picture],
            ["--wear", "muse", "--wait", "5"], ["--reset", "c-1", "--wait", "5"], [self.picture, "--wait", "0"], [self.picture, "--wait", "7201"],
            [self.picture, "--wait", "soon"], [self.picture, "--bogus"], ["--job"], ["--job", "--apply"], ["--job", "a/b"], ["--reset", "../x"],
            ["--job", "a", "--job", "b"], ["--wear", "muse", "--wear", "codex"], [self.picture, "--wait", "5", "--wait", "6"], ["--reset", "a", "--reset", "b"],
            ["--carry", "f.glb"], ["--carry", "f.glb", "--world", "not-a-world"], ["--world", "@a/b"], [self.picture, "--world", "@a/b"], ["--wear", "muse", "--world", "@a/b"],
            ["--carry", "a.glb", "--carry", "b.glb", "--world", "@a/b"], ["--carry", "a.glb", "--world", "@a/b", "--world", "@c/d"], ["--carry", "a.glb", "--world", "@a/b", self.picture],
            ["--carry", "a.glb", "--world", "@a/b", "--job", "x"], ["--carry", "a.glb", "--world", "@a/b/c"], ["--carry", "a.glb", "--world", "@a b/c"],
        ]
        for args in cases:
            with self.assertRaises(body.Usage, msg=args):
                body.parse_args(args)
        for args in ([], ["--apply"], [self.picture, "--bogus"], [self.picture, "--job", "job-1"], ["--job", "a", "--job", "b"]):
            result = self.body(*args)
            self.assertEqual(result.returncode, 2, args)
            self.assertIn("usage", result.stderr.lower(), args)
        self.assertEqual(Fake.calls, [])
        picked = body.parse_args(["x.png", "--apply", "--wait", "30"])
        self.assertEqual((picked.picture, picked.apply, picked.wait), ("x.png", True, 30))
        self.assertEqual(body.parse_args(["x.png"]).wait, body.DEFAULT_WAIT)
        carried = body.parse_args(["--carry", "f.glb", "--world", "@alice/game-1", "--wait", "30", "--apply"])
        self.assertEqual((carried.carry, carried.world, carried.wait, carried.apply), ("f.glb", "@alice/game-1", 30, True))
        self.assertEqual(body.parse_args(["--carry", "f.glb", "--world", "@@bot/den"]).world, "@@bot/den")

    def test_wear_refuses_odd_addresses_before_any_call(self):
        for odd in ("http://www.spawn.co/cdn/x.glb", "https://user@www.spawn.co/x.glb", "https://" + "u" + ":" + "p" + "@www.spawn.co/x.glb", "https://www.spawn.co/a b.glb",
                    "bad key!", "https://x/\"q\"", "file:///etc/passwd", "../x", "https://www.spawn.co/\u00e9.glb", "https://", "https:///x", "https://[", "https://[::1",
                    "https://www.spawn.co/x.glb?sig=abc", "https://www.spawn.co/x\x1b[31m.glb", "https://www.spawn.co/../etc/passwd"):
            with self.assertRaises(body.Usage, msg=odd):
                body.parse_args(["--wear", odd])
        for fine in ("muse", "claude-crab", MODEL, "https://www.spawn.co/cdn/value.0123abcd.glb"):
            self.assertEqual(body.parse_args(["--wear", fine]).wear, fine)
        self.assertEqual(self.body("--wear", "http://www.spawn.co/cdn/x.glb", "--apply").returncode, 2)
        self.assertEqual(Fake.calls, [])

    def test_the_poll_setting_is_checked_only_where_it_is_used(self):
        for bad in ("abc", "301", "0", "-1", "1.5", "", "1e2", " 5"):
            with self.assertRaises(body.Refuse, msg=bad):
                body.poll_seconds({"SDLCA_BODY_POLL": bad})
        self.assertEqual([body.poll_seconds({"SDLCA_BODY_POLL": v}) for v in ("1", "10", "300")], [1, 10, 300])
        self.assertEqual(body.poll_seconds({}), 10)
        result = self.body(self.picture, env={"SDLCA_BODY_POLL": "abc"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("SDLCA_BODY_POLL", result.stderr)
        self.assertEqual(Fake.calls, [])
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        self.answer("POST", "/api/character/reset", (200, {"success": True}))
        self.assertEqual(self.body("--reset", "char-1", "--apply", env={"SDLCA_BODY_POLL": "abc"}).returncode, 0, "an undo is not blocked by a setting it does not use")

    def test_help_prints_the_header_and_the_module_prints_its_usage(self):
        result = helpers.run([BIN, "--help"], env={"SDLCA_SPAWN_HOME": self.home}, timeout=30)
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: sdlca-body <account> <picture>", result.stdout)
        self.assertIn("--apply", result.stdout)
        inner = self.body("--help")
        self.assertEqual(inner.returncode, 0)
        self.assertIn("usage: sdlca-body", inner.stdout)
        self.assertEqual(Fake.calls, [])

    def test_a_stray_spawn_token_in_the_callers_shell_changes_nothing(self):
        self.answer("GET", "/api/agent/v1/me", (200, ME))
        result = self.body(self.picture, env={"SPAWN_TOKEN": "sak_somebody_elses_token"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Fake.calls[0][2], "Bearer " + TOKEN)


class HelperTests(unittest.TestCase):
    def test_pictures_are_told_apart_by_their_bytes(self):
        self.assertEqual(body.sniff_image(png_bytes())[0], "PNG")
        self.assertEqual(body.sniff_image(b"\xff\xd8\xff\xe0")[0], "JPEG")
        self.assertEqual(body.sniff_image(b"RIFF\x00\x00\x00\x00WEBPVP8 ")[0], "WebP")
        for data in (b"", b"GIF89a", b"%PDF", b"RIFF\x00\x00\x00\x00WAVEfmt ", b"\x89PNG"):
            self.assertIsNone(body.sniff_image(data), data)

    def test_embedded_data_is_named(self):
        self.assertEqual(body.metadata_notes("PNG", png_bytes()), [])
        self.assertEqual(body.metadata_notes("PNG", png_bytes(extra=[(b"tEXt", b"a\x00b"), (b"iTXt", b"x"), (b"tEXt", b"c")])), ["tEXt", "iTXt"])
        exif = b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", 2 + 8) + b"Exif\x00\x00ab" + b"\xff\xfe" + struct.pack(">H", 4) + b"hi" + b"\xff\xd9"
        self.assertEqual(body.metadata_notes("JPEG", exif), ["EXIF", "comment"])
        webp = b"RIFF\x00\x00\x00\x00WEBP" + b"EXIF" + struct.pack("<I", 3) + b"abc\x00" + b"XMP " + struct.pack("<I", 2) + b"zz"
        self.assertEqual(body.metadata_notes("WebP", webp), ["EXIF", "XMP"])

    def test_bytes_after_the_end_of_a_picture_are_counted(self):
        self.assertEqual(body.trailing_bytes("PNG", png_bytes()), 0)
        self.assertEqual(body.trailing_bytes("PNG", png_bytes(trailing=b"12345")), 5)
        self.assertEqual(body.trailing_bytes("WebP", webp_bytes()), 0)
        self.assertEqual(body.trailing_bytes("WebP", webp_bytes(trailing=b"12345")), 5)
        self.assertEqual(body.trailing_bytes("JPEG", jpeg_bytes()), 0)
        self.assertEqual(body.trailing_bytes("JPEG", jpeg_bytes(trailing=b"12345")), 5)
        self.assertEqual(body.trailing_bytes("JPEG", jpeg_bytes(scans=3, trailing=b"12345")), 5, "a picture made of several scans")
        motion = b"\x00\x00\x00\x18ftypmp42" + b"\xff\xd9" + b"x" * 50  # a video that itself holds an end-of-image marker
        self.assertEqual(body.trailing_bytes("JPEG", jpeg_bytes(trailing=motion)), len(motion))

    def test_broken_files_do_not_hang_or_raise(self):
        junk = [b"\x89PNG\r\n\x1a\n" + b"\xff" * 64, b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00", b"\xff\xd8\xff\xff\xff\xff\xff", b"\xff\xd8\xff\xe1\x00\x00",
                b"RIFF\x00\x00\x00\x00WEBP" + b"\xff" * 20, b"RIFF\x00\x00\x00\x00WEBPEXIF\xff\xff\xff\xff", b"\xff\xd8\xff\xda\x00\x04\x01\x00" + b"\xff\x00" * 1000,
                b"\xff\xd8" + b"\xff\xda\x00\x04\x01\x00" + b"\xff" * 5000]
        for data in junk:
            for kind in ("PNG", "JPEG", "WebP"):
                self.assertIsInstance(body.metadata_notes(kind, data), list)
                self.assertIsInstance(body.trailing_bytes(kind, data), int)

    def test_text_from_outside_is_made_safe_to_print(self):
        self.assertEqual(body.clean("a\x1b[31mb\nc\u202ed"), "a?[31mb?c?d")
        self.assertEqual(body.clean("x" * 400, 20), "x" * 17 + "...")
        self.assertEqual(body.clean({"a": 1}), '{"a": 1}')
        self.assertEqual(body.clean(None), "None")
        with mock.patch.object(body, "SECRETS", [TOKEN]):
            self.assertEqual(body.clean("a " + TOKEN + " b"), "a [token] b")
            self.assertEqual(body.clean("x" * 280 + TOKEN, 300), "x" * 280 + "[token]", "the token is taken out before the text is cut")
            self.assertEqual(body.clean({"k": TOKEN}), '{"k": "[token]"}')

    def test_the_upload_body_is_well_formed_and_the_boundary_is_not_in_the_file(self):
        form, payload = body.multipart("image", "body.png", "image/png", b"abc")
        boundary = form.split("boundary=")[1]
        self.assertTrue(payload.startswith(("--" + boundary + "\r\n").encode()))
        self.assertTrue(payload.endswith(("\r\n--" + boundary + "--\r\n").encode()))
        self.assertIn(b'filename="body.png"', payload)

    def test_only_plain_addresses_are_printed_and_only_spawns_are_suggested(self):
        self.assertEqual(body.plain_address(MODEL), MODEL)
        for odd in ("http://www.spawn.co/x.glb", "https://www.spawn.co/x.glb?sig=abc", "https://u@www.spawn.co/x", "https://www.spawn.co/a b", None, 5):
            self.assertIsNone(body.plain_address(odd), odd)
        origin = "https://www.spawn.co"
        self.assertEqual(body.shareable_address(MODEL, origin), MODEL)
        self.assertEqual(body.shareable_address("https://spawn.co/x.glb", origin), "https://spawn.co/x.glb")
        for foreign in ("https://evil.example/x.glb", "https://169.254.169.254/latest/meta-data", "https://localhost/x.glb", "https://www.spawn.co/../../etc/passwd",
                        "https://spawn.co.evil.example/x.glb", "https://notspawn.co/x.glb", "https://:::"):
            self.assertIsNone(body.shareable_address(foreign, origin), foreign)

    def test_look_keys_are_found_in_the_shapes_spawn_might_use(self):
        self.assertEqual(body.look_keys({"looks": ["a", "b"]}), ["a", "b"])
        self.assertEqual(body.look_keys({"looks": [{"key": "a", "modelUrl": "x"}, {"look": "b"}, {"name": "c"}]}), ["a", "b", "c"])
        self.assertEqual(body.look_keys({"looks": {"a": "x", "b": "y"}}), ["a", "b"])
        self.assertEqual(body.look_keys({"looks": 5}), [])
        self.assertEqual(body.look_keys({}), [])


if __name__ == "__main__":
    unittest.main()
