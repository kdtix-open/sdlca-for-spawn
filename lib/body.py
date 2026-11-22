#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Give a Spawn agent account a body: make one from a picture, or put one that already exists on it.

Run it through bin/sdlca-body, which loads the account first and has the full usage text. The account's token file
(SPAWN_TOKEN_FILE), its folder (ACC) and SPAWN_ORIGIN (default https://www.spawn.co) come from the environment. The token is only
ever sent to that origin, a redirect is never followed, and the token is taken out of everything this program prints.

  sdlca-body <account> <picture> [--apply] [--wait <seconds>]
  sdlca-body <account> --job <jobId> [--apply] [--wait <seconds>]
  sdlca-body <account> --wear <address|look> [--apply]
  sdlca-body <account> --reset <characterId> [--apply]
  sdlca-body <account> --carry <file.glb> --world <@owner/world> [--apply] [--wait <seconds>]

The doors it uses are the ones Spawn's published guide describes (https://www.spawn.co/llms-full.txt, "Your Body" and the carry door):
the character doors picture, convert, jobs, equip and reset under /api/character/, PATCH /api/agent/v1/me for a body, and a world's
asset doors under /api/sdk/v1/<worldId>/assets/ to carry a model file to Spawn.
"""
import contextlib
import hashlib
import http.client
import ipaddress
import json
import math
import os
import re
import signal
import stat
import struct
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import safeurl  # noqa: E402

PROG = "sdlca-body"
USAGE = (
    "usage: sdlca-body <account> <picture> [--apply] [--wait <seconds>]\n"
    "       sdlca-body <account> --job <jobId> [--apply] [--wait <seconds>]\n"
    "       sdlca-body <account> --wear <address|look> [--apply]\n"
    "       sdlca-body <account> --reset <characterId> [--apply]\n"
    "       sdlca-body <account> --carry <file.glb> --world <@owner/world> [--apply] [--wait <seconds>]\n"
    "(sdlca-body --help has the details)"
)
MAX_IMAGE_BYTES = 4 * 1024 * 1024  # Spawn's guide says a picture is at most 4 MB; Spawn has the last word
MAX_MODEL_BYTES = 25 * 1024 * 1024  # the largest model file this tool will carry; Spawn has the last word
DIRECT_LIMIT = 4_400_000  # a file up to this size rides in the request of the carry door; Spawn's limit is 4.5 MB for the whole request
MAX_ANSWER_BYTES = 1024 * 1024  # what is read of any one answer
REQUEST_TIMEOUT = 90  # seconds without a byte from Spawn, for one read of the socket
CALL_LIMIT = 120  # seconds for one whole call, however slowly or endlessly Spawn sends its answer
UPLOAD_LIMIT = 300  # the same, for the call that sends the picture
DEFAULT_WAIT = 900  # seconds to wait for a sculpt; it runs for minutes
MIN_POLL, MAX_POLL = 1, 300  # SDLCA_BODY_POLL, seconds between the checks on a sculpt
RATE_LIMIT_PAUSE = 10  # seconds to wait after a 429 that names no time
NOT_FOUND_GRACE = 3  # checks on a sculpt that was only just started may find nothing at first
MARKER = "body-sculpt.json"  # in the account's folder: the record that stops a second paid sculpt
WORLD_RE = re.compile(r"@{1,2}[A-Za-z0-9_.-]{1,64}/[A-Za-z0-9_.-]{1,64}")  # a world's address, as Spawn lists it
TEMP_RE = re.compile(r"[A-Za-z0-9_./-]{1,300}")  # the temporary name Spawn gives an upload by address
MEDIA_RE = re.compile(r"[a-z0-9][a-z0-9.+-]{0,40}/[a-z0-9][a-z0-9.+-]{0,60}")  # a content type
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}")  # a job, character or asset id (Spawn's are UUIDs); it goes into a URL path
LOOK_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")  # a key from the "looks" the agent's own answer lists
DONE_STATUSES = {"completed", "complete", "succeeded", "success", "finished", "done"}  # Spawn's guide says "completed"
FAILED_WORDS = ("fail", "error", "cancel", "reject", "abort", "expire", "timeout", "timed", "block", "denied", "invalid", "refus")
PLAIN_ADDRESS = re.compile(r"https://[A-Za-z0-9._~:/-]{1,300}")  # no query, fragment or user information: nothing that could be a credential
SECRETS = []  # the tokens of the clients made so far: taken out of everything printed

MAY_HAVE_STARTED = ("Spawn may have started it anyway: look at your characters on spawn.co before you run this again, so that the sculpt is "
                    "not made, and paid for, twice.")


class Refuse(Exception):
    """A stop with a plain message for the person (exit status 1). `hint` is a line that says what to do next; `final` says that nothing
    can be carried on (the sculpt itself failed), so no resume hint is added."""

    def __init__(self, message, hint=None, final=False):
        super().__init__(message)
        self.hint = hint
        self.final = final


class Usage(Exception):
    """A wrong command line (exit status 2)."""


class TimedOut(Exception):
    """The wait ended before the sculpt did (exit status 3). It keeps running at Spawn. `last` is the last (status, stage) seen, or None
    when no check was answered."""

    def __init__(self, job_id, waited, last):
        super().__init__(job_id)
        self.job_id = job_id
        self.waited = waited
        self.last = last


class ApiError(Exception):
    """Spawn answered with an error status."""

    def __init__(self, status, code, message, retry_after=None):
        super().__init__("HTTP %d" % status)
        self.status = status
        self.code = code
        self.message = message
        self.retry_after = retry_after

    def text(self):
        text = "HTTP %d" % self.status + ((" " + self.code) if self.code else "")
        return text + ": " + self.message if self.message else text


class NetworkError(Exception):
    """No usable answer: the connection failed, timed out or broke, or the answer was not what Spawn sends."""


# ------------------------------------------------------------------------------------------------------------------ printing


def redact(text):
    """The text with every token this program has used taken out of it."""
    for secret in SECRETS:
        text = text.replace(secret, "[token]")
    return text


def clean(value, limit=300):
    """Text that came from Spawn or from a file name, made safe to print on one line: the token is taken out first (before any cut,
    so a cut cannot leave half of it), control characters (an escape sequence can rewrite a terminal), invisible direction marks
    and line breaks become '?', and the result is cut to `limit` characters."""
    text = value if isinstance(value, str) else (json.dumps(value, default=str) if isinstance(value, (dict, list)) else str(value))
    text = redact(text)
    out = "".join(c if (c == " " or (c.isprintable() and unicodedata.category(c)[0] != "C")) else "?" for c in text)
    return out if len(out) <= limit else out[: max(limit - 3, 0)] + "..."


def emit(text="", stream=None):
    """Everything this program prints goes through here, and so through redact(): the token cannot reach a terminal or a log by a path
    that forgot to clean its text. A closed pipe or terminal never stops the run: once a sculpt exists, finishing it matters more
    than the progress lines, and the record in the account's folder keeps what the person needs."""
    stream = sys.stdout if stream is None else stream
    try:
        print(redact(text), file=stream, flush=True)
    except OSError:
        if stream is sys.stdout:
            try:
                os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())  # so that the flush at exit does not fail either
            except (OSError, ValueError):
                pass


