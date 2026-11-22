# Optional tools: a setup walkthrough

This page shows the [extension framework](extensions.md) with four real tools: Tripo, Customuse, Playwright MCP and Context7. They are examples. None of them ships with the kit, the kit does not endorse them, and the extension folders for them are yours to write (the [extensions page](extensions.md#writing-an-extension-for-the-community) says how). The examples use the account `lanthief` and the kit in `~/repos/kdtix-open/spawn`. Replace both with yours. Do not paste any key into a chat.

What was run for real on 2026-11-21 is the folder validation and the handler tests. What was not run: a Tripo model, a Customuse call, and a Playwright page, through an agent. The page says so where it matters.

## The four tools

| Tool | What it gives an agent | How it connects | Keys |
| --- | --- | --- | --- |
| Tripo | 3D models from a text prompt, with `tripo make "prompt"` | A command line tool, through the wrapper | The CLI has its own device sign-in; an environment key is optional |
| Customuse | Its service tools | A remote MCP server at `https://api.customuse.com/v1/mcp` | A token, as `Authorization: Bearer ${CUSTOMUSE_TOKEN}` |
| Playwright MCP | A headless browser for public pages | A local MCP server (`@playwright/mcp`) | None |
| Context7 | Current library documentation | A local MCP server (`@upstash/context7-mcp`) | None |

## Where the keys live

Each account has its own folder, so each agent can have its own keys.

```
~/.sdlca/spawn/accounts/lanthief/
  env                       the account's settings (mode 0600)
  extensions                the names of the extensions that are on, one per line
  credentials.d/tripo.env   keys for one extension (mode 0600), as NAME='value' lines
  credentials.d/customuse.env
  mcp.json                  the MCP servers for this account (references only, no keys)
```

`SDLCA_CREDENTIALS_FILE` (see [Configuration](configuration.md#provider-keys)) still works for keys that are not tied to an extension. For an extension, use `credentials.d/<name>.env`: only the names the extension declares are read from it.

## Day zero, tool by tool

For each tool: put its folder in `~/.sdlca/spawn/extensions/<name>/`, then validate it.

```bash
cd ~/repos/kdtix-open/spawn
bin/sdlca-ext validate ~/.sdlca/spawn/extensions/tripo
```

### Tripo

1. In your own shell: `node -v` (20 or later), then `npm install -g tripo-cli`.
2. Sign in as yourself: `tripo login --region ov --no-wait`. It prints a link and a code. Open the link, approve, and run the command again until it says `logged_in`. Then `tripo doctor`.
3. `bin/sdlca-ext enable lanthief tripo`, then `bin/sdlca-ext check lanthief`.
4. Add the rule that `bin/sdlca-ext allow lanthief` prints. It looks like `"Bash($SDLCA_CODE_DIR/bin/sdlca-ext run lanthief tripo -- tripo *)"`. The agent then makes a model with `sdlca-ext run lanthief tripo -- tripo make "a ceramic vase with lilies"`.
5. If the CLI takes a key from the environment, put `TRIPO_API_KEY='...'` in `credentials.d/tripo.env` (check `tripo docs --llm` for the real name). Without one, the CLI uses your sign-in, which the agent can reach because it runs as you.

Each model costs the signed-in Tripo account money. Say so to the people who can ask the agent for one.

### Customuse

1. Put `CUSTOMUSE_TOKEN='...'` in `credentials.d/customuse.env`, then `chmod 600` it.
2. `bin/sdlca-ext enable lanthief customuse`.
3. `bin/sdlca-ext mcp-config lanthief --write` makes `mcp.json`. It holds `Bearer ${CUSTOMUSE_TOKEN}`, never the token.
4. Allow `mcp__customuse` (printed by `allow`) and add `--mcp-config <the mcp.json path> --strict-mcp-config` to `SDLCA_AGENT_CMD`.

If Customuse wants the token without the word `Bearer`, change `headers` in the extension's manifest. The sample at `claude mcp add` in Customuse's text had no `Bearer`; the desktop sample did. We have not found out which the server needs.

### Playwright MCP

1. Install a browser as your own user: `npx playwright install chromium`. This downloads about 200 MB into `~/.cache/ms-playwright/`.
2. The manifest runs `npx -y @playwright/mcp@0.0.86 --headless --isolated --executable-path <chrome>`. `--isolated` gives each run a throwaway profile with no sign-ins, and `--executable-path` names the browser you installed.
3. Enable it, write `mcp.json`, and allow `mcp__playwright`, as above.

The agent may use the browser on public pages and on pages it is testing. It must not drive Spawn's own website: the kit's [rule 11](compliance/spawn-rules.md) forbids scripting a logged-in browser session on Spawn. Page text is untrusted data.

#### Upgrading Playwright MCP

The MCP package and the browser must match. Playwright MCP 0.0.86 is built on a pre-release of Playwright 1.66, which wants a newer Chromium than `npx playwright install` fetches (the install gave Chromium build 1255, for Playwright 1.65.1). That is why the manifest names the browser by path. To move to a newer pair:

1. Find the newest release and what it needs: `npm view @playwright/mcp version` and `npm view @playwright/mcp@<version> dependencies`.
2. Install the matching browser by running the MCP package's own installer, from your own shell, which uses the version it expects: `npx -y @playwright/mcp@<version> --help` shows its options, and its `browser_install` tool installs a browser when it is missing (look for the browser path it prints, under `~/.cache/ms-playwright/`).
3. Edit the manifest: the `@playwright/mcp@<version>` pin and the `--executable-path` (run `ls ~/.cache/ms-playwright/`, and use the `chrome` file under the newest `chromium-<number>/chrome-linux64/`).
4. `bin/sdlca-ext validate <folder>`, then try it once with `npx -y @playwright/mcp@<version> --headless --isolated --executable-path <chrome>` and stop it with Ctrl-C.

We did not run steps 1 and 2 ourselves; 3 and 4 are what the framework checks. A stable release of Playwright MCP may not need `--executable-path` at all.

### Context7

Enable it, write `mcp.json`, and allow `mcp__context7`. It needs no key.

## Putting it together in the account's settings

```bash
SDLCA_MCP_FILE=/home/you/.sdlca/spawn/accounts/lanthief/mcp.json
PATH=/home/you/.nvm/versions/node/v24.16.0/bin:$PATH     # so npx, node and tripo are found under systemd
SDLCA_AGENT_CMD='claude -p --setting-sources user --permission-mode acceptEdits --mcp-config $SDLCA_MCP_FILE --strict-mcp-config --allowedTools "Read(//tmp/*.png)" "Glob" "Grep" "Bash(git *)" "Bash(spawn *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-say *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-api *)" "Bash($SDLCA_CODE_DIR/bin/sdlca-look *)" <the output of sdlca-ext allow>'
```

Quote every rule that has a space or a bracket, because the handler runs the command with `bash -c`. A rule such as `Bash(tripo *)` without quotes is a syntax error and the agent will not start.

## Troubleshooting

| What you see | What it means |
| --- | --- |
| `extension is not valid or its key file is unsafe` in `handler.log` | Run `bin/sdlca-ext list lanthief`. A key file with mode 644 is the usual cause. |
| `... is not installed or not on PATH` from `check` or `run` | The service's `PATH` lacks the tool. Add its folder to `PATH` in the account's `env`. |
| An MCP server shows as failed | Run its `npx` line by hand with the same arguments, and read the error. |
| The agent says it has no such tool | The rule from `allow` is not in `SDLCA_AGENT_CMD`, or `--mcp-config` is missing. |

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
