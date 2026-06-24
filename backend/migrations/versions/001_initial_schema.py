"""Initial schema — all existing tables.

Revision ID: 001
Revises: None
Create Date: 2026-06-24
"""
from typing import Sequence, Union

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── Auth ─────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id              VARCHAR(32) PRIMARY KEY,
            email           VARCHAR(255) NOT NULL UNIQUE,
            full_name       VARCHAR(255) NOT NULL,
            role            VARCHAR(20) NOT NULL DEFAULT 'user',
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            password_hash   TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_login      TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id              VARCHAR(32) PRIMARY KEY,
            user_id         VARCHAR(32) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            key_hash        TEXT NOT NULL,
            name            VARCHAR(255) NOT NULL,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_used       TIMESTAMPTZ
        )
    """)

    # ─── OCR Results ──────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS ocr_results (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            filename        TEXT NOT NULL,
            model_id        TEXT,
            provider        TEXT,
            tier            TEXT DEFAULT 'Normal',
            raw_text        TEXT,
            result_data     JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ocr_filename ON ocr_results(filename)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ocr_model ON ocr_results(model_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ocr_created ON ocr_results(created_at DESC)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ocr_result_type "
        "ON ocr_results USING gin ((result_data -> 'type'))"
    )

    # ─── Banking ──────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS statements (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            filename        TEXT NOT NULL,
            bank_name       TEXT,
            account_number  TEXT,
            account_holder  TEXT,
            currency        TEXT DEFAULT 'VND',
            period_start    DATE,
            period_end      DATE,
            opening_balance NUMERIC(18,2),
            closing_balance NUMERIC(18,2),
            total_credit    NUMERIC(18,2),
            total_debit     NUMERIC(18,2),
            transaction_count INTEGER DEFAULT 0,
            processing_tier TEXT DEFAULT 'Advance',
            analytics_json  JSONB,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id              SERIAL PRIMARY KEY,
            statement_id    UUID NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
            transaction_date DATE,
            description     TEXT,
            debit_amount    NUMERIC(18,2),
            credit_amount   NUMERIC(18,2),
            balance         NUMERIC(18,2),
            category        TEXT DEFAULT 'other',
            subcategory     TEXT DEFAULT '',
            category_confidence REAL DEFAULT 0.0,
            category_method TEXT DEFAULT 'default',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_txn_statement ON transactions(statement_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(transaction_date)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_txn_category ON transactions(category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_stmt_bank ON statements(bank_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_stmt_period ON statements(period_start, period_end)")

    # ─── Workflows & Jobs ─────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_canvas (
            id                  VARCHAR(32) PRIMARY KEY,
            title               VARCHAR(255) NOT NULL,
            user_id             VARCHAR(255) NOT NULL DEFAULT 'default',
            canvas_category     VARCHAR(32) NOT NULL DEFAULT 'dataflow_canvas',
            release             BOOLEAN NOT NULL DEFAULT FALSE,
            description         TEXT,
            dsl                 JSONB NOT NULL DEFAULT '{}',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS user_canvas_version (
            id                  VARCHAR(32) PRIMARY KEY,
            user_canvas_id      VARCHAR(255) NOT NULL REFERENCES user_canvas(id) ON DELETE CASCADE,
            title               VARCHAR(255),
            release             BOOLEAN NOT NULL DEFAULT TRUE,
            dsl                 JSONB NOT NULL DEFAULT '{}',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name            TEXT NOT NULL,
            description     TEXT,
            graph_data      JSONB NOT NULL DEFAULT '{}',
            status          TEXT NOT NULL DEFAULT 'draft',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workflow_id     UUID REFERENCES workflows(id) ON DELETE SET NULL,
            workflow_name   TEXT,
            status          TEXT NOT NULL DEFAULT 'queued',
            progress        REAL NOT NULL DEFAULT 0.0,
            nodes_data      JSONB NOT NULL DEFAULT '[]',
            steps_data      JSONB,
            filename        TEXT,
            file_count      INTEGER DEFAULT 1,
            max_retries     INTEGER DEFAULT 3,
            results         JSONB,
            error           TEXT,
            minio_path      TEXT,
            result_minio_path TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at      TIMESTAMPTZ,
            completed_at    TIMESTAMPTZ,
            cancelled_at    TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS job_logs (
            id              SERIAL PRIMARY KEY,
            job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            event_type      TEXT NOT NULL,
            node_id         TEXT,
            node_type       TEXT,
            node_label      TEXT,
            data            JSONB,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS execution_states (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            job_id          UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            workflow_id     UUID REFERENCES workflows(id) ON DELETE SET NULL,
            status          TEXT NOT NULL DEFAULT 'running',
            node_states     JSONB NOT NULL DEFAULT '{}',
            context         JSONB NOT NULL DEFAULT '{}',
            checkpoint_node TEXT,
            resume_from     TEXT,
            retention_hours INTEGER DEFAULT 72,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            job_id          UUID REFERENCES jobs(id) ON DELETE SET NULL,
            filename        TEXT NOT NULL,
            minio_path      TEXT NOT NULL,
            size_bytes      BIGINT,
            mime_type       TEXT,
            uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS data_store (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            filename        TEXT NOT NULL,
            action_tag      TEXT NOT NULL,
            result_data     TEXT,
            model_used      TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Workflow & job indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_canvas_user ON user_canvas(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_canvas_category ON user_canvas(canvas_category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_canvas_updated ON user_canvas(updated_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_canvas_version_canvas ON user_canvas_version(user_canvas_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_workflows_updated ON workflows(updated_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_jobs_workflow ON jobs(workflow_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_job_logs_job ON job_logs(job_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_job_logs_created ON job_logs(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_exec_states_job ON execution_states(job_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_exec_states_workflow ON execution_states(workflow_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_exec_states_status ON execution_states(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_exec_states_updated ON execution_states(updated_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_uploads_job ON uploads(job_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_uploads_uploaded ON uploads(uploaded_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_data_store_tag ON data_store(action_tag)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_data_store_created ON data_store(created_at DESC)")

    # ─── Durable Workflow Engine ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS workflow_runs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workflow_id     TEXT NOT NULL,
            workflow_name   TEXT NOT NULL DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'pending',
            input_data      JSONB NOT NULL DEFAULT '{}',
            output_data     JSONB NOT NULL DEFAULT '{}',
            error           TEXT,
            last_sequence   INTEGER NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at      TIMESTAMPTZ,
            completed_at    TIMESTAMPTZ,
            timeout_seconds INTEGER NOT NULL DEFAULT 3600,
            metadata        JSONB NOT NULL DEFAULT '{}'
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS workflow_events (
            id              BIGSERIAL PRIMARY KEY,
            workflow_run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
            sequence_num    INTEGER NOT NULL,
            event_type      TEXT NOT NULL,
            payload         JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(workflow_run_id, sequence_num)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS task_queue (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            queue_name      TEXT NOT NULL DEFAULT 'default',
            workflow_run_id UUID NOT NULL,
            activity_id     TEXT NOT NULL,
            activity_type   TEXT NOT NULL,
            payload         JSONB NOT NULL DEFAULT '{}',
            status          TEXT NOT NULL DEFAULT 'pending',
            worker_id       TEXT,
            visible_after   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            heartbeat_at    TIMESTAMPTZ,
            timeout_seconds INTEGER NOT NULL DEFAULT 300,
            attempt         INTEGER NOT NULL DEFAULT 0,
            max_attempts    INTEGER NOT NULL DEFAULT 3,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at      TIMESTAMPTZ,
            completed_at    TIMESTAMPTZ,
            result          JSONB,
            error           TEXT
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS durable_timers (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            workflow_run_id UUID NOT NULL,
            name            TEXT NOT NULL DEFAULT '',
            fire_at         TIMESTAMPTZ NOT NULL,
            status          TEXT NOT NULL DEFAULT 'scheduled',
            payload         JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            fired_at        TIMESTAMPTZ,
            UNIQUE(workflow_run_id, name)
        )
    """)

    # Durable engine indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_wf_runs_workflow ON workflow_runs(workflow_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_wf_runs_status ON workflow_runs(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_wf_runs_created ON workflow_runs(created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_wf_events_run ON workflow_events(workflow_run_id, sequence_num)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_wf_events_type ON workflow_events(workflow_run_id, event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_wf_events_created ON workflow_events(created_at DESC)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_taskq_poll "
        "ON task_queue(queue_name, status, visible_after) WHERE status = 'pending'"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_taskq_run ON task_queue(workflow_run_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_taskq_heartbeat "
        "ON task_queue(heartbeat_at, timeout_seconds) WHERE status = 'processing'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_taskq_completed "
        "ON task_queue(completed_at) WHERE status IN ('completed', 'failed')"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_timers_fire "
        "ON durable_timers(fire_at) WHERE status = 'scheduled'"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_timers_run ON durable_timers(workflow_run_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_timers_fired_at ON durable_timers(fired_at) WHERE status = 'fired'")

    # ─── Alembic version stamp ────────────────────────────────────────────────
    # (handled automatically by Alembic)


def downgrade() -> None:
    # Drop in reverse dependency order
    op.execute("DROP TABLE IF EXISTS durable_timers CASCADE")
    op.execute("DROP TABLE IF EXISTS task_queue CASCADE")
    op.execute("DROP TABLE IF EXISTS workflow_events CASCADE")
    op.execute("DROP TABLE IF EXISTS workflow_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS data_store CASCADE")
    op.execute("DROP TABLE IF EXISTS uploads CASCADE")
    op.execute("DROP TABLE IF EXISTS execution_states CASCADE")
    op.execute("DROP TABLE IF EXISTS job_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS jobs CASCADE")
    op.execute("DROP TABLE IF EXISTS workflows CASCADE")
    op.execute("DROP TABLE IF EXISTS user_canvas_version CASCADE")
    op.execute("DROP TABLE IF EXISTS user_canvas CASCADE")
    op.execute("DROP TABLE IF EXISTS transactions CASCADE")
    op.execute("DROP TABLE IF EXISTS statements CASCADE")
    op.execute("DROP TABLE IF EXISTS ocr_results CASCADE")
    op.execute("DROP TABLE IF EXISTS api_keys CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
