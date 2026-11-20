#!/usr/bin/env -S python3 -I -B
# SPDX-License-Identifier: Apache-2.0
"""Bring one world clone up to date with the world, by fast-forward only.

usage: python3 -I -B lib/refresh.py CLONE_DIR [GIT_ADDRESS]

The handler (sdlca-on-chat) runs this as trusted code just before an agent turn in a world's clone. The kit cannot
tell a read-only agent from a building one, so the update must be safe for both: the checked-out branch moves forward
only when that is a straight line. In every other case nothing changes and the reason is reported. It never makes a
merge commit, never leaves conflict markers, never rewrites history and never overwrites a file you changed, an
untracked file or an ignored file.

GIT_ADDRESS is the git address that sdlca-worlds recorded for this world, from Spawn's own listing and outside the clone
(the "git" field of the world in worlds.json, which lib/route.py hands to the handler; "-" when there is none). A missing
one, "-" and an empty one all mean that none is recorded. The update trusts only that address and never asks the clone where
the world is: it fetches from exactly that address and not through the name of a remote (so what the clone's configuration
says about the remote that the branch follows does not apply to it), and only when the clone's own remote and credential
helper agree with it. An agent that can edit .git/config therefore cannot point the update, or the account's token, at a host
of its choosing, with the exceptions that docs/security-model.md lists (a program that changes the file between the check and
the fetch, and a setting that the list below does not name).

Standard output is exactly one line with three tab-separated fields, STATUS, CODE and TEXT, and nothing else:

  STATUS   CODE         meaning
  current  ok           the clone was already at the world's tip
  updated  ok           the branch was fast-forwarded
  skipped  off          SDLCA_REFRESH_TIMEOUT is 0; git was not run
  skipped  unverified   no usable git address is recorded for this world (run sdlca-worlds --apply); git was not run
  skipped  not-git      the folder is not the top of a git work tree
  skipped  detached     no branch is checked out
  skipped  no-upstream  the branch has no upstream (or its remote has no address), or no commits yet
  skipped  ahead        the clone has commits that are not pushed
  skipped  diverged     the clone and the world have both moved on, or the world rewrote its history or moved back to an older commit
  skipped  untrusted    the folder, the clone's remote or the clone's own git settings are not trusted; the branch and the work tree were not touched
  failed   fetch        git could not fetch from the world
  failed   timeout      a git call took longer than SDLCA_REFRESH_TIMEOUT seconds and was stopped
  failed   merge        the fast-forward was refused or stopped (a local change or a lock file in the way, or it ran out of time)
  failed   error        anything else: git missing or too old, an answer this tool cannot read, a crash

TEXT is plain English for the log: one line, no tab, at most 200 characters. It can hold the first line of git's own
error, cleaned (control characters and user information in URLs removed, cut to 120 characters), and the host of an address
(never a whole address). It is meant for the log only. Never put it in a prompt, because a remote can influence it.

Environment: SDLCA_REFRESH_TIMEOUT is the number of seconds each git call may take (default 60; 0 turns the update
off; anything that is not a whole number counts as 60; more than a day counts as a day). The fast-forward gets at least
ten minutes whatever the value, because a checkout that is stopped half way leaves a half-updated work tree.
SPAWN_TOKEN_FILE and SDLCA_SPAWN_HOME (both set for the handler) say which token files a credential helper in the clone
may read.

Exit status: 0 for every outcome, because a refresh problem must never fail a turn. 2 for wrong usage (usage text goes to
standard error, and so does the text for --help, which exits 0), so standard output only ever carries the one line. A
crash prints its traceback to standard error, which the handler appends to the log.

Why it is built this way. The clone is a folder the agent may have written to: an agent that can edit files can change
.git/config and .git/hooks, and this code runs outside the agent's tool restrictions. So it never runs a shell, gives
git no setting from the clone that could start a program or send it elsewhere (the clone's own configuration is read
before the fetch and again before the fast-forward, and the clone is left alone if it sets one), turns off hooks and the
file system monitor on the command line, allows https only (unless the caller set GIT_ALLOW_PROTOCOL), never lets git
prompt, finds git only through absolute PATH entries, and removes the environment variables that can redirect git or
add a program. It refuses a clone whose reflogs or refs are links, because git appends to a reflog in place and a link
there would be written through. It fetches into a ref of its own (refs/sdlca/refresh-tip) and does not write FETCH_HEAD.
It leaves credential.helper alone on purpose: the clone logs in through a helper that sdlca-worlds (lib/gitcred.py)
wrote into its configuration, and an empty helper on the command line would erase it. A helper is accepted only in the form
sdlca-worlds writes and only when it is scoped to the origin (scheme, host and port) of the recorded address: a helper for any
other origin could hand the token to some other host, so it makes the clone untrusted.
The address comes from the caller and not from the clone. A remote that differs from it is refused before anything is
fetched, and the fetch names the address and not the remote, so the settings of the remote that the branch follows (a proxy,
a program to run, another url) do not apply to it. But git reads the word it is given as the NAME of a remote first, and a
remote section called like the address (a [remote "https://..."] with a url of its own) would be used, so a remote section whose
name is not a plain name (it has a colon, a slash or an at sign) makes the clone untrusted. The fetch writes the tracking branch
the clone's own fetch rule names (refs/remotes/origin/main) as well as refs/sdlca/refresh-tip, because the clone's reflog of
that branch is what lets "git rebase --fork-point" and the check for a world that moved back tell the world's old commits from
the clone's own.
The clone's settings are checked before git reads any object, and not only before the fetch: reading a commit that is missing
can fetch it from a promisor remote (extensions.partialclone, remote.NAME.promisor), which is a request that carries a token if
a helper is scoped to that remote, so those keys are on the list, GIT_NO_LAZY_FETCH=1 turns the fetching on demand off for git
2.44 and newer, and no git call that reads an object comes before the first check.
The check of the clone's settings is a list, so it cannot be complete: for example url.<base>.insteadOf would still rewrite an
address that is named on the command line, which is why it stays on the list. It is also made at one moment, so a program that
the agent left running could change the file between the check and the fetch. Only a separate Unix user for the agent closes
what the list does not name, and what a program of the agent's own can do (docs/security-model.md).
"""
import os
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import traceback
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gitcred  # noqa: E402

