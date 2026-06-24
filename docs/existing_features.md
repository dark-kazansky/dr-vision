# Doc Intelligence — Feature Documentation

> Last updated: 2026-06-24 | Version: 3.0

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Nuxt 4)                      │
│  Pages: OCR Upload, Workflow Builder, Settings, Observability │
│  Port: 3000                                                   │
└────────────────────────────────┬────────────────────────────┘
                                 │ HTTP/SSE
┌────────────────────────────────▼────────────────────────────┐
│                     Backend (FastAPI 0.109)                    │
│  Port: 8000                                                   │
│                                                               │
│  ┌─── Core Pipeline ───┐  ┌─── Workflow Engine ───┐          │
│  │ Parse (OCR)          │  │ Visual Builder (DAG)  │          │
│  │ Classify             │  │ Durable Execution     │          │
│  │ Extract              │  │ Job Queue + Scheduler │          │
│  │ Split                │  │ SSE Real-time Events  │          │
│  │ Layout Recognize     │  └──────────────────────┘          │
│  │ Table Recognize      │                                     │
│  │ Post-processing      │  ┌─── Data Services ────┐          │
│  │ Document Compare     │  │ Banking Data Mining   │          │
│  │ Batch Processing     │  │ Template Matching     │          │
│  │ Template Extract     │  │ Workflow Export/Import │          │
│  └──────────────────────┘  └──────────────────────┘          │
└──────┬──────────────────────────────────┬────────────────────┘
       │                                  │
