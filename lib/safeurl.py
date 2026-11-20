# SPDX-License-Identifier: Apache-2.0
"""Small guards for the kit's own HTTP calls, so a token is only ever sent where it should go."""
import re
import urllib.parse
import urllib.request


class _Refuse(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: Python would forward the Authorization header to the new host."""

    def redirect_request(self, *args, **kwargs):
        return None


def read_token(path):
    """The token in a file, or a stop. A token is plain visible ASCII: a line break or quote in the file would end up
    in urllib's error text ("Invalid header value b'Bearer ...'"), which would print the token."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        token = handle.read().strip()
    if not re.fullmatch(r'[\x21\x23-\x5b\x5d-\x7e]{1,4096}', token):  # visible ASCII except " and \
        raise SystemExit("the token file %s does not hold a plain token (a space, line break, quote or backslash is not allowed); store it again with sdlca-token" % path)
    return token


def opener(direct=False):
    """An opener that never follows a redirect. With direct=True it also ignores the proxy settings of the environment: for a plain-http
    origin (this machine only, see check_origin) a proxy would carry the token, in clear text, to another host."""
    handlers = [_Refuse]
    if direct:
        handlers.insert(0, urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(*handlers)


def check_origin(origin, allow_file=False):
    """Accept an https origin, plain http only for this machine, and file:// only when a test asks."""
    parts = urllib.parse.urlsplit(origin)
    if parts.username is not None or parts.password is not None:
        raise SystemExit("refusing to send a token to %r (an origin must not contain user information)" % origin)
    if parts.scheme == "https" and parts.hostname:
        return origin.rstrip("/")
    if parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost"):
        return origin.rstrip("/")
    if allow_file and parts.scheme == "file":
        return origin.rstrip("/")
    raise SystemExit("refusing to send a token to %r (use an https origin)" % origin)
