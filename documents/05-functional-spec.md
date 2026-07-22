# Functional Specification — M.DocAI

This document describes *how each capability behaves*, from inputs to outputs, based on the implemented backend + frontend.

## 0. Architecture at a glance

```
Frontend (Nuxt 3 SPA)  →  FastAPI Backend  →  Functions layer  →  Agents (per provider)  →  Model
   useOCR/useJourney/       routes.py /         parser, classifier,   bedrock/google/poe/     Claude / Gemini /
   useWorkflowApi           routes_workflows     extractor, splitter,  lmstudio/ollama/vllm    POE / local
                                                 schema_generator,
                                                 condition_evaluator
```

- **Agent-based design**: each capability ("function") is given an *agent* selected by the resolved tier→model→provider. `AgentFactory` builds OCR/VLM/LLM agents from a model spec.
- **Config**: `settings.yaml` (providers, models, upload/pdf/rate-limit/background settings) + `tier_config.py` (tier→model per capability) + env vars.

## 1. Input handling

- **Accepted types:** `png`, `jpg`, `jpeg`, `pdf` (from `upload.allowed_extensions`).
- **Max size:** 10 MB (`upload.max_size_mb`), validated streaming before save.
- **PDF rendering:** 200 DPI (`pdf.render_dpi`).
- **Storage:** files saved to a temp upload folder with a secure randomized name; removed after processing (`_safe_remove`). Path-traversal validation guards read endpoints.

## 2. Parse / OCR

**Endpoints:** `POST /ocr` (legacy alias) and `POST /parse`.

**Inputs:** `file`, `model_id`, `force_ocr` (default false), `parse_formatting` (default true), `process_all_pages` (default true), `tier` (default Normal), plus optional inline extraction params (`extraction_enabled`, `extraction_target`, `extraction_schema`, `extractor_model`).

**Flow:**
1. Validate file (type/size), save to temp.
2. If background enabled and PDF page count > `threshold_pages` (5): create a job, process on a daemon thread, return `{ background: true, job_id, message }`.
3. Otherwise (sync): resolve parser model from tier → build OCR agent → `Parser.parse(file, force_ocr)`.
4. If `parse_formatting`: run `TextParser.auto_parse` to normalize Markdown/HTML → clean text.
5. Persist raw OCR `.txt` (in `data/raw_ocr`) and generate `.docx` (in `data/parsed`).
6. If inline extraction enabled + schema present: run extraction and attach `extraction` block.

**Output (sync):** `{ success, text, parsed_text, file_type, is_scanned, pages, filename, model, extraction? }`.

**Retrieval endpoints:** `GET /raw-ocr/{name}` (text), `GET /parsed/{name}` (DOCX download), `GET /list-saved-files`.

## 3. Classify

**Endpoints:** `POST /classify` (file) and `POST /classify-text` (text).

**Inputs:** `file`/`text`, `classification_rules` (JSON: array of `{type|doc_type, description}`), `parser_model_id`, optional `classifier_model_id` (else from tier), `tier`, `max_pages`, `is_multimodal`.

**Flow:** OCR the file (or use provided text) → build classifier LLM agent from tier → `Classifier.classify(text, rules)`. Rules must be non-empty and each must have a `doc_type`. Content-hash duplicate detection avoids re-saving identical files. Results appended to `data/classified/result.json`.

**Output:** `ClassifyResponse` → `results: [{ fileName, documentType, confidence, reasoning }]`.

## 4. Extract

**Endpoints:** `POST /extract` (file), `POST /extract-text` (text).

**Schema field:** `{ name, type (FieldType), description, required }`. **FieldType** and **ExtractionTarget** (`document` | `page` | `table_row`) are defined in `core/schemas.py`.

**Flow (`/extract`):**
1. OCR the file.
2. If `generate_schema` + `schema_prompt`: generate schema via `SchemaGenerator`; else parse provided `extraction_schema` JSON.
3. Build `ExtractionConfig(fields, target)` → `Extractor.extract(text, config)`.

