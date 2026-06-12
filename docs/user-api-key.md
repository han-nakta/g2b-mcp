# User API key and live-fetch posture

This repository's default MCP alpha is a **public-safe artifact server**. It does not need a user's G2B/data.go.kr API key for the default MCP tools. v0.3 also includes an explicit opt-in live-read alpha for small user-owned lookups.

## Default alpha behavior

The packaged server answers from JSON artifacts included in the package:

- OpenAPI service and operation catalog
- request/response field summaries
- relationship evidence summaries
- ontology summary artifacts
- a public-safe dataset-status marker, when packaged

It intentionally does **not** perform live API requests, read private operator caches, or expose raw rows. Therefore, a user can install and run the default alpha MCP server without any API key.

## When a user needs an API key

A user needs their own API key only for **opt-in live workflows**, such as:

- live smoke checks against data.go.kr/G2B OpenAPI endpoints
- collecting or refreshing local private cache
- generating private derived artifacts from newly fetched data

Those workflows must run in the user's local/private environment and require `--enable-live-fetch`. Without that flag, live tools return `LIVE_FETCH_DISABLED` and do not make network requests.

## Recommended credential model

Use environment variables rather than CLI arguments, config files committed to git, or full request URLs.

Recommended variable name for live tooling:

```text
G2B_SERVICE_KEY
```

`G2B_SERVICE_KEY` is preferred. If it is not set, v0.3 may use a service-specific catalog variable such as `G2B_BID_PUBLIC_INFO_API_KEY` when that variable is already present. Tool output reports only whether a key is configured and which env name was used; it never returns the key value.

## Hidden-prompt setup wizard

For users who do not want to paste a key into shell history or MCP chat prompts, use the local setup wizard:

```bash
g2b-mcp --setup-api-key
```

The prompt hides input with `getpass`, writes `G2B_SERVICE_KEY` to `~/.config/g2b-mcp/.env` by default, and sets that file to mode `0600`. The command returns only status metadata such as the env file path and never echoes the key.

To use a custom location:

```bash
g2b-mcp --setup-api-key --api-key-env-file ~/.config/g2b-mcp/private.env
g2b-mcp --mode stdio --enable-live-fetch --api-key-env-file ~/.config/g2b-mcp/private.env
```

The MCP server auto-loads the env file at startup, but live network calls still require explicit `--enable-live-fetch`. Existing process environment variables take precedence over file values.

Do not commit real values to this repository. Keep real values in one of:

- a local shell environment
- the hidden-prompt wizard's local `0600` env file
- an ignored `.env` file
- a secret manager
- an MCP client/server configuration that is not committed

## Local-secret smoke testing

After setup, users or maintainers can run the repeatable local live smoke script. This is intentionally skipped in CI because it requires a real local API key.

```bash
g2b-live-smoke \
  --env-file ~/.config/g2b-mcp/.env \
  --days 14 \
  --limit 2 \
  --output /tmp/g2b_live_smoke_matrix.json
```

The matrix covers:

- bid notices: goods, services, works
- successful-bid summaries: goods
- contract summaries: goods

The script enables live fetch only inside its own process, caps row requests, writes only sanitized summaries, and fails if the safe JSON report contains exact secret values, authenticated URLs, email-like values, phone-like values, or business-id-like values.

Docker live smoke uses the same rule: load the env file, mount it read-only for leak scanning, and never paste the key into the command line.

```bash
docker run --rm \
  --env-file ~/.config/g2b-mcp/.env \
  -v ~/.config/g2b-mcp/.env:/tmp/g2b.env:ro \
  g2b-procurement-intelligence \
  g2b-live-smoke --env-file /tmp/g2b.env --days 7 --limit 2
```

## Hermes MCP configuration example

For the current public-safe artifact server, no key is required:

```yaml
mcp_servers:
  g2b:
    command: "g2b-mcp"
    args: ["--mode", "stdio"]
```

For v0.3 opt-in live-read mode after running `g2b-mcp --setup-api-key`, the server can load the local env file automatically:

```yaml
mcp_servers:
  g2b_live_local:
    command: "g2b-mcp"
    args: ["--mode", "stdio", "--enable-live-fetch"]
```

The `--enable-live-fetch` flag sets `G2B_ENABLE_LIVE_FETCH=1` inside the server process. If the key was not saved with the setup wizard, pass `G2B_SERVICE_KEY` through the trusted MCP client's private environment configuration. Live summaries are bounded (`numOfRows` capped at 10), sanitized, and never include full authenticated URLs or raw rows.

## Safety rules for future live tools

Any future live-fetch feature should keep these rules:

1. Default MCP startup remains public-safe and keyless.
2. Live fetch requires an explicit opt-in flag or separate command.
3. API keys are read from environment variables or the local 0600 env file created by `--setup-api-key`.
4. Tool output must never include the key, authenticated URL, raw rows, contact values, or private cache paths.
5. Live tools should return small status/count/schema summaries by default.
6. Broad backfill remains a local operator workflow, not a public default MCP action.
7. Tests must verify that no credential values or authenticated URLs appear in public artifacts, logs, or tool responses.

## Practical user-facing wording

Use this wording in release notes or onboarding:

> You do not need a G2B API key to use the current public MCP alpha. The alpha is a read-only catalog/evidence server over packaged public-safe artifacts. If you later enable optional live API checks or local collection, obtain your own data.go.kr/G2B service key and provide it only through your local environment, never through committed files or shared prompts.
