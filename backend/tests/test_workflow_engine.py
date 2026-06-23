"""
Unit tests for the Durable Workflow Orchestration Engine.

Tests cover:
- Models and RetryPolicy logic
- State Machine (deterministic replay)
- Scheduler decision logic (via state machine)
- Activity context parsing

Note: Event Store, Task Queue, Timer Service, and Worker tests require
a PostgreSQL connection and are integration tests (run separately with DB).
"""

import pytest
from datetime import datetime, timedelta, timezone


from services.workflow_engine.models import (
    ActivityDefinition,
    ActivityStatus,
    ActivityTask,
    DurableTimer,
    RetryPolicy,
    TaskStatus,
    TimerStatus,
    WorkflowDefinition,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowRunStatus,
)
from services.workflow_engine.retry_policy import (
    aggressive_policy,
    conservative_policy,
    default_policy,
    evaluate_retry,
    get_policy,
    list_policies,
    long_running_policy,
    no_retry_policy,
    ocr_policy,
)
from services.workflow_engine.state_machine import (
    NextActionType,
    StateMachine,
)
from services.workflow_engine.activities.base import (
    ActivityContext,
    ActivityError,
    NonRetryableError,
)


# =============================================================================
# Models Tests
# =============================================================================


class TestRetryPolicyModel:
    """Tests for RetryPolicy model methods."""

    def test_default_values(self):
        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.initial_delay_seconds == 1.0
        assert policy.backoff_multiplier == 2.0

    def test_get_delay_exponential(self):
        policy = RetryPolicy(
            initial_delay_seconds=1.0,
            backoff_multiplier=2.0,
            max_delay_seconds=60.0,
        )
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
        assert policy.get_delay(3) == 8.0

    def test_get_delay_capped(self):
        policy = RetryPolicy(
            initial_delay_seconds=10.0,
            backoff_multiplier=3.0,
            max_delay_seconds=50.0,
        )
        # 10 * 3^2 = 90, capped at 50
        assert policy.get_delay(2) == 50.0

    def test_is_retryable_no_patterns(self):
        policy = RetryPolicy(non_retryable_errors=[])
        assert policy.is_retryable("any error") is True
        assert policy.is_retryable("timeout") is True

    def test_is_retryable_with_patterns(self):
        policy = RetryPolicy(
            non_retryable_errors=["ValidationError", "PermissionDenied"]
        )
        assert policy.is_retryable("some transient error") is True
        assert policy.is_retryable("ValidationError: field required") is False
        assert policy.is_retryable("permissiondenied for user") is False  # case-insensitive

    def test_should_retry_within_limit(self):
        policy = RetryPolicy(max_attempts=3)
        assert policy.should_retry(0, "error") is True
        assert policy.should_retry(1, "error") is True
        assert policy.should_retry(2, "error") is False  # max_attempts - 1

    def test_should_retry_non_retryable_error(self):
        policy = RetryPolicy(
            max_attempts=5,
            non_retryable_errors=["Fatal"],
        )
        assert policy.should_retry(0, "Fatal error occurred") is False
        assert policy.should_retry(0, "Transient error") is True


class TestWorkflowEvent:
    """Tests for WorkflowEvent model."""

    def test_create_event(self):
        event = WorkflowEvent(
            workflow_run_id="abc123",
            sequence_num=1,
            event_type=WorkflowEventType.WORKFLOW_STARTED,
            payload={"input_data": {"file": "test.pdf"}},
        )
        assert event.workflow_run_id == "abc123"
        assert event.sequence_num == 1
        assert event.event_type == WorkflowEventType.WORKFLOW_STARTED
        assert event.payload["input_data"]["file"] == "test.pdf"

    def test_event_timestamp_auto(self):
        event = WorkflowEvent(
            workflow_run_id="x",
            event_type=WorkflowEventType.ACTIVITY_SCHEDULED,
        )
        assert event.timestamp is not None
        assert event.timestamp.tzinfo is not None