def say(text=""):
    emit(text)


def dig(value, *keys):
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def plain_address(value):
    """The address if it is a plain https one that is safe to print, else None."""
    return value if isinstance(value, str) and PLAIN_ADDRESS.fullmatch(value) else None


def shareable_address(value, origin):
    """A plain address on Spawn's own host (or the origin's, for a test), without a '..' step, that is fit to suggest to a person."""
    address = plain_address(value)
    if not address:
        return None
    try:
        host = urllib.parse.urlsplit(address).hostname or ""
        own = urllib.parse.urlsplit(origin).hostname or ""
    except ValueError:
        return None
    if not (host == own or host == "spawn.co" or host.endswith(".spawn.co")) or ".." in address.split("/"):
        return None
    return address


def elapsed(started):
    seconds = int(time.monotonic() - started)
    return "%dm%02ds" % (seconds // 60, seconds % 60)


def stamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def resume_hint(account, job_id):
    return "carry on with:  sdlca-body %s --job %s --apply" % (account, job_id)


# ---------------------------------------------------------------------------------------------------------------- the picture


def sniff_image(data):
    """(kind, content type, extension) from the file's own first bytes (never from its name), or None."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG", "image/png", "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG", "image/jpeg", "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WebP", "image/webp", "webp"
    return None


def png_size(data):
    """(width, height) of a PNG from its header chunk, or None."""
    if len(data) >= 24 and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    return None


def metadata_notes(kind, data):
    """Names of the embedded text or camera data a picture carries (it is sent as it is, so the person should know). Walks the
    file's own chunks or segments, each step moving forward, and stops at the first thing that does not fit."""
    notes = []

    def add(name):
        if name not in notes:
            notes.append(name)

    size = len(data)
    if kind == "PNG":
        pos = 8
        while pos + 8 <= size:
            length = int.from_bytes(data[pos : pos + 4], "big")
            name = data[pos + 4 : pos + 8]
            if name in (b"tEXt", b"zTXt", b"iTXt", b"eXIf"):
                add(name.decode("ascii"))
            if name == b"IEND":
                break
            pos += 12 + length
    elif kind == "JPEG":
        pos = 2
        while pos + 4 <= size and data[pos] == 0xFF:
            marker = data[pos + 1]
            if marker == 0xFF:  # a fill byte
                pos += 1
                continue
            if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:  # markers with no length
                pos += 2
                continue
            if marker in (0xD9, 0xDA):  # the end, or the start of the picture data
                break
            length = int.from_bytes(data[pos + 2 : pos + 4], "big")
            if length < 2:
                break
            segment = data[pos + 4 : pos + 2 + length]
            if marker == 0xE1 and segment.startswith(b"Exif\x00\x00"):
                add("EXIF")
            elif marker == 0xE1 and segment.startswith(b"http://ns.adobe.com/xap/"):
                add("XMP")
            elif marker == 0xED:
                add("Photoshop")
            elif marker == 0xFE:
                add("comment")
            pos += 2 + length
    elif kind == "WebP":
        pos = 12
        while pos + 8 <= size:
            name = data[pos : pos + 4]
            length = int.from_bytes(data[pos + 4 : pos + 8], "little")
            if name == b"EXIF":
                add("EXIF")
            elif name == b"XMP ":
                add("XMP")
            pos += 8 + length + (length & 1)
    return notes


def jpeg_end(data):
    """The offset just after the end-of-image marker of a JPEG, found by walking its segments and skipping its entropy-coded data, or
    None when the structure does not parse."""
    size = len(data)
    pos = 2
    while pos + 2 <= size:
        if data[pos] != 0xFF:
            return None
        marker = data[pos + 1]
        if marker == 0xFF:  # a fill byte
            pos += 1
            continue
        if marker == 0xD9:
            return pos + 2
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:  # markers with no length
            pos += 2
            continue
        if pos + 4 > size:
            return None
        length = int.from_bytes(data[pos + 2 : pos + 4], "big")
        if length < 2:
            return None
        pos += 2 + length
        if marker == 0xDA:  # a scan: coded data follows, up to the next marker that is not a stuffed byte, a restart or a fill
            while True:
                pos = data.find(b"\xff", pos)
                if pos < 0 or pos + 1 >= size:
                    return None
                following = data[pos + 1]
                if following == 0x00 or following == 0xFF or 0xD0 <= following <= 0xD7:
                    pos += 1
                    continue
                break
    return None


def trailing_bytes(kind, data):
    """How many bytes follow the end of the picture proper (0 when none are found or the structure does not parse). A phone's
    "motion photo" is a JPEG with a video after it, and such bytes are sent along with the picture."""
    size = len(data)
    end = None
    if kind == "PNG":
        pos = 8
        while pos + 12 <= size:
            length = int.from_bytes(data[pos : pos + 4], "big")
            name = data[pos + 4 : pos + 8]
            pos += 12 + length
            if name == b"IEND":
                end = pos
                break
    elif kind == "WebP":
        end = int.from_bytes(data[4:8], "little") + 8
    elif kind == "JPEG":
        end = jpeg_end(data)
    return size - end if end is not None and 0 < end < size else 0


def read_plain_file(path, limit, what, too_big):
    """The bytes of a plain file, or a stop. Nothing is sent anywhere here. It opens without blocking (so a named pipe cannot hang it),
    asks the open file what it is before reading from it, and reads at most one byte more than `limit`."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY)
    except OSError as error:
        raise Refuse("cannot open the %s %s: %s" % (what, clean(path, 200), error.strerror or type(error).__name__))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):  # asked of the open file itself, before anything is read from it
            raise Refuse("%s is not a plain file" % clean(path, 200))
        handle = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise
    with handle:
        try:
            data = handle.read(limit + 1)
        except OSError as error:
            raise Refuse("cannot read the %s %s: %s" % (what, clean(path, 200), error.strerror or type(error).__name__))
    if len(data) > limit:
        raise Refuse("%s is bigger than %s" % (clean(path, 200), too_big))
    if not data:
        raise Refuse("%s is empty" % clean(path, 200))
    return data


def read_image(path):
    """The picture's bytes and what they are, or a stop. The type is decided from the file's first bytes, so only a file that starts like a
    PNG, JPEG or WebP picture can leave this machine: a note or a token file is refused whatever it is called."""
    data = read_plain_file(path, MAX_IMAGE_BYTES, "picture", "the 4 MB that Spawn takes for a picture")
    found = sniff_image(data)
    if found is None:
        raise Refuse("%s is not a PNG, JPEG or WebP picture (the file's own first bytes decide, not its name)" % clean(path, 200))
    return data, found


def read_model(path):
    """The bytes of a glTF binary (.glb) model, or a stop: its header must say glTF version 2 and the length of the file it is in."""
    data = read_plain_file(path, MAX_MODEL_BYTES, "model", "the 25 MB this tool carries")
    if len(data) < 20 or data[:4] != b"glTF":
        raise Refuse("%s is not a glTF binary (.glb) model (the file's own first bytes decide, not its name)" % clean(path, 200))
    version, length = struct.unpack("<II", data[4:12])
    if version != 2:
        raise Refuse("%s is glTF version %d; a body is glTF 2" % (clean(path, 200), version))
    if length != len(data):
        raise Refuse("%s is cut short or has bytes after its end (its header says %d bytes and the file has %d)" % (clean(path, 200), length, len(data)))
    return data


def glb_skins(data):
    """How many skins (a skeleton) the model's JSON part names, or None when that part cannot be read."""
    try:
        size, kind = struct.unpack("<I4s", data[12:20])
        if kind != b"JSON" or 20 + size > len(data) or size > 8 * 1024 * 1024:
            return None
        document = json.loads(data[20 : 20 + size].decode("utf-8"))
    except (struct.error, ValueError, RecursionError):
        return None
    skins = document.get("skins") if isinstance(document, dict) else None
    return len(skins) if isinstance(skins, list) else 0


def multipart(field, filename, content_type, data):
    """A multipart/form-data body with one file. The file name is fixed by the caller: the name of the file on this machine, and the
    folders it sits in, are never sent."""
    while True:
        boundary = "sdlca-body-" + uuid.uuid4().hex
        if boundary.encode("ascii") not in data:
            break
    head = '--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\nContent-Type: %s\r\n\r\n' % (boundary, field, filename, content_type)
    return "multipart/form-data; boundary=" + boundary, head.encode("ascii") + data + ("\r\n--%s--\r\n" % boundary).encode("ascii")


# ------------------------------------------------------------------------------------------------------------------- Spawn


@contextlib.contextmanager
def hard_deadline(seconds):
    """Raise TimeoutError in this thread when `seconds` of wall-clock time are over. The socket timeout counts one wait for a byte, so
    an answer that trickles in, or never ends (endless chunk trailers, endless interim answers), would never trip it. Needs a Unix
    main thread; anywhere else it does nothing and the socket timeout is all there is."""
    if not hasattr(signal, "setitimer") or threading.current_thread() is not threading.main_thread():
        yield
        return

    def fire(signum, frame):
        raise TimeoutError("no complete answer in time")

    previous = signal.signal(signal.SIGALRM, fire)
    signal.setitimer(signal.ITIMER_REAL, max(float(seconds), 0.001))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class Client:
    """Calls to Spawn's own origin with the account's token. One attempt per call: a call that makes something is never repeated by
    this class (a second sculpt could be billed twice); the caller decides what may be asked again."""

    def __init__(self, origin, token):
        self.origin = origin
        self.token = token
        # Never follows a redirect, so the token cannot be forwarded to another host. For a plain-http origin (this machine only) it also
        # ignores the environment's proxy settings: a proxy would carry the token, in clear text, to another host.
        self.opener = safeurl.opener(direct=origin.startswith("http://"))
        if len(token) >= 8 and token not in SECRETS:
            SECRETS.append(token)

    def call(self, method, path, body=None, content_type=None, limit=CALL_LIMIT):
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/json"}
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            headers["Content-Type"] = content_type or "application/json"
        request = urllib.request.Request(self.origin + path, data=data, headers=headers, method=method)
        try:
            with hard_deadline(limit):
                try:
                    with self.opener.open(request, timeout=REQUEST_TIMEOUT) as response:
                        raw = response.read(MAX_ANSWER_BYTES + 1)
                except urllib.error.HTTPError as error:
                    raise self.api_error(error)
                except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as error:
                    reason = getattr(error, "reason", None) or error
                    raise NetworkError("could not get an answer from Spawn (%s)" % clean(reason))
        except TimeoutError:  # the alarm fired where nothing above caught it
            raise NetworkError("could not get an answer from Spawn (no complete answer in time)")
        if len(raw) > MAX_ANSWER_BYTES:
            raise NetworkError("Spawn's answer was larger than this tool reads (1 MB)")
        try:
            answer = json.loads(raw.decode("utf-8", "replace"))
        except (ValueError, RecursionError):  # RecursionError: an answer nested thousands of levels deep
            raise NetworkError("Spawn's answer was not JSON")
        if not isinstance(answer, dict):
            raise NetworkError("Spawn's answer was not a JSON object")
        return answer

    def put_storage(self, url, data, content_type, limit=UPLOAD_LIMIT):
        """PUT bytes to the signed storage address Spawn gave for an upload. That address stands for these bytes and no others, and it is
        another host: no Authorization header goes with it, and it is added to what is taken out of everything printed."""
        if len(url) >= 8 and url not in SECRETS:
            SECRETS.append(url)
        request = urllib.request.Request(url, data=data, headers={"Content-Type": content_type}, method="PUT")
        try:
            with hard_deadline(limit):
                try:
                    with self.opener.open(request, timeout=REQUEST_TIMEOUT) as response:
                        response.read(65536)
                        status = response.status
                except urllib.error.HTTPError as error:
                    raise ApiError(error.code, None, "Spawn's storage refused the file")
                except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as error:
                    reason = getattr(error, "reason", None) or error
                    raise NetworkError("could not reach Spawn's storage (%s)" % clean(reason))
        except TimeoutError:
            raise NetworkError("could not reach Spawn's storage (no complete answer in time)")
        if not 200 <= status < 300:
            raise ApiError(status, None, "Spawn's storage did not take the file")

    def api_error(self, error):
        code = message = None
        try:
            parsed = json.loads(error.read(65536).decode("utf-8", "replace"))
            if isinstance(parsed, dict):
                code = parsed.get("error")
                message = parsed.get("verdict") or parsed.get("message") or parsed.get("note")
        except (ValueError, RecursionError, OSError, AttributeError, http.client.HTTPException):
            pass
        if 300 <= error.code < 400:
            message = "Spawn answered with a redirect, which the kit never follows because the token would go along with it"
        retry_after = None
        try:
            seconds = float(error.headers.get("Retry-After")) if error.headers and error.headers.get("Retry-After") else None
            if seconds is not None and math.isfinite(seconds) and seconds >= 0:
                retry_after = min(seconds, 60.0)
        except (TypeError, ValueError):
            pass
        return ApiError(error.code, clean(code, 80) if code else None, clean(message, 300) if message else None, retry_after)


def need_id(answer, key, what, required=True):
    """An id from one of Spawn's answers, checked before it goes into a URL path or a request body. An id that holds the token is
    refused too: it is printed in messages."""
    value = answer.get(key)
    if isinstance(value, str) and ID_RE.fullmatch(value) and not any(secret in value for secret in SECRETS):
        return value
    if required:
        raise Refuse("Spawn's answer to %s had no usable %s (it said: %s)" % (what, key, clean(answer, 200)))
    return None


def failed(error, doing):
    """A stop that names the step, for an error Spawn sent."""
    return Refuse("Spawn refused %s: %s" % (doing, error.text()))


def unreachable(error, doing, hint=None):
    return Refuse("%s while %s." % (error, doing), hint=hint)


# --------------------------------------------------------------------------------------------------------- the paid sculpt's record


class Marker:
    """A small record in the account's folder that stops a second paid sculpt. It is made (and so the account is locked) just before the
    sculpt is asked for, says what is known about it, and is removed when the body is worn or the sculpt has failed. While it exists, a
    run that would start a sculpt refuses, whatever became of the terminal or the process that made it: the job id on the screen is
    not the only copy."""

    def __init__(self, folder):
        usable = bool(folder) and os.path.isabs(folder) and os.path.isdir(folder)
        self.path = os.path.join(folder, MARKER) if usable else None

    def read(self):
        """The recorded fields; {} for a file that cannot be read; None when there is no record."""
        if not self.path:
            return None
        try:
            with open(self.path, encoding="utf-8") as handle:
                record = json.load(handle)
        except FileNotFoundError:
            return None
        except (OSError, ValueError, RecursionError):
            return {}
        return record if isinstance(record, dict) else {}

    def job(self):
        record = self.read() or {}
        value = record.get("job")
        return value if isinstance(value, str) and ID_RE.fullmatch(value) else None

    def refuse_if_recorded(self, account):
        record = self.read()
        if record is None:
            return
        where = clean(self.path, 300)
        job = self.job()
        when = clean(record.get("at") or "an unknown time", 40)
        if job:
            raise Refuse("a sculpt is already recorded for this account (job %s, started %s), so a new one is not started." % (job, when),
                         hint="%s. If it is finished or you have given up on it, delete %s and run this again." % (resume_hint(account, job), where))
        raise Refuse("an earlier run may have started a sculpt that Spawn did not confirm (recorded %s), so a new one is not started." % when,
                     hint="Look at your characters on spawn.co. When you are sure that none is being sculpted, or you accept another, delete %s and run "
                          "this again." % where)

    def begin(self, character):
        """Make the record, failing if one exists (so two runs at once cannot both start a sculpt)."""
        record = {"state": "starting", "job": None, "character": character, "at": stamp()}
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            raise Refuse("another run has just recorded a sculpt for this account, so this one stops before starting a second.")
        except OSError as error:
            raise Refuse("cannot record the sculpt in %s (%s), so nothing was started." % (clean(self.path, 300), error.strerror or type(error).__name__))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle)

    def update(self, **fields):
        """Change the record. A failure here does not stop the run: the sculpt exists, and finishing it matters more."""
        record = self.read()
        if not self.path or record is None:
            return
        record.update(fields)
        temporary = self.path + ".tmp"
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(record, handle)
            os.replace(temporary, self.path)
        except OSError as error:
            say("  could not update %s (%s)" % (clean(self.path, 300), error.strerror or type(error).__name__))

    def clear(self):
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass
        except (OSError, TypeError) as error:
            say("  could not remove %s (%s); delete it before the next picture run" % (clean(self.path, 300), getattr(error, "strerror", None) or type(error).__name__))

    def clear_if(self, job_id):
        if self.path and self.job() == job_id:
            self.clear()