USAGE = "usage: python3 -I -B lib/refresh.py CLONE_DIR [GIT_ADDRESS]\n"
DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 24 * 3600  # an absurd value must not overflow the timer
MERGE_MINIMUM = 600  # seconds the fast-forward may take at least: stopping a checkout half way leaves a half-updated work tree
TERM_GRACE = 3.0  # seconds a stopped git gets to remove its lock files before it is killed outright
TEXT_LIMIT = 200
ERROR_LIMIT = 120
RAW_LIMIT = 1000  # git, or a remote, could say a megabyte on one line, and the patterns below are not linear: cut it first
HELPER_LIMIT = 2048  # the helper the kit writes is far shorter; the pattern for it must never see a long value
OUTPUT_LIMIT = 8 * 1024 * 1024  # more standard output than this is not an answer this tool can trust
ERROR_OUTPUT_LIMIT = 64 * 1024  # only the first line of standard error is used
MINIMUM_GIT = (2, 29)  # git fetch --no-write-fetch-head, and the settings below
TIP_REF = "refs/sdlca/refresh-tip"  # where the fetch puts the world's tip: nobody else writes it, unlike FETCH_HEAD
ADDRESS_SCHEMES = frozenset({"https", "http", "file"})  # what a recorded address may be; which of them git may use is GIT_ALLOW_PROTOCOL's business (https unless the caller says otherwise)
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost"})  # plain http carries a token only to this machine (check_origin in lib/common.sh)
HOST_LIMIT = 50  # characters of a host that go into a log line
REMOTE_NAME = re.compile(r"[A-Za-z0-9._/-]{1,40}")  # what a remote's name looks like in a log line

# Settings given to every git call. Settings on the command line beat the clone's own configuration and the user's
# global one. Not credential.helper: see the end of the module docstring.
GIT_SETTINGS = (
    "core.hooksPath=/dev/null",  # no hook runs, not even post-merge or reference-transaction
    "core.fsmonitor=false",  # the file system monitor is a program the clone's configuration can name
    "core.pager=cat",
    "gc.auto=0",  # git must not start a background clean-up that outlives the call
    "maintenance.auto=false",
    "merge.autoStash=false",  # a merge must never stash and re-apply work: that can leave conflict markers
    "user.name=sdlca-refresh",  # the name in the reflog line of a fast-forward: the clone's own user.name is never written to a file
    "user.email=sdlca-refresh@users.noreply.invalid",
)

# Variables that can redirect git to another repository, or make it run a program.
DROPPED_ENVIRONMENT = (
    "GIT_ASKPASS", "SSH_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND", "GIT_PROXY_COMMAND", "GIT_EXTERNAL_DIFF",
    "GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)

# Keys in the clone's OWN configuration (.git/config, and .git/config.worktree when git reads it; reading them runs nothing)
# that make git run a program during a fetch or a fast-forward, send it somewhere else, or pull in settings this check
# cannot see. Compared in lower case: git lists section and variable names that way. Every http.* key is handled
# separately, below.
RISKY_KEYS = re.compile(
    r"filter\..+"  # clean, smudge and process filters run on every file a fast-forward writes
    r"|core\.(?:fsmonitor|sshcommand|gitproxy|askpass|alternaterefscommand|worktree)"  # programs, and a work tree somewhere else
    r"|include\..+|includeif\..+"  # settings from another file: the check cannot see them
    r"|url\..+\.(?:push)?insteadof"  # rewrites where git connects
    r"|remote\..+\.(?:proxy|proxyauthmethod|uploadpack|receivepack|vcs)"  # a proxy, or a program to run for the remote
    r"|extensions\.partialclone|promisor\..+|remote\..+\.(?:promisor|partialclonefilter)"  # a promisor remote: git fetches a missing object from it, even for a read
    r"|fetch\.bundleuri|bundle\..+"  # a second place to download from
    r"|gpg\.(?:.+\.)?program"  # runs when signatures are checked
    r"|uploadpack\.packobjectshook"
    r"|merge\..+\.driver"  # a merge driver is a program
    r"|branch\..+\.mergeoptions"  # can add options to every merge, such as --squash
)
# Of the http.* keys the clone may hold only these. The kit writes http.<url>.proactiveAuth (for its scoped credential
# helper); the rest are tuning that cannot send a request anywhere else or change whom git trusts. Anything else under
# http. does that: http.proxy, http.curloptResolve and http.followRedirects change where the request goes, and
# http.sslVerify, http.sslCAInfo and http.sslCAPath change whom git trusts, so a request that carries a token could be
# read by someone else.
HTTP_HARMLESS = frozenset({"postbuffer", "lowspeedlimit", "lowspeedtime", "maxrequests", "minsessions", "noepsv", "useragent", "version"})
REMOTE_KEY = re.compile(r"remote\.(.+)\.([^.]+)")  # remote.<name>.<variable>: the name can hold dots, so the variable is what follows the last one
PLAIN_REMOTE_NAME = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9._-]*")  # what the name of a remote looks like when it is a name and not an address
CREDENTIAL_HELPER = re.compile(r"credential\.(?:(.+)\.)?helper")
HELPER_SHAPE = re.compile(r"!f\(\) \{ echo username=(.+); echo password=\$\(cat (.+)\); \}; f")
ACCOUNT_TOKEN = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}(?:/[a-z0-9][a-z0-9_-]{0,63})?/token")  # the kit's account names (valid_account_name)

