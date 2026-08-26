"""
Smoke tests for the shared run/workflow stores and condition evaluator.
"""

from __future__ import annotations

import pytest

from dr_vision_msbe import (
    Condition,
    ConditionEvaluator,
    ConditionOperator,
    RunStore,
    WorkflowStore,
)


def test_workflow_store_round_trip(tmp_path):
    store = WorkflowStore(str(tmp_path))
    record = store.create(
        name="Demo",
        nodes=[
            {"id": "u", "type": "upload"},
            {"id": "p", "type": "parse", "connections": ["u"]},
        ],
        description="example",
    )
    fetched = store.get(record["id"])
    assert fetched["nodes"][1]["connections"] == [{"targetId": "u"}]

    store.update(record["id"], name="Demo v2")
    again = store.get(record["id"])
    assert again["name"] == "Demo v2"

    assert store.remove(record["id"]) is True
    assert store.get(record["id"]) is None


def test_workflow_store_rejects_invalid_node(tmp_path):
    store = WorkflowStore(str(tmp_path))
    with pytest.raises(ValueError):
        store.create(name="Bad", nodes=[{"id": "x", "type": "made_up"}])


def test_run_store_create_finish(tmp_path):
    store = RunStore(str(tmp_path))
    rec = store.create(
        workflow_id=None,
        workflow_name="Test",
        input_files=["a.pdf"],
        nodes=[{"id": "n1", "label": "Parse", "type": "parse"}],
    )
    rid = rec["id"]
    store.start(rid)
    store.update_node(rid, "n1", status="running", started_at=1)
    store.update_node(rid, "n1", status="completed", finished_at=2, output_summary="ok")
    store.finish(rid, status="completed")
    fetched = store.get(rid)
    assert fetched["status"] == "completed"
    assert fetched["nodes"][0]["status"] == "completed"


def test_run_store_marks_stale_running_runs_failed_on_reload(tmp_path):
    store = RunStore(str(tmp_path))
    rec = store.create(
        workflow_id=None,
        workflow_name="Stale",
        input_files=[],
        nodes=[{"id": "n1", "label": "Parse", "type": "parse"}],
    )
    rid = rec["id"]
    store.start(rid)
    # Simulate crash: do not finish.
    store2 = RunStore(str(tmp_path))
    fetched = store2.get(rid)
    assert fetched["status"] == "failed"
    assert "interrupted" in (fetched.get("error") or "")


def test_condition_evaluator_branches():
    ev = ConditionEvaluator()
    res = ev.evaluate_from_previous_result(
        {"document_type": "Invoice"},
        [Condition(operator=ConditionOperator.EQUALS, value="Invoice")],
    )
    assert res.success and res.matched_index == 0

    res = ev.evaluate_from_previous_result(
        {"document_type": "Other"},
        [Condition(operator=ConditionOperator.EQUALS, value="Invoice")],
    )
    assert res.success and res.matched_index is None