# ----------------------------------------------------------------------------------------------------------------- the agent


def require_agent(me):
    """Stop unless Spawn says this is an agent's own account. A person's token would change the person's own character."""
    kind = me.get("actorClass")
    if kind != "agent":
        raise Refuse("this is not an agent account (Spawn says: %s). A body is made for an agent's own account, the one sdlca-onboard "
                     "sets up, never for a person's." % (clean(kind, 40) if kind else "nothing about its kind"))


def show_agent(me, account):
    handle = clean(me.get("handle") or "?", 80)
    name = clean(me.get("name") or "", 60)
    say("%s: account %s is the agent %s%s" % (PROG, account, handle, (' (shown as "%s")' % name) if name else ""))
    person = me.get("linkedTo")
    paid_by = dig(me, "budget", "paidBy")
    lane = dig(me, "budget", "lanes", "generation", "state")
    if person:
        say("  linked to:  %s%s" % (clean(person, 80), (" (generation is %s)" % clean(lane, 20)) if lane else ""))
    else:
        say("  linked to:  nobody")
    if paid_by:
        say("  paid by:    %s" % clean(paid_by, 80))
    worn = me.get("characterModelUrl")
    say("  wears now:  %s" % ("a body of its own (a new one replaces it)" if worn else "Spawn's default body (it has none of its own)"))


