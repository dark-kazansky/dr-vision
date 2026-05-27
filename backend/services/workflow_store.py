"""
In-memory Workflow Store.

Stores workflow definitions (name, description, steps) keyed by UUID.
Thread-safe via a reentrant lock.

This is intentionally simple — no database required.
For persistence across restarts, replace with a file-backed or DB store.
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class WorkflowNotFoundError(Exception):
    """Raised when a workflow_id does not exist in the store."""
    pass


class WorkflowStore:
    """Thread-safe in-memory store for workflow definitions."""

    def __init__(self) -> None:
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, name: str, description: Optional[str], steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a new workflow and return its full record."""
        workflow_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        record = {
            "workflow_id": workflow_id,
            "name": name,
            "description": description,
            "steps": steps,
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            self._workflows[workflow_id] = record
        return dict(record)

    def get(self, workflow_id: str) -> Dict[str, Any]:
        """Return a workflow record by ID. Raises WorkflowNotFoundError if missing."""
        with self._lock:
            record = self._workflows.get(workflow_id)
        if record is None:
            raise WorkflowNotFoundError(workflow_id)
        return dict(record)

    def list_all(self) -> List[Dict[str, Any]]:
        """Return all workflow records sorted by created_at descending."""
        with self._lock:
            records = list(self._workflows.values())
        return sorted(records, key=lambda r: r["created_at"], reverse=True)

    def update(
        self,
        workflow_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Update fields of an existing workflow. Raises WorkflowNotFoundError if missing."""
        with self._lock:
            record = self._workflows.get(workflow_id)
            if record is None:
                raise WorkflowNotFoundError(workflow_id)
            if name is not None:
                record["name"] = name
            if description is not None:
                record["description"] = description
            if steps is not None:
                record["steps"] = steps
            record["updated_at"] = datetime.now(timezone.utc)
            return dict(record)

    def delete(self, workflow_id: str) -> None:
        """Delete a workflow. Raises WorkflowNotFoundError if missing."""
        with self._lock:
            if workflow_id not in self._workflows:
                raise WorkflowNotFoundError(workflow_id)
            del self._workflows[workflow_id]


# Module-level singleton
workflow_store = WorkflowStore()
