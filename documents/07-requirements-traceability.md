# Requirements Traceability & Gap Analysis — M.DocAI

Maps the 13 items from [`requirement.md`](../requirement.md) to what is actually built in `backend/` + `frontend/`.

Legend: ✅ Implemented · 🟡 Partial · 🔴 Not built.

| # | Requirement | Status | Evidence in code | Gap / notes |
|---|-------------|:---:|------------------|-------------|
| 1 | **Job orchestrator and management** | 🟡 | `workflow_orchestrator.py` (topological graph exec, branch pruning, cancel), `run_store.py`, `background_tasks.job_manager`, `/workflow-runs*`, JobsView dashboard | Orchestration + run history + background jobs exist. Missing: scheduling, retries/queue management as a first-class "job scheduler", multi-worker scaling. |
| 2 | **Create API key and management** | 🔴 | — | No API-key issuance/revocation/scoping. Only admin Bedrock-token config (`/api/config/update-bedrock-token`). Public endpoints are unauthenticated. |
| 3 | **SDK to use M.DocAI; Deploy by API or SDK** | 🟡 | DeployDialog generates cURL snippets per capability | API deploy path exists (cURL docs + live REST). No packaged/downloadable client SDK in any language. |
| 4 | **Logs, Monitoring, Audit Trail** | 🟡 | `RequestLoggingMiddleware`, run/node logs in `run_store`, JobsView (stat tiles, logs, per-node status), `/health`, `/models/check` | Operational logging + monitoring present. Missing: durable, user-attributed **audit trail** and log retention/export for compliance. |
| 5 | **Document Profile Library** | 🔴 | Schemas/rules/categories are entered per-request; `data/` holds transient outputs | No persistent, browsable library of reusable document profiles (type + schema + rules + categories). AI schema-generation exists but results aren't stored as a library. |
| 6 | **Login & IAM** | 🔴 | — | No authentication, sessions, users, or roles. Assumes trusted network. |
| 7 | **OCR & Parse keeping original layout** | ✅ | `/parse` (`parse_formatting`), `TextParser`, DOCX generation, Parsed Result (Markdown/HTML with tables) | Complete. |
| 8 | **OCR & parse following a given template** | 🟡 | Extraction schema + `extraction_target` shape output; split "sections" mode by categories | Structured/templated output achievable via schema/categories. No dedicated "parse to a fixed template layout" feature distinct from extraction. |
| 9 | **OCR & Information Extraction by schema (library / manual / AI-generated)** | 🟡 | `/extract`, `/extract-text`, `SchemaBuilder` (manual + JSON), `/generate-schema` (AI) | Manual + AI-generated ✅. **"from library" source 🔴** (no persistent schema library — ties to #5). |
| 10 | **Smart Split (mixed file → separate docs w/ auto name; or single doc → parts)** | 🟡 | `/split` with `sections` and `document_type` modes; page ranges + confidence | Both split modes work. **Auto-naming and per-document export of separated files 🔴/🟡** — boundaries returned, but individual named output files aren't fully produced/downloadable. |
| 11 | **Classifier (system list or given list)** | 🟡 | `/classify`, `/classify-text`, ClassifyConfigPanel (user rules) | User-provided ("given list") ✅. **Built-in "system list" of default document types 🔴** — there is a `utils/documentTypes.ts` helper on the frontend, but no server-side canonical system taxonomy. |
| 12 | **Smart Sheet** | 🔴 | — | **Now specified** (see [05-functional-spec.md §12](05-functional-spec.md)): intelligently identify and isolate distinct **regions** within a spreadsheet, extract each region, and output them as **Parquet** (type-preserving, dataframe-ready) plus **metadata** for regions (location, title, description) and the sheet (title, description). Not yet built. |
| 13 | **Document Journey (end-to-end workflow combining OCR/split/classify/smart sheet/logic)** | ✅ | `JourneyWorkflow.vue`, `useJourney`, `workflow_orchestrator.py`, `/workflows*`, condition nodes | Core journey works (Parse/OCR/Classify/Extract/Split/Condition). Excludes Smart Sheet (#12) and Validate/User-Script nodes (shown "coming soon"). |

## Summary scoreboard

| Status | Count | Items |
|--------|:-----:|-------|
| ✅ Implemented | 2 | #7, #13 |
| 🟡 Partial | 6 | #1, #3, #4, #8, #9, #10, #11 *(7 rows — #8/#9/#10/#11 partial)* |
| 🔴 Not built | 4 | #2, #5, #6, #12 |

> Note: several "partial" items are close to complete; the biggest true gaps are **IAM/Login (#6)**, **API key management (#2)**, **Document Profile Library (#5)**, and **Smart Sheet (#12)** (now specified, not yet built).

## Top gaps → recommended priority

1. **Login & IAM (#6)** — prerequisite for any external/multi-tenant deployment. Blocks #2 and audit attribution.
2. **API key management (#2)** — required to expose the API safely to integrators (#3).
3. **Document Profile Library (#5)** — unlocks reusability across Classify/Extract/Split/Journey and completes #9 & #11.
4. **Audit trail (#4)** — compliance need for a banking deployment.
5. **Split auto-naming/export (#10)** — finishes the "Smart Split" promise.
6. **Smart Sheet (#12)** — now specified (see [05-functional-spec.md §12](05-functional-spec.md)); ready for build scoping.
7. **Client SDK (#3)** and **Validate/User-Script journey nodes (#13)** — developer-experience improvements.

See [08-roadmap.md](08-roadmap.md) for sequencing.