class TestActivityTask:
    """Tests for ActivityTask model."""

    def test_defaults(self):
        task = ActivityTask(
            workflow_run_id="run1",
            activity_id="act1",
            activity_type="ocr_parse",
        )
        assert task.status == TaskStatus.PENDING
        assert task.attempt == 0
        assert task.max_attempts == 3
        assert task.timeout_seconds == 300
        assert task.queue_name == "default"

    def test_custom_values(self):
        task = ActivityTask(
            workflow_run_id="run1",
            activity_id="act1",
            activity_type="ocr_extract",
            queue_name="heavy",
            timeout_seconds=600,
            max_attempts=5,
            attempt=2,
        )
        assert task.queue_name == "heavy"
        assert task.timeout_seconds == 600
        assert task.attempt == 2


class TestDurableTimer:
    """Tests for DurableTimer model."""

    def test_is_due_not_yet(self):
        timer = DurableTimer(
            workflow_run_id="run1",
            fire_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert timer.is_due is False

    def test_is_due_past(self):
        timer = DurableTimer(
            workflow_run_id="run1",
            fire_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        assert timer.is_due is True

    def test_is_due_already_fired(self):
        timer = DurableTimer(
            workflow_run_id="run1",
            fire_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            status=TimerStatus.FIRED,
        )
        assert timer.is_due is False


# =============================================================================
# Retry Policy Tests
# =============================================================================


class TestRetryPolicyModule:
    """Tests for the retry_policy module functions."""

    def test_evaluate_retry_should_retry(self):
        policy = default_policy()
        decision = evaluate_retry(policy, attempt=0, error="timeout", add_jitter=False)
        assert decision.should_retry is True
        assert decision.delay_seconds == 1.0

    def test_evaluate_retry_max_attempts(self):
        policy = RetryPolicy(max_attempts=2)
        decision = evaluate_retry(policy, attempt=1, error="error", add_jitter=False)
        assert decision.should_retry is False
        assert "Max attempts" in decision.reason

    def test_evaluate_retry_non_retryable(self):
        policy = RetryPolicy(
            max_attempts=5,
            non_retryable_errors=["ValidationError"],
        )
        decision = evaluate_retry(
            policy, attempt=0, error="ValidationError: bad input", add_jitter=False
        )
        assert decision.should_retry is False
        assert "Non-retryable" in decision.reason

    def test_evaluate_retry_with_jitter(self):
        policy = RetryPolicy(initial_delay_seconds=10.0)
        decision = evaluate_retry(policy, attempt=0, error="err", add_jitter=True)
        # Jitter adds ±25%, so delay should be between 7.5 and 12.5
        assert 7.0 <= decision.delay_seconds <= 13.0

    def test_predefined_policies(self):
        assert default_policy().max_attempts == 3
        assert aggressive_policy().max_attempts == 5
        assert conservative_policy().max_attempts == 2
        assert no_retry_policy().max_attempts == 1
        assert ocr_policy().max_attempts == 3
        assert long_running_policy().max_attempts == 4

    def test_get_policy_by_name(self):
        policy = get_policy("ocr")
        assert policy.max_attempts == 3
        assert "UnsupportedFileType" in policy.non_retryable_errors

    def test_get_policy_unknown(self):
        with pytest.raises(ValueError, match="Unknown retry policy"):
            get_policy("nonexistent")

    def test_list_policies(self):
        policies = list_policies()
        assert "default" in policies
        assert "ocr" in policies
        assert "aggressive" in policies


# =============================================================================
# State Machine Tests
# =============================================================================


class TestStateMachine:
    """Tests for the deterministic state machine replay."""

    def _make_definition(self, activities=None):
        """Helper to create a test workflow definition."""
        if activities is None:
            activities = [
                ActivityDefinition(
                    activity_id="act1",
                    activity_type="ocr_parse",
                    label="Parse Document",
                ),
                ActivityDefinition(
                    activity_id="act2",
                    activity_type="ocr_classify",
                    label="Classify Document",
                    depends_on=["act1"],
                ),
                ActivityDefinition(
                    activity_id="act3",
                    activity_type="ocr_extract",
                    label="Extract Data",
                    depends_on=["act2"],
                ),
            ]
        return WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test Workflow",
            activities=activities,
        )

    def _make_event(self, run_id, seq, event_type, payload=None):
        """Helper to create a test event."""
        return WorkflowEvent(
            workflow_run_id=run_id,
            sequence_num=seq,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            payload=payload or {},
        )

    def test_replay_empty_events(self):
        definition = self._make_definition()
        run = StateMachine.replay([], definition)

        assert run.status == WorkflowRunStatus.PENDING
        assert len(run.activity_states) == 3
        assert run.activity_states["act1"].status == ActivityStatus.PENDING
        assert run.activity_states["act2"].status == ActivityStatus.PENDING
        assert run.activity_states["act3"].status == ActivityStatus.PENDING

    def test_replay_workflow_started(self):
        definition = self._make_definition()
        events = [
            self._make_event("run1", 1, WorkflowEventType.WORKFLOW_STARTED, {
                "input_data": {"file_path": "/test.pdf"},
            }),
        ]
        run = StateMachine.replay(events, definition)

        assert run.status == WorkflowRunStatus.RUNNING
        assert run.input_data == {"file_path": "/test.pdf"}
        assert run.started_at is not None

    def test_replay_activity_lifecycle(self):
        definition = self._make_definition()
        events = [
            self._make_event("run1", 1, WorkflowEventType.WORKFLOW_STARTED, {}),
            self._make_event("run1", 2, WorkflowEventType.ACTIVITY_SCHEDULED, {
                "activity_id": "act1", "activity_type": "ocr_parse",
            }),
            self._make_event("run1", 3, WorkflowEventType.ACTIVITY_STARTED, {
                "activity_id": "act1",
            }),
            self._make_event("run1", 4, WorkflowEventType.ACTIVITY_COMPLETED, {
                "activity_id": "act1",
                "output": {"text": "Hello World", "pages": 1},
                "duration_ms": 1500,
            }),
        ]
        run = StateMachine.replay(events, definition)

        assert run.status == WorkflowRunStatus.RUNNING
        assert run.activity_states["act1"].status == ActivityStatus.COMPLETED
        assert run.activity_results["act1"] == {"text": "Hello World", "pages": 1}
        assert run.activity_states["act1"].duration_ms == 1500

    def test_replay_activity_failed(self):
        definition = self._make_definition()
        events = [
            self._make_event("run1", 1, WorkflowEventType.WORKFLOW_STARTED, {}),
            self._make_event("run1", 2, WorkflowEventType.ACTIVITY_SCHEDULED, {
                "activity_id": "act1", "activity_type": "ocr_parse",
            }),
            self._make_event("run1", 3, WorkflowEventType.ACTIVITY_FAILED, {
                "activity_id": "act1",
                "error": "Connection timeout",
            }),
        ]
        run = StateMachine.replay(events, definition)

        assert run.activity_states["act1"].status == ActivityStatus.FAILED
        assert run.activity_states["act1"].error == "Connection timeout"

    def test_replay_activity_retry(self):
        definition = self._make_definition()
        events = [
            self._make_event("run1", 1, WorkflowEventType.WORKFLOW_STARTED, {}),
            self._make_event("run1", 2, WorkflowEventType.ACTIVITY_SCHEDULED, {
                "activity_id": "act1", "activity_type": "ocr_parse",
            }),
            self._make_event("run1", 3, WorkflowEventType.ACTIVITY_FAILED, {
                "activity_id": "act1", "error": "timeout",
            }),
            self._make_event("run1", 4, WorkflowEventType.ACTIVITY_RETRYING, {
                "activity_id": "act1", "attempt": 1,
            }),
            self._make_event("run1", 5, WorkflowEventType.ACTIVITY_COMPLETED, {
                "activity_id": "act1", "output": {"text": "ok"},
            }),
        ]
        run = StateMachine.replay(events, definition)

        assert run.activity_states["act1"].status == ActivityStatus.COMPLETED
        assert run.activity_results["act1"] == {"text": "ok"}

    def test_replay_workflow_completed(self):
        definition = self._make_definition([
            ActivityDefinition(activity_id="act1", activity_type="ocr_parse"),
        ])
        events = [
            self._make_event("run1", 1, WorkflowEventType.WORKFLOW_STARTED, {}),
            self._make_event("run1", 2, WorkflowEventType.ACTIVITY_COMPLETED, {
                "activity_id": "act1", "output": {"text": "done"},
            }),
            self._make_event("run1", 3, WorkflowEventType.WORKFLOW_COMPLETED, {
                "output_data": {"activity_results": {"act1": {"text": "done"}}},
            }),
        ]
        run = StateMachine.replay(events, definition)

        assert run.status == WorkflowRunStatus.COMPLETED
        assert run.completed_at is not None

    def test_replay_workflow_cancelled(self):
        definition = self._make_definition()
        events = [
            self._make_event("run1", 1, WorkflowEventType.WORKFLOW_STARTED, {}),
            self._make_event("run1", 2, WorkflowEventType.WORKFLOW_CANCELLED, {}),
        ]
        run = StateMachine.replay(events, definition)
        assert run.status == WorkflowRunStatus.CANCELLED

    def test_replay_timer_lifecycle(self):
        definition = self._make_definition()
        events = [
            self._make_event("run1", 1, WorkflowEventType.WORKFLOW_STARTED, {}),
            self._make_event("run1", 2, WorkflowEventType.TIMER_SCHEDULED, {
                "timer_id": "delay-1",
            }),
            self._make_event("run1", 3, WorkflowEventType.TIMER_FIRED, {
                "timer_id": "delay-1",
            }),
        ]
        run = StateMachine.replay(events, definition)

        assert run.status == WorkflowRunStatus.RUNNING
        assert "delay-1" not in run.pending_timers

    def test_replay_deterministic(self):
        """Same events always produce the same state."""
        definition = self._make_definition()
        events = [
            self._make_event("run1", 1, WorkflowEventType.WORKFLOW_STARTED, {
                "input_data": {"file": "test.pdf"},
            }),
            self._make_event("run1", 2, WorkflowEventType.ACTIVITY_COMPLETED, {
                "activity_id": "act1", "output": {"text": "hello"},
            }),
        ]

        run1 = StateMachine.replay(events, definition)
        run2 = StateMachine.replay(events, definition)

        assert run1.status == run2.status
        assert run1.activity_results == run2.activity_results
        assert run1.activity_states["act1"].status == run2.activity_states["act1"].status


class TestStateMachineNextAction:
    """Tests for StateMachine.determine_next_action."""

    def _make_definition(self):
        return WorkflowDefinition(
            workflow_id="test",
            name="Test",
            activities=[
                ActivityDefinition(
                    activity_id="act1",
                    activity_type="ocr_parse",
                    label="Parse",
                ),
                ActivityDefinition(
                    activity_id="act2",
                    activity_type="ocr_classify",
                    label="Classify",
                    depends_on=["act1"],
                ),
            ],
        )

    def test_schedule_first_activity(self):
        definition = self._make_definition()
        events = [
            WorkflowEvent(
                workflow_run_id="run1",
                sequence_num=1,
                event_type=WorkflowEventType.WORKFLOW_STARTED,
                payload={},
            ),
        ]
        run = StateMachine.replay(events, definition)
        action = StateMachine.determine_next_action(run, definition)

        assert action.action_type == NextActionType.SCHEDULE_ACTIVITY
        assert action.activity_id == "act1"

    def test_schedule_next_after_dependency_complete(self):
        definition = self._make_definition()
        events = [
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=1,
                event_type=WorkflowEventType.WORKFLOW_STARTED, payload={},
            ),
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=2,
                event_type=WorkflowEventType.ACTIVITY_COMPLETED,
                payload={"activity_id": "act1", "output": {"text": "ok"}},
            ),
        ]
        run = StateMachine.replay(events, definition)
        action = StateMachine.determine_next_action(run, definition)

        assert action.action_type == NextActionType.SCHEDULE_ACTIVITY
        assert action.activity_id == "act2"

    def test_wait_activity_when_running(self):
        definition = self._make_definition()
        events = [
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=1,
                event_type=WorkflowEventType.WORKFLOW_STARTED, payload={},
            ),
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=2,
                event_type=WorkflowEventType.ACTIVITY_SCHEDULED,
                payload={"activity_id": "act1", "activity_type": "ocr_parse"},
            ),
        ]
        run = StateMachine.replay(events, definition)
        action = StateMachine.determine_next_action(run, definition)

        assert action.action_type == NextActionType.WAIT_ACTIVITY

    def test_complete_workflow_all_done(self):
        definition = self._make_definition()
        events = [
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=1,
                event_type=WorkflowEventType.WORKFLOW_STARTED, payload={},
            ),
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=2,
                event_type=WorkflowEventType.ACTIVITY_COMPLETED,
                payload={"activity_id": "act1", "output": {}},
            ),
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=3,
                event_type=WorkflowEventType.ACTIVITY_COMPLETED,
                payload={"activity_id": "act2", "output": {}},
            ),
        ]
        run = StateMachine.replay(events, definition)
        action = StateMachine.determine_next_action(run, definition)

        assert action.action_type == NextActionType.COMPLETE_WORKFLOW

    def test_retry_on_failure(self):
        definition = WorkflowDefinition(
            workflow_id="test",
            name="Test",
            activities=[
                ActivityDefinition(
                    activity_id="act1",
                    activity_type="ocr_parse",
                    retry_policy=RetryPolicy(max_attempts=3),
                ),
            ],
        )
        events = [
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=1,
                event_type=WorkflowEventType.WORKFLOW_STARTED, payload={},
            ),
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=2,
                event_type=WorkflowEventType.ACTIVITY_FAILED,
                payload={"activity_id": "act1", "error": "timeout"},
            ),
        ]
        run = StateMachine.replay(events, definition)
        action = StateMachine.determine_next_action(run, definition)

        assert action.action_type == NextActionType.RETRY_ACTIVITY
        assert action.activity_id == "act1"
        assert action.delay_seconds > 0

    def test_fail_workflow_exhausted_retries(self):
        definition = WorkflowDefinition(
            workflow_id="test",
            name="Test",
            activities=[
                ActivityDefinition(
                    activity_id="act1",
                    activity_type="ocr_parse",
                    retry_policy=RetryPolicy(max_attempts=1),
                ),
            ],
        )
        events = [
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=1,
                event_type=WorkflowEventType.WORKFLOW_STARTED, payload={},
            ),
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=2,
                event_type=WorkflowEventType.ACTIVITY_FAILED,
                payload={"activity_id": "act1", "error": "fatal"},
            ),
        ]
        run = StateMachine.replay(events, definition)
        action = StateMachine.determine_next_action(run, definition)

        assert action.action_type == NextActionType.FAIL_WORKFLOW
        assert "fatal" in action.error

    def test_no_op_for_terminal_state(self):
        definition = self._make_definition()
        events = [
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=1,
                event_type=WorkflowEventType.WORKFLOW_STARTED, payload={},
            ),
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=2,
                event_type=WorkflowEventType.WORKFLOW_COMPLETED, payload={},
            ),
        ]
        run = StateMachine.replay(events, definition)
        action = StateMachine.determine_next_action(run, definition)

        assert action.action_type == NextActionType.NO_OP


