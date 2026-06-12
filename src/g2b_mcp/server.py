"""Public-safe G2B MCP server.

By default this module serves packaged JSON artifacts only. Optional v0.3 live
read tools are enabled only with an explicit flag/environment opt-in and return
bounded, sanitized summaries. The public server does not read operator caches or
expose raw rows, credentials, or authenticated URLs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable

try:  # Optional at import time so artifact tests can run without MCP installed.
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - depends on optional runtime dependency
    FastMCP = None  # type: ignore[assignment]

SENSITIVE_FIELD_PATTERNS = {
    "contact_or_email": re.compile(r"(email|e[-_]?mail|mail)", re.I),
    "contact_or_phone": re.compile(r"(tel|phone|fax|mobile|전화|팩스)", re.I),
    "officer_or_contact_person": re.compile(r"(officer|manager|담당|contact|ofcl|chrg)", re.I),
    "representative_person": re.compile(r"(rprsnt|representative|대표자|대표)", re.I),
    "address": re.compile(r"(address|addr|adrs|주소)", re.I),
    "business_registration_identifier": re.compile(r"(bizno|bizrno|사업자|business.*number|empno)", re.I),
}
SENSITIVE_VALUE_PATTERNS = [
    re.compile(r"https?://[^\s'\"<>]+", re.I),
    re.compile(r"(?:serviceKey|ServiceKey|api[_-]?key|token)=[^&\s'\"<>]+", re.I),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)0\d{1,2}[-. ]?\d{3,4}[-. ]?\d{4}(?!\d)"),
    re.compile(r"(?<!\d)\d{3}[- ]?\d{2}[- ]?\d{5}(?!\d)"),
]

PUBLIC_SAFE_NOTICE = {
    "mode": "public_safe_artifact_server",
    "no_live_fetch": True,
    "no_raw_rows": True,
    "no_credentials": True,
    "privacy_boundary": "Returns catalog/schema/status/evidence summaries only. Sensitive-capable field names are summarized by category/count where practical.",
}

LIVE_PRIVACY_NOTICE = {
    "no_credentials": True,
    "key_exposed": False,
    "no_authenticated_url": True,
    "no_raw_rows": True,
    "sanitized_items_only": True,
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


def _live_fetch_enabled() -> bool:
    return os.environ.get("G2B_ENABLE_LIVE_FETCH", "").strip().lower() in {"1", "true", "yes", "on"}


def _catalog_api_key_envs(svc: dict[str, Any] | None = None) -> list[str]:
    envs = ["G2B_SERVICE_KEY"]
    if svc and svc.get("api_key_env"):
        envs.append(str(svc["api_key_env"]))
    return list(dict.fromkeys(envs))


def _configured_api_key(svc: dict[str, Any] | None = None) -> tuple[str | None, str | None]:
    for env_name in _catalog_api_key_envs(svc):
        value = os.environ.get(env_name, "")
        if value:
            return env_name, value
    return None, None


def _credential_values_for_redaction() -> list[str]:
    values = []
    for env_name, value in os.environ.items():
        if not value:
            continue
        if env_name == "G2B_SERVICE_KEY" or (env_name.startswith("G2B_") and env_name.endswith("_API_KEY")):
            values.append(value)
            try:
                values.append(urllib.parse.quote(value, safe=""))
            except Exception:
                pass
    return sorted(set(values), key=len, reverse=True)


def _redact_sensitive_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    redacted = value
    for secret in _credential_values_for_redaction():
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    for pattern in SENSITIVE_VALUE_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _safe_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_sensitive_text(value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _redact_sensitive_text(str(value))


def _live_privacy() -> dict[str, Any]:
    return {**LIVE_PRIVACY_NOTICE, "live_fetch_enabled": _live_fetch_enabled()}


def _operation_param_names(op: dict[str, Any]) -> set[str]:
    return {str(p.get("name")) for p in op.get("request_params", []) or [] if p.get("name")}


def _auth_param_name(op: dict[str, Any]) -> str:
    return str(op.get("auth_param") or "ServiceKey")


def _coerce_num_rows(value: Any, default: int = 10) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError):
        num = default
    return max(1, min(num, 10))


def _clean_params_for_operation(op: dict[str, Any], params: dict[str, Any], num_rows: int | None = None) -> dict[str, Any]:
    allowed = _operation_param_names(op)
    auth = _auth_param_name(op)
    cleaned: dict[str, Any] = {}
    for key, value in (params or {}).items():
        if key == auth or key.lower() in {"servicekey", "service_key", "api_key", "apikey"}:
            continue
        if key in allowed:
            cleaned[key] = value
    if "pageNo" in allowed:
        cleaned.setdefault("pageNo", 1)
    if "numOfRows" in allowed:
        cleaned["numOfRows"] = _coerce_num_rows(num_rows if num_rows is not None else cleaned.get("numOfRows", 10))
    if "type" in allowed:
        cleaned.setdefault("type", "json")
    return cleaned


def g2b_check_api_key(service: str = "") -> dict[str, Any]:
    """Check whether a user-owned API key is configured without exposing it."""
    svc = _find_service(service) if service else None
    env_name, _value = _configured_api_key(svc)
    return {
        "configured": bool(env_name),
        "configured_env": env_name or "",
        "live_fetch_enabled": _live_fetch_enabled(),
        "key_exposed": False,
        "preferred_env": "G2B_SERVICE_KEY",
        "fallback_envs_considered": [e for e in _catalog_api_key_envs(svc) if e != "G2B_SERVICE_KEY"],
        "privacy": _live_privacy(),
    }


def g2b_validate_operation_params(service: str, operation: str, params: dict[str, Any]) -> dict[str, Any]:
    """Validate params against packaged catalog only; never performs network I/O."""
    svc = _find_service(service)
    op = _find_operation(svc, operation)
    params = params or {}
    auth = _auth_param_name(op)
    allowed = _operation_param_names(op)
    auth_like = {auth, "ServiceKey", "serviceKey", "service_key", "api_key", "apikey"}
    missing = [
        str(p.get("name"))
        for p in op.get("request_params", []) or []
        if p.get("required") and p.get("name") not in auth_like and p.get("name") not in params
    ]
    unknown = [k for k in params if k not in allowed and k not in auth_like]
    auth_policy = {k: "ignored_from_params_use_env" for k in params if k in auth_like}
    return {
        "service": svc.get("slug", service),
        "operation": op.get("operation", operation),
        "valid": not missing and not unknown,
        "missing_required_non_auth_params": missing,
        "unknown_params": unknown,
        "auth_param_policy": auth_policy or {auth: "read_from_env_never_from_params"},
        "hints": {
            "numOfRows_max_for_live_summary": 10,
            "pageNo_default": 1,
            "auth_source": "environment_only",
            "preferred_api_key_env": "G2B_SERVICE_KEY",
            "service_specific_fallback_env": svc.get("api_key_env", ""),
        },
        "privacy": _live_privacy(),
    }


def g2b_build_safe_request_preview(service: str, operation: str, params: dict[str, Any]) -> dict[str, Any]:
    """Build a sanitized request preview without key values or a full authenticated URL."""
    svc = _find_service(service)
    op = _find_operation(svc, operation)
    env_name, _value = _configured_api_key(svc)
    cleaned = _clean_params_for_operation(op, params or {})
    sanitized = dict(cleaned)
    auth = _auth_param_name(op)
    if env_name:
        sanitized[auth] = "[REDACTED_FROM_ENV]"
    return {
        "service": svc.get("slug", service),
        "operation": op.get("operation", operation),
        "endpoint": op.get("endpoint", ""),
        "method": svc.get("method") or "GET",
        "sanitized_params": sanitized,
        "credential_configured": bool(env_name),
        "credential_source": env_name or "",
        "warning": "Preview omits key value and never returns a full authenticated URL.",
        "privacy": _live_privacy(),
    }


def _build_live_url(endpoint: str, params: dict[str, Any], auth_param: str, api_key: str) -> str:
    query = {**params, auth_param: api_key}
    return endpoint + "?" + urllib.parse.urlencode(query)


def _parse_json_or_xml(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"data": parsed}
    except json.JSONDecodeError:
        pass
    root = ET.fromstring(text)

    def elem_to_obj(elem: ET.Element) -> Any:
        children = list(elem)
        if not children:
            return elem.text or ""
        grouped: dict[str, Any] = {}
        for child in children:
            value = elem_to_obj(child)
            if child.tag in grouped:
                if not isinstance(grouped[child.tag], list):
                    grouped[child.tag] = [grouped[child.tag]]
                grouped[child.tag].append(value)
            else:
                grouped[child.tag] = value
        return grouped

    return {root.tag: elem_to_obj(root)}


def _body_items(body: Any) -> list[dict[str, Any]]:
    if not isinstance(body, dict):
        return []
    items = body.get("items", [])
    if isinstance(items, dict) and "item" in items:
        items = items["item"]
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict)]


def _amount_band(value: Any) -> str:
    try:
        amount = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return ""
    if amount < 10_000_000:
        return "under_10m_krw"
    if amount < 100_000_000:
        return "10m_to_100m_krw"
    if amount < 1_000_000_000:
        return "100m_to_1b_krw"
    return "over_1b_krw"


def _sanitize_item(item: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    safe_aliases = {
        "bidNtceNm": "title",
        "ntceInsttNm": "notice_org",
        "dminsttNm": "demand_org",
        "bidNtceDt": "notice_date",
        "opengDt": "notice_date",
        "bidClseDt": "close_date",
        "bsnsDivNm": "procurement_type",
        "cntrctCnclsMthdNm": "procurement_type",
    }
    amount_fields = {"presmptPrce", "asignBdgtAmt", "bdgtAmt", "bssamt"}
    for key, value in item.items():
        if _sensitive_categories([key]):
            continue
        if key in safe_aliases and value not in (None, ""):
            safe[safe_aliases[key]] = _safe_value(value)
        elif key in amount_fields:
            band = _amount_band(value)
            if band:
                safe["amount_band"] = band
        elif key in {"bidNtceNm", "dminsttNm", "bidNtceDt", "bidClseDt"} and value not in (None, ""):
            safe[key] = _safe_value(value)
    return safe


def _summarize_payload(payload: dict[str, Any], request_preview: dict[str, Any]) -> dict[str, Any]:
    response = payload.get("response", payload)
    header = response.get("header", {}) if isinstance(response, dict) else {}
    body = response.get("body", {}) if isinstance(response, dict) else {}
    items = _body_items(body)
    field_names = sorted({str(k) for item in items for k in item.keys() if not _sensitive_categories([str(k)])})
    sanitized_items = [_sanitize_item(item) for item in items[:3]]
    return {
        "result_code": header.get("resultCode") or header.get("result_code") or "",
        "result_msg": _safe_value(header.get("resultMsg") or header.get("result_msg") or ""),
        "total_count": (body.get("totalCount") or body.get("total_count") or 0) if isinstance(body, dict) else 0,
        "item_count": len(items),
        "field_names": field_names[:50],
        "sanitized_items": sanitized_items,
        "request": request_preview,
        "privacy": _live_privacy(),
    }


def g2b_call_operation_summary(service: str, operation: str, params: dict[str, Any], num_rows: int = 10) -> dict[str, Any]:
    """Call one operation only in explicit live mode and return a sanitized summary."""
    svc = _find_service(service)
    op = _find_operation(svc, operation)
    preview = g2b_build_safe_request_preview(service, operation, {**(params or {}), "numOfRows": num_rows})
    if not _live_fetch_enabled():
        return {"error": {"code": "LIVE_FETCH_DISABLED", "message": "Start with --enable-live-fetch to permit bounded live reads."}, "request": preview, "privacy": _live_privacy()}
    env_name, api_key = _configured_api_key(svc)
    if not api_key:
        return {"error": {"code": "API_KEY_NOT_CONFIGURED", "message": "Set G2B_SERVICE_KEY or the service-specific catalog env locally."}, "request": preview, "privacy": _live_privacy()}
    cleaned = _clean_params_for_operation(op, params or {}, num_rows=num_rows)
    preview = g2b_build_safe_request_preview(service, operation, cleaned)
    url = _build_live_url(str(op.get("endpoint", "")), cleaned, _auth_param_name(op), api_key)
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "g2b-mcp/0.3-live-alpha"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = _parse_json_or_xml(response.read())
    except Exception:
        return {
            "error": {
                "code": "LIVE_FETCH_FAILED",
                "message": "Live G2B request failed. Credential values, authenticated URLs, and upstream bodies are intentionally redacted.",
            },
            "request": preview,
            "privacy": _live_privacy(),
        }
    summary = _summarize_payload(payload, preview)
    summary.update({"service": svc.get("slug", service), "operation": op.get("operation", operation)})
    if env_name:
        summary["credential_source"] = env_name
    return summary


def _date_yyyymmddhhmm(value: str, end: bool = False) -> str:
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 8:
        return digits + ("2359" if end else "0000")
    return digits[:12]


def g2b_search_bid_notices(keyword: str, start_date: str, end_date: str, category: str = "goods", limit: int = 10) -> dict[str, Any]:
    """Small opt-in live bid notice search over common notice categories."""
    normalized = (category or "goods").strip().lower()
    operation_by_category = {
        "goods": "getBidPblancListInfoThng",
        "things": "getBidPblancListInfoThng",
        "services": "getBidPblancListInfoServc",
        "service": "getBidPblancListInfoServc",
        "works": "getBidPblancListInfoCnstwk",
        "construction": "getBidPblancListInfoCnstwk",
    }
    operation = operation_by_category.get(normalized, "getBidPblancListInfoThng")
    svc = _find_service("bid_public_info")
    op = _find_operation(svc, operation)
    allowed = _operation_param_names(op)
    params: dict[str, Any] = {"inqryDiv": "1", "inqryBgnDt": _date_yyyymmddhhmm(start_date), "inqryEndDt": _date_yyyymmddhhmm(end_date, end=True), "numOfRows": _coerce_num_rows(limit), "pageNo": 1, "type": "json"}
    keyword_candidates = ["bidNtceNm", "ntceInsttNm", "dminsttNm", "prdctClsfcNoNm"]
    for candidate in keyword_candidates:
        if candidate in allowed and keyword:
            params[candidate] = keyword
            break
    result = g2b_call_operation_summary("bid_public_info", operation, params, num_rows=limit)
    result.setdefault("service", "bid_public_info")
    result.setdefault("operation", operation)
    result["category"] = "goods" if normalized in {"goods", "things"} else normalized
    if keyword and not any(k in allowed for k in keyword_candidates):
        result["keyword_note"] = "No cataloged keyword parameter for this operation; searched by date window only."
    return result


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
        g2b_check_api_key,
        g2b_validate_operation_params,
        g2b_build_safe_request_preview,
        g2b_call_operation_summary,
        g2b_search_bid_notices,
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
    parser.add_argument("--enable-live-fetch", action="store_true", help="Opt in to bounded live reads using a user-owned key from environment")
    args = parser.parse_args(argv)
    if args.artifact_dir:
        os.environ["G2B_ARTIFACT_DIR"] = args.artifact_dir
    if args.enable_live_fetch:
        os.environ["G2B_ENABLE_LIVE_FETCH"] = "1"
    transport = "streamable-http" if args.mode == "http" else args.mode
    server = create_mcp_server(host=args.host, port=args.port, stateless_http=(transport == "streamable-http"))
    server.run(transport=transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
