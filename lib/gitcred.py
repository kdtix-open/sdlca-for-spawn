# SPDX-License-Identifier: Apache-2.0
"""Git settings that give a clone one account's token, for Spawn's git host only."""
import shlex
import urllib.parse


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
    parts = urllib.parse.urlsplit(git_url)
    config = ["credential.helper="]
    if parts.scheme == "https" and parts.hostname and parts.username is None:
        scope = "https://" + parts.netloc
        config.append("credential.%s.helper=%s" % (scope, helper_command(username, token_file)))
        config.append("http.%s.proactiveAuth=basic" % scope)
    config.append("remote.origin.fetch=+refs/notes/*:refs/notes/*")
    return config
