# Product Requirements Document (PRD) — M.DocAI

## 1. Overview

M.DocAI is an AI **document digitalization** platform. It ingests PDF/image documents and, in a single pass, produces output that is both **human-readable** (layout-preserving text + DOCX) and **machine-readable** (structured JSON), plus classifications and document splits, and lets users chain these into automated pipelines ("Document Journeys").

It is delivered **self-service** across three surfaces of the same capability set:
- **Web app** — no-code, for business users.
- **REST API** — for direct integration (live today).
- **Client SDK** — for developers (roadmap; wraps the REST API).

"Self-service" is the product principle: a business user completes a task without IT, and a developer provisions access (sign-in → issue scoped API key → install SDK) and integrates without an admin in the loop. The self-service developer backbone (IAM, API-key management, SDK) is the top roadmap priority — see §9 and [08-roadmap.md](08-roadmap.md).

- **Backend:** FastAPI service (default port 8082), agent-based architecture.
- **Frontend:** Nuxt 3 / Vue 3 SPA.
- **Model providers:** AWS Bedrock (Claude), Google Gemini, POE, LM Studio / Ollama / vLLM (local).

## 2. Goals

| Goal | Description |
|------|-------------|
| G1 | Digitalize documents into **human-readable** (clean, layout-preserving text + DOCX) **and machine-readable** (structured JSON) output from one pass |
| G2 | Classify documents into caller-defined types |
| G3 | Extract structured data via schema (manual, library, or AI-generated) |
| G4 | Split mixed/complex documents into sections or by document type |
| G5 | Let non-technical users build end-to-end pipelines visually |
| G6 | Give users control over speed/quality/cost via tiers |
| G7 | Expose all capabilities **self-service** via REST API and a client SDK, with self-service key provisioning |
| G8 | Handle large documents reliably (background jobs, run history) |

## 3. Non-goals (current release)

Not in the *current* release, but note the first three are the **committed top roadmap priorities** that complete the self-service promise — they are deferred, not abandoned:

- Full user authentication / role-based IAM. *(P0 — self-service backbone)*
- Self-service API-key lifecycle management. *(P0 — self-service backbone)*
- A packaged client SDK (language libraries). *(P1/P2 — self-service backbone)*
- A durable, shareable Document Profile / template Library.
- Regulatory-grade audit trail.
- "Smart Sheet" spreadsheet-style extraction.

(These are tracked as gaps — see [07-requirements-traceability.md](07-requirements-traceability.md).)

## 4. Personas

See [03-personas-and-use-cases.md](03-personas-and-use-cases.md). Primary: Operations processor, Business analyst, Automation owner, Developer/integrator, Administrator.

## 5. Feature requirements

### 5.1 Parse / OCR — Digitalization (G1) — ✅
- Upload PNG/JPG/JPEG/PDF (≤10 MB).
- Extract text; optionally force OCR on text-based PDFs (`force_ocr`).
- **Human-readable output:** preserve layout as Markdown/HTML; optional formatting parse to clean text (`parse_formatting`); downloadable **DOCX**.
- **Machine-readable output:** optional inline extraction attaches a structured-data (`extraction`) block to the same response, so one call yields both forms.
- Process single page or all pages (`process_all_pages`).
- Save raw OCR text and generate a downloadable **DOCX**.
- Endpoints: `POST /ocr`, `POST /parse`; retrieve via `GET /raw-ocr/{name}`, `GET /parsed/{name}`, `GET /list-saved-files`.

### 5.2 Classify (G2) — ✅
- Caller supplies classification rules (`doc_type` + `description`).
- Returns `documentType`, `confidence`, `reasoning`.
- Works from a file (`POST /classify`) or from already-OCR'd text (`POST /classify-text`).
- Duplicate-file detection via content hash.

### 5.3 Extract (G3) — ✅ (with gap on Library)
- Schema fields: `name`, `type`, `description`, `required`.
- Extraction target scope: `document`, `page`, or `table_row`.
- Schema sources: **manual** (form or JSON), **AI-generated** (`POST /generate-schema` from a prompt + optional sample doc). 🔴 *"from library" source is not persisted server-side.*
- Endpoints: `POST /extract`, `POST /extract-text`.

### 5.4 Split (G4) — ✅
- **Sections mode**: split into user-defined categories (e.g., header/body/main table/footer/appendix), with optional uncategorized bucket.
- **Document-type mode**: identify document-type boundaries and page ranges within a mixed file.
- Endpoint: `POST /split` (`split_mode` = `sections` | `document_type`).

