# API Reference — M.DocAI Backend

FastAPI service. Default base URL `http://localhost:8082` (frontend `API_BASE_URL`). Production display base used in DeployDialog snippets: `http://mdocai.msb.com.vn:8000`. Interactive docs at `/docs` (Swagger) and `/redoc`.

> **Self-service:** every capability below is callable directly over REST today (and via copyable DeployDialog snippets) — this is the self-service integration surface. A **client SDK** and **self-service API-key issuance** are on the near-term roadmap (see gaps H3/H4 and [08-roadmap.md](08-roadmap.md)); until then, the interactive `/docs` is the fastest self-serve starting point.
>
> **Auth:** none currently enforced on processing endpoints (trusted-network assumption). Rate limiting applies per client IP (default 30 rpm, burst 10). Once self-service key management ships, endpoints will require a per-key credential.

## Conventions
- File-processing endpoints use `multipart/form-data`.
- All support `tier` ∈ {`Rapid`, `Normal`, `Advance`} where applicable.
- Allowed files: PNG/JPG/JPEG/PDF, ≤10 MB.

---

## Document processing

### POST /parse  (alias: POST /ocr)
Parse a document to text (+ optional inline extraction).

**Form fields:** `file` (required), `model_id` (required), `force_ocr` (bool, false), `parse_formatting` (bool, true), `process_all_pages` (bool, true), `tier` (Normal), `extraction_enabled` (bool, false), `extraction_target`, `extraction_schema` (JSON), `extractor_model`.

**Response (sync):**
```json
{ "success": true, "text": "...", "parsed_text": "...", "file_type": "pdf",
  "is_scanned": true, "pages": 3, "filename": "doc.pdf", "model": "...",
  "extraction": { "success": true, "structured_data": {}, "field_errors": {} } }
```
**Response (background, PDF > 5 pages):**
```json
{ "success": true, "background": true, "job_id": "...", "message": "..." }
```

### POST /classify
**Form fields:** `file`, `parser_model_id`, `classifier_model_id` (optional→tier), `classification_rules` (JSON `[{type,description}]`), `tier`, `max_pages` (5), `is_multimodal` (false).
**Response:** `{ success, results: [{ fileName, documentType, confidence, reasoning }], error, error_type }`.

### POST /classify-text
Classify already-extracted text. **Fields:** `text`, `classification_rules`, `classifier_model_id?`, `tier`.

### POST /extract
**Fields:** `file`, `parser_model_id`, `extractor_model_id` (qwen3-max), `extraction_schema` (JSON), `extraction_target` (document), `generate_schema` (false), `schema_prompt?`.
**Response:** `{ success, structured_data, field_errors, filename }`.

### POST /extract-text
Extract from text. **Fields:** `text`, `extraction_schema`, `extraction_target`, `extractor_model_id?`, `tier`.

### POST /generate-schema
AI-generate an extraction schema. **Fields:** `prompt`, `file?`, `tier`.
**Response:** `{ success, schema: [{ name, type, description, required }] }`.

### POST /split
**Fields:** `file`, `categories` (JSON `[{name,description,order?}]`), `allow_uncategorized` (true), `parser_tier`, `splitter_tier`, `split_mode` (`sections` | `document_type`).
**Response:** `{ success, chunks[], unknown_chunks[], document_types[]|null, filename }`.

### POST /condition/evaluate
**Fields:** `conditions` (JSON), `previous_result` (JSON), `field_name` (document_type).
**Response:** `{ success, matched_index, is_else }`.

---

## Background jobs

### GET /job/{job_id}/status
`{ job_id, status, progress, created_at, completed_at }`. 404 if unknown.

### GET /job/{job_id}/result
Full payload when `completed`/`failed`; 409 while still processing.

---

## Workflows (persistence + run)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/workflows` | List saved workflows |
| POST | `/workflows` | Create (`name`, `description?`, `nodes[]`) → 201 |
| GET | `/workflows/{id}` | Fetch one |
| PUT | `/workflows/{id}` | Update |
| DELETE | `/workflows/{id}` | Delete |
| POST | `/workflows/{id}/run` | Run saved workflow (`files[]`) |
| POST | `/workflows/run` | Run ad-hoc graph (`files[]`, `nodes` JSON, `workflow_name?`) |
| POST | `/workflow/execute` | Legacy sequential step runner (`file`, `workflow` JSON) |

## Workflow runs (history)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/workflow-runs?status=&limit=&offset=` | List runs (limit 1–200) |
| GET | `/workflow-runs/{run_id}` | Full run record (nodes, logs, status) |
| POST | `/workflow-runs/{run_id}/cancel` | Cooperative cancel (409 if not running) |
| DELETE | `/workflow-runs/{run_id}` | Delete a run |
| POST | `/workflow-runs/clear-finished` | Remove completed/failed/cancelled runs |

---

## Configuration & diagnostics

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | `{ status, server_running, available_models }` (healthy/degraded/unhealthy) |
| GET | `/models/check` | Per-model availability + API-key presence, grouped by provider |
| GET | `/tier-config` | Tier→model maps + descriptions/colors for frontend |
| GET | `/raw-ocr/{name}` | Retrieve saved raw OCR text |
| GET | `/parsed/{name}` | Download generated DOCX |
| GET | `/list-saved-files` | List saved OCR/DOCX outputs |
| POST | `/api/config/update-bedrock-token` | Set AWS Bedrock bearer token + region (JSON body) |
| GET | `/` | API info | 
| GET | `/test-logging` | Logging sanity check |

---

## Error handling
- `400` — validation (bad file type/size, invalid JSON rules/schema/categories, invalid `split_mode`, empty rules).
- `404` — unknown job/workflow/run/file.
- `409` — job/result not ready, cancel on non-running run.
- `500` — processing failures (parse/classify/extract/split), save failures.

Legacy error types (from `/ocr`): `invalid_model`, `invalid_file`, `connection_error`, `processing_error`, `file_too_large`.

---

## Deploy snippet reference (DeployDialog)
The web app's DeployDialog emits copyable **cURL** snippets (multipart form) for each capability, against the production display base. These are documentation aids; the app itself calls the endpoints above. No SDK or auth header is currently included — see gaps H3/H4 in [07-requirements-traceability.md](07-requirements-traceability.md).
