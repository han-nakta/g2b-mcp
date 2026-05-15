"""Relationship evidence helper placeholders.

Future implementation should wrap artifacts/relationship_evidence_graph.json
without exposing raw rows or PII.
"""
from __future__ import annotations

from g2b_openapi.catalog import load_artifact


def list_relationships(status: str = "") -> list[dict]:
    graph = load_artifact("relationship_evidence_graph.json")
    edges = graph.get("relationships") or graph.get("edges") or []
    if status:
        edges = [edge for edge in edges if edge.get("status") == status]
    return edges
