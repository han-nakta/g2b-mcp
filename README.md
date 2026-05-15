# G2B Procurement Intelligence

Privacy-safe package skeleton for a G2B/Nara procurement OpenAPI catalog, relationship evidence graph, ontology artifacts, and future MCP server.

## Status

This repository is a **Ver.1.0 publication skeleton**, not the live operator workspace. The source-of-truth implementation currently remains in the private Hermes/Eva workspace. This skeleton freezes the public package boundary before porting runtime code.

Current baseline:

- 18 G2B-related OpenAPI services / 191 operations cataloged.
- API-01~17 representative evidence phase closed.
- API-18 `pub_prcrmnt_stat_info` remains `unresolved_period_stat` for public OpenAPI rows.
- MCP readiness in the source workspace: 100/100, verdict `mcp_ready_after_restart`.
- Vercel/Supabase are deferred until the local MCP tool contract and artifact schema are stable.

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
  g2b_openapi/
  g2b_graph/
  g2b_mcp/
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
- `.env` files
- full authenticated request URLs
- raw G2B response rows
- `cache/`, raw/bronze/silver/gold data
- 담당자명, 전화번호, 이메일, 주소, 사업자등록번호 등 PII 가능 field values

## MCP Ver.1.0 contract

The first MCP line is read-only and privacy-safe by default:

- API catalog/status
- operation schema/quirk description
- dependency-aware collection plan summary
- dataset/readiness summary
- relationship evidence graph query
- ontology node/edge/query summary
- stabilization/readiness criteria

Live fetch, smoke tests, and backfill are local operator workflows, not public default MCP behavior.

## Relationship status vocabulary

- `verified`: strong live value evidence and stable join key
- `probable`: useful value support with remaining validation caveats
- `candidate`: schema/value candidate before promotion
- `lookup_candidate`: master/reference normalization candidate
- `unresolved`: blocker remains, such as bridge key or public row mismatch
- `reconstructed`: derived from the 17 collected APIs, not the official statistics API

## Local checks

```bash
python3 -m json.tool artifacts/catalog.json >/dev/null
python3 -m pytest
```

## Deployment posture

Do not attach Vercel/Supabase first. The recommended order is:

1. Freeze MCP tool contract and artifact schema.
2. Port runtime code from the Hermes workspace into `src/`.
3. Keep live credentials and raw cache local-only.
4. Add a read-only Vercel dashboard or Supabase public-safe metadata mirror only after the MCP layer is stable.