┌──────▼──────┐  ┌───────────┐  ┌────────▼────────┐
│ PostgreSQL  │  │   MinIO   │  │  AI Providers   │
│ Port: 5433  │  │ Port: 9000│  │ LM Studio       │
│ ocr_results │  │ Object    │  │ Google Gemini   │
│ workflows   │  │ Storage   │  │ AWS Bedrock     │
│ banking     │  │           │  │ Ollama          │
│ auth        │  │           │  │ OpenAI-compat   │
└─────────────┘  └───────────┘  └─────────────────┘
```

**Tech Stack:**
- Backend: Python 3.11, FastAPI, asyncpg, Pydantic v2
- Frontend: Nuxt 4, Vue 3 Composition API, TypeScript, TailwindCSS
- Database: PostgreSQL 16 (JSONB storage for OCR results)
- Object Storage: MinIO
- AI: Multi-provider (LM Studio local, Google Gemini, AWS Bedrock, Ollama)

---

## Implemented Features (Code Complete)

### Core OCR Pipeline

| ID | Feature | Endpoints | Component |
|----|---------|-----------|-----------|
| feat-001 | Multi-model OCR (PNG/JPG/PDF) | `POST /ocr`, `POST /parse` | `components/parser.py` |
| feat-031 | Layout Recognition (DeepDoc ONNX) | `POST /layout/recognize`, `GET /layout/models` | `components/layout_recognizer.py` |
| feat-060 | Table Structure Recognition | `POST /table/recognize`, `GET /table/models` | `components/table_recognizer.py` |
| feat-061 | OCR Post-processing (auto-correct, confidence) | `POST /postprocess` | `components/ocr_postprocessor.py` |

**Details:**
- **Parse**: Upload image/PDF → OCR via configurable model → raw text + metadata. Results stored in PostgreSQL `ocr_results` table (JSONB).
- **Layout Recognize**: YOLOv10-based detection of 10 element types (title, text, table, figure, equation, etc.). ONNX model auto-downloaded from HuggingFace.
- **Table Recognize**: Detects rows/columns/cells within table regions. Export to JSON, CSV, Markdown, or HTML.
- **Post-processing**: Pattern-based correction (O→0 in numbers, Vietnamese diacritics), per-word confidence scoring, currency normalization.

### Document Classification & Extraction

| ID | Feature | Endpoints | Component |
|----|---------|-----------|-----------|
| feat-001 | Document Classification | `POST /classify`, `POST /classify/text` | `components/classifier.py` |
| feat-001 | Structured Extraction | `POST /extract` | `components/extractor.py` |
| feat-001 | Document Split | `POST /split` | `components/splitter.py` |
| feat-063 | Template Matching | CRUD `/templates`, `POST /templates/match`, `POST /templates/{id}/extract` | `services/template_service.py`, `services/template_matcher.py` |
| feat-065 | Document Comparison | `POST /compare/text`, `POST /compare/files` | `components/document_comparator.py` |

**Details:**
- **Classify**: LLM-based classification with configurable rules (doc_type + description). Supports file upload or raw text input.
- **Extract**: Schema-driven structured extraction (define fields + types → LLM extracts). Results stored in DB.
- **Split**: Split multi-document PDFs by content type or section.
- **Templates**: 6+ built-in templates (Vietnamese invoice, receipt, contract, bank statement, etc.). Auto-detect template → apply extraction schema.
- **Compare**: Line/word/paragraph diff with similarity scoring, unified diff output.

### Workflow Engine

| ID | Feature | Endpoints | Component |
|----|---------|-----------|-----------|
| feat-005 | Visual Workflow Builder | Frontend: `/workflow-builder` page | `useWorkflowState.ts`, `useNodeRegistry.ts` |
| feat-006 | Job Manager (queue, retry, status) | `GET /jobs`, `POST /jobs/{id}/cancel` | `services/job_queue.py`, `services/job_executor.py` |
| feat-007 | Stateful Execution | `GET /execution-states`, `GET /execution-states/{id}` | `services/execution_state.py` |
| feat-009 | Scheduling & Triggers | Cron-based triggers | `services/job_persistence.py` |
| feat-010 | Observability (monitoring, logging) | `GET /observability/metrics`, `GET /observability/traces` | `services/observability.py` |
| feat-050-054 | Durable Workflow Engine | `POST /durable/runs`, `GET /durable/runs/{id}`, SSE `/durable/runs/{id}/events` | `services/workflow_engine/` |
| feat-042 | Async Document Processing | `POST /documents/process`, `GET /documents/{id}/stream` (SSE) | `services/document_job_runner.py` |
| feat-062 | Multi-file Batch Processing | `POST /batch/process`, `GET /batch/{id}`, SSE `/batch/{id}/stream` | `services/batch_processor.py` |
| feat-064 | Workflow Export/Import | `GET /workflows/{id}/export`, `POST /workflows/import` | `api/v1/workflow_export.py` |

**Details:**
- **Visual Builder**: Vue Flow-based infinite canvas with drag-and-drop nodes, edge validation, minimap, undo/redo, auto-save.
- **Durable Engine**: Event-sourced state machine with PostgreSQL task queue, cooperative cancellation, resume on crash.
- **Batch Processing**: Upload folder/zip → parallel processing with SSE progress, per-file status, cancel support.

### Infrastructure & Data

| ID | Feature | Endpoints | Component |
|----|---------|-----------|-----------|
| feat-003 | Banking Data Mining | `POST /banking/statements`, `GET /banking/statements`, `GET /banking/stats` | `storage/banking_repository.py` |
| feat-012 | DB-First Persistence | OCR results, jobs, uploads in PostgreSQL | `storage/ocr_result_repository.py`, `storage/workflow_repository.py` |
| feat-013 | Data Store (tagged results) | `GET /data-store`, `POST /data-store`, `DELETE /data-store/{id}` | Via `workflow_repository.py` |
| feat-014 | JWT Authentication | `POST /auth/login`, `POST /auth/register`, Bearer token required | `auth/` module |
| feat-015 | Secrets Management | `.env.example` templates, env-var override, startup validation | `settings.py` |

### Frontend

| ID | Feature | Page/Component |
|----|---------|----------------|
| feat-002 | Upload UI (drag-drop, preview, results) | `pages/index.vue` |
| feat-004 | Settings (providers, models) | `pages/settings.vue` |
| feat-005 | Workflow Builder | `pages/workflow-builder.vue` |
| — | API Explorer | `pages/api-explorer.vue` |
| — | Observability Dashboard | `pages/observability.vue` |
| — | Login | `pages/login.vue` |

---

## Pending Features (Not Implemented)

### Deployment & Operations (Priority: HIGH)

| ID | Feature | Description | Complexity |
|----|---------|-------------|------------|
| feat-016 | HTTPS & Reverse Proxy | Nginx/Traefik with TLS termination, production CORS | Medium |
| feat-017 | Database Migrations | Alembic for versioned schema changes with rollback | Medium |
| feat-018 | CI/CD Pipeline | Automated lint, test, build, deploy (GitHub Actions) | Medium |
| feat-019 | Container Hardening & K8s | Production container configs, Kubernetes manifests | High |
| feat-020 | Backup & Disaster Recovery | Automated PostgreSQL + MinIO backup with restore procedures | Medium |
| feat-021 | Production Monitoring | Prometheus metrics, structured logging, uptime alerts | Medium |

### Code Quality (Priority: MEDIUM)

| ID | Feature | Description | Complexity |
|----|---------|-------------|------------|
| feat-022 | Fix Pre-existing Test Failures | Resolve failing tests, enable strict TypeScript | Medium |

### Architecture (Priority: LOW — defer until scale needed)

| ID | Feature | Description | Complexity |
|----|---------|-------------|------------|
| feat-023 | Monorepo Restructure | `services/` directory + `packages/common` shared lib | High |
| feat-024 | DR-Gateway Service | Reverse proxy routing to downstream services | Medium |
| feat-025 | DR-OCR Service | Isolated OCR/AI processing service | High |
| feat-026 | DR-Journey Service | Isolated workflow engine service | High |
| feat-027 | DR-Banking Service | Isolated banking data mining service | Medium |
| feat-028 | Inter-Service Communication | Service discovery, health checks, Redis messaging | High |
| feat-029 | Frontend Adaptation | Route through Gateway instead of direct backend | Low |
| feat-030 | Docker Compose Orchestration | Full multi-service compose with integration tests | Medium |

---

## Features NOT in feature_list.json (Future Roadmap)

| Feature | Description | Priority |
|---------|-------------|----------|
| Document Versioning | Store multiple OCR runs per file, compare results across models | Medium |
| Multi-tenant / Workspace | Per-team data isolation, org-level settings | High |
| Webhook Integration | Push results to external systems (ERP, CRM) on workflow completion | Medium |
| Human-in-the-Loop Review | Low-confidence results → review queue for human correction | High |
| Full-text Document Search | Search across all processed documents (PostgreSQL tsvector or Elasticsearch) | High |
| Audit Trail | Who uploaded/processed/modified what and when | Medium |
| Rate Limiting per User/Org | Cost management for AI model usage | Low |
| Export & Reporting Dashboard | Processing stats, accuracy metrics, cost per model | Medium |
| API Versioning (v1/v2) | Maintain backward compatibility during evolution | Low |
| Plugin System | Allow external components to register as workflow nodes | Low |

---

## API Reference Summary

### Public Endpoints (no auth required)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health + available models |
| POST | `/auth/login` | Authenticate → JWT tokens |
| POST | `/auth/register` | Create new user account |
| GET | `/docs` | Swagger UI |

### Authenticated Endpoints (Bearer token required)

#### OCR Pipeline
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ocr`, `/parse` | OCR a document (image or PDF) |
| POST | `/classify` | Classify document type |
| POST | `/classify/text` | Classify from raw text |
| POST | `/extract` | Structured data extraction |
| POST | `/split` | Split multi-document file |
| POST | `/postprocess` | Post-process OCR text |
| POST | `/layout/recognize` | Layout detection (ONNX) |
| POST | `/table/recognize` | Table structure extraction |
| POST | `/compare/text` | Compare two texts |
| POST | `/compare/files` | Compare two uploaded files |

