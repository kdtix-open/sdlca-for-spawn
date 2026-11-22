# Optional extensions

This page is for the person who runs the SDLCA agent kit and wants an agent to use an outside tool, such as a 3D-model service or a documentation lookup, and for anyone who wants to write such an extension for the community. The kit ships the framework only. It ships no extension, and none is part of the kit: each one lives in its own folder (or its own repository) that you choose to install. Extensions are not made or endorsed by Spawn, or by the makers of the tools they use. The kit is unofficial.

The command is `bin/sdlca-ext`; run `bin/sdlca-ext --help` for every option. A worked example for four real tools is in [Optional tools: setup walkthrough](optional-tools.md).

## What an extension is

A folder in `~/.sdlca/spawn/extensions/<name>/` (the place is `$SDLCA_SPAWN_HOME/extensions`) holding:

| File | What it is |
| --- | --- |
| `extension.json` | The manifest. The only file the kit reads to decide what an extension may do. |
| `README.md` | For people: how to install the tool, what leaves your machine, what it costs, how to keep it up. It must have the headings `## What leaves your machine` and `## Costs`. |
| `prompt.md` | Optional. Up to 4,000 characters for the agent: when to use the tool, and any rule. It goes into the agent's prompt as data. |

### The manifest

```json
{
  "name": "tripo",
  "version": "0.1.0",
  "summary": "Generate 3D models from a text prompt.",
  "homepage": "https://developers.tripo3d.ai/en/docs",
  "license": "Apache-2.0",
  "maintainer": "who looks after it",
  "inject": "wrapper",
  "commands": ["tripo"],
  "credentials": [{ "env": "TRIPO_API_KEY", "url": "https://...", "note": "where to get it", "required": false }],
  "mcp": {},
  "check": ["tripo", "doctor"]
}
```

