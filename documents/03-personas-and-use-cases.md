# Personas & Use Cases — M.DocAI

## Personas

### P1 — Ops Processor ("Lan")
- **Role:** Back-office document handler.
- **Technical level:** Low. Comfortable with web apps, not code.
- **Goals:** Convert scanned documents to text/data quickly; separate mixed PDFs; get results she can paste into other systems.
- **Frustrations:** Manual re-typing; documents that mix several forms in one file.
- **Uses:** Parse, Split, Classify views; downloads DOCX.

### P2 — Business Analyst ("Minh")
- **Role:** Defines what "a contract" or "a financial statement" looks like for the team.
- **Technical level:** Medium. Understands data fields, no programming.
- **Goals:** Define classification rules and extraction schemas; validate accuracy.
- **Uses:** Classify rules, SchemaBuilder (manual + AI-generated), Extract view; tier selection to tune accuracy.

### P3 — Automation Owner ("Huong")
- **Role:** Designs repeatable document processes.
- **Technical level:** Medium. Thinks in flows/branches.
- **Goals:** Build a single pipeline that OCRs → classifies → routes by type → extracts/splits accordingly; run on batches; monitor runs.
- **Uses:** Document Journey builder, Condition nodes, Jobs dashboard.

### P4 — Developer / Integrator ("Duc")
- **Role:** Builds systems that need document intelligence.
- **Technical level:** High.
- **Goals:** Call M.DocAI from another application; get JSON back.
- **Uses:** DeployDialog snippets, REST API, health/tier-config endpoints.

### P5 — Administrator ("Tuan")
- **Role:** Runs the platform.
- **Technical level:** High.
- **Goals:** Configure model credentials; keep the service healthy; watch throughput.
- **Uses:** KeyDialog (Bedrock token), `/health`, `/models/check`, logs, run history.

---

## Use cases

### UC1 — OCR a scanned contract and export to Word (P1)
1. Lan opens **Parse**, uploads `CONTRACT.pdf`.
2. Chooses **Normal** tier, enables "Process all PDF pages".
3. Clicks Process → sees Raw Result and Parsed Result (layout preserved).
4. Downloads the generated DOCX.
- **Value:** No re-typing; layout kept.

### UC2 — Classify an inbox of mixed documents (P2)
1. Minh opens **Classify**, defines rules: `Contract`, `Financial Statement (BCTC)`, `KYC`, `Correspondence`.
2. Uploads several files, enables "Process all files".
3. Each file returns a type + confidence + reasoning.
- **Value:** Automatic sorting with explainability.

### UC3 — Extract fields from financial statements (P2)
1. Minh opens **Extract**, describes the data in plain language → clicks **Generate Schema** (AI proposes fields).
2. Adjusts fields (name/type/required), sets target = `document`.
3. Uploads BCTC files → gets structured JSON per document.
- **Value:** Structured data without writing a schema by hand.

### UC4 — Split a mixed PDF into separate documents (P1)
1. Lan opens **Split**, chooses **Document-type mode**.
2. Provides the expected document types.
3. System returns type + page ranges per document within the file.
- **Value:** One upload → cleanly separated documents.

### UC5 — Split a report into structural sections (P2)
1. Choose **Sections mode**, define categories: header, body, main table, footer, appendix.
2. Upload report → get categorized chunks (+ optional uncategorized bucket).

### UC6 — Build an end-to-end Journey with branching (P3)
1. Huong opens **Doc Journey**; adds Upload → Parse → Classify.
2. Adds a **Condition** node: if type = `Contract` → Extract (contract schema); else if `BCTC` → Split; else → stop.
3. Saves the workflow; runs it on a batch of files.
4. Watches progress and per-node results in the **Jobs** dashboard.
- **Value:** Reusable, no-code automation with routing.

### UC7 — Process a large multi-page PDF asynchronously (P1/P5)
1. Upload a 40-page PDF (> threshold).
2. Backend returns a `job_id`; the app polls status until complete, then shows results.
- **Value:** Large files don't block the UI or time out.

### UC8 — Integrate parsing into another system (P4)
1. Duc opens **DeployDialog** on the Parse tab → copies the cURL snippet.
2. Adapts it into his service; sends files, receives JSON.
- **Value:** Embed document intelligence anywhere.

### UC9 — Configure model credentials (P5)
1. Tuan opens **KeyDialog**, pastes the AWS Bedrock bearer token + region.
2. Saved to environment/.env; new requests use it immediately.
- **Value:** Self-serve model backend configuration.

### UC10 — Monitor & manage runs (P3/P5)
1. Open **Jobs**; filter by status via stat tiles; search a run.
2. Open a run's detail drawer to inspect per-node status, timing, and logs.
3. Cancel a running workflow or clear finished runs.
- **Value:** Operational visibility.
