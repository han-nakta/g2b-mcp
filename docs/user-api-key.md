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

Do not commit real values to this repository. Keep real values in one of:

- a local shell environment
- an ignored `.env` file
- a secret manager
- an MCP client/server configuration that is not committed

## Hermes MCP configuration example

For the current public-safe artifact server, no key is required:

```yaml
mcp_servers:
  g2b:
    command: "g2b-mcp"
    args: ["--mode", "stdio"]
```

For v0.3 opt-in live-read mode, pass the key explicitly to that trusted local process through the MCP client's environment configuration:

```yaml
mcp_servers:
  g2b_live_local:
    command: "g2b-mcp"
    args: ["--mode", "stdio", "--enable-live-fetch"]
    env:
      G2B_SERVICE_KEY: "put-your-own-local-key-here"
```

The `--enable-live-fetch` flag sets `G2B_ENABLE_LIVE_FETCH=1` inside the server process. Live summaries are bounded (`numOfRows` capped at 10), sanitized, and never include full authenticated URLs or raw rows.

## Safety rules for future live tools

Any future live-fetch feature should keep these rules:

1. Default MCP startup remains public-safe and keyless.
2. Live fetch requires an explicit opt-in flag or separate command.
3. API keys are read from environment variables only.
4. Tool output must never include the key, authenticated URL, raw rows, contact values, or private cache paths.
5. Live tools should return small status/count/schema summaries by default.
6. Broad backfill remains a local operator workflow, not a public default MCP action.
7. Tests must verify that no credential values or authenticated URLs appear in public artifacts, logs, or tool responses.

## Practical user-facing wording

Use this wording in release notes or onboarding:

> You do not need a G2B API key to use the current public MCP alpha. The alpha is a read-only catalog/evidence server over packaged public-safe artifacts. If you later enable optional live API checks or local collection, obtain your own data.go.kr/G2B service key and provide it only through your local environment, never through committed files or shared prompts.
