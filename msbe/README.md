# M.DocAI MSBE — Microservice Backend (next gen)

A new microservice rewrite of the M.DocAI backend. Improves on `ms-backend/` by adding a first-class **orchestrator service** that owns workflow CRUD and graph-aware run execution (the same engine that landed in `backend/core/workflow_orchestrator.py`).

## Architecture

```
              ┌────────────────────────────────────────────┐
client ──►    │            API Gateway   :8090             │
              │  CORS · rate-limit · request log · proxy   │
              └─┬──────────┬───────────┬────────┬──────────┘
                │          │           │        │
        /workflows   /workflow-runs  /parse,    /classify,
        /workflows/run                /ocr      /classify-text
                │          │           │        │
                ▼          ▼           ▼        ▼
        ┌────────────────────┐   ┌──────────┐   ┌────────────┐
        │  Orchestrator :8091│   │ Parser   │   │ Classifier │
        │  · workflow store  │   │  :8001   │   │   :8002    │
        │  · run store       │   └──────────┘   └────────────┘
        │  · DAG executor    │
        │  · cancel + logs   │   …extractor :8003, splitter :8004,
        └────────────────────┘     schema-generator :8005
```

* **Gateway** (`gateway/`) is the only public entry point. It proxies file-bound calls (parse, classify, extract, split, generate-schema) directly to the matching service and forwards the orchestrator's HTTP surface (`/workflows*`, `/workflow-runs*`).
* **Orchestrator** (`services/orchestrator/`) owns saved-graph CRUD, the run history, and the DAG executor. It calls the worker services over HTTP via `ServiceClient` instead of importing them.
* **Worker services** are independently deployable. Each ships a `Dockerfile`, `requirements.txt`, and a small FastAPI app exposing one or two endpoints. Stubs are included so the service mesh boots; port them from `ms-backend/services/*` as needed.
* **Shared library** (`shared/dr_vision_msbe/`) holds typed schemas, the run/workflow stores, the condition evaluator, and the inter-service HTTP client.

## Why a second backend?

`ms-backend/` exists and works; this is not a replacement on day one. `msbe/` is where the new orchestrator-first design lives so you can iterate without disrupting `ms-backend/`. When `msbe/` reaches feature parity it can take over the namespace.

## Quick start

```bash
# Install the shared library once.
pip install -e msbe/shared

# Start everything in Docker.
cd msbe
docker compose up --build

# Or run a single service locally for development.
cd msbe/services/orchestrator
pip install -r requirements.txt
uvicorn main:app --port 8091 --reload
```

The gateway listens on **`8090`** by default to avoid clashing with `backend/` (8082) and `ms-backend/gateway` (8080).

## Endpoint inventory

| Method | Path                                  | Service       |
|-------:|---------------------------------------|---------------|
|  GET   | `/health`                             | Gateway (aggregated) |
|  POST  | `/parse`, `/ocr`                      | Parser        |
|  POST  | `/classify`                           | Classifier    |
|  POST  | `/classify-text`                      | Classifier    |
|  POST  | `/extract`, `/extract-text`           | Extractor     |
|  POST  | `/split`                              | Splitter      |
|  POST  | `/generate-schema`                    | Schema gen.   |
|  GET   | `/workflows`                          | Orchestrator  |
|  POST  | `/workflows`                          | Orchestrator  |
|  GET   | `/workflows/{id}`                     | Orchestrator  |
|  PUT   | `/workflows/{id}`                     | Orchestrator  |
| DELETE | `/workflows/{id}`                     | Orchestrator  |
|  POST  | `/workflows/{id}/run`                 | Orchestrator  |
|  POST  | `/workflows/run`                      | Orchestrator  |
|  GET   | `/workflow-runs`                      | Orchestrator  |
|  GET   | `/workflow-runs/{run_id}`             | Orchestrator  |
|  POST  | `/workflow-runs/{run_id}/cancel`      | Orchestrator  |
| DELETE | `/workflow-runs/{run_id}`             | Orchestrator  |
|  POST  | `/workflow-runs/clear-finished`       | Orchestrator  |

## Environment variables

| Variable                      | Default                     | Purpose                              |
|-------------------------------|-----------------------------|--------------------------------------|
| `GATEWAY_PORT`                | `8090`                      | Gateway HTTP port                    |
| `ORCHESTRATOR_SERVICE_URL`    | `http://orchestrator:8091`  | Orchestrator base URL                |
| `PARSER_SERVICE_URL`          | `http://parser:8001`        | Parser base URL                      |
| `CLASSIFIER_SERVICE_URL`      | `http://classifier:8002`    | Classifier base URL                  |
| `EXTRACTOR_SERVICE_URL`       | `http://extractor:8003`     | Extractor base URL                   |
| `SPLITTER_SERVICE_URL`        | `http://splitter:8004`      | Splitter base URL                    |
| `SCHEMA_GENERATOR_SERVICE_URL`| `http://schema-generator:8005` | Schema generator base URL         |
| `MSBE_DATA_DIR`               | `./data`                    | Where the orchestrator persists workflows + runs |
| `CORS_ORIGINS`                | `http://localhost:3000`     | Comma-separated CORS allowlist       |

Copy `.env.example` to `.env` to override any of these.

## Tests

```bash
# From repo root
python -m pytest msbe/tests -q
```

The smoke tests exercise the orchestrator service in isolation (stores, topology, condition routing) and the gateway proxy contract.