| Field | Rule |
| --- | --- |
| `name`, `version`, `summary`, `license` | Required. The name is 2 to 32 characters (lowercase letters, digits, hyphens) and equals the folder name. The summary is at most 200 characters. |
| `homepage`, `maintainer` | Optional. A homepage is an https address. |
| `inject` | `wrapper` (the default) or `env`. See [how keys reach the agent](#how-keys-reach-the-agent). |
| `commands` | Bare command names the agent may run. A name that can run other programs or print the environment (`env`, `printenv`, `sh`, `bash`, `python3`, `node`, `npx`, `curl`, `git` and others) is refused. |
| `credentials` | The environment variables the extension needs. Only these names are ever read from its key file. Names starting `SPAWN_`, `SDLCA_`, `GIT_`, `LD_` or `BASH_`, and `PATH`, `HOME` and a few more, are refused. |
| `mcp` | MCP servers, in the shape Claude Code takes: `{"type": "http", "url": "https://...", "headers": {...}}`, or `{"command": "npx", "args": [...], "env": {...}}`. See [MCP servers](#mcp-servers). |
| `check` | A command, as a list of words, that proves the tool works. It must start with one of `commands`. |

Any other field is an error.

## What the kit does, and does not do

The kit does these things, and no others, for an extension:

- It checks the folder with `sdlca-ext validate` every time it uses it.
- It reads the keys the manifest declares from a key file, and nothing else in that file.
- It puts a short description (and `prompt.md`) into the prompt of an agent that has the extension enabled.
- It prints the permission rules and the MCP configuration the manifest implies. You paste or write them yourself.
- It runs the manifest's `check` when you ask, and a listed command through `run`.

It never installs a program, never runs a script from the extension folder, never changes `SDLCA_AGENT_CMD` or an agent's permissions, and never sends anything anywhere. The [security model](security-model.md#optional-extensions) says what an extension can still do once you allow it.

## Day zero: turn an extension on for an account

The examples use the account `alice`, an extension called `demo`, and a key named `DEMO_KEY`.

1. **Install the extension.** Put its folder in `~/.sdlca/spawn/extensions/demo/`, for example with `git clone` of the repository its author publishes. Read its `README.md` and `extension.json` first. Check it: `bin/sdlca-ext validate ~/.sdlca/spawn/extensions/demo`.
2. **Install the tool itself,** as the README says, from your own shell. The kit does not do this.
3. **Put the key in its file.** The file is `~/.sdlca/spawn/accounts/alice/credentials.d/demo.env`, with one `DEMO_KEY='the value'` line per key, and mode 0600 (`chmod 600`). Do not paste a key into a chat. The kit refuses a file that others can read. It also refuses a link, and a value that is not plain text: nothing in the file is expanded, so `$(...)` and backticks are just characters, and an unquoted value with a space or a `$` is an error that names the line (never the value).
4. **Turn it on.** `bin/sdlca-ext enable alice demo` adds the name to `accounts/alice/extensions`. It tells you which keys are still missing.
5. **Check it.** `bin/sdlca-ext check alice` runs the manifest's `check` with the keys. Output is shown with every key value replaced by `[redacted]`.
6. **Allow it.** `bin/sdlca-ext allow alice` prints the permission rules, ready to paste inside the quotes after `--allowedTools` in your `SDLCA_AGENT_CMD`. If the extension has MCP servers, run `bin/sdlca-ext mcp-config alice --write` to make `accounts/alice/mcp.json`, and add `--mcp-config <that file> --strict-mcp-config` to the command too. The kit never does this for you, because widening an agent's permissions is your decision.
7. **Try it.** Ask the agent in chat to use the tool. The agent's prompt lists the extension and how to run it.

## Day n+1: keep it

- **See the state.** `bin/sdlca-ext list alice` shows each installed extension, whether it is on for `alice`, and whether its required keys are present (it never shows a value).
- **Update an extension.** Replace its folder (`git pull` in a clone). The kit validates it again on the next turn. A new manifest that is invalid stops the turn that needs it, with a line in `handler.log`, and the event is kept so you can [replay it](operations.md#replay-a-failed-turn). If the new manifest asks for more commands or servers, run `allow` again and compare.
- **Rotate a key.** Replace the line in the key file. The next turn uses it.
- **Turn it off.** `bin/sdlca-ext disable alice demo`. The key file stays until you delete it.
- **When a turn stops with "an enabled extension is not valid or its key file is unsafe".** Run `bin/sdlca-ext list alice` and `bin/sdlca-ext validate <folder>`; the message names the problem. A key file with mode 644 is the usual cause: `chmod 600` it.

## How keys reach the agent

There are two ways, set by `inject` in the manifest.

- **`wrapper` (the default).** The agent's own environment never holds the key. The agent runs the tool through `sdlca-ext run alice demo -- tool args`, which reads the key and starts that one command with it. Inside an agent turn `run` works only for the turn's own account, only for an enabled extension and only for the commands in its manifest. The permission rule that `allow` prints names that exact form, so an agent cannot use the wrapper to run something else. Limit: the tool itself may keep its own sign-in in your home folder, and the agent runs as you; the wrapper cannot hide that.
- **`env`.** The handler puts the declared keys in the agent's environment for the turn. Use this only when something outside the kit's control reads the key from the environment, which is the case for an MCP server that takes a `${NAME}` value. An agent that may run any command can read its environment, so the rules that `allow` prints are narrow, and you should keep them narrow.

An extension that uses `${NAME}` in an MCP server must use `env`. The validator checks this.

## MCP servers

Servers go in the manifest in the same shape that Claude Code takes, with these limits, so that a manifest can be reviewed in a minute:

- A remote server is `type: "http"` with a plain https address (no user name, query or fragment). A header whose name suggests a secret (`Authorization`, anything with `key`, `token`, `secret` or `cookie`) must take its value from a `${NAME}` that the manifest declares under `credentials`. A secret written into the file is refused.
- A local server runs through `npx`, `uvx` or `bunx`, and its package must be pinned to an exact version (`pkg@1.2.3`), so a new release cannot change what runs. Its `env` values must be exactly `${NAME}`.
- `mcp-config` prints the merged JSON (or writes it with `--write`, refusing to replace a file that exists unless you add `--force`). Two enabled extensions that use the same server name are an error.
- The permission rule for a server is `mcp__<server>`, which allows all of its tools. Treat what a server returns as untrusted data.

## Writing an extension for the community

1. `bin/sdlca-ext scaffold my-tool` makes a folder with a manifest, a README and a prompt, each with `TODO` markers. Edit them.
2. `bin/sdlca-ext validate <folder>` until it says `ok` and shows no warning.
3. In the README, be exact about three things: what is sent to the tool's maker (prompts, files, pictures), who pays and how, and how to remove it. Say that the extension is not made by the tool's maker unless it is.
4. Never put a key, a token, an invite code or a cookie in any file. The validator looks, but it cannot find everything.
5. Do not copy the tool's own text, code, art or logos. A short attributed quote is the limit (25 words or fewer, with a URL), as in the rest of this project. Use the tool's real name only to say what it is.
6. Publish it in a repository of its own. Community extensions are not part of this repository, and the kit does not fetch them: a person clones one on purpose.
7. If your tool needs something the manifest cannot say (a new kind of credential, for instance), open an issue to ask for it rather than working around the validator.

## Limits and what is planned

- One manifest version exists. A field that is added later will be optional.
- The `check` and `commands` rules are guards, not proof of safety. Read the extension before you turn it on.
- A shared index of community extensions is planned. Today you find them by their repository.

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
