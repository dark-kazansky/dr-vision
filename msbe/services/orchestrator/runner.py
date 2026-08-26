"""
Workflow execution engine for the MSBE orchestrator.

Walks a graph in topological order, evaluates condition nodes to prune
unreachable branches, calls worker services over HTTP for each node, and
writes per-node status / logs into the run store as it goes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from dr_vision_msbe import (
    Condition,
    ConditionEvaluator,
    ConditionOperator,
    RunStore,
    ServiceClient,
)

from graph import index_nodes, outgoing, reachable_through, topological_order

logger = logging.getLogger(__name__)


class WorkflowCancelled(Exception):
    """Raised when a run is cancelled mid-execution."""


def _summarise(value: Any, limit: int = 200) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "…"
    try:
        s = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        s = str(value)
    return s if len(s) <= limit else s[:limit] + "…"


def _now_ms() -> int:
    return int(asyncio.get_event_loop().time() * 1000)


@dataclass
class WorkerClients:
    """Container for the HTTP clients used by node executors."""

    parser: ServiceClient
    classifier: ServiceClient
    extractor: ServiceClient
    splitter: ServiceClient

    async def close(self) -> None:
        await asyncio.gather(
            self.parser.close(),
            self.classifier.close(),
            self.extractor.close(),
            self.splitter.close(),
            return_exceptions=True,
        )


@dataclass
class FileBlob:
    """Lightweight handle to an uploaded file kept in memory by the gateway/orchestrator."""

    name: str
    content_type: str
    data: bytes


# ---------------------------------------------------------------------------
# Per-node executors. They reuse a small per-file OCR cache so a chain of
# parse/classify/extract/split nodes only OCRs once per (tier, formatting).
# ---------------------------------------------------------------------------

async def _call_parse(
    clients: WorkerClients,
    file_blob: FileBlob,
    tier: str,
    *,
    parse_formatting: bool,
    cache: Dict[str, Any],
) -> Dict[str, Any]:
    cache_key = f"{tier}:{int(parse_formatting)}"
    if cache_key in cache:
        return cache[cache_key]

    # The real parser service requires `model_id` (matches the monolith).
    # Resolve it from the tier so the orchestrator never sends an unknown model.
    from config import TierConfig  # local import: shared lib mirrors monolith

    model_id = TierConfig.get_parser_model(tier)

    files = {"file": (file_blob.name, file_blob.data, file_blob.content_type or "application/octet-stream")}
    data = {
        "model_id": model_id,
        "tier": tier,
        "process_all_pages": "true",
        "parse_formatting": "true" if parse_formatting else "false",
    }
    response = await clients.parser.post("/parse", files=files, data=data)
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(payload.get("error") or "Parse failed")
    cache[cache_key] = payload
    return payload


async def _run_parse(node, clients, file_blob, *, parse_formatting, cache):
    return await _call_parse(clients, file_blob, node.get("tier", "Normal"),
                             parse_formatting=parse_formatting, cache=cache)


async def _run_classify(node, clients, file_blob, *, cache, previous_text):
    rules = (node.get("config") or {}).get("rules") or []
    if not rules:
        raise RuntimeError("Classify node has no rules")
    text = previous_text
    if not text:
        parsed = await _call_parse(clients, file_blob, node.get("tier", "Normal"),
                                   parse_formatting=False, cache=cache)
        text = parsed.get("text", "")
    response = await clients.classifier.post(
        "/classify-text",
        data={
            "text": text,
            "classification_rules": json.dumps(rules),
            "tier": node.get("tier", "Normal"),
        },
    )
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(payload.get("error") or "Classify failed")
    return payload


async def _run_extract(node, clients, file_blob, *, cache, previous_text):
    cfg = node.get("config") or {}
    schema_fields = (cfg.get("schema") or {}).get("fields") or []
    if not schema_fields:
        raise RuntimeError("Extract node has no schema fields")
    text = previous_text
    if not text:
        parsed = await _call_parse(clients, file_blob, node.get("tier", "Normal"),
                                   parse_formatting=True, cache=cache)
        text = parsed.get("text", "")
    response = await clients.extractor.post(
        "/extract-text",
        data={
            "text": text,
            "extraction_schema": json.dumps(schema_fields),
            "extraction_target": cfg.get("target", "document"),
            "tier": node.get("tier", "Normal"),
        },
    )
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(payload.get("error") or "Extract failed")
    return payload


async def _run_split(node, clients, file_blob):
    cfg = node.get("config") or {}
    categories = cfg.get("categories") or []
    if not categories:
        raise RuntimeError("Split node has no categories")
    files = {"file": (file_blob.name, file_blob.data, file_blob.content_type or "application/octet-stream")}
    response = await clients.splitter.post(
        "/split",
        files=files,
        data={
            "categories": json.dumps(categories),
            "parser_tier": node.get("tier", "Normal"),
            "splitter_tier": node.get("tier", "Normal"),
            "allow_uncategorized": str(cfg.get("allow_uncategorized", True)).lower(),
        },
    )
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(payload.get("error") or "Split failed")
    return payload


def _evaluate_condition(node: Dict[str, Any], previous_result: Any) -> Optional[int]:
    cfg = node.get("config") or {}
    raw_conditions = cfg.get("conditions") or []
    if not raw_conditions:
        return None
    conditions = [
        Condition(
            operator=ConditionOperator(c.get("operator", "equals")),
            value=c.get("value"),
            valueMin=c.get("valueMin"),
            valueMax=c.get("valueMax"),
        )
        for c in raw_conditions
    ]
    field_name = cfg.get("field_name") or "document_type"
    evaluator = ConditionEvaluator()
    if isinstance(previous_result, dict):
        result = evaluator.evaluate_from_previous_result(previous_result, conditions, field_name)
    else:
        result = evaluator.evaluate(previous_result, conditions, None)
    if not result.success:
        raise RuntimeError(f"Condition evaluation failed: {result.error}")
    return result.matched_index


# ---------------------------------------------------------------------------
# Top-level executor
# ---------------------------------------------------------------------------

async def execute_run(
    *,
    run_id: str,
    nodes: List[Dict[str, Any]],
    files: List[FileBlob],
    clients: WorkerClients,
    store: RunStore,
) -> Dict[str, Any]:
    nodes_by_id = index_nodes(nodes)
    order = topological_order(nodes)
    upload_node_ids = [n["id"] for n in nodes if n.get("type") == "upload"]
    pruned: Set[str] = set()

    def cancel_check() -> None:
        if store.is_cancel_requested(run_id):
            raise WorkflowCancelled()

    per_file_results: List[Dict[str, Any]] = []

    for file_index, file_blob in enumerate(files):
        cancel_check()
        store.log(run_id, f"Processing file {file_index + 1}/{len(files)}: {file_blob.name}")

        node_results: Dict[str, Any] = {}
        ocr_cache: Dict[str, Any] = {}

        for uid in upload_node_ids:
            node_results[uid] = {"files": [file_blob.name]}
            if file_index == 0:
                ts = _now_ms()
                store.update_node(
                    run_id,
                    uid,
                    status="completed",
                    started_at=ts,
                    finished_at=ts,
                    output_summary=_summarise({"files": [file_blob.name]}),
                )

        for node_id in order:
            cancel_check()
            node = nodes_by_id[node_id]
            ntype = node.get("type")

            if ntype == "upload":
                continue
            if node_id in pruned:
                if file_index == 0:
                    store.update_node(run_id, node_id, status="skipped")
                continue
            if node.get("inactive"):
                if file_index == 0:
                    store.update_node(
                        run_id, node_id,
                        status="skipped",
                        error="Inactive node — backend not implemented",
                    )
                continue

            incoming_source = next(
                (n["id"] for n in nodes if any(c["targetId"] == node_id for c in outgoing(n))),
                None,
            )
            previous_result = node_results.get(incoming_source) if incoming_source else None
            previous_text: Optional[str] = None
            if isinstance(previous_result, dict):
                previous_text = previous_result.get("text") or previous_result.get("parsed_text")

            if file_index == 0:
                store.update_node(run_id, node_id, status="running", started_at=_now_ms())

            try:
                if ntype == "ocr":
                    result = await _run_parse(node, clients, file_blob,
                                              parse_formatting=False, cache=ocr_cache)
                elif ntype == "parse":
                    result = await _run_parse(node, clients, file_blob,
                                              parse_formatting=True, cache=ocr_cache)
                elif ntype == "classify":
                    result = await _run_classify(node, clients, file_blob,
                                                 cache=ocr_cache, previous_text=previous_text)
                elif ntype == "extract":
                    result = await _run_extract(node, clients, file_blob,
                                                cache=ocr_cache, previous_text=previous_text)
                elif ntype == "split":
                    result = await _run_split(node, clients, file_blob)
                elif ntype == "condition":
                    matched_index = _evaluate_condition(node, previous_result)
                    result = {
                        "success": True,
                        "matched_index": matched_index,
                        "is_else": matched_index is None,
                    }
                    outs = outgoing(node)
                    chosen_targets = [c["targetId"] for c in outs if c.get("outputIndex") == matched_index]
                    other_targets = [c["targetId"] for c in outs if c.get("outputIndex") != matched_index]
                    keep = reachable_through(nodes_by_id, chosen_targets) if chosen_targets else set()
                    discard = reachable_through(nodes_by_id, other_targets)
                    pruned.update(t for t in discard if t not in keep)
                else:
                    raise RuntimeError(f"Unsupported node type: {ntype}")

                node_results[node_id] = result
                if file_index == 0:
                    store.update_node(
                        run_id, node_id,
                        status="completed",
                        finished_at=_now_ms(),
                        output_summary=_summarise(result),
                    )
            except WorkflowCancelled:
                raise
            except Exception as exc:
                if file_index == 0:
                    store.update_node(
                        run_id, node_id,
                        status="failed",
                        finished_at=_now_ms(),
                        error=str(exc),
                    )
                store.log(run_id, f"Node {node.get('label', node_id)} failed: {exc}",
                          level="error", node_id=node_id)
                raise

        per_file_results.append({"fileName": file_blob.name, "results": node_results})

    return {"files": per_file_results}


async def run_workflow(
    *,
    nodes: List[Dict[str, Any]],
    files: List[FileBlob],
    clients: WorkerClients,
    store: RunStore,
    workflow_id: Optional[str] = None,
    workflow_name: str = "Ad-hoc workflow",
) -> Dict[str, Any]:
    record = store.create(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        input_files=[f.name for f in files],
        nodes=[
            {"id": n["id"], "label": n.get("label") or n["id"], "type": n.get("type", "unknown")}
            for n in nodes
        ],
    )
    run_id = record["id"]
    store.start(run_id)

    try:
        result = await execute_run(
            run_id=run_id, nodes=nodes, files=files, clients=clients, store=store,
        )
        store.finish(run_id, status="completed")
        return {"run": store.get(run_id), "result": result}
    except WorkflowCancelled:
        store.finish(run_id, status="cancelled", error="Cancelled by user")
        return {"run": store.get(run_id), "result": None}
    except Exception as exc:
        logger.exception("Workflow run %s failed", run_id)
        store.finish(run_id, status="failed", error=str(exc))
        return {"run": store.get(run_id), "result": None, "error": str(exc)}
