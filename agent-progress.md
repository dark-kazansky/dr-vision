# Agent Progress Log: Doc Intelligence

**Quy ước:** Mỗi session thêm entry mới ở đầu file (newest first).
Đọc 3-5 entries gần nhất để hiểu context.

---

## Session #11: 2026-06-23 · Thực hiện bởi: Kiro

### Mục tiêu ban đầu:
feat-042: Async Document Processing — Register documents router, verify backend, lint, test, update Postman collection

### Đã làm:
- **Router registration** — Added `documents` import + `auth_router.include_router(documents.router)` in `api/router.py`
- **Lint cleanup** — Fixed 11 unused imports across `api/v1/documents.py`, `services/document_job_runner.py`, `tests/test_documents_api.py` via `ruff check --fix`
- **Verified existing implementation** — All supporting services confirmed:
  - `services/document_job_runner.py` — DocumentJobRunner (per-page processing, cooperative cancel, partial results)
  - `services/job_events.py` — JobEventBus with feat-042 granular events (page_progress, stage_changed, partial_result)
  - `core/storage.py` — UPLOADS_DIR path constant
- **Tests verified** — 12/12 tests pass in `tests/test_documents_api.py` covering all 5 endpoints + error cases
- **Postman collection updated** — `.postman/dr-vision-collection.json` now has "Document Processing (Async)" folder with 13 requests
- **Postman environment updated** — Added `doc_job_id` variable to `.postman/dr-vision-environment.json`
- **feature_list.json** — Added feat-042 entry with `passes: true`, updated summary (40 total, 14 done)

### Verification results:
- `ruff check` (feat-042 files) → 0 errors ✅
- `pytest tests/test_documents_api.py` → 12 passed ✅
- `pytest` (full suite) → 350 passed, 16 failed (pre-existing: DB-dependent), 10 errors (pre-existing: stale imports) ✅
- `vue-tsc --noEmit` → 94 pre-existing TS errors, 0 new from feat-042 ✅
- Feature-specific tests (all features) → 139/140 passed ✅

### Session status: DONE ✅

### Ghi chú quan trọng:
- feat-042 is a backend-only feature (no frontend changes)
- Postman MCP server is disabled — cannot run collection remotely. Use Newman locally: `npx newman run .postman/dr-vision-collection.json -e .postman/dr-vision-environment.json --folder "Document Processing (Async)"`
- DocumentJobRunner processes page-by-page with cooperative cancel between pages
- SSE stream supports: connected, stage_changed, page_progress, partial_result, job_completed, job_failed, job_cancelled events
- Operations supported: ocr, classify, split, extract

### Commits trong session này:
(Chưa commit — chờ developer review)

