"""Read packaged public-safe G2B artifact JSON files.

The public package intentionally does not include live API credentials, raw cache,
or backfill execution logic.
"""
from __future__ import annotations

from g2b_mcp.server import artifact_dir, load_artifact

__all__ = ["artifact_dir", "load_artifact"]
