# SPDX-License-Identifier: Apache-2.0
"""Git settings that give a clone one account's token, for Spawn's git host only.

It also holds the one parser for a git address, so that the two programs that care what an address is agree: sdlca-worlds
records a world's git address (only one that passes recordable), and lib/refresh.py holds a clone to that record.
"""
import collections
import re
import shlex

# scheme, host (lower case), port and path as written, and "host[:port]" as written, of an address that is plain scheme://host[:port]/path.
GitUrl = collections.namedtuple("GitUrl", "scheme host port path authority")

URL_LIMIT = 2048  # a git address is far shorter; nothing longer is looked at
VISIBLE_ASCII = re.compile(r"[\x21-\x7e]+")  # no space, no control character, nothing outside ASCII (fullmatch: "$" would accept a trailing newline)
URL_SHAPE = re.compile(
    r"([A-Za-z][A-Za-z0-9+.-]*)://"  # the scheme
    r"((?:[A-Za-z0-9][A-Za-z0-9._-]*|\[[0-9A-Fa-f:.]+\])?)"  # a host name or IPv4 address, or an IPv6 address in brackets; empty only for file:///path
    r"(?::([0-9]{1,5}))?"  # a port
    r"((?:/[^?#\\]*)?)"  # a path: no query, no fragment and no backslash. No "@" before the path, so no user information
)


def parse_url(raw):
    """Split a git address of the plain form scheme://host[:port]/path, or None for anything else: user information, a query or a
    fragment, a backslash, a space or control character, a character outside ASCII, a port that is not 1 to 65535, a missing host (except
    in file:///path), a text of more than 2048 characters, or not a string at all. The scheme and the host are lower-cased; the port and
    the path stay as written. Nothing here is cleverer than a person reading the address: whatever it cannot split plainly is refused."""
    if not isinstance(raw, str) or len(raw) > URL_LIMIT or not VISIBLE_ASCII.fullmatch(raw):
        return None
    match = URL_SHAPE.fullmatch(raw)
    if match is None:
        return None
    scheme, host, port, path = match.groups()
    scheme = scheme.lower()
    if port is not None and not 1 <= int(port) <= 65535:
        return None
    if not host and (scheme != "file" or port is not None):
        return None
    authority = host + (":" + port if port is not None else "")
    return GitUrl(scheme, host.lower(), port or "", path, authority)


def credential_scope(git_url):
    """The scope a credential helper is attached to for this address, https://host[:port] as it is written, or None when the address
    cannot carry one: it is not https, it has no host, or it has user information in it. A clone of such an address gets no helper, and
    sdlca-worlds records no git address for it (the clone of a world is held to the address Spawn gave for it, and only an address that
    can carry the account's token is one the kit works with)."""
    url = parse_url(git_url)
    if url is None or url.scheme != "https" or not url.host:
        return None
    return "https://" + url.authority


def has_dot_segment(path):
    """True when the path of an address has a . or .. segment, spelled out or percent-encoded (%2e). A client or a server may resolve such a
    segment, so the address could mean another place than its text says, and two programs cannot compare it by its text."""
    for segment in path.rstrip("/").split("/"):
        if segment.replace("%2e", ".").replace("%2E", ".") in (".", ".."):
            return True
    return False


def recordable(git_url):
    """True for an address that sdlca-worlds records and that lib/refresh.py will hold a clone to: one that credential_scope accepts (https,
    a host, no user information) and whose path has no dot segment. The two programs share this rule, so that nothing is recorded that the
    update would only refuse later."""
    url = parse_url(git_url)
    return url is not None and credential_scope(git_url) is not None and not has_dot_segment(url.path)


def helper_command(username, token_file):
    """A git credential helper that answers with this account's name and the token read from its file."""
    return "!f() { echo username=%s; echo password=$(cat %s); }; f" % (shlex.quote(username), shlex.quote(token_file))


def clone_config(git_url, username, token_file):
    """`key=value` settings for `git clone --config`.

    The helper is attached to the git host of THIS url only (credential.https://host.helper), not to every
    remote, so git never offers the token to any other host: a hostile submodule, LFS or remote URL in a
    world gets no credentials. An empty `credential.helper=` first makes git forget any helper from the
    global or system configuration. Anything that is not an https url (a local path in a test) gets no helper.
    """
    scope = credential_scope(git_url)
    config = ["credential.helper="]
    if scope:
        config.append("credential.%s.helper=%s" % (scope, helper_command(username, token_file)))
        config.append("http.%s.proactiveAuth=basic" % scope)
    config.append("remote.origin.fetch=+refs/notes/*:refs/notes/*")
    return config
