# Doc Intelligence — Microservice Architecture (Future Roadmap)

> Status: NOT IMPLEMENTED — This document describes a potential future architecture.
> Current state: Monolith (backend/ + frontend/) deployed via Docker Compose.
> Implement only when the monolith becomes a scaling bottleneck or team size > 5.

## Tổng quan

Tách monolith `backend/` thành 4 services độc lập, giao tiếp qua API Gateway.

## Service Map

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Nuxt 4)                      │
│                    localhost:3000                         │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP (single entry point)
┌────────────────────────▼────────────────────────────────┐
│              DR-Gateway (port 8000)                       │
│  Auth (JWT) │ Rate Limit │ CORS │ Routing │ Health Agg   │
└───┬──────────────────┬──────────────────┬───────────────┘
    │                  │                  │
    │ /api/v1/ocr/*    │ /api/v1/jobs/*   │ /api/v1/banking/*
    │ /api/v1/parse/*  │ /api/v1/workflows│
    │ /api/v1/extract  │ /api/v1/data-store
    │ /api/v1/classify │ /api/v1/observability
    │ /api/v1/split    │                  │
    ▼                  ▼                  ▼
┌─────────┐    ┌────────────┐    ┌───────────┐
│ DR-OCR  │    │ DR-Journey │    │DR-Banking │
│  :8001  │    │   :8002    │    │   :8003   │
└────┬────┘    └─────┬──────┘    └─────┬─────┘
     │               │                 │
     │         ┌─────▼──────┐          │
     │         │   Redis    │          │
     │         │  (events)  │          │
     │         └────────────┘          │
     │               │                 │
     └───────┬───────┴─────────┬───────┘
             │                 │
      ┌──────▼──────┐  ┌──────▼──────┐
      │ PostgreSQL  │  │    MinIO    │
      │  (port 5433)│  │  (port 9000)│
      └─────────────┘  └─────────────┘
```

## Services Chi Tiết

### 1. DR-Gateway (services/gateway/) — Port 8000

**Trách nhiệm:**
- Reverse proxy: route requests tới downstream services based on URL prefix
- CORS: centralized configuration (single entry point for frontend)
- Health aggregation: gọi /health từng service, trả summary
- SSE/streaming: forward chunked responses transparently
- Error wrapping: 503 when downstream unavailable, 504 on timeout

**KHÔNG chứa:** Auth, rate limiting, business logic — sống ở service tương ứng.

**Từ code hiện tại:**
- Không move code nào — gateway là service mới, pure proxy
- Auth (`backend/auth/`) → stays in Journey service (owns user DB)
- Rate limiting → stays in individual services

**Database:** Không cần DB.

---

### 2. DR-OCR (services/ocr/) — Port 8001

**Trách nhiệm:**
- AI agent management (factory pattern, multi-provider)
- OCR processing (image + PDF)
- Document parsing, classification, extraction, splitting
- Model configuration (YAML-driven)
- File handling (upload → process → store results in MinIO)

**Từ code hiện tại:**
- `backend/agents/` → `services/ocr/agents/`
- `backend/components/` → `services/ocr/components/` (trừ transaction_categorizer)
- `backend/services/parse_service.py` → `services/ocr/`
- `backend/services/classify_service.py` → `services/ocr/`
- `backend/services/extract_service.py` → `services/ocr/`
- `backend/services/split_service.py` → `services/ocr/`
- `backend/config/settings.yaml` → `services/ocr/config/`
- `backend/core/prompts.py` → `services/ocr/`

**Database:** Không cần DB riêng (stateless). Chỉ MinIO cho file storage.

---

### 3. DR-Journey (services/journey/) — Port 8002

**Trách nhiệm:**
- Workflow builder (CRUD, canvas, node connections)
- Job queue (async, PostgreSQL persistence, concurrency control)
- Execution state (checkpoint, resume, context passing)
- Job events (SSE real-time progress)
- Observability (timeline, metrics, errors, audit, dashboard)
- Data Store (lưu kết quả xử lý với tag phân loại)
- Workflow triggers (API trigger, batch mode)

**Từ code hiện tại:**
- `backend/services/job_*.py` → `services/journey/`
- `backend/services/workflow_*.py` → `services/journey/`
- `backend/services/execution_state.py` → `services/journey/`
- `backend/services/observability.py` → `services/journey/`
- `backend/storage/workflow_repository.py` → `services/journey/`

**Database:** journey schema (jobs, workflows, execution_states, data_store, job_logs, uploads)

---

### 4. DR-Banking (services/banking/) — Port 8003

**Trách nhiệm:**
- Banking document management (upload, store, retrieve)
- Transaction categorization (merchant matching, tier config)
- Banking analytics (summary, trends, categories)
- Banking schema definitions (field types per document)
- OCR integration (gọi OCR service để extract từ bank statements)

**Từ code hiện tại:**
- `backend/storage/banking_repository.py` → `services/banking/`
- `backend/services/banking_analytics_service.py` → `services/banking/`
- `backend/config/banking_schemas.py` → `services/banking/config/`
- `backend/config/merchant_database.py` → `services/banking/config/`
- `backend/config/tier_config.py` → `services/banking/config/`
- `backend/components/transaction_categorizer.py` → `services/banking/`

**Database:** banking schema (documents, transactions, categories)

---

## Shared Package (packages/common/)

```python
# packages/common/dr_common/
├── __init__.py
├── schemas.py          # BaseResponse, ErrorResponse, PaginationParams
├── exceptions.py       # ServiceError, NotFoundError, ValidationError
├── utils.py            # strip_code_blocks, file validators
├── auth.py             # Token decode (verify gateway token)
├── service_client.py   # httpx wrapper: retry, timeout, correlation ID
├── event_bus.py        # Redis pub/sub wrapper
├── circuit_breaker.py  # Circuit breaker pattern
└── config.py           # Shared settings loader
```

---

## Giao tiếp

### Sync (HTTP — request/response)
- Frontend → Gateway → Service
- Journey → OCR: execute node (POST /ocr, /parse, /extract...)
- Banking → OCR: extract bank statement (POST /ocr)

### Async (Redis Pub/Sub — fire & forget)
- OCR → `doc-intelligence.ocr.completed` → Journey listens (update job state)
- Journey → `doc-intelligence.job.status_changed` → Gateway relays via SSE
- Banking → `doc-intelligence.banking.processed` → Journey listens (create data store entry)

---

## Database Strategy

**Phase 1: Shared DB, separate schemas**
```sql
CREATE SCHEMA auth;      -- gateway owns
CREATE SCHEMA journey;   -- journey owns
CREATE SCHEMA banking;   -- banking owns
-- OCR: no schema needed (stateless)
```

**Phase 2 (future): Separate databases**
- Khi banking cần compliance isolation
- Khi journey cần scale DB riêng

---

## Thứ tự Implementation

| Phase | Feature | Mô tả |
|-------|---------|-------|
| 1 | feat-023 | Tạo monorepo structure + shared package |
| 2 | feat-024 | Gateway service (auth tách ra) |
| 2 | feat-025 | OCR service (agents + components tách ra) |
| 3 | feat-026 | Journey service (workflow + jobs tách ra) |
| 3 | feat-027 | Banking service (banking domain tách ra) |
| 4 | feat-028 | Inter-service communication (Redis events, circuit breaker) |
| 4 | feat-029 | Frontend adaptation (gọi qua gateway) |
| 5 | feat-030 | Docker orchestration + integration tests |

---

## Migration Strategy

**Parallel Running:** Trong quá trình tách, legacy `backend/` vẫn chạy được. Mỗi service mới được verify độc lập trước khi frontend chuyển sang gọi qua gateway.

**Rollback:** Nếu service mới có issue, frontend có thể fallback về legacy backend bằng cách đổi `NUXT_PUBLIC_API_BASE_URL`.

---

*Last updated: 2026-06-12*
