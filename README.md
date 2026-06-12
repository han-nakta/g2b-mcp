# G2B Procurement Intelligence

Privacy-safe MCP/package boundary for a G2B/Nara procurement OpenAPI catalog, relationship evidence graph, ontology artifacts, and dataset-status surface.

> **Status: v0.2 public MCP artifact alpha + v0.3 opt-in live-read alpha.** Default mode is still the keyless, public-safe artifact server. v0.3 adds bounded live lookup tools only when the local user explicitly starts the server with `--enable-live-fetch` and provides their own API key through environment variables. The repo does not include raw rows, credentials, operator cache, or live backfill execution.

## What this does

Ask an MCP-capable assistant questions like:

```text
"What G2B OpenAPI services are available?"
"Show operations for bid_public_info."
"Describe getBidPblancListInfoThng without exposing credentials."
"Which relationship edges are unresolved?"
"What is this repo allowed to expose publicly?"
```

The server answers from packaged, public-safe artifacts. It is useful for API discovery, schema explanation, relationship-evidence inspection, and publication-boundary checks.

## Current baseline

- 18 G2B-related OpenAPI services / 191 operations cataloged.
- API-01~17 representative evidence phase closed in the private operator workspace.
- API-18 `pub_prcrmnt_stat_info` remains `unresolved_period_stat` until public OpenAPI rows are verified.
- Public MCP server exposes packaged catalog/schema/evidence summaries only.
- Vercel/Supabase-style product surfaces remain deferred until the MCP and public/private boundaries stay stable.

## Example flows

### 1. Explore the API catalog

```text
g2b_list_services()
g2b_list_operations(service="bid_public_info")
g2b_describe_operation(service="bid_public_info", operation="getBidPblancListInfoThng")
```

Use this when an agent needs to understand which G2B operation, date format, or response schema applies before writing code.

### 2. Inspect relationship evidence

```text
g2b_graph_list_relationships(status="unresolved")
g2b_graph_get_edge_evidence(edge_id="...")
g2b_graph_query_join_map(entity="BidNotice")
```

Use this to see how bid notices, successful bids, contracts, organizations, products, and related entities are connected without exposing row-level values.

### 3. Check publication safety

```text
g2b_privacy_boundary()
g2b_dataset_status()
```

Use this to confirm that the public server is not reading private operator cache or returning raw rows. If no sanitized dataset-status artifact is packaged, `g2b_dataset_status()` returns a `not_packaged` marker.

## What is included

```text
artifacts/
  catalog.json
  entity_dictionary.json
  graph_schema.json
  join_map.json
  relationship_evidence_graph.json
  ontology_pack.json
docs/
  mcp-tool-contract.md
  example-queries.md
  publication-plan.md
  runbooks/api-01-bid-public-info-operator.md
src/
  g2b_mcp/server.py
  g2b_openapi/
  g2b_graph/
tests/
```

## Privacy boundary

Included:

- catalog/schema metadata
- service and operation descriptions
- relationship status/evidence summaries
- ontology node/edge summaries
- public-safe runbooks and tool contracts

Excluded:

- API keys or credentials
- `.env` files with real values
- full authenticated request URLs
- raw G2B response rows
- `cache/`, raw/bronze/silver/gold data
- 담당자명, 전화번호, 이메일, 주소, 사업자등록번호 등 PII 가능 field values

See [DATA_BOUNDARY.md](DATA_BOUNDARY.md) and [SECURITY.md](SECURITY.md).

## Install

From a local checkout:

```bash
python3 -m pip install -e .
# Optional MCP runtime support:
python3 -m pip install -e '.[mcp]'
```

## API keys

You do **not** need a G2B/data.go.kr API key to use the default MCP alpha. The default server is a read-only artifact server: it answers from packaged catalog/evidence JSON and does not perform live API calls.

v0.3 includes an opt-in live-read alpha for small user-owned lookups. To use it, run the local MCP process with `--enable-live-fetch` and set `G2B_SERVICE_KEY` in the process environment. If `G2B_SERVICE_KEY` is absent, the server may use a service-specific catalog env name such as `G2B_BID_PUBLIC_INFO_API_KEY` when that variable is already present. Tool outputs never return key values or full authenticated URLs.

For a safer local setup flow, run the hidden-prompt wizard:

```bash
g2b-mcp --setup-api-key
```

The wizard saves only to the user's local env file, defaulting to `~/.config/g2b-mcp/.env` with file mode `0600`. The MCP server auto-loads that file at startup, while live calls still require explicit `--enable-live-fetch`.

See [docs/user-api-key.md](docs/user-api-key.md).

## Run as MCP server

STDIO mode:

```bash
g2b-mcp --mode stdio
```

Streamable HTTP mode:

```bash
g2b-mcp --mode streamable-http --host 127.0.0.1 --port 8000
# endpoint: http://127.0.0.1:8000/mcp
```

Use a custom artifact directory if needed:

```bash
G2B_ARTIFACT_DIR=/path/to/public-safe/artifacts g2b-mcp --mode stdio
```

## Docker

```bash
docker build -t g2b-procurement-intelligence .
docker run --rm -p 8000:8000 g2b-procurement-intelligence
```

For a local-only Docker live smoke with your own secret env file, do **not** copy keys into the repo or command line. Mount/load the env file read-only and keep live fetch explicit:

```bash
docker run --rm \
  --env-file ~/.config/g2b-mcp/.env \
  -v ~/.config/g2b-mcp/.env:/tmp/g2b.env:ro \
  g2b-procurement-intelligence \
  g2b-live-smoke --env-file /tmp/g2b.env --days 7 --limit 2
```

The smoke script calls only bounded summary reads and reports whether privacy checks passed. It does not print key values, authenticated URLs, or raw rows.

### Opt-in live-read mode

Bounded live reads require both a user-owned key and an explicit flag:

```bash
G2B_SERVICE_KEY="your-local-data-go-kr-key" g2b-mcp --mode stdio --enable-live-fetch
```

Or use the hidden-prompt setup wizard first, then start live mode without putting the key in shell history:

```bash
g2b-mcp --setup-api-key
g2b-mcp --mode stdio --enable-live-fetch
```

Without `--enable-live-fetch`, live tools return `LIVE_FETCH_DISABLED` and make no network request. Live responses are capped, summarized, and sanitized; they do not return raw rows, key values, or authenticated URLs.

## Public MCP tools

Artifact/catalog tools:

- `g2b_list_services`
- `g2b_list_operations`
- `g2b_describe_operation`
- `g2b_api_key_setup_instructions`
- `g2b_check_api_key`
- `g2b_validate_operation_params`
- `g2b_build_safe_request_preview`
- `g2b_call_operation_summary`
- `g2b_search_bid_notices`
- `g2b_graph_list_entities`
- `g2b_graph_query_join_map`
- `g2b_graph_list_relationships`
- `g2b_graph_get_edge_evidence`
- `g2b_graph_list_unresolved_edges`
- `g2b_dataset_status`
- `g2b_ontology_list_nodes`
- `g2b_ontology_list_edges`
- `g2b_privacy_boundary`

Live read tools are opt-in and bounded. Broad smoke-test campaigns, cache refresh, and backfill remain local/private operator workflows, not public default MCP behavior.

## Local checks

```bash
python3 -m unittest discover -s tests -v
# Run transport integration too when the optional MCP dependency is installed:
python3 -m pip install -e '.[mcp]'
python3 -m unittest tests/test_mcp_transport.py -v
python3 -m py_compile src/g2b_mcp/server.py src/g2b_openapi/catalog.py src/g2b_graph/relationships.py scripts/g2b_live_smoke.py
uv build
git diff --check
```

Optional local-secret live smoke, skipped from CI by design:

```bash
g2b-live-smoke \
  --env-file ~/.config/g2b-mcp/.env \
  --days 14 \
  --limit 2 \
  --output /tmp/g2b_live_smoke_matrix.json
```

The smoke matrix covers bid notices for goods/services/works plus goods successful-bid and contract summaries. It exits non-zero if any bounded live call fails or if exact secret values, authenticated URLs, email-like values, phone-like values, or business-id-like values appear in the safe JSON report.

## Deployment posture

Recommended order:

1. Keep this public MCP artifact server stable and privacy-safe.
2. Add only public-safe derived dataset status or aggregate artifacts.
3. Add HTTP hosting only after credential and raw-row boundaries remain green in tests.
4. Add supplier-oriented recommendation chain tools after the aggregate/query layer is public-safe.