class TestStateMachineActivityInput:
    """Tests for StateMachine.get_activity_input."""

    def test_basic_input(self):
        definition = WorkflowDefinition(
            workflow_id="test",
            name="Test",
            activities=[
                ActivityDefinition(
                    activity_id="act1",
                    activity_type="ocr_parse",
                    config={"tier": "Premium"},
                ),
            ],
        )
        events = [
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=1,
                event_type=WorkflowEventType.WORKFLOW_STARTED,
                payload={"input_data": {"file_path": "/test.pdf"}},
            ),
        ]
        run = StateMachine.replay(events, definition)
        activity_input = StateMachine.get_activity_input(run, definition.activities[0])

        assert activity_input["workflow_run_id"] == "run1"
        assert activity_input["activity_type"] == "ocr_parse"
        assert activity_input["config"] == {"tier": "Premium"}
        assert activity_input["workflow_input"] == {"file_path": "/test.pdf"}

    def test_upstream_outputs(self):
        definition = WorkflowDefinition(
            workflow_id="test",
            name="Test",
            activities=[
                ActivityDefinition(activity_id="act1", activity_type="ocr_parse"),
                ActivityDefinition(
                    activity_id="act2",
                    activity_type="ocr_classify",
                    depends_on=["act1"],
                ),
            ],
        )
        events = [
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=1,
                event_type=WorkflowEventType.WORKFLOW_STARTED, payload={},
            ),
            WorkflowEvent(
                workflow_run_id="run1", sequence_num=2,
                event_type=WorkflowEventType.ACTIVITY_COMPLETED,
                payload={"activity_id": "act1", "output": {"text": "parsed text"}},
            ),
        ]
        run = StateMachine.replay(events, definition)
        activity_input = StateMachine.get_activity_input(run, definition.activities[1])

        assert "upstream_outputs" in activity_input
        assert activity_input["upstream_outputs"]["act1"] == {"text": "parsed text"}
        assert activity_input["previous_output"] == {"text": "parsed text"}