def look_keys(me):
    """The look keys the agent's own answer lists. Spawn's guide does not spell the shape out, so a list of names, a list of objects
    with a key (what Spawn answered when this was written) and an object keyed by name are all understood."""
    looks = me.get("looks")
    keys = []
    if isinstance(looks, dict):
        keys = list(looks)
    elif isinstance(looks, list):
        for item in looks:
            if isinstance(item, str):
                keys.append(item)
            elif isinstance(item, dict):
                for field in ("key", "look", "name", "id"):
                    if isinstance(item.get(field), str):
                        keys.append(item[field])
                        break
    return [clean(k, 64) for k in keys if isinstance(k, str)][:20]


# --------------------------------------------------------------------------------------------------------------- the steps


def failed_status(status):
    return any(word in status for word in FAILED_WORDS)


def wait_for_job(client, job_id, wait, poll, grace=0):
    """Ask for the sculpt every `poll` seconds until it is completed, has failed, or `wait` seconds are over. Asking is harmless, so a
    slow answer, a rate limit, a server error or a dropped connection is asked again until the time is up. `grace` is how many times
    "no such sculpt" is put down to a sculpt that was only just started and is not shown yet."""
    started = time.monotonic()
    deadline = started + wait
    path = "/api/character/jobs/" + urllib.parse.quote(job_id, safe="")
    shown = last = None
    noted = set()
    in_trouble = False
    missing = 0
    while True:
        pause = poll
        job = None
        try:
            job = client.call("GET", path, limit=min(CALL_LIMIT, max(deadline - time.monotonic(), 1)))
            in_trouble = False
        except ApiError as error:
            if error.status == 404 and missing < grace:
                missing += 1
                if not in_trouble:
                    say("  Spawn does not show the sculpt yet; asking again")
                    in_trouble = True
            elif error.status == 404:
                raise Refuse("Spawn does not know a sculpt with the id %s (%s)" % (clean(job_id, 100), error.text()), final=(grace == 0))
            elif error.status != 429 and error.status < 500:
                raise failed(error, "the check on the sculpt")
            else:
                pause = max(poll, error.retry_after if error.retry_after is not None else (RATE_LIMIT_PAUSE if error.status == 429 else 0))
                if not in_trouble:
                    say("  Spawn did not answer well (%s); asking again" % error.text())
                    in_trouble = True
        except NetworkError as error:
            if not in_trouble:
                say("  %s; asking again" % error)
                in_trouble = True
        if job is not None:
            status = clean(job.get("status") or "", 40).strip().lower()
            stage = clean(job.get("stage") or "", 60)
            reason = clean(job.get("error"), 300) if job.get("error") else None
            last = (status, stage)
            if last != shown:
                shown = last
                say("  %s  status %s%s" % (elapsed(started), status or "?", (", stage " + stage) if stage else ""))
            if failed_status(status):
                raise Refuse("the sculpt did not finish (status %s%s). Nothing was worn." % (status, (": " + reason) if reason else ""), final=True)
            if reason and reason not in noted:  # a message on a sculpt that has not failed: shown, not acted on
                noted.add(reason)
                say("  Spawn says: %s" % reason)
            if status in DONE_STATUSES:
                return job
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimedOut(job_id, int(time.monotonic() - started), last)
        time.sleep(min(max(pause, MIN_POLL), remaining))