USERINFO_IN_URL = re.compile(r"([A-Za-z][A-Za-z0-9+.-]*://)[^/\s]*@")
SECRET_SHAPES = re.compile(r"(?:sak_|sbk_|xox[a-z]-|xapp-|ghp_|gho_|github_pat_|glpat-)[A-Za-z0-9_-]+")
SECRET_HEADERS = re.compile(r"(?i)(authorization:?\s*(?:basic|bearer)\s+|password=)\S+")
SAFE_REMOTE = re.compile(r"[^\s\x00-\x1f\x7f-][^\s\x00-\x1f\x7f]*")  # a remote name or url: no space, no control character, never an option
SAFE_REFSPEC = re.compile(r"[^\s\x00-\x1f\x7f:*?\[\\^~+-][^\s\x00-\x1f\x7f:*?\[\\^~]*")  # a ref: nothing that means more in a refspec
OBJECT_ID = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
GIT_VERSION = re.compile(r"git version (\d+)\.(\d+)")


class GitTimeout(Exception):
    """A git call took longer than the limit and was stopped."""


class Stop(Exception):
    """The update ends here, with this answer."""

    def __init__(self, status, code, text):
        super().__init__(text)
        self.answer = (status, code, text)


def timeout_from(raw):
    """Seconds allowed for each git call. Unset or not a non-negative whole number: 60. 0: the update is off. A day at most."""
    if raw is not None and re.fullmatch(r"[0-9]+", raw):
        digits = raw.lstrip("0") or "0"
        return MAX_TIMEOUT if len(digits) > 6 else min(int(digits), MAX_TIMEOUT)  # int() is never given a number that long
    return DEFAULT_TIMEOUT


def clean(text, limit):
    """One plain line: secrets and user information in URLs removed, control characters turned into spaces, cut to limit."""
    text = text[:RAW_LIMIT]
    text = USERINFO_IN_URL.sub(r"\1", text)
    text = SECRET_SHAPES.sub("[removed]", text)
    text = SECRET_HEADERS.sub(r"\1[removed]", text)
    text = "".join(" " if unicodedata.category(ch)[0] == "C" or unicodedata.category(ch) in ("Zl", "Zp") else ch for ch in text)
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text


def first_line(text):
    for line in text.replace("\r", "\n").split("\n"):
        if line.strip():
            return line
    return ""


def git_said(returncode, stderr):
    line = clean(first_line(stderr), ERROR_LIMIT)
    return "git said: " + line if line else "git exited with status %d and said nothing" % returncode


def plural(count, singular, many):
    return "%d %s" % (count, singular if count == 1 else many)


def safe_path(raw):
    """PATH with only its absolute entries. An empty entry or a relative one means the current folder, and a program named
    git (or false, which an old git runs for core.fsmonitor=false) must never be found inside the clone."""
    entries = (os.defpath if raw is None else raw).split(os.pathsep)
    return os.pathsep.join(entry for entry in entries if entry and os.path.isabs(entry))


def git_environment(environ, clone):
    env = dict(environ)
    for name in DROPPED_ENVIRONMENT:
        env.pop(name, None)
    env["PATH"] = safe_path(environ.get("PATH"))
    env["GIT_TERMINAL_PROMPT"] = "0"  # a prompt would hang a turn that nobody can answer
    env["GIT_NO_LAZY_FETCH"] = "1"  # git 2.44 and newer: a missing object is never fetched on demand from a promisor remote (older git ignores it)
    env["LC_ALL"] = "C"  # git's messages are not translated, and no output is parsed in any case
    env.setdefault("GIT_ALLOW_PROTOCOL", "https")  # also overrides protocol.*.allow in the clone's configuration
    env["GIT_CEILING_DIRECTORIES"] = os.path.dirname(clone)  # never look for a repository above the clone's own folder
    return env