# =============================================================================
# Activity Context Tests
# =============================================================================


class TestActivityContext:
    """Tests for ActivityContext helper."""

    def test_basic_properties(self):
        payload = {
            "workflow_run_id": "run123",
            "activity_id": "act1",
            "activity_type": "ocr_parse",
            "config": {"tier": "Premium", "rules": []},
            "workflow_input": {"file_path": "/uploads/test.pdf"},
        }
        ctx = ActivityContext(payload)

        assert ctx.workflow_run_id == "run123"
        assert ctx.activity_id == "act1"
        assert ctx.activity_type == "ocr_parse"
        assert ctx.file_path == "/uploads/test.pdf"
        assert ctx.tier == "Premium"

    def test_upstream_outputs(self):
        payload = {
            "config": {},
            "workflow_input": {},
            "upstream_outputs": {"act1": {"text": "hello"}},
            "previous_output": {"text": "hello"},
        }
        ctx = ActivityContext(payload)

        assert ctx.upstream_outputs == {"act1": {"text": "hello"}}
        assert ctx.previous_output == {"text": "hello"}

    def test_default_tier(self):
        ctx = ActivityContext({"config": {}, "workflow_input": {}})
        assert ctx.tier == "Normal"

    def test_empty_file_path(self):
        ctx = ActivityContext({"config": {}, "workflow_input": {}})
        assert ctx.file_path == ""