**Output:** `{ success, structured_data, field_errors, filename }`. For `document` target → single object; for `page`/`table_row` → list.

**Schema generation** (`POST /generate-schema`): `prompt` + optional sample `file` (parsed, first 2000 chars) → returns proposed `schema` list. Uses the extractor tier's model.

## 5. Split

**Endpoint:** `POST /split`.

**Inputs:** `file`, `categories` (JSON: `[{name, description, order?}]`), `allow_uncategorized` (default true), `parser_tier`, `splitter_tier`, `split_mode` (`sections` | `document_type`).

**Sections mode:** `Splitter.split(...)` → categorized `chunks` (`content`, `category`, `page_number`, `confidence`) + `unknown_chunks`.

**Document-type mode:** `Splitter.split_by_document_type(...)` → `document_types` (`type_name`, `page_numbers[]`, `confidence`).

Results saved to `data/splited/{name}.json`. `split_mode` is validated (400 on invalid value).

## 6. Condition evaluation

**Endpoint:** `POST /condition/evaluate`.

**Inputs:** `conditions` (JSON: `[{operator, value?, valueMin?, valueMax?}]`), `previous_result` (JSON), `field_name` (default `document_type`).

**Operators:** equals, not_equals, greater_than, less_than, contains, between.

**Output:** `{ success, matched_index, is_else }` — `matched_index` is the first matching condition, or `null`/`is_else` for the implicit else.

## 7. Document Journey / Workflow

### 7.1 Node model
- Each node: `{ id, type, label?, tier?, config?, connections: [{targetId, outputIndex?}], inactive? }`.
- **Types:** `upload`, `parse`, `ocr`, `classify`, `extract`, `split`, `condition`. (`validate`, `user_script` exist in UI but are inactive/not implemented.)

### 7.2 Persistence & runs (endpoints)
- CRUD: `GET/POST /workflows`, `GET/PUT/DELETE /workflows/{id}`.
- Run: `POST /workflows/{id}/run` (saved), `POST /workflows/run` (ad-hoc, `nodes` form field).
- History: `GET /workflow-runs` (paginated, status filter), `GET /workflow-runs/{id}`, `POST /workflow-runs/{id}/cancel`, `DELETE /workflow-runs/{id}`, `POST /workflow-runs/clear-finished`.

### 7.3 Orchestration (`workflow_orchestrator.py`)
- Builds node index; computes **topological order** (Kahn; falls back to insertion order on cycles/legacy linear graphs).
- Processes **files one at a time** across the whole graph (OCR cache scoped per file).
- `ocr`/`parse` share a cache keyed by `tier:parse_formatting`; `parse` applies formatting, `ocr` does not.
- **Condition nodes** evaluate against the incoming node's result, then **prune** all branches reachable only through unmatched outputs (marked `skipped`).
- Per-node status pushed to `run_store` (running/completed/failed/skipped) with timings, output summary, and logs. Cooperative cancellation checked between nodes.
- Legacy `POST /workflow/execute` also exists (sequential step list: parse/classify/extract/split).

### 7.4 Frontend fallback
- `useJourney.executeWorkflow` prefers the backend orchestrator (`useWorkflowApi.checkAvailable`); if unreachable, runs an in-browser sequential executor hitting `/parse`, `/classify(-text)`, `/extract-text`, `/split`, `/condition/evaluate`, caching OCR text between nodes; records the run into `useJobs` (localStorage).

## 8. Tiers

- **Tiers:** Rapid, Normal, Advance (`Tier` enum).
- **Per-capability maps** in `tier_config.py`: parser, extractor, classifier LLM, splitter. Each maps a tier → `{model, provider}` (currently AWS Bedrock Claude Haiku/Sonnet/Opus).
- **Resolution:** `get_*_model_spec(tier)` → `(model_id, provider)`; validates model exists in `settings.yaml`, else falls back to Normal tier.
- **Frontend:** `GET /tier-config` exports maps + descriptions + colors; `useTierConfig` provides getters and a built-in fallback map.