### 5.5 Document Journey / Workflow (G5) — ✅
- Visual node-graph builder on an infinite pan/zoom canvas.
- Node types: **Upload, Parse, OCR, Classify, Extract, Split, Condition** (✅); **Validate, User Script** (🔴 shown, backend not implemented).
- Condition nodes support operators (equals, not_equals, greater_than, less_than, contains, between) and **multiple outputs** (one per condition + Else) for branching.
- Save/load workflows; run against one or many files.
- Backend orchestrator executes graph in topological order with branch pruning, OCR caching per (file, tier), and cooperative cancellation. Falls back to in-browser execution if orchestrator unreachable.
- Endpoints: `/workflows*` (CRUD + run), `/workflows/run` (ad-hoc), `/workflow-runs*` (history), `/condition/evaluate`.

### 5.6 Tiered processing (G6) — ✅
- Three tiers: **Rapid / Normal / Advance**, each mapping to a model per capability (parser, extractor, classifier, splitter).
- Frontend fetches mapping via `GET /tier-config`; falls back to a built-in map if unavailable.
- Non-existent model in a tier falls back to the Normal-tier model.

### 5.7 Self-service access — API & SDK (G7) — 🟡
- ✅ **Live REST API** for every capability (parse/classify/extract/split/journey), with interactive `/docs` (Swagger) + `/redoc`.
- ✅ **DeployDialog** generates copyable cURL snippets per capability — self-serve starting point for integrators.
- ✅ Administrator can set AWS Bedrock credentials via **KeyDialog** → `POST /api/config/update-bedrock-token`.
- 🔴 **Self-service developer backbone not yet built:** no end-user sign-in, no self-service API-key issuance/scoping/revocation, no packaged client SDK, and public endpoints are unauthenticated (trusted-network assumption). These three (IAM, API keys, SDK) are the committed P0/P1 items that make the API *truly* self-service — see [08-roadmap.md](08-roadmap.md).

### 5.8 Jobs, background processing & monitoring (G8) — 🟡
- Large PDFs (> threshold pages) run as background jobs; client polls `GET /job/{id}/status` and `GET /job/{id}/result`.
- **Jobs view**: run-history dashboard with stat tiles (total/running/completed/failed/queued), searchable table, per-node detail drawer, logs, auto-refresh, cancel/delete/clear.
- 🟡 Logging is operational (request logging middleware, run logs); 🔴 no dedicated audit trail / compliance log store.

## 6. Non-functional requirements

| Area | Requirement | Status |
|------|-------------|--------|
| Performance | Non-blocking processing (async + threads); OCR result caching in journeys | ✅ |
| Scalability | Background jobs for heavy documents; TTL cleanup of job results | ✅ |
| Reliability | Retry logic for provider calls; graceful tier fallback; safe temp-file cleanup | ✅ |
| Rate limiting | Per-client-IP token-bucket (default 30 rpm, burst 10) | ✅ |
| Security | CORS allowlist; secure file save; path traversal validation on file reads | 🟡 (no user auth) |
| File constraints | PNG/JPG/JPEG/PDF, ≤10 MB, PDF rendered at 200 DPI | ✅ |
| Observability | Structured request logging; run/node status + logs | 🟡 |
| Configurability | YAML config + env overrides; tier mapping in code; hot model/provider add | ✅ |

## 7. Constraints & dependencies

- Requires model-provider credentials (AWS Bedrock token, Google/POE API keys) or local model servers.
- Default file size limit 10 MB; supported types limited to PDF/PNG/JPG/JPEG.
- Model availability depends on external providers; local models require LM Studio/Ollama/vLLM running.

## 8. Assumptions

- Deployment is internal/enterprise (MSB), initially trusted-network — explaining the lack of end-user auth.
- Configuration is managed by administrators, not end users (except Bedrock token via KeyDialog).

## 9. Release readiness summary

Core document **digitalization** (parse to human- and machine-readable output, classify, extract, split, journey, tiers, jobs) is implemented and usable today, both no-code in the web app and via the live REST API. The primary gap is the **self-service developer backbone — IAM/login, self-service API-key management, and a client SDK** — which turns "there is an API" into "developers can provision and integrate on their own." Secondary gaps: a persistent Profile Library, a formal audit trail, and Smart Sheet. See the traceability matrix.
