# Security Policy

## Public boundary

This repository is a public-safe MCP/package boundary for G2B procurement intelligence artifacts. It must not contain:

- API key values, bearer tokens, credentials, or authenticated URLs.
- Raw G2B response rows, operator cache, bronze/silver/gold datasets, or live backfill state.
- 담당자명, 전화번호, 이메일, 주소, 사업자등록번호, or other PII-like values.
- Supplier/award-party raw identifiers beyond packaged evidence summaries.

The MCP server defaults to packaged artifact reads only. It does not perform live fetches or broad collection.

## Reporting issues

If you find a credential, raw row, or privacy-sensitive value in a public artifact, treat it as a security issue and remove it before opening a public issue with details. Use a private channel for sensitive reports.

## Maintainer checklist before release

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile src/g2b_mcp/server.py src/g2b_openapi/catalog.py src/g2b_graph/relationships.py
git diff --check
```