## 9. Background jobs

- Config: `background_tasks.enabled`, `threshold_pages` (5), `job_ttl_seconds` (3600).
- Heavy PDFs offloaded to a daemon thread; `job_manager` tracks status/progress/result.
- Poll: `GET /job/{id}/status`, `GET /job/{id}/result` (409 if not yet complete).

## 10. Cross-cutting

- **CORS:** allowlist from `settings.yaml` (localhost + `aimsb.theworkpc.com`); restrictive fallback.
- **Rate limiting:** per-IP token bucket (default 30 rpm, burst 10).
- **Request logging:** `RequestLoggingMiddleware`.
- **Health/diagnostics:** `GET /health`, `GET /models/check`, `GET /test-logging`, `GET /` (API info).
- **Admin config:** `POST /api/config/update-bedrock-token` sets Bedrock token/region in env + `.env`.

## 11. Providers & models (from settings.yaml)

- **Providers:** Google Studio (Gemini), POE, LM Studio (local), AWS Bedrock, plus agent support for Ollama and vLLM.
- **Models include:** Gemini 2.5/3 family, POE assistant/qwen3-max/claude-opus-4.5, local DeepSeek-OCR / LightOnOCR, Bedrock Claude Haiku/Sonnet.
- New models/providers can be added in YAML without code changes (server restart).

## 12. Smart Sheet (planned — spec)

> Requirement #12. Not yet implemented; this section is the target specification. Complements Extract (§4): Extract pulls caller-defined *fields* from documents; Smart Sheet discovers and isolates *tabular regions* inside spreadsheets and emits them as typed datasets.

**Purpose:** A spreadsheet often holds several unrelated tables/blocks on one sheet (a summary block, a detail table, notes, a pivot). Smart Sheet digitalizes such files into machine-readable, dataframe-ready datasets — one per region — with descriptive metadata for downstream routing.

**Inputs (proposed):** `file` (spreadsheet — e.g. XLSX/CSV; exact accepted types TBD in build), `tier`, optional hints (e.g. sheets to include, min region size).

**Flow (proposed):**
1. **Identify regions** — intelligently detect the distinct regions within each sheet (contiguous tabular blocks separated by blank rows/cols, header inference, type-run detection). Record each region's location (sheet + cell range).
2. **Isolate & extract** — extract each region independently into a typed table (column names + inferred dtypes), trimming surrounding empty cells and separating adjacent/overlapping regions.
3. **Serialize to Parquet** — write **one Parquet file per region**. Parquet is a portable, type-preserving columnar format supported across languages; outputs load directly as dataframes (e.g. `pandas.read_parquet(...)`) with no re-typing.
4. **Generate metadata** — produce:
   - **Per region:** extracted location (sheet + cell range), title, description.
   - **Per spreadsheet:** title, description.
   The metadata assists downstream flows (routing, cataloging, human review).

**Output (proposed):**
```json
{ "success": true,
  "spreadsheet": { "title": "...", "description": "..." },
  "regions": [
    { "title": "...", "description": "...",
      "location": { "sheet": "Sheet1", "range": "A1:F23" },
      "parquet": "data/smartsheet/<name>/region_1.parquet",
      "columns": [{ "name": "...", "type": "..." }] }
  ] }
```

**Journey integration (proposed):** a **Smart Sheet** node emits one output per region (or a region collection) so condition/extract/classify nodes downstream can act per region.

**Open build questions:** accepted input formats (native XLSX vs. OCR'd spreadsheet images), region-detection model vs. heuristic, Parquet delivery (individual downloads vs. bundled archive), and retention of `data/smartsheet/` outputs. See [08-roadmap.md](08-roadmap.md).