class TestActivityErrors:
    """Tests for activity error classes."""

    def test_activity_error_retryable(self):
        err = ActivityError("timeout")
        assert err.retryable is True
        assert str(err) == "timeout"

    def test_non_retryable_error(self):
        err = NonRetryableError("invalid file type")
        assert err.retryable is False
        assert str(err) == "invalid file type"

    def test_error_with_details(self):
        err = ActivityError("failed", details={"code": 500})
        assert err.details == {"code": 500}


# =============================================================================
# WorkflowDefinition Tests
# =============================================================================


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition model."""

    def test_create_minimal(self):
        defn = WorkflowDefinition(
            workflow_id="wf-1",
            name="Test",
            activities=[
                ActivityDefinition(activity_id="a1", activity_type="parse"),
            ],
        )
        assert defn.workflow_id == "wf-1"
        assert len(defn.activities) == 1
        assert defn.timeout_seconds == 3600

    def test_activity_defaults(self):
        act = ActivityDefinition(
            activity_id="a1",
            activity_type="ocr_parse",
        )
        assert act.timeout_seconds == 300
        assert act.queue_name == "default"
        assert act.retry_policy.max_attempts == 3
        assert act.depends_on == []

    def test_activity_with_dependencies(self):
        act = ActivityDefinition(
            activity_id="a2",
            activity_type="ocr_classify",
            depends_on=["a1"],
        )
        assert act.depends_on == ["a1"]