def group_alive(group):
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def signal_group(group, number):
    try:
        os.killpg(group, number)
    except (ProcessLookupError, PermissionError):
        pass


def stop_group(process):
    """Stop git and everything it started, not only the child. SIGTERM first: git removes its lock files when it is asked
    to stop, and SIGKILL would leave .git/index.lock behind. Whatever is still running after the grace period is killed."""
    group = process.pid
    signal_group(group, signal.SIGTERM)
    deadline = time.monotonic() + TERM_GRACE
    while True:
        process.poll()  # reaps git once it has exited, so that the group can become empty
        if not group_alive(group):
            break
        if time.monotonic() >= deadline:
            signal_group(group, signal.SIGKILL)
            break
        time.sleep(0.05)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


class Git:
    def __init__(self, exe, clone, env, timeout):
        self.exe, self.clone, self.env, self.timeout = exe, clone, env, timeout

    def run(self, *args, timeout=None):
        """(returncode, stdout, stderr). A timeout stops the whole process group and raises GitTimeout. Git writes into two
        temporary files and not into pipes: a program that git started and that keeps a pipe open (a credential helper that
        stays around) would otherwise hold the call until the limit, although git itself had finished."""
        command = [self.exe]
        for setting in GIT_SETTINGS:
            command += ["-c", setting]
        command += list(args)
        limit = self.timeout if timeout is None else timeout
        with tempfile.TemporaryFile() as out_file, tempfile.TemporaryFile() as err_file:
            process = subprocess.Popen(
                command, cwd=self.clone, env=self.env, stdin=subprocess.DEVNULL,
                stdout=out_file, stderr=err_file, start_new_session=True,
            )
            try:
                process.wait(timeout=limit)
            except subprocess.TimeoutExpired:
                stop_group(process)
                raise GitTimeout()
            except BaseException:  # for example our own SIGTERM: do not leave git running
                stop_group(process)
                raise
            out_file.seek(0)
            out = out_file.read(OUTPUT_LIMIT + 1)
            err_file.seek(0)
            err = err_file.read(ERROR_OUTPUT_LIMIT)
        if len(out) > OUTPUT_LIMIT:
            raise Stop("failed", "error", "git printed more than this tool reads")
        return process.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")

    def must(self, *args):
        """Standard output of a call that has to succeed."""
        returncode, out, err = self.run(*args)
        if returncode != 0:
            raise Stop("failed", "error", git_said(returncode, err))
        return out

    def config(self, key):
        """The value git would use for a setting, or None if it is not set."""
        returncode, out, err = self.run("config", "--get", key)
        if returncode == 1:
            return None
        if returncode != 0:
            raise Stop("failed", "error", git_said(returncode, err))
        return out[:-1] if out.endswith("\n") else out


def kit_token_file(path, environ):
    """True for the token file of this account (SPAWN_TOKEN_FILE, set for the handler) and for $SDLCA_SPAWN_HOME/accounts/<name>/token,
    which is where the kit keeps the others (a clone that another of your accounts made is served too)."""
    own = environ.get("SPAWN_TOKEN_FILE")
    if own and path == own:
        return True
    home = environ.get("SDLCA_SPAWN_HOME") or os.path.join(environ.get("HOME") or os.path.expanduser("~"), ".sdlca", "spawn")
    if path.endswith("/") or ".." in path.split("/"):  # not a spelling that the kit writes, and not one that names a file inside the accounts folder
        return False
    prefix = os.path.join(os.path.normpath(home), "accounts") + os.sep
    path = os.path.normpath(path)
    return path.startswith(prefix) and ACCOUNT_TOKEN.fullmatch(path[len(prefix):]) is not None


def helper_is_the_kits(value, environ):
    """True for an empty helper (it only clears the list) and for exactly what lib/gitcred.py writes, with a user name and a
    token file that are each one plainly quoted word, the token file being one of the kit's own. Anything else is a command
    somebody else wrote, or a way to make the kit send some other file to a host."""
    if value == "":
        return True
    if len(value) > HELPER_LIMIT:
        return False
    match = HELPER_SHAPE.fullmatch(value)
    if not match:
        return False
    try:
        words = [shlex.split(part) for part in match.groups()]
    except ValueError:
        return False
    if not all(len(w) == 1 for w in words):
        return False
    return gitcred.helper_command(words[0][0], words[1][0]) == value and kit_token_file(words[1][0], environ)


def address_key(url):
    """What two spellings of one address have in common, or None when it is not an address this tool will compare. The scheme and the
    host are in lower case (git.spawn.co and GIT.Spawn.CO are one host), a trailing slash or .git on the path does not count, and the
    port and the rest of the path are compared as written: nothing is folded that git or a server might treat as another address,
    and a path with a . or .. segment (spelled out or percent-encoded) is not compared at all, because a client may resolve it."""
    if gitcred.has_dot_segment(url.path):
        return None
    segments = url.path.rstrip("/").split("/")
    if len(segments[-1]) > len(".git") and segments[-1].endswith(".git"):  # a folder that is only ".git" is not an empty name plus a suffix
        segments[-1] = segments[-1][: -len(".git")]
    return (url.scheme, url.host, url.port, "/".join(segments))


