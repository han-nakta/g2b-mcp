"""Live catalog check: one call per operation, stores ONLY field names/status, never values or the key.

Usage: python scripts/g2b_catalog_live_check.py OUT.json [operation-or-service-slug ...]
Reads G2B_SERVICE_KEY from ~/.config/g2b-mcp/.env. Set WINDOW_DAYS to widen the date window (default 6).
Operations that need identifiers or filters (see docs/catalog-verification.md) may return empty results.
"""

import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

env = {}
for line in (Path.home() / ".config/g2b-mcp/.env").read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env["G2B_SERVICE_KEY"]
cat = json.load(
    open(Path(__file__).resolve().parents[1] / "artifacts" / "catalog.json")
)
only = set(sys.argv[2:]) if len(sys.argv) > 2 else None
out_path = sys.argv[1]
today = dt.date.today()
end = today - dt.timedelta(days=1)
bgn = end - dt.timedelta(days=int(os.environ.get("WINDOW_DAYS", "6")))
pm = today.replace(day=1) - dt.timedelta(days=1)


def fmt(sample, is_end, name=""):
    n = len(re.sub(r"\D", "", sample or ""))
    if n not in (4, 6, 8, 12):
        n = (
            12
            if name.endswith("Dt")
            else 8
            if name.endswith("Date")
            else 6
            if name.endswith("Ym")
            else 4
            if name.endswith("Year")
            else 0
        )
    d = end if is_end else bgn
    if n == 12:
        return d.strftime("%Y%m%d") + ("2359" if is_end else "0000")
    if n == 8:
        return d.strftime("%Y%m%d")
    if n == 6:
        return pm.strftime("%Y%m")
    if n == 4:
        return str(pm.year)
    return sample


def scrub(t):
    return (
        str(t).replace(KEY, "[KEY]").replace(urllib.parse.quote(KEY, safe=""), "[KEY]")
    )


def fieldnames(items):
    names = []
    for it in items:
        if isinstance(it, dict):
            for k in it:
                if k not in names:
                    names.append(k)
    return names


results = []
for s in cat["services"]:
    for o in s["operations"]:
        if only and o["operation"] not in only and s["slug"] not in only:
            continue
        params = {"ServiceKey": KEY, "numOfRows": "1", "pageNo": "1", "type": "json"}
        used = {}
        for p in o["request_params"]:
            n = p["name"]
            if n.lower() in ("servicekey", "numofrows", "pageno", "type"):
                continue
            if not p.get("required") and not re.match(r"inqry(Bgn|End)", n):
                continue
            smp = p.get("sample") or p.get("default") or "1"
            if re.search(r"Bgn", n):
                smp = fmt(p.get("sample"), False, n)
            elif re.search(r"End", n):
                smp = fmt(p.get("sample"), True, n)
            params[n] = smp
            used[n] = smp
        url = o["endpoint"] + "?" + urllib.parse.urlencode(params)
        rec = {
            "service": s["slug"],
            "operation": o["operation"],
            "params_used": sorted(used),
        }
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "g2b-mcp-validate"}),
                timeout=40,
            ) as r:
                body = r.read(5_000_000).decode("utf-8", "replace")
                rec["http"] = r.status
        except urllib.error.HTTPError as e:
            body = e.read(200_000).decode("utf-8", "replace")
            rec["http"] = e.code
        except Exception as e:
            rec.update(status="network_error", detail=scrub(repr(e))[:120])
            results.append(rec)
            continue
        try:
            j = json.loads(body)
            resp = j.get("response", j)
            hdr = resp.get("header", {}) if isinstance(resp, dict) else {}
            b = resp.get("body", {}) if isinstance(resp, dict) else {}
            rec["result_code"] = str(hdr.get("resultCode", ""))
            rec["result_msg"] = scrub(hdr.get("resultMsg", ""))[:80]
            items = b.get("items", []) if isinstance(b, dict) else []
            if isinstance(items, dict):
                items = items.get("item", [])
            if isinstance(items, dict):
                items = [items]
            rec["total_count"] = b.get("totalCount", "") if isinstance(b, dict) else ""
            rec["item_count"] = len(items) if isinstance(items, list) else 0
            rec["response_fields"] = (
                fieldnames(items) if isinstance(items, list) else []
            )
            if not hdr:
                rec["raw_keys"] = list(j)[:5] if isinstance(j, dict) else []
                rec["detail"] = scrub(body)[:160]
        except ValueError:
            rec["result_code"] = (
                re.search(r"<(?:resultCode|returnReasonCode)>([^<]*)", body)
                or [None, ""]
            )[1]
            rec["result_msg"] = scrub(
                (
                    re.search(r"<(?:resultMsg|returnAuthMsg|errMsg)>([^<]*)", body)
                    or [None, ""]
                )[1]
            )[:80]
            rec["non_json"] = True
            rec["detail"] = scrub(re.sub(r"\s+", " ", body))[:160]
        rec["status"] = (
            "ok_data"
            if rec.get("item_count")
            else ("ok_empty" if rec.get("result_code") == "00" else "error")
        )
        cf = [
            f["name"]
            for f in o.get("sample_output_fields", [])
            if f.get("in_reference_doc", True) is not False
        ]
        cfo = [
            f["name"]
            for f in o.get("sample_output_fields", [])
            if f.get("in_reference_doc", True) is False
        ]
        if rec.get("response_fields"):
            rf = set(rec["response_fields"])
            rec["resp_not_in_catalog"] = sorted(rf - set(cf) - set(cfo))
            rec["doc_fields_missing_in_resp"] = sorted(set(cf) - rf)
            rec["catalog_only_fields_seen"] = sorted(set(cfo) & rf)
        results.append(rec)
        time.sleep(0.25)
json.dump(results, open(out_path, "w"), ensure_ascii=False, indent=1)
import collections

print(collections.Counter(r.get("status") for r in results))
