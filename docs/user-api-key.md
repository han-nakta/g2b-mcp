# User API key and live-fetch posture

This repository's current public MCP alpha is a **public-safe artifact server**. It does not need a user's G2B/data.go.kr API key for the default MCP tools.

## Default alpha behavior

The packaged server answers from JSON artifacts included in the package:

- OpenAPI service and operation catalog
- request/response field summaries
- relationship evidence summaries
- ontology summary artifacts
- a public-safe dataset-status marker, when packaged

It intentionally does **not** perform live API requests, read private operator caches, or expose raw rows. Therefore, a user can install and run the alpha MCP server without any API key.

## When a user needs an API key

A user needs their own API key only for future or separate **opt-in live workflows**, such as:

- live smoke checks against data.go.kr/G2B OpenAPI endpoints
- collecting or refreshing local private cache
- generating private derived artifacts from newly fetched data

Those workflows should run in the user's local/private environment, not in the public default MCP server mode.

## Recommended credential model

Use environment variables rather than CLI arguments, config files committed to git, or full request URLs.

Recommended variable name for future live tooling:

```text
G2B_SERVICE_KEY
```

If an operation or service later requires separate credentials, use service-specific variables documented by that tool, but keep them in the same local-only pattern.

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

If a future opt-in live-fetch mode is added, pass the key explicitly to that trusted local process through the MCP client's environment configuration. Example shape:

```yaml
mcp_servers:
  g2b_live_local:
    command: "g2b-mcp"
    args: ["--mode", "stdio", "--enable-live-fetch"]
    env:
      G2B_SERVICE_KEY: "put-your-own-local-key-here"
```

The `--enable-live-fetch` flag above is an example for a future opt-in mode; it is not part of the current alpha server.

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