def wear_job(client, account, job_id, character_known=None):
    """Put the finished body on the agent (POST equip), then read the agent's profile back to see that it names a body."""
    say("- wearing the body ...")
    try:
        result = client.call("POST", "/api/character/equip", {"jobId": job_id})
    except ApiError as error:
        raise failed(error, "wearing the body")
    except NetworkError as error:
        raise unreachable(error, "wearing the body")
    if result.get("success") is not True:
        raise Refuse("Spawn did not confirm that the body is worn (it said: %s)" % clean(result))
    character = need_id(result, "characterId", "wearing the body", required=False) or character_known
    model = result.get("modelUrl")
    address = shareable_address(model, client.origin)
    worn = None
    try:
        worn = client.call("GET", "/api/agent/v1/me").get("characterModelUrl")
        if worn and isinstance(model, str) and worn != model:
            say("  checked: the agent's profile names a body, but not at the address Spawn gave for this one")
        else:
            say("  checked: the agent's profile %s" % ("now names the body" if worn else "does not name a body yet"))
    except (ApiError, NetworkError) as error:
        say("  could not read the profile back (%s)" % (error.text() if isinstance(error, ApiError) else error))
    say()
    if worn:
        say("done: the body is worn. Every world this agent joins from now on dresses its player in it. (A body is shown while the agent")
        say("is in a world.)")
    else:
        say("Spawn says the body is worn, but the agent's profile does not show one yet. Give it a minute, then run the same command without")
        say("--apply to see what the agent wears now.")
    if character:
        say("to take it off:           sdlca-body %s --reset %s --apply" % (account, character))
    else:
        say("Spawn did not give the character's id, so there is no command here to take the body off.")
    if address:
        say("to share this body with another agent without a new sculpt: Spawn refuses this address as it is (tried on 2026-11-20), so the")
        say("file has to be carried to Spawn first:   curl -L -o body.glb %s" % address)
        say("  then:   sdlca-body <account> --carry body.glb --world <@owner/world> --apply   and   sdlca-body <other account> --wear <the address it prints> --apply")


def finish_job(client, account, job_id, wait, poll, marker, grace=0):
    """Wait for the sculpt, then wear it. From here on the sculpt exists, so every way this can stop that is not the sculpt itself
    failing says how to carry on, and the person is never pushed to run the whole thing again."""
    say("- waiting for the sculpt (up to %d seconds; it usually takes minutes) ..." % wait)
    record = marker.read() or {}
    known = record.get("character") if isinstance(record.get("character"), str) and ID_RE.fullmatch(record.get("character")) else None
    try:
        wait_for_job(client, job_id, wait, poll, grace)
        wear_job(client, account, job_id, known)
    except Refuse as stop:
        if stop.final:
            marker.clear_if(job_id)  # the sculpt itself failed: nothing is left to carry on with
        elif not stop.hint:
            stop.hint = resume_hint(account, job_id)
        raise
    except KeyboardInterrupt:
        say()
        say("stopped. The sculpt keeps running at Spawn. " + resume_hint(account, job_id))
        raise SystemExit(130)
    marker.clear_if(job_id)


def make_body(client, account, data, found, wait, poll, marker):
    kind, content_type, extension = found
    say("- uploading the picture (%d KB) ..." % round(len(data) / 1024))
    form, payload = multipart("image", "body." + extension, content_type, data)
    try:
        draft = client.call("POST", "/api/character/picture", payload, form, limit=UPLOAD_LIMIT)
    except ApiError as error:
        raise failed(error, "the picture")
    except NetworkError as error:
        raise unreachable(error, "uploading the picture")
    asset = need_id(draft, "resultAssetId", "the upload")
    character = need_id(draft, "characterId", "the upload", required=False)
    draft_status = clean(draft.get("status") or "", 40).strip().lower()
    if draft.get("error") or failed_status(draft_status):
        raise Refuse("Spawn did not accept the picture as a draft (status %s%s). Nothing was sculpted." % (
            draft_status or "?", (": " + clean(draft.get("error"), 300)) if draft.get("error") else ""), final=True)
    say("  uploaded as a draft (character %s, picture %s%s)" % (character or "?", asset, (", status " + draft_status) if draft_status else ""))
    say("- starting the sculpt (the linked person pays for this step) ...")
    # The one call that costs money. The record is made BEFORE it: from here until the body is worn, a second picture run for this account
    # refuses. Whatever happens to the call, the person must learn whether a sculpt may exist, because the natural next step, running the
    # whole command again, would make (and bill) a second one.
    marker.begin(character)
    where = clean(marker.path, 300)
    unsure = "The tool has recorded this in %s: a new picture run for this account refuses until you have looked and deleted that file." % where
    try:
        job = client.call("POST", "/api/character/convert", {"sourceAssetId": asset})
    except ApiError as error:
        if error.status >= 500 or error.status == 408:  # Spawn may have started the sculpt and failed to say so
            marker.update(state="unknown")
            raise Refuse("Spawn answered the request for the sculpt with %s, so it is not known whether it started. %s" % (error.text(), MAY_HAVE_STARTED),
                         hint=unsure)
        marker.clear()  # a refusal: nothing was started
        raise failed(error, "the sculpt")
    except NetworkError as error:
        marker.update(state="unknown")
        raise Refuse("%s while starting the sculpt. %s" % (error, MAY_HAVE_STARTED), hint=unsure)
    except KeyboardInterrupt:
        marker.update(state="unknown")
        emit("", sys.stderr)
        emit("%s: stopped while Spawn was being asked to start the sculpt. %s" % (PROG, MAY_HAVE_STARTED), sys.stderr)
        emit("  " + unsure, sys.stderr)
        raise SystemExit(130)
    job_id = need_id(job, "jobId", "the sculpt", required=False)
    if not job_id:
        marker.update(state="unknown")
        raise Refuse("Spawn answered the request for the sculpt (it said: %s) but gave no usable job id, so the sculpt has probably started "
                     "and cannot be followed from here. %s" % (clean(job, 200), MAY_HAVE_STARTED), hint=unsure)
    marker.update(state="started", job=job_id)
    say("  started: job %s" % job_id)
    say("  if this run is stopped now, %s" % resume_hint(account, job_id))
    finish_job(client, account, job_id, wait, poll, marker, grace=NOT_FOUND_GRACE)


