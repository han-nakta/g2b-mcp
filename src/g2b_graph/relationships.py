"""Relationship evidence helpers over packaged public-safe artifacts."""
from __future__ import annotations

from typing import Any

from g2b_mcp.server import g2b_graph_get_edge_evidence, g2b_graph_list_relationships


def list_relationships(status: str = "") -> list[dict[str, Any]]:
    return g2b_graph_list_relationships(status=status)["edges"]


__all__ = ["list_relationships", "g2b_graph_get_edge_evidence", "g2b_graph_list_relationships"]