def recorded_address(raw):
    """The recorded git address as a gitcred.GitUrl, or None when none is recorded or the update cannot work with the one that is: it is
    not a plain URL (see gitcred.parse_url: no user information, no query, no odd characters), its scheme is not https, http or file, or
    its path has a dot segment. The value is "-" when the handler found none in the registry."""
    url = gitcred.parse_url(raw)
    if url is None or url.scheme not in ADDRESS_SCHEMES or address_key(url) is None:
        return None
    return url


def token_origin(url):
    """(scheme, host, port) of an address that an account's token may be sent to: https, or plain http to this machine. None for any other,
    so that no credential helper can be scoped to it."""
    if url.host and (url.scheme == "https" or (url.scheme == "http" and url.host in LOOPBACK_HOSTS)):
        return (url.scheme, url.host, url.port)
    return None


def scope_origin(scope):
    """(scheme, host, port) of what a credential helper's key is scoped to, as git spells it in credential.<scope>.helper (already in
    lower case), or None when the scope is anything but a bare http or https origin: a path, wildcard or user information in it, or
    no host. Ports are compared as written."""
    url = gitcred.parse_url(scope)
    if url is None or url.path or url.scheme not in ("https", "http") or not url.host:
        return None
    return (url.scheme, url.host, url.port)


def remote_label(remote):
    """A remote's name for a log line. git also accepts an address as branch.<name>.remote, so a name that is not plainly a name (it has a
    colon, an at sign or any other character an address has, or is long) is not shown: a log line names hosts and never a whole address."""
    return remote if REMOTE_NAME.fullmatch(remote) else "(a name that is not plain)"


def where(url):
    """Where an address points, for a log line: the host (and port), or a plain statement. Never a path, never user information."""
    if url is None:
        return "an address that is not a plain URL"
    if not url.host:
        return "a local file address"
    return "host " + clean(url.host + (":" + url.port if url.port else ""), HOST_LIMIT)


def risky_http(key):
    """True for an http.* key that the clone may not hold (see HTTP_HARMLESS). The variable name is the part after the last dot."""
    name = key.rsplit(".", 1)[1]
    if name in HTTP_HARMLESS:
        return False
    return not (name == "proactiveauth" and key.count(".") >= 2)  # only the form with a url in it, as the kit writes it


def risky_setting(key, value, environ, origin=None):
    """True if this setting of the clone's own configuration is one the update will not run git with. origin is token_origin() of the
    recorded address: a credential helper may be scoped to that origin and to no other (any helper scoped elsewhere, even an empty one,
    is refused: it could hand the token to some other host), and with no origin to scope to (None) no helper may be scoped at all."""
    lowered = key.lower()
    if RISKY_KEYS.fullmatch(lowered):
        return True
    named = REMOTE_KEY.fullmatch(key)  # the name is compared as written: git matches the word it is given to a remote's name exactly
    if named and not PLAIN_REMOTE_NAME.fullmatch(named.group(1)):
        return True  # git reads the address that the fetch names as the NAME of a remote first, so a remote called like an address would be used
    if lowered.startswith("http."):
        return risky_http(lowered)
    match = CREDENTIAL_HELPER.fullmatch(lowered)
    if match:
        scope = match.group(1)
        if scope is None:  # not scoped to one host: it would be asked for every host, so only the empty one that clears the list is fine
            return value != ""
        if origin is None or scope_origin(scope) != origin:
            return True
        return not helper_is_the_kits(value, environ)
    return False


def config_entries(git, clone):
    """(key, value) pairs of the clone's own configuration. Git reads .git/config.worktree only when extensions.worktreeConfig is on."""
    returncode, out, err = git.run("config", "--local", "--list", "-z")
    if returncode != 0:
        raise Stop("failed", "error", "the clone's git settings could not be read (" + git_said(returncode, err) + ")")
    outputs = [out]
    returncode, out, err = git.run("config", "--local", "--bool", "--get", "extensions.worktreeConfig")
    if returncode not in (0, 1):
        raise Stop("failed", "error", "the clone's git settings could not be read (" + git_said(returncode, err) + ")")
    if returncode == 0 and out.strip() == "true":
        path = os.path.join(clone, git.must("rev-parse", "--git-path", "config.worktree").rstrip("\n"))
        if os.path.lexists(path):
            returncode, out, err = git.run("config", "--file", path, "--list", "-z")
            if returncode != 0:
                raise Stop("failed", "error", "the clone's git settings could not be read (" + git_said(returncode, err) + ")")
            outputs.append(out)
    for out in outputs:
        for entry in out.split("\0"):
            if entry:
                key, _, value = entry.partition("\n")
                yield key, value


def shown_key(key):
    """A key as a log line shows it. The name of a remote is chosen by whoever wrote the clone's settings, and git takes an address as that
    name, so a remote key whose name is not plain is shown without it: a log line names hosts and never a whole address."""
    named = REMOTE_KEY.fullmatch(key)
    if named and not PLAIN_REMOTE_NAME.fullmatch(named.group(1)):
        return "remote.(a name that is not plain)." + named.group(2)
    return key