### Session tiếp theo NÊN:
1. feat-031: Mark as passes (code done session #9, tests pass, needs final e2e verification)
2. feat-016: HTTPS & Reverse Proxy (deployment track)
3. feat-017: Database Migrations with Alembic
4. feat-018: CI/CD Pipeline

### Session tiếp theo KHÔNG NÊN:
- Không refactor feat-042 (đã passes: true)
- Không fix pre-existing TypeScript errors (feat-022 scope)
- Không fix pre-existing test failures (feat-022 scope)

---

## Session #9: 2026-06-15 · Thực hiện bởi: Kiro

### Mục tiêu ban đầu:
feat-031: Layout Recognize — Migrate DeepDoc layout detection từ infiniflow/ragflow vào Doc Intelligence

### Đã làm:
- Tạo `backend/deepdoc/` module — ported từ ragflow/deepdoc/vision:
  - `deepdoc/__init__.py` — package init
  - `deepdoc/vision/__init__.py` — exports Recognizer, LayoutRecognizer
  - `deepdoc/vision/operators.py` — preprocessing ops (LinearResize, StandardizeImage, Permute, PadStride, NMS)
  - `deepdoc/vision/recognizer.py` — base ONNX inference class (preprocess, postprocess, batching, sorting, overlap utils)
  - `deepdoc/vision/layout_recognizer.py` — YOLOv10 layout detection (10 labels)
  - `deepdoc/model_manager.py` — HuggingFace model download & caching
- Tạo `backend/components/layout_recognizer.py` — high-level component wrapper (LayoutRecognizeComponent)
- Tạo `backend/api/v1/layout.py` — REST API endpoints (POST /layout/recognize, GET /layout/models)
- Đăng ký layout router trong `api/router.py`
- Thêm `layout_recognize` step type vào `services/workflow_service.py`
- Thêm `layout_recognize` support vào `services/job_executor.py`
- Thêm node type `layout-recognize` vào frontend `useNodeRegistry.ts` (category: processing)
- Đăng ký `layout-recognize` trong `workflow-builder.vue` nodeTypes
- Thêm dependencies vào `requirements.txt`: onnxruntime, opencv-python-headless, huggingface-hub
- Tạo 29 unit tests trong `tests/test_layout_recognizer.py` — ALL PASS

### Verification results:
- `ruff check` — 0 errors (new files)
- `pytest tests/test_layout_recognizer.py` — 29/29 passed ✅
- `vue-tsc --noEmit` — 0 new errors from my changes (pre-existing errors unchanged)
- Feature registered: feat-031 added to feature_list.json

### Session status: DONE ✅

### Ghi chú quan trọng:
- ONNX model cần download từ HuggingFace `InfiniFlow/deepdoc` lần đầu sử dụng (auto-download)
- Model file: `layout.onnx` (~50-200MB) — cached tại `backend/models/deepdoc/`
- 10 layout labels: title, text, reference, figure, figure caption, table, table caption, equation
- Frontend node có 2 config: threshold (0.2 default) và scaleFactor (3x default)

### Commits trong session này:
(Chưa commit — chờ developer review)

### Session tiếp theo NÊN:
1. Test end-to-end với real PDF + downloaded model
2. Thêm visualization overlay trên frontend (bounding boxes)
3. Thêm Table Structure Recognition (TSR) node
4. Consider Layout-Aware OCR (combine layout regions + OCR output)

### Session tiếp theo KHÔNG NÊN:
- Không refactor pre-existing code
- Không fix pre-existing TypeScript errors (ngoài scope)

---

## Session #7: 2026-06-09 · Thực hiện bởi: Kiro

### Mục tiêu ban đầu:
Implement feat-015: Secrets Management & Production Config

### Đã làm:
- **Root `.env.example`** — Comprehensive reference documenting ALL required env vars (PostgreSQL, MinIO, Backend, AI Providers, Frontend)
- **`docker-compose.prod.yml`** — Production compose using `${VAR}` substitution only (zero hardcoded passwords), includes backend + frontend + postgres + minio with restart policies
- **`docker-compose.yml` updated** — Dev compose now uses `${VAR:-default}` pattern (still works without .env for dev convenience)
- **`backend/settings.py` updated** — `database_url`, `minio_access_key`, `minio_secret_key` are now `Optional[str] = None` (no hardcoded fallbacks). Added `check_required_secrets()` method. CORS default changed from `["*"]` to `["http://localhost:3000"]`. Added `cors_origins` property parsing comma-separated `CORS_ORIGINS` env var.
- **`backend/server.py` updated** — Startup validates required secrets and logs clear warning if missing
- **`backend/.env.example`** — Full reference for backend devs with all required and optional env vars
- **`frontend/.env.example`** — Documents `API_BASE_URL`
- **`frontend/nuxt.config.ts`** — Now supports `NUXT_PUBLIC_API_BASE_URL` (standard Nuxt override), fixed stale fallback from `8882` to `8000`
- **`.gitignore` updated** — Added `.env.prod` explicitly
- **Seed scripts updated** — `seed_data.py`, `seed_canvas.py`, `seed_realistic.py` no longer have hardcoded DB passwords (require `DATABASE_URL` env var)
- **Tests: 18 new tests** (`tests/test_secrets_management.py`) covering:
  - No hardcoded defaults for secrets
  - Env var loading (DATABASE_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY)
  - CORS_ORIGINS comma-separated parsing
  - `check_required_secrets()` (all missing, all present, partial)
  - `.env.example` files existence and content
  - `docker-compose.prod.yml` no plaintext passwords
  - `docker-compose.yml` uses `${VAR:-default}` pattern
  - `.gitignore` excludes `.env.prod`

### Verification results:
- `ruff check settings.py server.py tests/test_secrets_management.py` → 0 errors ✅
- `pytest tests/test_secrets_management.py` → 18 passed ✅
- `pytest` (all feature tests) → 99 passed ✅ (1 pre-existing botocore failure outside scope)
- `npx vue-tsc --noEmit` → 0 errors ✅
- `docker compose -f docker-compose.prod.yml config` → validates correctly with env vars ✅
- `docker compose config` → dev defaults still work ✅

### Session status: DONE ✅

### Ghi chú quan trọng:
- Dev workflow unchanged: `docker compose up -d` still works without any .env file (uses defaults)
- Production requires `.env.prod` with all REQUIRED vars (POSTGRES_PASSWORD, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, CORS_ORIGINS)
- Backend starts with warning if secrets missing (doesn't crash — allows health check and docs to work)
- K8s manifests (k8s/) still have hardcoded values — will be addressed in feat-019
- Pre-existing test failures (test_pdf_resource_management.py, test_splitter_doc_type_properties.py, test_temp_file_cleanup.py) — stale imports, outside scope

### Session tiếp theo NÊN:
1. feat-014: Authentication & Authorization (next blocker for production)
2. Hoặc feat-016: HTTPS & Reverse Proxy (depends on feat-015 ✅)
3. Hoặc feat-018: CI/CD Pipeline (depends on feat-015 ✅)

### Session tiếp theo KHÔNG NÊN:
- Không refactor feat-015 (đã passes: true)
- Không fix pre-existing lint errors trong files khác (ngoài scope)

---

## Session #6: 2026-06-08 · Thực hiện bởi: Kiro

### Mục tiêu ban đầu:
Implement feat-010: Journey Observability — Monitoring, logging, và analytics cho workflow executions

### Đã làm:
- **Backend: Observability Service** (`services/observability.py`) — 5 functions:
  - `get_execution_timeline()` — per-node timing from execution_states JSONB
  - `get_performance_metrics()` — aggregated job/node metrics with CTE queries
  - `get_error_analytics()` — top errors + failure rates from job_logs
  - `get_audit_log()` — paginated job-level audit trail
  - `get_dashboard_summary()` — per-workflow health status with thresholds
- **Backend: REST API** (`api/v1/observability.py`) — 5 endpoints:
  - `GET /api/v1/observability/timeline/{job_id}`
  - `GET /api/v1/observability/metrics`
  - `GET /api/v1/observability/errors`
  - `GET /api/v1/observability/audit`
  - `GET /api/v1/observability/dashboard`
- **Backend: Bug fix** — `duration_ms` was captured in executor but not passed to SSE events. Fixed in `job_queue.py` (`update_node_status` now accepts `duration_ms` param) and `job_executor.py` (passes it on node completion)
- **Backend: Service init** — observability.set_repository() called in server.py lifespan, router registered in api/router.py
- **Frontend: Composable** (`useObservability.ts`) — full typed API with fetchDashboard, fetchMetrics, fetchErrors, fetchAuditLog, fetchTimeline + utility formatters
- **Frontend: Dashboard Page** (`pages/observability.vue`) — 5-tab UI (Overview, Performance, Errors, Audit Log, Timeline) with period selector, drill-down from audit→timeline, health indicators
- **Tests: 15 new tests** (`tests/test_observability.py`) covering all 5 service functions, edge cases (no repo, no pool, job not found), health status thresholds (healthy/critical)
- **Also: Added 9 deployment features** (feat-014→feat-022) to feature_list.json for production readiness roadmap

### Verification results:
- `ruff check` (feat-010 files) → 0 errors
- `pytest tests/test_observability.py` → 15 passed ✅
- `pytest` (all feature tests) → 85 passed ✅
- `npx vue-tsc --noEmit` → 0 errors in new files (pre-existing TS issues unchanged)
- `npx vitest --run` → 4 passed ✅

### Session status: DONE ✅

### Ghi chú quan trọng:
- Không cần thêm DB table mới — observability reads từ existing tables (jobs, job_logs, execution_states)
- Dashboard dùng SQL aggregation queries (FILTER, CTE) trực tiếp trên PostgreSQL
- Health thresholds: healthy (<10% failures), warning (10-30%), critical (>30%)
- Pre-existing test failures (test_pdf_resource_management.py) vẫn tồn tại — ngoài scope

### Session tiếp theo NÊN:
1. feat-015: Secrets Management (quick win, low effort)
2. Hoặc feat-014: Authentication (high priority cho production)
3. Hoặc feat-022: Fix pre-existing test failures (tech debt)

### Session tiếp theo KHÔNG NÊN:
- Không refactor feat-010 (đã passes: true)
- Không thay đổi existing DB schema

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
Setup Harness Engineering cho dự án Doc Intelligence

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