def storage_target(url, origin):
    """The signed storage address, checked before the file is sent to it: https, a name for a host (never an address), no user information.
    A plain-http address on this machine is allowed only when the origin is one too, which is how the tests run."""
    if not isinstance(url, str) or not 8 <= len(url) <= 4096 or re.search(r"[\s\"'\\<>`]", url) or not url.isascii() or any(ord(c) < 32 for c in url):
        raise Refuse("Spawn gave an upload address that this tool will not use")
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname or ""
    except ValueError:
        raise Refuse("Spawn gave an upload address that this tool will not use")
    if parts.username is not None or parts.password is not None or not host:
        raise Refuse("Spawn gave an upload address that this tool will not use")
    loopback = host in ("127.0.0.1", "localhost") and origin.startswith("http://")
    if parts.scheme == "http" and loopback:
        return url
    try:
        ipaddress.ip_address(host)
        literal = True
    except ValueError:
        literal = False
    if parts.scheme != "https" or literal or host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or "." not in host:
        raise Refuse("Spawn gave an upload address that this tool will not use")
    return url


def find_world(me, address):
    """The world in the agent's own list with this address, where its standing lets it carry a file (editor, admin or owner)."""
    worlds = [w for w in (me.get("worlds") if isinstance(me.get("worlds"), list) else []) if isinstance(w, dict)]
    usable = [w for w in worlds if w.get("standing") in ("owner", "admin", "editor")]
    for world in worlds:
        if world.get("address") == address:
            if world.get("standing") not in ("owner", "admin", "editor"):
                raise Refuse("the agent is only a %s of %s; carrying a file needs editor standing there" % (clean(world.get("standing") or "visitor", 20), clean(address, 100)))
            if not isinstance(world.get("worldId"), str) or not ID_RE.fullmatch(world["worldId"]):
                raise Refuse("Spawn's list gave no usable id for %s" % clean(address, 100))
            return world
    names = ", ".join(clean(w.get("address"), 100) for w in usable[:10]) or "none"
    raise Refuse("this agent does not reach the world %s. Worlds where it can carry a file: %s" % (clean(address, 100), names))


def put_asset(client, path, body, content_type, wait, poll, limit):
    """PUT to the asset door, asked again while Spawn is still placing a large file (503 while it is placed, then 200 exists). Carrying the
    same bytes twice costs nothing, so this is safe to repeat."""
    deadline = time.monotonic() + wait
    noted = False
    while True:
        try:
            return client.call("PUT", path, body, content_type, limit=limit)
        except ApiError as error:
            if error.status != 503 or time.monotonic() >= deadline:
                raise
            if not noted:
                say("  Spawn is still placing the file (%s); asking again" % error.text())
                noted = True
            time.sleep(min(max(poll, MIN_POLL), max(deadline - time.monotonic(), 0)))


def carry_by_address(client, base, name, data, wait, poll):
    """Spawn's road for a file over 4.5 MB: ask for a storage address, PUT the bytes there, then tell the asset door where they are."""
    target = client.call("POST", base + "upload-target", {"name": name, "sizeBytes": len(data)})
    if target.get("status") == "exists":
        return target
    upload_url, temp, content_type, biggest = target.get("uploadUrl"), target.get("tempPath"), target.get("contentType"), target.get("maxBytes")
    if target.get("status") != "upload" or not isinstance(temp, str) or not TEMP_RE.fullmatch(temp) or not isinstance(content_type, str) or not MEDIA_RE.fullmatch(content_type):
        raise Refuse("Spawn's answer to the request for an upload address had no usable parts (it said: %s)" % clean(target, 200))
    if isinstance(biggest, int) and not isinstance(biggest, bool) and len(data) > biggest:
        raise Refuse("Spawn takes at most %d bytes for this, and the file has %d" % (biggest, len(data)))
    try:
        client.put_storage(storage_target(upload_url, client.origin), data, content_type)
    except ApiError as error:
        raise Refuse("Spawn's storage refused the file (HTTP %d)" % error.status,
                     hint="The signed address may have run out. Carrying the same file again costs nothing, so run the same command again.")
    say("  the file is in Spawn's storage; asking the asset door to take it")
    return put_asset(client, base + name, {"tempPath": temp}, None, wait, poll, CALL_LIMIT)


def carry_model(client, account, world_id, data, wait, poll):
    digest = hashlib.sha256(data).hexdigest()
    name = "value.%s.glb" % digest
    base = "/api/sdk/v1/%s/assets/" % urllib.parse.quote(world_id, safe="")
    say("- carrying the file to Spawn (%d KB) ..." % round(len(data) / 1024))
    try:
        if len(data) <= DIRECT_LIMIT:
            result = put_asset(client, base + name, data, "model/gltf-binary", wait, poll, UPLOAD_LIMIT)
        else:
            result = carry_by_address(client, base, name, data, wait, poll)
    except ApiError as error:
        raise failed(error, "carrying the file")
    except NetworkError as error:
        raise unreachable(error, "carrying the file", hint="Carrying the same file again costs nothing, so run the same command again.")
    status = result.get("status")
    address = shareable_address(result.get("url"), client.origin)
    if status not in ("carried", "exists") or not address or not address.endswith("/" + name):
        raise Refuse("Spawn's answer to the carry was not what was asked for (it said: %s)" % clean(result, 200))
    say()
    say("done: Spawn %s the file. Its address, named by the file's own hash:" % ("has" if status == "exists" else "carried"))
    say("  " + address)
    if not os.environ.get("SDLCA_ASSET_MODE"):  # sdlca-asset (the command an agent may run) has no use for the body hint
        say("to put it on an agent:   sdlca-body <account> --wear %s --apply" % address)


UNSURE_AFTER = "It may have gone through anyway: run the same command without --apply to see what the agent wears now."


def wear_existing(client, target):
    say("- asking Spawn to dress the agent in %s ..." % (clean(target, 300) if target.startswith("https://") else 'the look "%s"' % clean(target, 64)))
    try:
        result = client.call("PATCH", "/api/agent/v1/me", {"body": target})
    except ApiError as error:
        meaning = {"body_not_carried": "Spawn wants the address of a body that was carried to it (uploaded by its bytes), and did not take this one. Carry the file "
                                       "first with: sdlca-body <account> --carry <file.glb> --world <@owner/world> --apply, then wear the address it prints.",
                   "body_no_rig": "That model has no skeleton; Spawn needs a rigged model."}.get(error.code or "")
        raise Refuse("Spawn refused that body: %s" % error.text(), hint=meaning)
    except NetworkError as error:
        raise unreachable(error, "putting on the body", hint=UNSURE_AFTER)
    if result.get("ok") is not True:
        raise Refuse("Spawn did not confirm the body (it said: %s)" % clean(result))
    body = result.get("body") if isinstance(result.get("body"), dict) else {}
    look = body.get("look")
    address = plain_address(body.get("modelUrl"))
    say()
    say("done: Spawn says the agent now wears %s. Every world it joins from now on dresses its player in it." % (
        ('the look "%s"' % clean(look, 64)) if look else (address or "that body")))


