# Data Boundary

## Included in this public repository

- G2B OpenAPI service and operation catalog metadata.
- Request/response schema summaries and operation notes.
- Public-safe relationship evidence graph summaries.
- Public-safe ontology node/edge summaries.
- MCP tool contracts and runbook documentation.

## Excluded from this public repository

- Live API credentials or authenticated URLs.
- Raw G2B rows and local operator caches.
- Backfill checkpoints and bronze/silver/gold datasets.
- Contact/person/address/business-registration field values.
- Any exact operational data that can identify private parties beyond already-packaged public-safe summaries.

## Runtime behavior

The public MCP server reads packaged JSON artifacts from `./artifacts` or `G2B_ARTIFACT_DIR` by default, and it does not need a user API key in default alpha mode. v0.3 live-read tools require explicit `--enable-live-fetch` opt-in plus a user-owned local environment key, and return only bounded sanitized summaries. If dataset status is not packaged, the server returns a `not_packaged` marker instead of reading private local state.

User-owned G2B/data.go.kr API keys are only for opt-in live workflows. They must stay in the user's local environment, secret manager, or the local `0600` env file created by `g2b-mcp --setup-api-key`, and must never be committed, logged, or returned in MCP tool output. See `docs/user-api-key.md` for the intended credential model.