def untrusted_setting(git, clone, environ, origin):
    """The first key in the clone's own configuration that could run a program or redirect git, or None, as a log line shows it."""
    for key, value in config_entries(git, clone):
        if risky_setting(key, value, environ, origin):
            return shown_key(key)
    return None


def stray_link(clone):
    """The first path under .git/logs or .git/refs that is a link (or, under logs, a file with more than one name), or None.
    Git appends to a reflog in place, so a link there would be followed and git would write into whatever it points to;
    a directory link under refs would send the files git writes there somewhere else."""
    dot_git = os.path.join(clone, ".git")
    for top, files_too in (("logs", True), ("refs", False)):
        base = os.path.join(dot_git, top)
        try:
            info = os.lstat(base)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            return os.path.join(".git", top)
        for folder, dirs, names in os.walk(base, followlinks=False):
            for name in dirs + names:
                path = os.path.join(folder, name)
                try:
                    info = os.lstat(path)
                except FileNotFoundError:  # git removed it while we looked
                    continue
                if stat.S_ISLNK(info.st_mode) or (files_too and stat.S_ISREG(info.st_mode) and info.st_nlink > 1):
                    return os.path.relpath(path, clone)
    return None


def ensure_trusted(git, clone, environ, origin):
    """Stop unless the folder and the clone's own configuration are ones this update will run git with. Called before git reads any
    object (reading a commit that is missing can fetch it from a promisor remote), again right before the fetch, and again before the
    fast-forward, which is the step that runs file filters."""
    path = stray_link(clone)
    if path:
        raise Stop("skipped", "untrusted", "the clone has a link where git writes a file (%s); the branch and the work tree were left as they were" % clean(path, 80))
    key = untrusted_setting(git, clone, environ, origin)
    if key:
        raise Stop("skipped", "untrusted", "the clone's own git settings include %s, which can run a program, send git or the token elsewhere or change whom it trusts; "
                   "the branch and the work tree were left as they were" % clean(key, 60))


def lock_in_the_way(clone, branch):
    """The first lock file that would make git half-apply a fast-forward (it updates the work tree and only then finds that it cannot move the branch)."""
    dot_git = os.path.join(clone, ".git")
    for name in ("index.lock", "HEAD.lock", os.path.join("refs", "heads", branch + ".lock")):
        path = os.path.normpath(os.path.join(dot_git, name))
        if path.startswith(dot_git + os.sep) and os.path.lexists(path):
            return os.path.relpath(path, clone)
    return None


def tracking_ref(git, branch):
    """The remote-tracking branch that the clone's own fetch rule says this branch follows (refs/remotes/origin/main), or None when
    there is none, or it is not under refs/remotes/. It is named even when the ref does not exist (yet). The fetch writes it as well
    as the private tip, because the reflog of this ref is what the fork-point logic of the clone, and moved_back below, read."""
    returncode, out, err = git.run("for-each-ref", "--format=%(refname) %(upstream)", "refs/heads/" + branch)
    if returncode != 0:
        return None
    for line in out.splitlines():
        name, _, upstream = line.partition(" ")
        if name == "refs/heads/" + branch and upstream.startswith("refs/remotes/") and upstream != TIP_REF and SAFE_REFSPEC.fullmatch(upstream):
            return upstream
    return None


def moved_back(git, tip, tracking):
    """True when the world's branch used to be somewhere that the clone's HEAD contains and no longer is: the world went back to an
    older commit, or rewrote its history. Only the reflog of the tracking branch can show that, so this is a best effort, and "no"
    also means "cannot tell". Such a clone looks like one with commits that are not pushed, and pushing them would bring back what
    the world removed."""
    if tracking is None:
        return False
    returncode, fork, err = git.run("merge-base", "--fork-point", tracking, "HEAD")
    if returncode != 0 or not OBJECT_ID.fullmatch(fork.strip()):
        return False
    return git.run("merge-base", "--is-ancestor", fork.strip(), tip)[0] == 1


def check_remote(git, remote, recorded):
    """Stop unless the remote that the branch follows has exactly one address in the clone's settings and it is the recorded one (after
    address_key: lower-case scheme and host, no trailing slash or .git). Nothing is fetched from the clone's remote in any case, but a
    clone that was changed to point somewhere else is one the update does not trust, and says where it points (the host, never the
    address, which could hold anything)."""
    shown = remote_label(remote)
    returncode, out, err = git.run("config", "--get-all", "-z", "remote.%s.url" % remote)
    if returncode == 1:
        raise Stop("skipped", "no-upstream", "the remote %s that the branch follows has no address in the clone's settings" % shown)
    if returncode != 0:
        raise Stop("failed", "error", git_said(returncode, err))
    values = out.split("\0")[:-1]  # git ends every value with a NUL
    if len(values) != 1:
        raise Stop("skipped", "untrusted", "the remote %s has %d addresses in the clone's settings, not one; nothing was fetched or changed" % (shown, len(values)))
    configured = gitcred.parse_url(values[0])
    key = address_key(configured) if configured is not None else None
    if key is not None and key == address_key(recorded):
        return
    here, there = where(configured), where(recorded)
    if here == there:  # the same place, so the scheme, the port or the path differs
        raise Stop("skipped", "untrusted", "the clone's remote %s is not the address recorded for this world, although both point to %s (the scheme, port or path "
                   "differs); nothing was fetched or changed" % (shown, here))
    raise Stop("skipped", "untrusted", "the clone's remote %s points to %s, not to %s, where the address recorded for this world is; nothing was fetched or changed"
               % (shown, here, there))


