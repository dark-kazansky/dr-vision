# Epics & User Stories — M.DocAI

Status: ✅ Implemented · 🟡 Partial · 🔴 Not built.
IDs are stable references for the backlog and traceability matrix.

---

## EPIC A — Parse / OCR ✅

**A1** — *As an ops processor, I want to upload a PDF or image and get its text so I don't re-type it.* ✅
- **AC:** Accepts PNG/JPG/JPEG/PDF ≤10 MB; returns extracted text; rejects unsupported types/oversize with a clear error.

**A2** — *As a user, I want the layout (tables, headings) preserved.* ✅
- **AC:** Result available as Markdown/HTML "Parsed Result"; tables rendered; raw text also available.

**A3** — *As a user, I want to process all pages of a multi-page PDF.* ✅
- **AC:** `process_all_pages` toggle; all pages processed; page count returned.

**A4** — *As a user, I want to download the result as a Word document.* ✅
- **AC:** DOCX generated and downloadable via `/parsed/{name}`.

**A5** — *As a user, I want to force OCR on a digital PDF when its embedded text is bad.* ✅
- **AC:** `force_ocr` flag re-OCRs instead of using embedded text.

**A6** — *As a user, I want to edit the parsed result before using it.* ✅
- **AC:** FullScreenEditor with Preview / editable Raw / Parsed columns and page navigation.

---

## EPIC B — Classify ✅

**B1** — *As an analyst, I want to define my own document types and have documents sorted into them.* ✅
- **AC:** Rules = doc_type + description; empty/invalid rules rejected; returns type + confidence + reasoning.

**B2** — *As a user, I want to classify without re-OCRing when I already have the text.* ✅
- **AC:** `POST /classify-text` accepts text directly.

**B3** — *As a user, I want duplicate uploads detected.* ✅
- **AC:** Content-hash duplicate detection avoids re-saving identical files.

---

## EPIC C — Extract ✅ / 🟡

**C1** — *As an analyst, I want to define an extraction schema (fields) manually.* ✅
- **AC:** Fields with name/type/description/required; form or JSON entry.

**C2** — *As an analyst, I want AI to propose a schema from a description.* ✅
- **AC:** `POST /generate-schema` from prompt (+ optional sample doc) returns fields.

**C3** — *As a user, I want to extract at document / per-page / per-table-row scope.* ✅
- **AC:** `extraction_target` = document | page | table_row; output shape matches target.

**C4** — *As an analyst, I want to save and reuse schemas from a shared library.* 🔴
- **AC (target):** Schemas persist server-side, are listable, and selectable in Extract and Journey. *(Not implemented — see gap C4.)*

---

## EPIC D — Split ✅

**D1** — *As a user, I want to split a mixed PDF into its constituent documents by type.* ✅
- **AC:** `split_mode=document_type` returns type + page ranges + confidence.

**D2** — *As a user, I want to split one document into structural sections.* ✅
- **AC:** `split_mode=sections` returns categorized chunks; optional uncategorized bucket.

**D3** — *As a user, I want auto-named separated outputs.* 🟡
- **AC (target):** Each split document is auto-named and individually downloadable. *(Boundaries/ranges returned; per-file export/naming not fully realized.)*

---

## EPIC E — Document Journey / Workflow ✅ / 🟡

**E1** — *As an automation owner, I want to visually build a pipeline of steps.* ✅
- **AC:** Drag-drop nodes (Upload, Parse, OCR, Classify, Extract, Split, Condition), connect, rename, zoom/pan.

**E2** — *As an automation owner, I want conditional branching based on results.* ✅
- **AC:** Condition node with operators (equals/not_equals/greater/less/contains/between) and multiple outputs + Else; unmatched branches pruned.

**E3** — *As a user, I want to save and reload workflows.* ✅
- **AC:** Save (name+desc) / load / clear; persisted server-side and in localStorage.

**E4** — *As a user, I want to run a workflow on one or many files.* ✅
- **AC:** `/workflows/{id}/run` and `/workflows/run`; per-file results aggregated.

