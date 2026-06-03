"""Public-safe G2B MCP server.

This module serves the packaged JSON artifacts only. It intentionally does not
perform live G2B API calls, does not read operator caches, and does not expose raw
rows. The public server is designed as a catalog/status/evidence surface for MCP
clients.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

try:  # Optional at import time so artifact tests can run without MCP installed.
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - depends on optional runtime dependency
    FastMCP = None  # type: ignore[assignment]

SENSITIVE_FIELD_PATTERNS = {
    "contact_or_email": re.compile(r"(email|e[-_]?mail|mail)", re.I),
    "contact_or_phone": re.compile(r"(tel|phone|fax|mobile|전화|팩스)", re.I),
    "officer_or_contact_person": re.compile(r"(officer|manager|담당|contact)", re.I),
    "representative_person": re.compile(r"(rprsnt|representative|대표자|대표)", re.I),
    "address": re.compile(r"(address|addr|주소)", re.I),
    "business_registration_identifier": re.compile(r"(bizno|사업자|business.*number)", re.I),
}

PUBLIC_SAFE_NOTICE = {
    "mode": "public_safe_artifact_server",
    "no_live_fetch": True,
    "no_raw_rows": True,
    "no_credentials": True,
    "privacy_boundary": "Returns catalog/schema/status/evidence summaries only. Sensitive-capable field names are summarized by category/count where practical.",
}


def artifact_dir() -> Path:
    """Return artifact directory, preferring explicit env override."""
    env = os.environ.get("G2B_ARTIFACT_DIR")
    candidates = []
    if env:
        candidates.append(Path(env))
    here = Path(__file__).resolve()
    candidates.extend([
        Path.cwd() / "artifacts",
        here.parent / "artifacts",  # wheel-installed artifact location
        here.parents[2] / "artifacts",  # editable checkout from src/g2b_mcp/server.py
        here.parents[3] / "artifacts" if len(here.parents) > 3 else here.parents[2] / "artifacts",
    ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_artifact(name: str) -> Any:
    path = artifact_dir() / name
    return json.loads(path.read_text(encoding="utf-8"))


def _services() -> list[dict[str, Any]]:
    return load_artifact("catalog.json").get("services", [])


def _find_service(service: str) -> dict[str, Any]:
    wanted = service.strip()
    for svc in _services():
        if wanted in {svc.get("slug"), svc.get("service_no"), svc.get("name_en"), svc.get("name_ko")}:
            return svc
    raise KeyError(f"Unknown G2B service: {service}")


def _find_operation(service: dict[str, Any], operation: str) -> dict[str, Any]:
    wanted = operation.strip()
    for op in service.get("operations", []) or []:
        if wanted in {op.get("operation"), op.get("name_ko"), op.get("endpoint")}:
            return op
    raise KeyError(f"Unknown operation for {service.get('slug')}: {operation}")


def _sensitive_categories(fields: list[str]) -> dict[str, int]:
    counts = {name: 0 for name in SENSITIVE_FIELD_PATTERNS}
    for field in fields:
        for category, pattern in SENSITIVE_FIELD_PATTERNS.items():
            if pattern.search(str(field)):
                counts[category] += 1
    return {k: v for k, v in counts.items() if v}


def _field_name(field: Any) -> str:
    if isinstance(field, dict):
        return str(field.get("name") or field.get("field") or field.get("id") or "")
    return str(field)


def _safe_service_summary(svc: dict[str, Any]) -> dict[str, Any]:
    return {
        "service_no": svc.get("service_no", ""),
        "slug": svc.get("slug", ""),
        "name_ko": svc.get("name_ko", ""),
        "name_en": svc.get("name_en", ""),
        "operation_count": len(svc.get("operations", []) or []),
        "catalog_status": svc.get("catalog_status", ""),
        "formats": svc.get("formats", []),
        "api_key_env": svc.get("api_key_env", ""),
    }


def _safe_operation_summary(op: dict[str, Any], include_fields: bool = False) -> dict[str, Any]:
    response_fields = [_field_name(f) for f in (op.get("sample_output_fields", []) or [])]
    sensitive = _sensitive_categories(response_fields)
    safe = {
        "operation": op.get("operation", ""),
        "name_ko": op.get("name_ko", ""),
        "endpoint": op.get("endpoint", ""),
        "status": op.get("status", ""),
        "auth_param": op.get("auth_param", ""),
        "date_format": op.get("date_format", ""),
        "request_param_count": len(op.get("request_params", []) or []),
        "response_field_count": len(response_fields),
        "sensitive_field_count": sum(sensitive.values()),
        "sensitive_field_categories": sensitive,
        "daily_traffic_limit": op.get("daily_traffic_limit", ""),
        "notes": op.get("notes", ""),
    }
    if include_fields:
        safe["request_params"] = op.get("request_params", []) or []
        safe["safe_response_field_names"] = [f for f in response_fields if f and not _sensitive_categories([f])]
    return safe


def g2b_list_services() -> dict[str, Any]:
    """List the 18 packaged G2B OpenAPI service summaries."""
    services = [_safe_service_summary(svc) for svc in _services()]
    return {"service_count": len(services), "services": services, "privacy": PUBLIC_SAFE_NOTICE}


def g2b_list_operations(service: str) -> dict[str, Any]:
    """List public-safe operation summaries for one service."""
    svc = _find_service(service)
    operations = [_safe_operation_summary(op) for op in svc.get("operations", []) or []]
    return {"service": _safe_service_summary(svc), "operation_count": len(operations), "operations": operations, "privacy": PUBLIC_SAFE_NOTICE}


def g2b_describe_operation(service: str, operation: str, include_fields: bool = False) -> dict[str, Any]:
    """Describe one operation without exposing credentials or raw rows."""
    svc = _find_service(service)
    op = _find_operation(svc, operation)
    return {"service": _safe_service_summary(svc), "operation": _safe_operation_summary(op, include_fields=include_fields), "privacy": PUBLIC_SAFE_NOTICE}


def g2b_graph_list_entities() -> dict[str, Any]:
    """List ontology/data-graph entities from the packaged dictionary."""
    artifact = load_artifact("entity_dictionary.json")
    entities = artifact.get("entities", {})
    compact = {
        name: {
            "description_ko": info.get("description_ko", ""),
            "candidate_field_count": info.get("candidate_field_count", 0),
        }
        for name, info in entities.items()
    }
    return {"entity_count": len(compact), "entities": compact, "privacy": PUBLIC_SAFE_NOTICE}


def g2b_graph_query_join_map(entity: str = "", source_service: str = "", target_service: str = "") -> dict[str, Any]:
    """Query packaged join-map candidates by entity/source/target."""
    join_map = load_artifact("join_map.json")
    mappings = join_map.get("mappings", [])
    if entity:
        mappings = [m for m in mappings if m.get("entity") == entity]
    if source_service:
        mappings = [m for m in mappings if m.get("source", {}).get("service") == source_service]
    if target_service:
        mappings = [m for m in mappings if m.get("target", {}).get("service") == target_service]
    return {"mapping_count": len(mappings), "mappings": mappings, "thresholds": join_map.get("thresholds", {}), "privacy": PUBLIC_SAFE_NOTICE}


def _relationship_graph() -> dict[str, Any]:
    return load_artifact("relationship_evidence_graph.json")


def g2b_graph_list_relationships(status: str = "", source: str = "", target: str = "") -> dict[str, Any]:
    """List packaged relationship-evidence graph edges."""
    graph = _relationship_graph()
    edges = graph.get("edges", [])
    if status:
        edges = [edge for edge in edges if edge.get("status") == status]
    if source:
        edges = [edge for edge in edges if edge.get("source") == source]
    if target:
        edges = [edge for edge in edges if edge.get("target") == target]
    return {"id": graph.get("id"), "status_values": graph.get("status_values", []), "edge_count": len(edges), "edges": edges, "privacy": graph.get("privacy", PUBLIC_SAFE_NOTICE)}


def g2b_graph_get_edge_evidence(edge_id: str) -> dict[str, Any]:
    """Return one relationship edge and its public-safe evidence."""
    graph = _relationship_graph()
    for edge in graph.get("edges", []):
        if edge.get("id") == edge_id:
            return {"id": graph.get("id"), "edge": edge, "privacy": graph.get("privacy", PUBLIC_SAFE_NOTICE)}
    raise KeyError(f"Unknown relationship edge: {edge_id}")


def g2b_graph_list_unresolved_edges() -> dict[str, Any]:
    """List unresolved/candidate relationship edges that need bounded follow-up."""
    graph = _relationship_graph()
    statuses = {"candidate", "lookup_candidate", "unresolved"}
    edges = [edge for edge in graph.get("edges", []) if edge.get("status") in statuses]
    return {"id": graph.get("id"), "edge_count": len(edges), "edges": edges, "privacy": graph.get("privacy", PUBLIC_SAFE_NOTICE)}


def g2b_dataset_status() -> dict[str, Any]:
    """Return packaged/public-safe dataset status when available.

    The public skeleton may not include live dataset state. In that case return a
    clear not-live marker instead of reading private operator cache.
    """
    path = artifact_dir() / "dataset_status.json"
    if not path.exists():
        return {
            "state": "not_packaged",
            "message": "No dataset_status.json is packaged in this public repo. Live/operator dataset state remains local-only.",
            "required_datasets": ["bid_notices", "successful_bids", "contracts"],
            "privacy": PUBLIC_SAFE_NOTICE,
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("privacy", PUBLIC_SAFE_NOTICE)
    return data


def g2b_ontology_list_nodes() -> dict[str, Any]:
    ontology = load_artifact("ontology_pack.json")
    nodes = ontology.get("nodes", {})
    return {"node_count": len(nodes), "nodes": nodes, "pack": ontology.get("pack", {}), "privacy": ontology.get("privacy", PUBLIC_SAFE_NOTICE)}


def g2b_ontology_list_edges(source: str = "", target: str = "", relationship: str = "") -> dict[str, Any]:
    ontology = load_artifact("ontology_pack.json")
    edges = ontology.get("edges", [])
    if source:
        edges = [edge for edge in edges if edge.get("source") == source]
    if target:
        edges = [edge for edge in edges if edge.get("target") == target]
    if relationship:
        edges = [edge for edge in edges if edge.get("relationship") == relationship]
    return {"edge_count": len(edges), "edges": edges, "pack": ontology.get("pack", {}), "privacy": ontology.get("privacy", PUBLIC_SAFE_NOTICE)}


def g2b_privacy_boundary() -> dict[str, Any]:
    """Explain what this public MCP server will and will not expose."""
    return {
        **PUBLIC_SAFE_NOTICE,
        "excluded": [
            "API key values and authenticated URLs",
            "raw G2B response rows and operator caches",
            "contacts, phone numbers, emails, addresses, business registration identifiers",
            "exact supplier/award-party operational detail beyond packaged evidence summaries",
            "live backfill or broad collection execution",
        ],
        "included": [
            "service and operation catalog metadata",
            "schema/request/response field summaries",
            "relationship evidence summaries",
            "ontology node/edge summaries",
            "dataset-state marker or public-safe packaged status",
        ],
    }


def _tool_functions() -> list[Callable[..., dict[str, Any]]]:
    return [
        g2b_list_services,
        g2b_list_operations,
        g2b_describe_operation,
        g2b_graph_list_entities,
        g2b_graph_query_join_map,
        g2b_graph_list_relationships,
        g2b_graph_get_edge_evidence,
        g2b_graph_list_unresolved_edges,
        g2b_dataset_status,
        g2b_ontology_list_nodes,
        g2b_ontology_list_edges,
        g2b_privacy_boundary,
    ]


def create_mcp_server(host: str = "127.0.0.1", port: int = 8000, stateless_http: bool = True):
    """Create a FastMCP server with public-safe G2B tools."""
    if FastMCP is None:
        raise RuntimeError("mcp package is not installed; install with `pip install 'g2b-procurement-intelligence[mcp]'`")
    mcp = FastMCP(
        "g2b-procurement-intelligence",
        instructions="Public-safe G2B procurement catalog, evidence graph, ontology, and dataset status MCP server. Does not expose raw rows or credentials.",
        host=host,
        port=port,
        streamable_http_path="/mcp",
        stateless_http=stateless_http,
        json_response=True,
    )
    for func in _tool_functions():
        mcp.tool()(func)
    return mcp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the public-safe G2B MCP server")
    parser.add_argument("--mode", choices=["stdio", "sse", "streamable-http", "http"], default="stdio")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--artifact-dir", default=os.environ.get("G2B_ARTIFACT_DIR", ""))
    args = parser.parse_args(argv)
    if args.artifact_dir:
        os.environ["G2B_ARTIFACT_DIR"] = args.artifact_dir
    transport = "streamable-http" if args.mode == "http" else args.mode
    server = create_mcp_server(host=args.host, port=args.port, stateless_http=(transport == "streamable-http"))
    server.run(transport=transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