def check_folder(clone):
    if os.path.islink(clone):
        raise Stop("skipped", "untrusted", "the clone folder is a symbolic link")
    if not os.path.isdir(clone):
        raise Stop("skipped", "not-git", "the clone folder does not exist")
    dot_git = os.path.join(clone, ".git")
    if os.path.islink(dot_git):
        raise Stop("skipped", "untrusted", "the .git entry in the clone is a symbolic link")
    if os.path.exists(dot_git) and not os.path.isdir(dot_git):
        raise Stop("skipped", "untrusted", "the .git entry in the clone is a file that points to a git folder somewhere else")


def check_version(git):
    """Older git lacks something this update relies on, and would fail in a way that is hard to read."""
    returncode, out, err = git.run("--version")
    match = GIT_VERSION.match(out) if returncode == 0 else None
    if match and (int(match.group(1)), int(match.group(2))) < MINIMUM_GIT:
        raise Stop("failed", "error", "git %s.%s is older than the %d.%d this update needs" % (match.group(1), match.group(2), *MINIMUM_GIT))


def update(git, clone, address, recorded, environ):
    """The whole update. address is the recorded git address as the caller gave it (what the fetch uses, spelled as recorded) and
    recorded the same parsed by recorded_address. Returns (status, code, text) or raises Stop or GitTimeout."""
    origin = token_origin(recorded)
    check_folder(clone)
    check_version(git)

    returncode, out, err = git.run("rev-parse", "--show-toplevel")
    if returncode != 0:
        raise Stop("skipped", "not-git", "not a git work tree (" + git_said(returncode, err) + ")")
    if os.path.realpath(out.rstrip("\n")) != os.path.realpath(clone):
        raise Stop("skipped", "not-git", "git says the top of the work tree is somewhere else")

    # The clone's settings come first, before the first call that reads an object: git fetches a missing object (HEAD's commit, say) on its
    # own from a promisor remote that the settings name, as this user, and with the token if a helper is scoped to that remote.
    ensure_trusted(git, clone, environ, origin)

    returncode, out, err = git.run("symbolic-ref", "-q", "HEAD")
    if returncode == 1 or (returncode == 0 and not out.startswith("refs/heads/")):
        raise Stop("skipped", "detached", "no branch is checked out")
    if returncode != 0:
        raise Stop("failed", "error", git_said(returncode, err))
    branch = out.strip()[len("refs/heads/"):]
    shown = clean(branch, 60)

    returncode, head, err = git.run("rev-parse", "--verify", "-q", "HEAD^{commit}")
    if returncode != 0:
        if git.run("rev-parse", "--verify", "-q", "refs/heads/" + branch)[0] == 0:  # the branch exists, but what it points to cannot be read
            raise Stop("failed", "error", "branch %s points to a commit that git cannot read; the clone is damaged" % shown)
        raise Stop("skipped", "no-upstream", "branch %s has no commits yet" % shown)
    head = head.strip()
    remote = git.config("branch.%s.remote" % branch)
    merge = git.config("branch.%s.merge" % branch)
    if not remote or not merge:
        raise Stop("skipped", "no-upstream", "branch %s has no upstream" % shown)
    if not SAFE_REMOTE.fullmatch(remote) or not SAFE_REFSPEC.fullmatch(merge):
        raise Stop("skipped", "untrusted", "the upstream settings of branch %s are not usable" % shown)

    ensure_trusted(git, clone, environ, origin)
    check_remote(git, remote, recorded)

    # The fetch names the recorded address and not the remote, so what the clone's settings say about the remote (a proxy, a program
    # to run, another url) does not apply to it. Only url.<base>.insteadOf, the http.* keys and a remote section that is called like the
    # address (git reads the word it is given as the name of a remote first) still could, and all three are refused above.
    # The world's tip goes into a ref of this update's own, and FETCH_HEAD is not written: another git process in the clone
    # can rewrite FETCH_HEAD between our fetch and our read of it, and a link at .git/FETCH_HEAD would be written through.
    # The tracking branch (origin/main) is written in the same fetch. A fetch through the remote's name did that on its own, because
    # the remote's fetch rule matches the branch; a fetch from an address does not, and the reflog of that branch is what moved_back
    # and "git rebase --fork-point" read. It is the ref that git itself names for the branch (for-each-ref %(upstream)), so a clone
    # with an unusual fetch rule gets the right one, and none is written when the rule maps the branch anywhere but under refs/remotes/.
    # The clone's extra notes rule is not used: the fetch names this one branch.
    tracking = tracking_ref(git, branch)
    refspecs = ["+%s:%s" % (merge, TIP_REF)]
    if tracking:
        refspecs.append("+%s:%s" % (merge, tracking))
    returncode, out, err = git.run("fetch", "--no-tags", "--no-recurse-submodules", "--no-write-fetch-head", "--quiet", "--", address, *refspecs)
    if returncode != 0:
        raise Stop("failed", "fetch", git_said(returncode, err))
    tip = git.must("rev-parse", "--verify", "-q", TIP_REF + "^{commit}").strip()
    if not OBJECT_ID.fullmatch(head) or not OBJECT_ID.fullmatch(tip):
        raise Stop("failed", "error", "git gave an answer this tool cannot read")
    if head == tip:
        return "current", "ok", "already at " + tip[:7]

    counts = git.must("rev-list", "--left-right", "--count", "HEAD..." + tip, "--").split()
    if len(counts) != 2 or not all(c.isdigit() for c in counts):
        raise Stop("failed", "error", "git gave an answer this tool cannot read")
    ahead, behind = int(counts[0]), int(counts[1])
    if ahead and behind:
        raise Stop("skipped", "diverged", "the clone has %s the world lacks, and the world has %s the clone lacks" % (plural(ahead, "commit", "commits"), plural(behind, "commit", "commits")))
    if ahead:
        if moved_back(git, tip, tracking):
            raise Stop("skipped", "diverged", "the world moved back or rewrote its history: the clone has %s the world no longer has" % plural(ahead, "commit", "commits"))
        raise Stop("skipped", "ahead", "%s %s not pushed" % (plural(ahead, "local commit", "local commits"), "is" if ahead == 1 else "are"))
    if not behind:
        raise Stop("failed", "error", "git gave an answer this tool cannot read")

    # The fetch took a while, and the clone's files can change in that time: look again, right before the step that runs file filters.
    ensure_trusted(git, clone, environ, origin)
    lock = lock_in_the_way(clone, branch)
    if lock:
        raise Stop("failed", "merge", "a lock file from another git command is in the way (%s); the work tree was not touched" % clean(lock, 80))

    limit = max(git.timeout, MERGE_MINIMUM)
    try:
        returncode, out, err = git.run("merge", "--ff-only", "--quiet", "--no-edit", "--no-overwrite-ignore", tip, timeout=limit)
    except GitTimeout:
        raise Stop("failed", "merge", "the fast-forward ran out of time after %s and was stopped; some files in the clone may be half updated, so run git status" % plural(limit, "second", "seconds"))
    if returncode != 0:
        raise Stop("failed", "merge", git_said(returncode, err))
    if git.must("rev-parse", "--verify", "-q", "HEAD^{commit}").strip() != tip:
        raise Stop("failed", "merge", "git reported success but the branch did not move")
    return "updated", "ok", "%s..%s, %s" % (head[:7], tip[:7], plural(behind, "new commit", "new commits"))


