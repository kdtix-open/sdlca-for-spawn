# SPDX-License-Identifier: Apache-2.0
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

import helpers


class Recorder(BaseHTTPRequestHandler):
    posts = []
    rate_limit_first = False
    server_error_first = False
    redirect_to = None
    answer = {"ok": True}
    body_429 = None

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if Recorder.redirect_to:
            Recorder.posts.append(("redirect", None, None))
            self.send_response(307)
            self.send_header("Location", Recorder.redirect_to)
            self.end_headers()
            return
        if Recorder.server_error_first and not Recorder.posts:
            Recorder.posts.append(("503", None, None))
            self.send_response(503)
            self.end_headers()
            return
        if Recorder.rate_limit_first and not Recorder.posts:
            Recorder.posts.append(("429", None, None))
            self.send_response(429)
            if Recorder.body_429:
                payload = json.dumps(Recorder.body_429).encode()
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            else:
                self.send_header("Retry-After", "0")
                self.end_headers()
            return
        Recorder.posts.append((self.path, self.headers.get("Authorization"), body))
        payload = json.dumps(Recorder.answer).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class SayTests(unittest.TestCase):
    def setUp(self):
        Recorder.posts = []
        Recorder.rate_limit_first = False
        Recorder.server_error_first = False
        Recorder.redirect_to = None
        Recorder.answer = {"ok": True}
        Recorder.body_429 = None
        self.server = HTTPServer(("127.0.0.1", 0), Recorder)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.tmp = tempfile.TemporaryDirectory()
        self.token = os.path.join(self.tmp.name, "token")
        with open(self.token, "w") as handle:
            handle.write("sak_test_token\n")
        self.env = {"SPAWN_TOKEN_FILE": self.token, "SPAWN_ORIGIN": "http://127.0.0.1:%d" % self.server.server_port, "SDLCA_SAY_PAUSE": "0"}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def say(self, args, text):
        return helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-say")] + args, env=self.env, stdin=text)

    def test_room_reply_is_split_numbered_and_authenticated(self):
        result = self.say(["room", "@alice/game-1", "main", "dev", "7"], " ".join("word%d" % i for i in range(120)))
        self.assertEqual(result.returncode, 0, result.stderr)
        posts = Recorder.posts
        self.assertGreater(len(posts), 2)
        for path, auth, body in posts:
            self.assertEqual(path, "/api/agent/v1/chat/room")
            self.assertEqual(auth, "Bearer sak_test_token")
            self.assertLessEqual(len(body["text"]), 200)
            self.assertEqual((body["world"], body["room"], body["ref"]), ("@alice/game-1", "main", "dev"))
        self.assertEqual(posts[0][2]["replyTo"], 7)
        self.assertTrue(all("replyTo" not in p[2] for p in posts[1:]))
        self.assertEqual(len({p[2]["nonce"] for p in posts}), len(posts))

    def test_every_call_gets_fresh_nonces_so_an_identical_later_reply_is_a_new_message(self):
        self.say(["dm", "@alice", "-"], "ok thanks")
        first = Recorder.posts[0][2]["nonce"]
        Recorder.posts = []
        self.say(["dm", "@alice", "-"], "ok thanks")
        self.assertNotEqual(Recorder.posts[0][2]["nonce"], first)

    def test_dm_goes_to_the_dm_door_without_reply_to(self):
        self.say(["dm", "@alice", "-"], "hi")
        path, _, body = Recorder.posts[0]
        self.assertEqual(path, "/api/agent/v1/chat/dm")
        self.assertEqual((body["to"], body["text"]), ("@alice", "hi"))
        self.assertNotIn("replyTo", body)

    def test_retries_after_a_429(self):
        Recorder.rate_limit_first = True
        result = self.say(["dm", "@alice", "-"], "hi")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([p[0] for p in Recorder.posts], ["429", "/api/agent/v1/chat/dm"])

    def test_a_retry_after_in_the_json_body_is_honored(self):
        Recorder.rate_limit_first = True
        Recorder.body_429 = {"retry_after_ms": 0}
        result = self.say(["dm", "@alice", "-"], "hi")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_server_errors_are_retried(self):
        Recorder.server_error_first = True
        result = self.say(["dm", "@alice", "-"], "hi")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([p[0] for p in Recorder.posts], ["503", "/api/agent/v1/chat/dm"])

    def test_a_long_reply_is_capped_and_says_how_much_was_left_out(self):
        env = dict(self.env, SDLCA_SAY_MAX_LINES="3")
        result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-say"), "dm", "@alice", "-"], env=env, stdin=" ".join(["word"] * 500))
        self.assertEqual(result.returncode, 0, result.stderr)
        texts = [p[2]["text"] for p in Recorder.posts]
        self.assertEqual(len(texts), 3)
        self.assertIn("more lines were not sent", texts[-1])
        self.assertTrue(all(len(t) <= 200 for t in texts))

    def test_ok_false_from_spawn_is_an_error(self):
        Recorder.answer = {"ok": False}
        result = self.say(["dm", "@alice", "-"], "hi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ok=false", result.stderr)

    def test_redirects_are_never_followed_so_the_token_cannot_leave(self):
        seen = []

        class Thief(BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *args):
                pass

        other = HTTPServer(("127.0.0.1", 0), Thief)
        threading.Thread(target=other.serve_forever, daemon=True).start()
        Recorder.redirect_to = "http://127.0.0.1:%d/steal" % other.server_port
        result = self.say(["dm", "@alice", "-"], "hi")
        other.shutdown()
        other.server_close()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(seen, [])

    def test_a_plain_http_origin_that_is_not_this_machine_is_refused(self):
        env = dict(self.env, SPAWN_ORIGIN="http://example.invalid")
        result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-say"), "dm", "@alice", "-"], env=env, stdin="hi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to send a token", result.stderr)

    def test_an_origin_with_user_information_is_refused(self):
        env = dict(self.env, SPAWN_ORIGIN="https://www.spawn.co@elsewhere.example")
        result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-say"), "dm", "@alice", "-"], env=env, stdin="hi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("user information", result.stderr)

    def test_reply_to_must_be_a_number_or_a_dash(self):
        result = self.say(["dm", "@alice", "7; rm -rf"], "hi")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(Recorder.posts, [])

    def test_empty_input_and_bad_usage_fail_without_posting(self):
        self.assertNotEqual(self.say(["dm", "@alice", "-"], "  \n").returncode, 0)
        self.assertNotEqual(self.say(["nope"], "hi").returncode, 0)
        self.assertEqual(Recorder.posts, [])

    def test_missing_token_variable_is_a_clear_error(self):
        env = dict(self.env)
        del env["SPAWN_TOKEN_FILE"]
        result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-say"), "dm", "@a", "-"], env=env, stdin="hi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SPAWN_TOKEN_FILE", result.stderr)

    def test_a_token_file_with_a_line_break_is_refused_without_printing_it(self):
        with open(self.token, "w") as handle:
            handle.write("sak_first_line\nsak_second_line\n")
        result = self.say(["dm", "@alice", "-"], "hi")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not hold a plain token", result.stderr)
        self.assertNotIn("sak_first_line", result.stderr + result.stdout)
        self.assertEqual(Recorder.posts, [])

    def test_a_long_reply_always_keeps_room_for_a_line_of_text_before_the_note(self):
        for cap in ("0", "1", "-5"):
            Recorder.posts = []
            env = dict(self.env, SDLCA_SAY_MAX_LINES=cap)
            result = helpers.run(["python3", "-I", "-B", os.path.join(helpers.ROOT, "bin", "sdlca-say"), "dm", "@alice", "-"], env=env, stdin=" ".join("word%d" % i for i in range(500)))
            self.assertEqual(result.returncode, 0, result.stderr)
            texts = [p[2]["text"] for p in Recorder.posts]
            self.assertEqual(len(texts), 2, cap)
            self.assertTrue(texts[0].startswith("(1/") or "word0" in texts[0], texts[0])
            self.assertIn("more lines were not sent", texts[1])

    def test_a_retry_after_that_is_not_a_plain_number_is_ignored_not_a_crash(self):
        Recorder.rate_limit_first = True
        for body in ({"retry_after_ms": -5000}, {"retry_after_ms": "NaN"}, {"retry_after_ms": "Infinity"}, {"retry_after_ms": None}, ["not", "a", "dict"]):
            Recorder.posts = []
            Recorder.body_429 = body
            env = dict(self.env)
            env["SDLCA_SAY_PAUSE"] = "0"
            result = helpers.run(["python3", "-I", "-B", "-c", (
                "import importlib.machinery, importlib.util, io, sys, urllib.error\n"
                "loader = importlib.machinery.SourceFileLoader('sdlca_say', sys.argv[1])\n"
                "spec = importlib.util.spec_from_loader('sdlca_say', loader)\n"
                "mod = importlib.util.module_from_spec(spec); loader.exec_module(mod)\n"
                "import json\n"
                "err = urllib.error.HTTPError('http://x', 429, 'x', {}, io.BytesIO(json.dumps(%r).encode()))\n"
                "value = mod.retry_after(err)\n"
                "assert 0 <= value < 100, value\n" % (body,)), os.path.join(helpers.ROOT, "bin", "sdlca-say")], env=env)
            self.assertEqual(result.returncode, 0, "%r: %s" % (body, result.stderr))

    def test_a_retry_after_header_that_is_not_a_plain_number_is_ignored(self):
        for header in ("-3", "nan", "inf", "Wed, 21 Oct 2026 07:28:00 GMT"):
            result = helpers.run(["python3", "-I", "-B", "-c", (
                "import importlib.machinery, importlib.util, io, sys, urllib.error, email.message\n"
                "loader = importlib.machinery.SourceFileLoader('sdlca_say', sys.argv[1])\n"
                "spec = importlib.util.spec_from_loader('sdlca_say', loader)\n"
                "mod = importlib.util.module_from_spec(spec); loader.exec_module(mod)\n"
                "headers = email.message.Message(); headers['Retry-After'] = %r\n"
                "err = urllib.error.HTTPError('http://x', 429, 'x', headers, io.BytesIO(b'{}'))\n"
                "value = mod.retry_after(err)\n"
                "assert value == 3.0, value\n" % (header,)), os.path.join(helpers.ROOT, "bin", "sdlca-say")])
            self.assertEqual(result.returncode, 0, "%r: %s" % (header, result.stderr))

    def test_reply_to_with_non_ascii_digits_is_refused(self):
        for value in ("\u0663", "\u00b2", "\uff17"):
            result = self.say(["dm", "@alice", value], "hi")
            self.assertNotEqual(result.returncode, 0, repr(value))
        self.assertEqual(Recorder.posts, [])


if __name__ == "__main__":
    unittest.main()