#### Batch & Async Processing
| Method | Path | Description |
|--------|------|-------------|
| POST | `/batch/process` | Submit batch (folder/zip) |
| GET | `/batch/{id}` | Batch status |
| GET | `/batch/{id}/stream` | SSE progress stream |
| POST | `/batch/{id}/cancel` | Cancel batch |
| POST | `/documents/process` | Async single document |
| GET | `/documents/{id}/stream` | SSE progress for document |

#### Templates
| Method | Path | Description |
|--------|------|-------------|
| POST | `/templates` | Create template |
| GET | `/templates` | List templates |
| GET | `/templates/{id}` | Get template details |
| PUT | `/templates/{id}` | Update template |
| DELETE | `/templates/{id}` | Delete template |
| POST | `/templates/match` | Auto-detect template for text |
| POST | `/templates/{id}/extract` | Apply template to file |

#### Workflow & Jobs
| Method | Path | Description |
|--------|------|-------------|
| POST | `/durable/runs` | Start workflow run |
| GET | `/durable/runs/{id}` | Get run status |
| GET | `/durable/runs/{id}/events` | SSE real-time events |
| POST | `/durable/runs/{id}/cancel` | Cancel run |
| GET | `/workflows/{id}/export` | Export workflow JSON |
| POST | `/workflows/import` | Import workflow JSON |
| GET | `/jobs` | List all jobs |
| GET | `/execution-states` | List execution states |

#### Data & Storage
| Method | Path | Description |
|--------|------|-------------|
| GET | `/ocr-results` | List OCR results (paginated) |
| GET | `/ocr-results/{id}` | Get result by ID |
| GET | `/ocr-results/by-filename/{name}` | Get by filename |
| GET | `/ocr-results/stats` | Storage statistics |
| DELETE | `/ocr-results/{id}` | Delete result |
| GET | `/list-saved-files` | List all processed files |
| POST | `/banking/statements` | Store bank statement |
| GET | `/banking/statements` | List statements |
| GET | `/data-store` | List data store entries |

#### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/providers` | Available AI providers |
| GET | `/observability/metrics` | System metrics |
| GET | `/observability/traces` | Execution traces |

---

## Running the System

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16 (via Docker)

### Quick Start

```bash
# Start infrastructure
make up-infra

# Start backend (local dev)
cd backend && python main.py

# Start frontend (local dev)
cd frontend && npm run dev
```

### Full Docker Stack

```bash
# Development (hot-reload)
docker compose up -d

# Production
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

### Verification

```bash
make verify    # Run full pipeline: lint + tests + type check
make lint      # Backend ruff only
make test      # Backend pytest only
make health    # Check if services respond
```
