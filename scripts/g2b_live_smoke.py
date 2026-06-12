#!/usr/bin/env python3
"""Checkout-friendly wrapper for the packaged g2b-live-smoke command."""

from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
src = repo_root / "src"
if src.exists():
    sys.path.insert(0, str(src))

from g2b_mcp.live_smoke import main  # type: ignore[import-not-found]


if __name__ == "__main__":
    raise SystemExit(main())
