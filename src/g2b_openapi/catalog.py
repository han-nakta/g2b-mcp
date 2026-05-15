"""Read packaged public-safe G2B artifact JSON files.

This skeleton intentionally does not include live API credentials, raw cache,
or backfill execution logic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def artifact_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "artifacts"


def load_artifact(name: str) -> Any:
    path = artifact_dir() / name
    return json.loads(path.read_text(encoding="utf-8"))