**E5** — *As a user, I want the workflow to run reliably server-side.* ✅
- **AC:** Topological execution, OCR caching per (file,tier), cooperative cancel; in-browser fallback if orchestrator unreachable.

**E6** — *As a user, I want validation and custom-script steps.* 🔴
- **AC (target):** Validate and User Script nodes execute. *(Shown as "coming soon", backend not implemented.)*

---

## EPIC F — Tiers ✅

**F1** — *As a user, I want to choose speed vs. quality per task.* ✅
- **AC:** Rapid/Normal/Advance selector; mapping fetched from `/tier-config`; per-tier model per capability.

**F2** — *As an admin, I want a bad tier config to degrade gracefully.* ✅
- **AC:** Non-existent model in a tier falls back to Normal-tier model with a warning.

---

## EPIC G — Jobs, Background Processing & Monitoring 🟡

**G1** — *As a user, I want large documents processed without the UI hanging.* ✅
- **AC:** > threshold pages → background job; `job_id` returned; poll status/result.

**G2** — *As an operator, I want a dashboard of runs with status and logs.* ✅
- **AC:** Jobs view: stat tiles as filters, searchable table, per-node detail + logs, auto-refresh, cancel/delete/clear.

**G3** — *As a compliance officer, I want an immutable audit trail of who did what.* 🔴
- **AC (target):** Durable, user-attributed audit log. *(Only operational logging today.)*

---

## EPIC H — Deploy / API access 🟡

**H1** — *As a developer, I want ready-to-use API snippets per capability.* ✅
- **AC:** DeployDialog generates copyable cURL for parse/classify/extract/split/journey.

**H2** — *As an admin, I want to configure model credentials in-app.* ✅
- **AC:** KeyDialog sets AWS Bedrock token + region via API.

**H3** — *As a developer, I want a client SDK.* 🔴
- **AC (target):** Installable language SDK wrapping the API.

**H4** — *As an admin, I want to issue and manage API keys for callers.* 🔴
- **AC (target):** Create/revoke/scope API keys; keys required on public endpoints.

---

## EPIC I — Identity & Access 🔴

**I1** — *As an admin, I want users to log in.* 🔴
**I2** — *As an admin, I want role-based permissions (IAM).* 🔴
- **AC (target):** Authenticated sessions; roles gate features/endpoints.

---

## EPIC J — Document Profile Library 🔴

**J1** — *As an analyst, I want a reusable library of document profiles (type + schema + rules + categories).* 🔴
- **AC (target):** Save/browse/apply profiles across Classify/Extract/Split/Journey.

---

## EPIC K — Smart Sheet 🔴 (now specified)

Turn a spreadsheet that contains several distinct tables/blocks ("regions") into cleanly separated, typed, dataframe-ready datasets with metadata.

**K1** — *As an analyst, I want the system to automatically detect the distinct regions in a spreadsheet, so I don't have to manually mark where each table starts and ends.* 🔴
- **AC (target):** Given a spreadsheet with multiple tables/blocks, the system identifies each region and its bounding location (sheet + cell range).

**K2** — *As an analyst, I want each detected region extracted and isolated as its own dataset.* 🔴
- **AC (target):** Each region is extracted independently; overlapping/adjacent regions are separated; empty padding is trimmed.

**K3** — *As a developer, I want each region output as a Parquet file so I can load it directly as a typed dataframe.* 🔴
- **AC (target):** One Parquet file per region; column types preserved; loadable with e.g. `pandas.read_parquet` with no re-typing.

**K4** — *As a downstream consumer, I want metadata describing each region and the sheet so I can route/interpret them programmatically.* 🔴
- **AC (target):** Per-region metadata = extracted location (sheet + range), title, description; per-spreadsheet metadata = title, description. Returned alongside the Parquet outputs.

**K5** — *As an automation owner, I want Smart Sheet available as a Journey node so it composes with parse/classify/extract/split.* 🔴
- **AC (target):** A Smart Sheet node emits one output per region (or a region collection) that downstream nodes can consume.
