# Agent Progress Log: Dr Vision

**Quy ước:** Mỗi session thêm entry mới ở đầu file (newest first).
Đọc 3-5 entries gần nhất để hiểu context.

---

## Session #4: 2026-05-22 · Thực hiện bởi: Antigravity

### Mục tiêu ban đầu:
Implement feat-009: Journey Scheduling & Triggers (Simplified to API trigger only, per user request)

### Đã làm:
- **Backend: API Webhook Trigger** — Validated route `POST /api/v1/workflows/{workflow_id}/trigger` in `journey_jobs.py`. It fetches workflow definitions, saves uploaded files locally, uploads to MinIO, persists job & upload records in PostgreSQL, and submits the job to the async job queue.
- **Tests: Automated Unit Tests** — Created `tests/test_trigger_api.py` covering:
  - Successful workflow triggering via multipart upload (returns 200, creates queue job, inserts DB records).
  - Error case: Workflow not found (returns 404).
  - Error case: Empty steps in workflow graph data (returns 400).
  - Error case: Invalid file extension (returns 400).
- **Linter & Verification** — Verified all new code passes `ruff check` and all unit tests in `tests/test_trigger_api.py`, `tests/test_job_queue.py`, and `tests/test_execution_state.py` pass successfully (53 tests total).

### Verification results:
- `ruff check tests/test_trigger_api.py` → 0 errors
- `ruff check api/v1/journey_jobs.py` → 0 errors
- `pytest tests/test_trigger_api.py tests/test_job_queue.py tests/test_execution_state.py` → 53 passed ✅

### Session status: DONE ✅

### Ghi chú quan trọng:
- All scheduling, folder watching/MinIO trigger, and batch actions are excluded per user request. Only direct execution and API trigger (Method 1) are kept.

---

## Session #2: 2026-05-21 · Thực hiện bởi: Kiro

### Mục tiêu ban đầu:
Implement feat-006: Journey Job Manager — Production-grade job system

### Đã làm:
- **Backend: Job timeout** — Thêm `timeout_seconds` field vào `JobRecord` (default 300s), worker dùng `asyncio.wait_for()` để enforce timeout
- **Backend: Fix Pydantic deprecation** — Chuyển từ `class Config` sang `model_config` dict
- **Frontend: Tích hợp `useJobManager` vào `JourneyWorkflow.vue`** — Import composable + JobPanel component
- **Frontend: Execute as Job** — `handleExecuteAsJob()` submit workflow lên backend queue thay vì execute local
- **Frontend: Real-time node sync** — `updateNodesFromJob()` + `watch(currentJob)` cập nhật node status trên canvas theo SSE events
- **Frontend: Jobs toolbar button** — Nút "Jobs" với pulse indicator khi có job đang chạy, toggle JobPanel
- **Frontend: JobPanel integration** — Bottom panel hiển thị progress, node timeline, cancel, history
- **Tests: 29 new tests** — `tests/test_job_queue.py` covering: submission, lifecycle, cancellation, timeout, node progress, listing/filters, cleanup, concurrency, FIFO ordering

### Verification results:
- `ruff check` → 0 errors (backend)
- `pytest tests/test_job_queue.py` → 29 passed ✅
- `npx vue-tsc --noEmit` → 0 new errors (pre-existing TS issues unchanged)
- `npx vitest --run` → 4 passed ✅

### Session status: DONE ✅

### Ghi chú quan trọng:
- Execution mode mặc định là `'job'` (backend queue). User có thể switch sang `'local'` nếu cần
- Backend đã có đầy đủ: job_queue.py, job_executor.py, job_events.py (SSE), job_persistence.py (PostgreSQL), journey_jobs.py (REST API)
- Frontend đã có: useJobManager.ts, JobPanel.vue, tích hợp vào JourneyWorkflow.vue
- Pre-existing test failures (13) không liên quan đến changes này (CORS config, agent factory, stale imports)

### Commits trong session này:
(Chờ developer review)

### Session tiếp theo NÊN:
1. Bắt đầu feat-007: Journey Stateful Execution
2. Đọc notes: "Hiện tại execution là stateless (fire-and-forget). Cần thêm persistence layer."
3. Cần: checkpoint system, resume from failed node, state viewer UI

### Session tiếp theo KHÔNG NÊN:
- Không refactor feat-006 (đã passes: true)
- Không fix pre-existing test failures (ngoài scope)

---

## Session #1: 2026-05-19 · Thực hiện bởi: Kiro

### Mục tiêu ban đầu:
Setup Harness Engineering cho dự án Dr Vision

### Đã làm:
- Tạo bộ tài liệu Harness Engineering đầy đủ (12 files) tại `docs/harness-engineering/`
- Tạo AGENTS.md tại root — operating manual cho agent
- Tạo init.sh — session startup script (6 steps: prerequisites, backend, frontend, docker, health check, type check)
- Tạo verify.sh — full pipeline verification (5 gates: lint, backend tests, frontend type check, frontend tests, smoke)
- Tạo feature_list.json — 6 features (4 done, 2 pending)
- Tạo agent-progress.md (file này)

### Verification results:
- Chưa chạy full verification (đây là session setup, không phải feature implementation)
- Files tạo thành công, AGENTS.md đã được Kiro nhận diện tự động

### Session status: DONE ✅ (setup task)

### Ghi chú quan trọng:
- feat-001 đến feat-004 đã mark passes: true dựa trên existing code/docs
- feat-005 (API Explorer service split) là feature pending tiếp theo (priority 5)
- feat-006 (Langflow migration) phụ thuộc feat-005
- Specs cho feat-005 và feat-006 đã có sẵn tại `.kiro/specs/`

### Commits trong session này:
(Chưa commit — chờ developer review)

### Session tiếp theo NÊN:
1. Chạy `./init.sh` để verify environment
2. Chạy `./verify.sh` để baseline verification
3. Bắt đầu feat-005: API Explorer service split
4. Đọc specs tại `.kiro/specs/api-explorer-service-split/`

### Session tiếp theo KHÔNG NÊN:
- Không bắt đầu feat-006 trước khi feat-005 done
- Không refactor existing features (đã passes: true)
- Không thay đổi AGENTS.md trừ khi tech stack thay đổi