def refresh(clone_arg, address_arg, environ):
    """Run the update and return (status, code, text). Never raises. address_arg is the git address recorded for the world: None, "" and
    "-" mean that none is. Without a usable one nothing is trusted and no git runs (this is decided before any look at the clone)."""
    timeout = timeout_from(environ.get("SDLCA_REFRESH_TIMEOUT"))
    if timeout == 0:
        return "skipped", "off", "SDLCA_REFRESH_TIMEOUT is 0"
    clone = os.path.abspath(clone_arg)
    try:
        if address_arg in (None, "", "-"):
            raise Stop("skipped", "unverified", "no git address is recorded for this world, so git was not run (sdlca-worlds --apply records it)")
        recorded = recorded_address(address_arg)
        if recorded is None:  # the value is not echoed: it could hold anything
            raise Stop("skipped", "unverified", "the git address recorded for this world is not one this update accepts, so git was not run "
                       "(sdlca-worlds --apply records the one Spawn gives)")
        path = safe_path(environ.get("PATH"))
        exe = shutil.which("git", path=path)
        if not exe:
            raise Stop("failed", "error", "git is not installed, or is not on PATH")
        git = Git(os.path.abspath(exe), clone, git_environment(environ, clone), timeout)  # an absolute path: PATH is never searched from inside the clone
        return update(git, clone, address_arg, recorded, environ)
    except Stop as stop:
        return stop.answer
    except GitTimeout:
        return "failed", "timeout", "a git call took longer than %s and was stopped" % plural(timeout, "second", "seconds")
    except Exception as error:  # a refresh problem must never fail a turn
        traceback.print_exc(file=sys.stderr)  # the handler appends this to its log
        return "failed", "error", "the update crashed (%s)" % type(error).__name__


def main(argv=None, environ=None):
    argv = sys.argv[1:] if argv is None else argv
    environ = os.environ if environ is None else environ
    if argv in (["-h"], ["--help"]):
        sys.stderr.write(USAGE)
        return 0
    if len(argv) not in (1, 2) or not argv[0]:
        sys.stderr.write(USAGE)
        return 2
    status, code, text = refresh(argv[0], argv[1] if len(argv) == 2 else None, environ)
    line = "%s\t%s\t%s\n" % (status, code, clean(text, TEXT_LIMIT) or "-")
    sys.stdout.buffer.write(line.encode("utf-8", "replace"))  # bytes: the locale of the caller must not decide
    sys.stdout.buffer.flush()
    return 0


def stop_on_signal(number, frame):
    raise SystemExit(128 + number)  # unwinds through Git.run, which stops the git it started


if __name__ == "__main__":
    for name in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(name, stop_on_signal)
    sys.exit(main())
