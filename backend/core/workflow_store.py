"""
Persistent CRUD for saved workflow graphs.

Workflows are stored as JSON files under ``data/workflows/``. The shape
mirrors the frontend ``SavedWorkflow`` type so callers can round-trip a
graph without translation.

A workflow is a list of nodes; each node has an id, type, label, tier,
optional config (rules, schema, conditions, etc.) and optional
``connections`` describing edges to other nodes.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _gen_workflow_id() -> str:
    return f"wf-{_now_ms()}-{uuid.uuid4().hex[:8]}"


VALID_NODE_TYPES = {
    "upload",
    "ocr",
    "parse",
    "classify",
    "extract",
    "split",
    "condition",
    "validate",
    "script",
}


def _sanitize_node(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Drop runtime-only fields and validate node shape."""
    if "id" not in raw or "type" not in raw:
        raise ValueError("Each node must have 'id' and 'type'")
    if raw["type"] not in VALID_NODE_TYPES:
        raise ValueError(f"Unknown node type: {raw['type']}")

    keep_keys = {
        "id",
        "type",
        "label",
        "x",
        "y",
        "tier",
        "config",
        "connections",
        "inactive",
    }
    cleaned: Dict[str, Any] = {k: v for k, v in raw.items() if k in keep_keys}

    # Normalise connections: the frontend used to allow bare strings; coerce
    # everything to ``{"targetId": ..., "outputIndex": ...}``.
    connections = cleaned.get("connections")
    if isinstance(connections, list):
        normalised = []
        for c in connections:
            if isinstance(c, str):
                normalised.append({"targetId": c})
            elif isinstance(c, dict) and "targetId" in c:
                normalised.append(
                    {
                        "targetId": c["targetId"],
                        **({"outputIndex": c["outputIndex"]} if "outputIndex" in c else {}),
                    }
                )
        cleaned["connections"] = normalised

    return cleaned


class WorkflowStore:
    """Thread-safe, file-backed CRUD for saved workflow graphs."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir
        self._lock = threading.RLock()
        self._index: Dict[str, Dict[str, Any]] = {}
        os.makedirs(self._base_dir, exist_ok=True)
        self._load_existing()

    # -------------------------------------------------------------------
    # Persistence helpers
    # -------------------------------------------------------------------
    def _path_for(self, wf_id: str) -> str:
        return os.path.join(self._base_dir, f"{wf_id}.json")

    def _load_existing(self) -> None:
        try:
            for fname in os.listdir(self._base_dir):
                if not fname.endswith(".json"):
                    continue
                full = os.path.join(self._base_dir, fname)
                try:
                    with open(full, "r", encoding="utf-8") as f:
                        record = json.load(f)
                    wid = record.get("id")
                    if not wid:
                        continue
                    self._index[wid] = record
                except Exception as e:
                    logger.warning("Failed to load workflow file %s: %s", full, e)
        except FileNotFoundError:
            pass

    def _write(self, record: Dict[str, Any]) -> None:
        path = self._path_for(record["id"])
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
        os.replace(tmp, path)

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------
    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._index.values())
        items.sort(key=lambda r: r.get("updatedAt", 0), reverse=True)
        return [self._summary(r) for r in items]

    @staticmethod
    def _summary(record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": record["id"],
            "name": record.get("name"),
            "description": record.get("description"),
            "createdAt": record.get("createdAt"),
            "updatedAt": record.get("updatedAt"),
            "nodeCount": len(record.get("nodes", [])),
        }

    def get(self, wf_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._index.get(wf_id)
            return json.loads(json.dumps(record)) if record else None

    def create(
        self,
        *,
        name: str,
        nodes: List[Dict[str, Any]],
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not name.strip():
            raise ValueError("Workflow name is required")
        cleaned_nodes = [_sanitize_node(n) for n in nodes]
        now = _now_ms()
        record = {
            "id": _gen_workflow_id(),
            "name": name.strip(),
            "description": (description or "").strip() or None,
            "nodes": cleaned_nodes,
            "createdAt": now,
            "updatedAt": now,
        }
        with self._lock:
            self._index[record["id"]] = record
            self._write(record)
        return record

    def update(
        self,
        wf_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            current = self._index.get(wf_id)
            if not current:
                return None
            updated = dict(current)
            if name is not None:
                if not name.strip():
                    raise ValueError("Workflow name cannot be empty")
                updated["name"] = name.strip()
            if description is not None:
                updated["description"] = description.strip() or None
            if nodes is not None:
                updated["nodes"] = [_sanitize_node(n) for n in nodes]
            updated["updatedAt"] = _now_ms()
            self._index[wf_id] = updated
            self._write(updated)
            return updated

    def remove(self, wf_id: str) -> bool:
        with self._lock:
            if wf_id not in self._index:
                return False
            del self._index[wf_id]
            try:
                os.remove(self._path_for(wf_id))
            except FileNotFoundError:
                pass
            return True


_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "workflows")
workflow_store = WorkflowStore(_DEFAULT_DIR)
