"""
Graph helpers used by the orchestrator runner.

Pulled into a separate module so the topology + branch-pruning logic
can be unit-tested independently of any I/O.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Set

logger = logging.getLogger(__name__)


def index_nodes(nodes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {n["id"]: n for n in nodes}


def outgoing(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalise a node's connections into a list of dicts."""
    raw = node.get("connections") or []
    out: List[Dict[str, Any]] = []
    for c in raw:
        if isinstance(c, str):
            out.append({"targetId": c})
        elif isinstance(c, dict) and "targetId" in c:
            out.append(c)
    return out


def topological_order(nodes: List[Dict[str, Any]]) -> List[str]:
    """
    Return node ids in topological order, falling back to insertion order
    when no edges are declared (legacy linear workflow).
    """
    if not any(n.get("connections") for n in nodes):
        return [n["id"] for n in nodes]

    indeg: Dict[str, int] = {n["id"]: 0 for n in nodes}
    adj: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    for n in nodes:
        for c in outgoing(n):
            tgt = c["targetId"]
            if tgt in indeg:
                adj[n["id"]].append(tgt)
                indeg[tgt] += 1

    order_index = {n["id"]: i for i, n in enumerate(nodes)}
    ready = sorted([nid for nid, d in indeg.items() if d == 0], key=lambda x: order_index[x])
    out: List[str] = []
    while ready:
        nid = ready.pop(0)
        out.append(nid)
        for tgt in adj[nid]:
            indeg[tgt] -= 1
            if indeg[tgt] == 0:
                ready.append(tgt)
        ready.sort(key=lambda x: order_index[x])

    if len(out) != len(nodes):
        logger.warning("Workflow graph contains a cycle; falling back to insertion order")
        return [n["id"] for n in nodes]
    return out


def reachable_through(
    nodes_by_id: Dict[str, Dict[str, Any]],
    start_ids: Iterable[str],
) -> Set[str]:
    seen: Set[str] = set()
    stack = list(start_ids)
    while stack:
        nid = stack.pop()
        if nid in seen or nid not in nodes_by_id:
            continue
        seen.add(nid)
        for c in outgoing(nodes_by_id[nid]):
            stack.append(c["targetId"])
    return seen