def reset_body(client, character):
    say("- taking the made body off (character %s) ..." % character)
    try:
        result = client.call("POST", "/api/character/reset", {"characterId": character})
    except ApiError as error:
        raise failed(error, "the reset")
    except NetworkError as error:
        raise unreachable(error, "resetting the body", hint=UNSURE_AFTER)
    if result.get("success") is not True:
        raise Refuse("Spawn did not confirm the reset (it said: %s)" % clean(result))
    say()
    say("done: Spawn says the reset went through. The agent goes back to the default body.")


# ---------------------------------------------------------------------------------------------------------- command line


class Options:
    picture = job = wear = reset = carry = world = None
    apply = False
    wait = None


def parse_args(argv):
    opts = Options()
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help"):
            raise Usage("")
        if arg == "--apply":
            opts.apply = True
        elif arg in ("--wait", "--job", "--wear", "--reset", "--carry", "--world"):
            name = arg[2:]
            i += 1
            if i >= len(argv) or argv[i].startswith("--"):
                raise Usage("%s needs a value" % arg)
            if getattr(opts, name) is not None:
                raise Usage("%s was given twice" % arg)
            setattr(opts, name, argv[i])
        elif arg.startswith("--"):
            raise Usage("unknown option %s" % clean(arg, 60))
        elif opts.picture is None:
            opts.picture = arg
        else:
            raise Usage("more than one picture was given")
        i += 1
    modes = [name for name in ("picture", "job", "wear", "reset", "carry") if getattr(opts, name) is not None]
    if len(modes) != 1:
        raise Usage("give exactly one of: a picture, --job, --wear, --reset or --carry" if not modes else "a picture, --job, --wear, --reset and --carry cannot be mixed")
    if opts.world is not None and modes[0] != "carry":
        raise Usage("--world only applies to --carry")
    if modes[0] == "carry":
        if opts.world is None or not WORLD_RE.fullmatch(opts.world):
            raise Usage("--carry needs --world <@owner/world>, the address of a world where the agent is an editor")
    if opts.wait is not None:
        if modes[0] not in ("picture", "job", "carry"):
            raise Usage("--wait only applies to a picture, --job or --carry")
        if not re.fullmatch(r"[0-9]{1,4}", opts.wait) or not 1 <= int(opts.wait) <= 7200:
            raise Usage("--wait must be a whole number of seconds from 1 to 7200")
        opts.wait = int(opts.wait)
    else:
        opts.wait = DEFAULT_WAIT
    if opts.job is not None and not ID_RE.fullmatch(opts.job):
        raise Usage("--job needs the id the sculpt was given (letters, digits, - and _)")
    if opts.reset is not None and not ID_RE.fullmatch(opts.reset):
        raise Usage("--reset needs a character id (letters, digits, - and _)")
    if opts.wear is not None:
        if opts.wear.startswith("https://"):
            try:
                host = urllib.parse.urlsplit(opts.wear).hostname
            except ValueError:
                host = None
            if not PLAIN_ADDRESS.fullmatch(opts.wear) or not host or ".." in opts.wear.split("/"):
                raise Usage("--wear needs a plain https address (letters, digits and . _ ~ : / - only, with a host and no '..') or a look key")
        elif not LOOK_RE.fullmatch(opts.wear):
            raise Usage("--wear needs a plain https address or a look key (letters, digits, - _ .)")
    return opts


def poll_seconds(env):
    raw = env.get("SDLCA_BODY_POLL", "10")
    if not re.fullmatch(r"[0-9]{1,3}", raw) or not MIN_POLL <= int(raw) <= MAX_POLL:
        raise Refuse("SDLCA_BODY_POLL must be a whole number of seconds from %d to %d, not '%s'" % (MIN_POLL, MAX_POLL, clean(raw, 40)))
    return int(raw)


