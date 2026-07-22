"""
Persistent run-history store for the workflow orchestrator.

Stores each run as a JSON file under ``data/workflow_runs/`` so history
survives restarts. The in-memory index is kept thread-safe via a single
lock; updates write through to disk synchronously.

Run schema mirrors what the frontend ``useJobs`` composable expects so
the Jobs tab can swap from localStorage to this backend with no UX change.
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

# Status vocabularies kept aligned with the frontend types in useJobs.ts.
JOB_STATUSES = {"queued", "running", "completed", "failed", "cancelled"}
NODE_STATUSES = {"pending", "running", "completed", "failed", "skipped"}

MAX_LOGS_PER_RUN = 1000


def _now_ms() -> int:
    return int(time.time() * 1000)


def _gen_run_id() -> str:
    return f"run-{_now_ms()}-{uuid.uuid4().hex[:8]}"


class RunStore:
    """
    Thread-safe, file-backed run store.

    Each run is persisted as ``<run_id>.json`` inside ``base_dir``.
    """

    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir
        self._lock = threading.RLock()
        self._index: Dict[str, Dict[str, Any]] = {}
        os.makedirs(self._base_dir, exist_ok=True)
        self._load_existing()

    # -------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------
    def _path_for(self, run_id: str) -> str:
        return os.path.join(self._base_dir, f"{run_id}.json")

    def _load_existing(self) -> None:
        """Populate the in-memory index from disk on construction."""
        try:
            for fname in os.listdir(self._base_dir):
                if not fname.endswith(".json"):
                    continue
                full = os.path.join(self._base_dir, fname)
                try:
                    with open(full, "r", encoding="utf-8") as f:
                        record = json.load(f)
                    rid = record.get("id")
                    if not rid:
                        continue
                    # If the process crashed mid-run, mark stale runs failed.
                    if record.get("status") in {"queued", "running"}:
                        record["status"] = "failed"
                        record["error"] = record.get("error") or "Run interrupted by server restart"
                        record["finishedAt"] = record.get("finishedAt") or _now_ms()
                        self._write(record)
                    self._index[rid] = record
                except Exception as e:
                    logger.warning("Failed to load run file %s: %s", full, e)
        except FileNotFoundError:
            pass

    def _write(self, record: Dict[str, Any]) -> None:
        """Atomic write of a single run record."""
        path = self._path_for(record["id"])
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
        os.replace(tmp, path)

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------
    def create(
        self,
        *,
        workflow_id: Optional[str],
        workflow_name: str,
        input_files: List[str],
        nodes: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Create a new ``queued`` run record and persist it."""
        run_id = _gen_run_id()
        now = _now_ms()
        record: Dict[str, Any] = {
            "id": run_id,
            "workflowId": workflow_id,
            "workflowName": workflow_name,
            "status": "queued",
            "createdAt": now,
            "startedAt": None,
            "finishedAt": None,
            "inputFiles": input_files,
            "nodes": [
                {
                    "nodeId": n["id"],
                    "nodeLabel": n.get("label") or n["id"],
                    "nodeType": n.get("type", "unknown"),
                    "status": "pending",
                    "startedAt": None,
                    "finishedAt": None,
                    "error": None,
                    "outputSummary": None,
                }
                for n in nodes
            ],
            "logs": [
                {
                    "ts": now,
                    "level": "info",
                    "message": f"Run created with {len(nodes)} node(s) and {len(input_files)} file(s)",
                }
            ],
            "error": None,
            "cancelRequested": False,
        }
        with self._lock:
            self._index[run_id] = record
            self._write(record)
        return record

    def get(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._index.get(run_id)
            return json.loads(json.dumps(record)) if record else None

    def list(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        with self._lock:
            items = list(self._index.values())
        items.sort(key=lambda r: r.get("createdAt", 0), reverse=True)
        if status:
            items = [r for r in items if r.get("status") == status]
        total = len(items)
        sliced = items[offset : offset + limit]
        # Strip heavy fields from list responses; full record served via /runs/{id}.
        summaries = [
            {
                "id": r["id"],
                "workflowId": r.get("workflowId"),
                "workflowName": r.get("workflowName"),
                "status": r.get("status"),
                "createdAt": r.get("createdAt"),
                "startedAt": r.get("startedAt"),
                "finishedAt": r.get("finishedAt"),
                "inputFiles": r.get("inputFiles", []),
                "totalNodes": len(r.get("nodes", [])),
                "completedNodes": sum(
                    1 for n in r.get("nodes", []) if n.get("status") in ("completed", "skipped")
                ),
                "failedNodes": sum(
                    1 for n in r.get("nodes", []) if n.get("status") == "failed"
                ),
                "error": r.get("error"),
            }
            for r in sliced
        ]
        return {"total": total, "limit": limit, "offset": offset, "runs": summaries}

    # -------------------------------------------------------------------
    # Mutators
    # -------------------------------------------------------------------
    def start(self, run_id: str) -> None:
        with self._lock:
            record = self._index.get(run_id)
            if not record:
                return
            record["status"] = "running"
            record["startedAt"] = _now_ms()
            self._append_log(record, "info", "Run started")
            self._write(record)

    def update_node(
        self,
        run_id: str,
        node_id: str,
        *,
        status: Optional[str] = None,
        error: Optional[str] = None,
        output_summary: Optional[str] = None,
        started_at: Optional[int] = None,
        finished_at: Optional[int] = None,
    ) -> None:
        with self._lock:
            record = self._index.get(run_id)
            if not record:
                return
            for n in record["nodes"]:
                if n["nodeId"] != node_id:
                    continue
                if status is not None:
                    if status not in NODE_STATUSES:
                        raise ValueError(f"Invalid node status: {status}")
                    n["status"] = status
                if error is not None:
                    n["error"] = error
                if output_summary is not None and n.get("outputSummary") is None:
                    n["outputSummary"] = output_summary
                if started_at is not None:
                    n["startedAt"] = started_at
                if finished_at is not None:
                    n["finishedAt"] = finished_at
                break
            self._write(record)

    def log(
        self,
        run_id: str,
        message: str,
        *,
        level: str = "info",
        node_id: Optional[str] = None,
    ) -> None:
        with self._lock:
            record = self._index.get(run_id)
            if not record:
                return
            self._append_log(record, level, message, node_id=node_id)
            self._write(record)

    def _append_log(
        self,
        record: Dict[str, Any],
        level: str,
        message: str,
        *,
        node_id: Optional[str] = None,
    ) -> None:
        record["logs"].append(
            {
                "ts": _now_ms(),
                "level": level,
                "message": message,
                "nodeId": node_id,
            }
        )
        if len(record["logs"]) > MAX_LOGS_PER_RUN:
            record["logs"] = record["logs"][-MAX_LOGS_PER_RUN:]

    def finish(
        self,
        run_id: str,
        *,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        if status not in {"completed", "failed", "cancelled"}:
            raise ValueError(f"Invalid finish status: {status}")
        with self._lock:
            record = self._index.get(run_id)
            if not record:
                return
            record["status"] = status
            record["finishedAt"] = _now_ms()
            if error:
                record["error"] = error
            self._append_log(
                record,
                "info" if status == "completed" else "error",
                f"Run {status}" + (f": {error}" if error else ""),
            )
            self._write(record)

    def request_cancel(self, run_id: str) -> bool:
        """Mark a running job for cancellation. Returns True if accepted."""
        with self._lock:
            record = self._index.get(run_id)
            if not record:
                return False
            if record["status"] not in {"queued", "running"}:
                return False
            record["cancelRequested"] = True
            self._append_log(record, "warn", "Cancellation requested")
            self._write(record)
            return True

    def is_cancel_requested(self, run_id: str) -> bool:
        with self._lock:
            record = self._index.get(run_id)
            return bool(record and record.get("cancelRequested"))

    def remove(self, run_id: str) -> bool:
        with self._lock:
            if run_id not in self._index:
                return False
            del self._index[run_id]
            try:
                os.remove(self._path_for(run_id))
            except FileNotFoundError:
                pass
            return True

    def remove_finished(self) -> int:
        with self._lock:
            ids = [
                rid
                for rid, rec in self._index.items()
                if rec.get("status") in {"completed", "failed", "cancelled"}
            ]
            for rid in ids:
                self.remove(rid)
            return len(ids)


# Module-level singleton wired to ``backend/data/workflow_runs/``.
_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "workflow_runs")
run_store = RunStore(_DEFAULT_DIR)
