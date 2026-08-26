# dr_vision_msbe

Shared Python package for MSBE services. Editable install:

```bash
pip install -e msbe/shared
```

## Modules

- `dr_vision_msbe.schemas` — Pydantic models for workflows, runs, and node configs.
- `dr_vision_msbe.condition_evaluator` — branch routing for condition nodes.
- `dr_vision_msbe.run_store` — file-backed, thread-safe run history.
- `dr_vision_msbe.workflow_store` — file-backed, thread-safe saved-workflow CRUD.
- `dr_vision_msbe.service_client` — async HTTP client with typed errors.
- `dr_vision_msbe.settings` — environment-driven service URL resolver.