def run(argv, env):
    opts = parse_args(argv)
    # An agent turn may carry a file (bin/sdlca-asset sets SDLCA_ASSET_MODE), which spends nothing and changes no body; nothing else.
    if env.get("SDLCA_TURN_ACCOUNT") and not (env.get("SDLCA_ASSET_MODE") and opts.carry is not None):
        raise Refuse("an agent turn may not change a body: this is for the person who runs the kit, from their own shell")
    poll = poll_seconds(env) if (opts.picture is not None or opts.job is not None or opts.carry is not None) else MIN_POLL
    account = clean(env.get("ACCOUNT") or "<account>", 80)
    marker = Marker(env.get("ACC"))
    image = model = None
    if opts.picture is not None:  # checked here, before anything is sent: a file that is not a picture never leaves this machine
        image = read_image(opts.picture)
        if opts.apply and not marker.path:
            raise Refuse("the account's folder is not known (ACC is not set), so the sculpt cannot be recorded; run this as: sdlca-body <account> ...")
        marker.refuse_if_recorded(account)
    elif opts.carry is not None:  # the same for a model: only a real glTF binary can leave this machine
        model = read_model(opts.carry)
    token_file = env.get("SPAWN_TOKEN_FILE")
    if not token_file:
        raise Refuse("SPAWN_TOKEN_FILE is not set; run this as: sdlca-body <account> ...")
    try:
        client = Client(safeurl.check_origin(env.get("SPAWN_ORIGIN", "https://www.spawn.co")), safeurl.read_token(token_file))
    except SystemExit as stop:  # safeurl stops with a plain message (and never one that holds the token)
        raise Refuse(clean(stop.code, 300))
    except (OSError, ValueError) as error:  # ValueError: an origin that urllib cannot split
        raise Refuse("SPAWN_ORIGIN or the token file cannot be used (%s)" % (getattr(error, "strerror", None) or type(error).__name__))

    try:
        me = client.call("GET", "/api/agent/v1/me")
    except ApiError as error:
        raise Refuse("Spawn would not say who this account is (%s)%s" % (
            error.text(), ". If the agent was revoked, set it up again with sdlca-onboard." if error.status in (401, 403) else "."))
    except NetworkError as error:
        raise Refuse("%s while asking who this account is." % error)
    require_agent(me)
    show_agent(me, account)

    if image is not None:
        data, found = image
        lane = dig(me, "budget", "lanes", "generation")
        state = lane.get("state") if isinstance(lane, dict) else None
        if state is not None and state != "open":
            why = clean(lane.get("why") or lane.get("verdict") or "", 300)
            ask = clean(lane.get("ask") or "", 200)
            raise Refuse("Spawn has the generation lane %s for this agent, so it cannot make a body%s." % (clean(state, 20), (" (it says: %s)" % why) if why else ""),
                         hint=("see %s" % ask) if ask else (None if me.get("linkedTo") else "Generation is a person's: link the agent to a person first (see docs/getting-started.md)."))
        kind = found[0]
        digest = hashlib.sha256(data).hexdigest()
        size = png_size(data) if kind == "PNG" else None
        say("  picture:    %s" % clean(opts.picture, 200))
        say("              %s%s, %d KB, sha256 %s..." % (kind, (", %d x %d" % size) if size else "", round(len(data) / 1024), digest[:16]))
        notes = metadata_notes(kind, data)
        if notes:
            say("              carries %s data; it is sent along as it is (remove it first if you do not want it shared)" % ", ".join(notes))
        extra = trailing_bytes(kind, data)
        if extra:
            say("              carries %d bytes after the end of the picture (a motion photo's video, say); they are sent along as they are" % extra)
        say("  it will:    upload the picture as a draft, sculpt it into a rigged 3D body (this is the step that is paid for), wait for the")
        say("              sculpt (about %d seconds at most), and wear it. The file's name and folder are not sent. Spawn reviews an" % opts.wait)
        say("              uploaded picture like any other, and the body is shown to everyone who sees the agent in a world: use only a")
        say("              picture you have the right to upload (Spawn's terms apply to you).")
    elif opts.carry is not None:
        world = find_world(me, opts.world)
        digest = hashlib.sha256(model).hexdigest()
        skins = glb_skins(model)
        say("  model:      %s" % clean(opts.carry, 200))
        say("              glTF binary, %d KB (%d bytes), sha256 %s..." % (round(len(model) / 1024), len(model), digest[:16]))
        say("              %s" % (("it has a skeleton (%d skin%s)" % (skins, "" if skins == 1 else "s")) if skins else
                                  ("it names no skeleton, and Spawn refuses a body without one (body_no_rig)" if skins == 0 else "whether it has a skeleton could not be read")))
        say("  world:      %s (the agent is %s there)" % (clean(world.get("address"), 100), clean(world.get("standing"), 20)))
        say("  it will:    carry the file to Spawn through that world, %s." % ("in one call" if len(model) <= DIRECT_LIMIT else
                                                                          "by address (three calls; the middle one goes to Spawn's storage, without the token)"))
        say("              The file is stored with that world's assets and served from a public address named by its hash (anyone who knows the")
        say("              address can fetch it), and Spawn screens it. It prints the address.%s Use only a file you may upload." %
            ("" if env.get("SDLCA_ASSET_MODE") else " Wear it with --wear."))
    elif opts.job is not None:
        say("  it will:    wait for the sculpt %s (up to %d seconds), then wear it. Nothing is made again." % (opts.job, opts.wait))
        try:
            job = client.call("GET", "/api/character/jobs/" + urllib.parse.quote(opts.job, safe=""))
            say("  that sculpt: status %s%s" % (clean(job.get("status") or "?", 40), (", stage " + clean(job["stage"], 60)) if job.get("stage") else ""))
        except ApiError as error:
            raise failed(error, "the check on that sculpt")
        except NetworkError as error:
            raise Refuse("%s while checking the sculpt." % error)
    elif opts.wear is not None:
        say("  it will:    ask Spawn to dress the agent in %s." % clean(opts.wear, 200))
        keys = look_keys(me)
        say("  looks it can wear by name: %s" % (", ".join(keys) if keys else "Spawn listed none in its answer"))
        say("  Spawn takes a look key or the address of a file that was carried to it (sdlca-body --carry prints one). It refused the address printed")
        say("  after a sculpt (tried on 2026-11-20). Whether it takes the one you gave is its decision, and a dry run cannot ask it.")
    else:
        say("  it will:    take the made body off character %s (back to the default body)." % opts.reset)

    if not opts.apply:
        say()
        say("This was a dry run: nothing was uploaded, made or changed (the tool only read from Spawn).")
        say("Add --apply to do it.")
        return 0

    say()
    if image is not None:
        make_body(client, account, image[0], image[1], opts.wait, poll, marker)
    elif opts.carry is not None:
        carry_model(client, account, find_world(me, opts.world)["worldId"], model, opts.wait, poll)
    elif opts.job is not None:
        finish_job(client, account, opts.job, opts.wait, poll, marker)
    elif opts.wear is not None:
        wear_existing(client, opts.wear)
    else:
        reset_body(client, opts.reset)
    return 0


def interrupt(signum, frame):
    raise KeyboardInterrupt


def main(argv, env=None):
    env = os.environ if env is None else env
    previous = {}
    if threading.current_thread() is threading.main_thread():
        for name in ("SIGTERM", "SIGHUP"):  # a closed terminal or a stop ends the run the way Ctrl-C does, with the same hint
            if hasattr(signal, name):
                try:
                    previous[name] = signal.signal(getattr(signal, name), interrupt)
                except (ValueError, OSError):
                    pass
    try:
        return run(argv, env)
    except Usage as problem:
        if str(problem):
            emit("%s: %s" % (PROG, problem), sys.stderr)
            emit(USAGE, sys.stderr)
            return 2
        emit(USAGE)
        return 0
    except Refuse as stop:
        emit("%s: %s" % (PROG, stop), sys.stderr)
        if stop.hint:
            emit("  " + stop.hint, sys.stderr)
        return 1
    except KeyboardInterrupt:
        emit("", sys.stderr)
        emit("%s: stopped. Whatever was already sent to Spawn stays there." % PROG, sys.stderr)
        return 130
    except TimedOut as late:
        account = clean(env.get("ACCOUNT") or "<account>", 80)
        emit("", sys.stderr)
        if late.last and late.last[0]:
            emit("%s: the sculpt was still running after %d seconds (its last status was '%s'). It keeps running at Spawn, and nothing is lost." % (
                PROG, late.waited, late.last[0]), sys.stderr)
        elif late.last:
            emit("%s: the sculpt had not finished after %d seconds. It keeps running at Spawn, and nothing is lost." % (PROG, late.waited), sys.stderr)
        else:
            emit("%s: Spawn did not answer the checks on the sculpt in %d seconds, so its state is not known. It was started, and it keeps running "
                 "at Spawn if nothing went wrong there." % (PROG, late.waited), sys.stderr)
        emit("  " + resume_hint(account, late.job_id), sys.stderr)
        return 3
    except Exception as error:  # nothing unforeseen may print a traceback or an error's own text, which could hold data it should not
        emit("%s: stopped by an unexpected %s; check the state at Spawn before you run this again." % (PROG, type(error).__name__), sys.stderr)
        return 1
    finally:
        for name, handler in previous.items():
            try:
                signal.signal(getattr(signal, name), handler)
            except (ValueError, OSError):
                pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
