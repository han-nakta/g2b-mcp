#!/usr/bin/env python3
"""Run bounded, privacy-safe live G2B MCP smoke checks.

This script is intentionally local-only. It loads a user/operator-owned env file,
requires explicit live opt-in, calls a small matrix of public G2B APIs through the
same sanitizer used by the MCP tools, and prints/stores only privacy-safe summary
metadata. It never prints credential values or authenticated URLs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from g2b_mcp import server
except ModuleNotFoundError:
    # Allow running directly from a source checkout without installing the package.
    from g2b_mcp import server  # type: ignore


SENSITIVE_PATTERNS = {
    "authenticated_url": re.compile(r"https?://[^\s\"<>]+(?:ServiceKey|serviceKey)[^\s\"<>]*", re.I),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone_like": re.compile(r"(?<!\d)(?:0\d{1,2}[- .]?\d{3,4}[- .]?\d{4})(?!\d)"),
    "business_id_like": re.compile(r"(?<!\d)\d{3}[- ]?\d{2}[- ]?\d{5}(?!\d)"),
}


def _yyyymmddhhmm(value: dt.date, end: bool = False) -> str:
    return value.strftime("%Y%m%d") + ("2359" if end else "0000")


def _load_secret_values(env_file: Path | None) -> dict[str, str]:
    """Read candidate secrets for leak scanning. Never print the values."""
    if not env_file or not env_file.exists():
        return {}
    secrets: dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if value and (name == "G2B_SERVICE_KEY" or (name.startswith("G2B_") and name.endswith("_API_KEY"))):
            secrets[name] = value
    return secrets


def _case_summary(case: str, result: dict[str, Any]) -> dict[str, Any]:
    error_obj = result.get("error")
    error: dict[str, Any] = error_obj if isinstance(error_obj, dict) else {}
    status = "pass" if not error and str(result.get("result_code", "")) in {"", "00"} else "error"
    return {
        "case": case,
        "status": status,
        "error_code": error.get("code", ""),
        "service": result.get("service", ""),
        "operation": result.get("operation", ""),
        "category": result.get("category", ""),
        "credential_source": result.get("credential_source", ""),
        "result_code": result.get("result_code", ""),
        "result_msg": result.get("result_msg", ""),
        "total_count": result.get("total_count", ""),
        "item_count": result.get("item_count", ""),
        "sanitized_item_count": len(result.get("sanitized_items") or []),
        "field_name_count": len(result.get("field_names") or []),
    }


def _privacy_scan(rendered_json: str, secrets: dict[str, str]) -> dict[str, Any]:
    exact_leaks = [name for name, value in secrets.items() if value and value in rendered_json]
    regex_hits = {name: len(pattern.findall(rendered_json)) for name, pattern in SENSITIVE_PATTERNS.items()}
    return {
        "secret_exact_leak_count": len(exact_leaks),
        "secret_exact_leak_names": exact_leaks,
        "regex_hits": regex_hits,
        "passed": len(exact_leaks) == 0 and all(count == 0 for count in regex_hits.values()),
    }


def run_smoke(env_file: Path | None, days: int, limit: int, include_items: bool) -> dict[str, Any]:
    if env_file:
        loaded = server.load_env_file(env_file, override=False)
    else:
        loaded = {}
    os.environ["G2B_ENABLE_LIVE_FETCH"] = "1"

    today = dt.date.today()
    start = today - dt.timedelta(days=days)
    start_yyyymmdd = start.strftime("%Y%m%d")
    end_yyyymmdd = today.strftime("%Y%m%d")

    raw_cases: dict[str, dict[str, Any]] = {
        "bid_goods": server.g2b_search_bid_notices("", start_yyyymmdd, end_yyyymmdd, "goods", limit),
        "bid_services": server.g2b_search_bid_notices("", start_yyyymmdd, end_yyyymmdd, "services", limit),
        "bid_works": server.g2b_search_bid_notices("", start_yyyymmdd, end_yyyymmdd, "works", limit),
        "scsbid_goods": server.g2b_search_successful_bids("", start_yyyymmdd, end_yyyymmdd, "goods", limit),
        "contract_goods": server.g2b_search_contracts("", start_yyyymmdd, end_yyyymmdd, "goods", limit),
    }

    statuses = {
        "bid_public_info": server.g2b_check_api_key("bid_public_info"),
        "scsbid_info": server.g2b_check_api_key("scsbid_info"),
        "cntrct_info": server.g2b_check_api_key("cntrct_info"),
    }
    summaries = [_case_summary(name, result) for name, result in raw_cases.items()]
    safe_cases = raw_cases if include_items else {name: _case_summary(name, result) for name, result in raw_cases.items()}

    report = {
        "smoke_version": 1,
        "date_window": {"start": start.isoformat(), "end": today.isoformat(), "days": days},
        "limit_per_call": limit,
        "live_fetch_enabled": True,
        "env_file_used": str(env_file) if env_file else "",
        "env_loaded_names": sorted(loaded.keys()),
        "api_key_status": statuses,
        "case_summaries": summaries,
        "cases": safe_cases,
    }
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True)
    report["privacy_scan"] = _privacy_scan(rendered, _load_secret_values(env_file))
    report["overall_passed"] = all(case["status"] == "pass" for case in summaries) and report["privacy_scan"]["passed"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded live G2B MCP smoke checks without exposing secrets.")
    parser.add_argument("--env-file", type=Path, default=Path.home() / ".config/g2b-mcp/.env", help="Local env file with G2B_SERVICE_KEY or G2B_*_API_KEY values.")
    parser.add_argument("--days", type=int, default=14, help="Lookback window for date-based live queries.")
    parser.add_argument("--limit", type=int, default=2, help="Rows requested per live query; capped by MCP sanitizer at 10.")
    parser.add_argument("--output", type=Path, default=None, help="Optional path to write the safe JSON report.")
    parser.add_argument("--include-sanitized-items", action="store_true", help="Include sanitized item previews in the JSON report. Never includes raw rows.")
    args = parser.parse_args()

    report = run_smoke(args.env_file.expanduser() if args.env_file else None, max(1, args.days), max(1, min(args.limit, 10)), args.include_sanitized_items)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(json.dumps({
            "output": str(args.output),
            "overall_passed": report["overall_passed"],
            "privacy_passed": report["privacy_scan"]["passed"],
            "case_statuses": {case["case"]: case["status"] for case in report["case_summaries"]},
        }, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(text)
    return 0 if report["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
