"""
Smoke tests for the workflow orchestrator, workflow store, and run store.

These tests intentionally avoid the LLM-backed node executors and focus
on the pieces that are local logic — graph topology, branch pruning,
condition evaluation routing, persistence and cancellation.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

import pytest

# Ensure backend/ is on the path when running directly with pytest.
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from core.run_store import RunStore  # noqa: E402
from core.workflow_store import WorkflowStore  # noqa: E402
from core import workflow_orchestrator as wo  # noqa: E402


# ---------------------------------------------------------------------------
# Topological order
# ---------------------------------------------------------------------------

def test_topological_order_linear():
    nodes = [
        {"id": "a", "type": "upload", "connections": [{"targetId": "b"}]},
        {"id": "b", "type": "parse", "connections": [{"targetId": "c"}]},
        {"id": "c", "type": "classify"},
    ]
    assert wo._topological_order(nodes) == ["a", "b", "c"]


def test_topological_order_falls_back_when_no_edges():
    nodes = [
        {"id": "a", "type": "upload"},
        {"id": "b", "type": "parse"},
    ]
    assert wo._topological_order(nodes) == ["a", "b"]


def test_topological_order_handles_branching():
    nodes = [
        {"id": "u", "type": "upload", "connections": [{"targetId": "p"}]},
        {"id": "p", "type": "parse", "connections": [{"targetId": "x"}, {"targetId": "y"}]},
        {"id": "x", "type": "classify"},
        {"id": "y", "type": "extract"},
    ]
    order = wo._topological_order(nodes)
    assert order.index("u") < order.index("p")
    assert order.index("p") < order.index("x")
    assert order.index("p") < order.index("y")


# ---------------------------------------------------------------------------
# Reachability used for branch pruning
# ---------------------------------------------------------------------------

def test_reachable_through_set():
    nodes = {
        "a": {"id": "a", "connections": [{"targetId": "b"}, {"targetId": "c"}]},
        "b": {"id": "b", "connections": [{"targetId": "d"}]},
        "c": {"id": "c"},
        "d": {"id": "d"},
    }
    assert wo._reachable_through(nodes, ["b"]) == {"b", "d"}
    assert wo._reachable_through(nodes, ["c"]) == {"c"}


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------

def test_evaluate_condition_matched_index():
    node = {
        "type": "condition",
        "config": {
            "conditions": [
                {"operator": "equals", "value": "Invoice"},
                {"operator": "equals", "value": "Receipt"},
            ],
            "field_name": "document_type",
        },
    }
    previous = {"document_type": "Receipt"}
    assert wo._evaluate_condition(node, previous) == 1


def test_evaluate_condition_else_branch():
    node = {
        "type": "condition",
        "config": {
            "conditions": [{"operator": "equals", "value": "Invoice"}],
            "field_name": "document_type",
        },
    }
    previous = {"document_type": "Other"}
    assert wo._evaluate_condition(node, previous) is None


# ---------------------------------------------------------------------------
# Run store
# ---------------------------------------------------------------------------

def test_run_store_create_update_finish_persists(tmp_path):
    store = RunStore(str(tmp_path))
    record = store.create(
        workflow_id=None,
        workflow_name="Test",
        input_files=["a.pdf"],
        nodes=[{"id": "n1", "label": "Parse", "type": "parse"}],
    )
    rid = record["id"]
    assert record["status"] == "queued"

    store.start(rid)
    store.update_node(rid, "n1", status="running", started_at=1)
    store.update_node(rid, "n1", status="completed", finished_at=2, output_summary="ok")
    store.finish(rid, status="completed")

    fetched = store.get(rid)
    assert fetched["status"] == "completed"
    assert fetched["nodes"][0]["status"] == "completed"
    assert fetched["nodes"][0]["outputSummary"] == "ok"

    # Reload from disk
    store2 = RunStore(str(tmp_path))
    fetched2 = store2.get(rid)
    assert fetched2["status"] == "completed"


def test_run_store_marks_stale_running_runs_failed_on_reload(tmp_path):
    store = RunStore(str(tmp_path))
    record = store.create(
        workflow_id=None,
        workflow_name="Stale",
        input_files=[],
        nodes=[{"id": "n1", "label": "Parse", "type": "parse"}],
    )
    rid = record["id"]
    store.start(rid)
    # Simulate crash: don't call finish.

    store2 = RunStore(str(tmp_path))
    fetched = store2.get(rid)
    assert fetched["status"] == "failed"
    assert "interrupted" in (fetched.get("error") or "")


def test_run_store_cancel_request(tmp_path):
    store = RunStore(str(tmp_path))
    record = store.create(
        workflow_id=None,
        workflow_name="Cancel",
        input_files=[],
        nodes=[{"id": "n1", "label": "Parse", "type": "parse"}],
    )
    rid = record["id"]
    store.start(rid)
    assert store.request_cancel(rid) is True
    assert store.is_cancel_requested(rid) is True
    # Cannot cancel a finished run.
    store.finish(rid, status="completed")
    assert store.request_cancel(rid) is False


# ---------------------------------------------------------------------------
# Workflow store
# ---------------------------------------------------------------------------

def test_workflow_store_round_trip(tmp_path):
    store = WorkflowStore(str(tmp_path))
    nodes = [
        {"id": "u1", "type": "upload", "label": "Upload", "tier": "Normal"},
        {"id": "p1", "type": "parse", "label": "Parse", "tier": "Normal", "connections": ["u1"]},
    ]
    record = store.create(name="Demo", nodes=nodes, description="example")
    assert record["nodes"][1]["connections"] == [{"targetId": "u1"}]

    fetched = store.get(record["id"])
    assert fetched["name"] == "Demo"

    updated = store.update(record["id"], name="Demo v2")
    assert updated["name"] == "Demo v2"

    # Reload from disk
    store2 = WorkflowStore(str(tmp_path))
    again = store2.get(record["id"])
    assert again["name"] == "Demo v2"

    assert store.remove(record["id"]) is True
    assert store.get(record["id"]) is None


def test_workflow_store_rejects_invalid_node():
    store = WorkflowStore(tempfile.mkdtemp())
    with pytest.raises(ValueError):
        store.create(name="Bad", nodes=[{"id": "x", "type": "made_up"}])
