"""
Workflow orchestrator — graph-aware executor for M.DocAI pipelines.

Walks a node graph in topological order, evaluates condition outputs to
prune branches, caches OCR text per (file, tier) so downstream nodes do
not re-parse, supports per-node cancellation, and pushes per-node status
updates to ``run_store``.

Design notes:
    * Each node may declare `connections: [{targetId, outputIndex?}]` for
      its outgoing edges. Condition nodes have multiple outputs indexed
      0..N-1 (one per condition) plus a final "else" at index N.
    * The executor evaluates a node and, if it is a condition, only the
      matched output edge is followed. All other branches reachable only
      through unmatched outputs are marked ``skipped``.
    * Files are processed sequentially per node (the previous in-browser
      executor did the same). For now this keeps semantics identical to
      the existing frontend behaviour and avoids a behaviour change.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set

from config import Config
from config.tier_config import TierConfig
from core.agent_factory import AgentFactory
from core.run_store import run_store
from functions.classifier import Classifier, ClassificationRule
from functions.condition_evaluator import (
    Condition,
    ConditionEvaluator,
    ConditionOperator,
)
from functions.extractor import Extractor
from functions.parser import Parser
from functions.splitter import ChunkCategory, Splitter
from functions.text_parser import TextParser
from core.schemas import (
    ExtractionConfig,
    ExtractionTarget,
    FieldType,
    SchemaField,
)

logger = logging.getLogger(__name__)


class WorkflowCancelled(Exception):
    """Raised when a run is cancelled mid-execution."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summarise(value: Any, limit: int = 200) -> str:
    """Compact preview suitable for the run_store outputSummary field."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "…"
    try:
        s = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        s = str(value)
    return s if len(s) <= limit else s[:limit] + "…"


def _index_nodes(nodes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {n["id"]: n for n in nodes}


def _outgoing(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = node.get("connections") or []
    out: List[Dict[str, Any]] = []
    for c in raw:
        if isinstance(c, str):
            out.append({"targetId": c})
        elif isinstance(c, dict) and "targetId" in c:
            out.append(c)
    return out


def _topological_order(nodes: List[Dict[str, Any]]) -> List[str]:
    """
    Return node ids in topological order.

    Falls back to insertion order if the graph contains cycles or if no
    edges are declared (legacy linear workflows).
    """
    if not any(n.get("connections") for n in nodes):
        return [n["id"] for n in nodes]

    indeg: Dict[str, int] = {n["id"]: 0 for n in nodes}
    adj: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    for n in nodes:
        for c in _outgoing(n):
            tgt = c["targetId"]
            if tgt in indeg:
                adj[n["id"]].append(tgt)
                indeg[tgt] += 1

    # Kahn — preserve original ordering as tiebreaker for determinism.
    order_index = {n["id"]: i for i, n in enumerate(nodes)}
    ready = sorted([nid for nid, d in indeg.items() if d == 0], key=lambda x: order_index[x])
    out: List[str] = []
    while ready:
        nid = ready.pop(0)
        out.append(nid)
        for tgt in adj[nid]:
            indeg[tgt] -= 1
            if indeg[tgt] == 0:
                ready.append(tgt)
        ready.sort(key=lambda x: order_index[x])

    if len(out) != len(nodes):
        # Cycle — fall back to insertion order so we still execute something.
        logger.warning("Workflow graph contains a cycle; falling back to insertion order")
        return [n["id"] for n in nodes]
    return out


# ---------------------------------------------------------------------------
# Per-node executors
# ---------------------------------------------------------------------------

@dataclass
class NodeContext:
    """Per-file state passed to node executors."""

    config: Config
    file_path: str
    file_name: str
    ocr_cache: Dict[str, Any]      # tier -> parsed result
    previous_result: Any
    node_results: Dict[str, Any]


async def _run_parse(node: Dict[str, Any], ctx: NodeContext, *, parse_formatting: bool) -> Dict[str, Any]:
    cache_key = f"{node['tier']}:{int(parse_formatting)}"
    if cache_key in ctx.ocr_cache:
        return ctx.ocr_cache[cache_key]

    model_id = TierConfig.get_parser_model(node["tier"])
    ocr_agent = AgentFactory.create_from_config(ctx.config, model_id)
    parser = Parser(ocr_agent=ocr_agent)
    result = await asyncio.to_thread(parser.parse, ctx.file_path)
    if not result.success:
        raise RuntimeError(f"Parse failed: {result.error}")

    text = result.text
    if parse_formatting:
        text = await asyncio.to_thread(TextParser.auto_parse, text)

    payload = {
        "success": True,
        "text": text,
        "file_type": result.file_type,
        "is_scanned": result.is_scanned,
        "pages": result.pages,
    }
    ctx.ocr_cache[cache_key] = payload
    return payload


async def _run_classify(node: Dict[str, Any], ctx: NodeContext) -> Dict[str, Any]:
    rules_data = (node.get("config") or {}).get("rules") or []
    if not rules_data:
        raise RuntimeError("Classify node has no rules")

    # Reuse OCR if available, else parse first.
    parsed = await _run_parse(node, ctx, parse_formatting=False)
    text = parsed["text"]

    model_id = TierConfig.get_classifier_llm_model(node["tier"])
    llm_agent = AgentFactory.create_llm_agent(model_id, config=ctx.config)
    classifier = Classifier(agent=llm_agent)

    rules = [
        ClassificationRule(
            doc_type=r.get("doc_type") or r.get("type", ""),
            description=r.get("description", ""),
        )
        for r in rules_data
    ]
    result = await asyncio.to_thread(classifier.classify, text, rules)
    if not result.success:
        raise RuntimeError(f"Classify failed: {result.error}")

    return {
        "success": True,
        "document_type": result.document_type,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
    }


async def _run_extract(node: Dict[str, Any], ctx: NodeContext) -> Dict[str, Any]:
    cfg = node.get("config") or {}
    schema = (cfg.get("schema") or {}).get("fields") or []
    if not schema:
        raise RuntimeError("Extract node has no schema fields")

    parsed = await _run_parse(node, ctx, parse_formatting=True)
    text = parsed["text"]

    extractor_model = TierConfig.get_extractor_model(node["tier"])
    llm_agent = AgentFactory.create_llm_agent(extractor_model, config=ctx.config)
    extractor = Extractor(agent=llm_agent)

    fields = [
        SchemaField(
            name=f["name"],
            type=FieldType(f["type"]),
            description=f.get("description", ""),
            required=f.get("required", False),
        )
        for f in schema
    ]
    extraction_config = ExtractionConfig(
        fields=fields,
        target=ExtractionTarget(cfg.get("target", "document")),
    )
    result = await asyncio.to_thread(extractor.extract, text, extraction_config)
    if not result.success:
        raise RuntimeError(f"Extract failed: {result.error}")

    return {
        "success": True,
        "structured_data": result.structured_data,
        "field_errors": result.field_errors,
    }


async def _run_split(node: Dict[str, Any], ctx: NodeContext) -> Dict[str, Any]:
    cfg = node.get("config") or {}
    categories_cfg = cfg.get("categories") or []
    if not categories_cfg:
        raise RuntimeError("Split node has no categories")

    splitter_model = TierConfig.get_splitter_model(node["tier"])
    vlm_agent = AgentFactory.create_vlm_agent(splitter_model, config=ctx.config)
    splitter = Splitter(agent=vlm_agent)
    categories = [
        ChunkCategory(
            name=c["name"],
            description=c.get("description", ""),
            order=c.get("order", 0),
        )
        for c in categories_cfg
    ]
    result = await asyncio.to_thread(
        splitter.split,
        ctx.file_path,
        categories,
        cfg.get("allow_uncategorized", True),
    )
    if not result.success:
        raise RuntimeError(f"Split failed: {result.error}")

    return {
        "success": True,
        "chunks": [
            {
                "content": c.content,
                "category": c.category,
                "page_number": c.page_number,
                "confidence": c.confidence,
            }
            for c in (result.chunks or [])
        ],
        "unknown_chunks": [
            {
                "content": c.content,
                "category": c.category,
                "page_number": c.page_number,
            }
            for c in (result.unknown_chunks or [])
        ],
    }


def _evaluate_condition(node: Dict[str, Any], previous_result: Any) -> Optional[int]:
    """
    Evaluate a condition node. Returns the index of the matched condition,
    or None for the implicit ``else`` branch.
    """
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
        eval_result = evaluator.evaluate_from_previous_result(
            previous_result, conditions, field_name
        )
    else:
        eval_result = evaluator.evaluate(previous_result, conditions, None)
    if not eval_result.success:
        raise RuntimeError(f"Condition evaluation failed: {eval_result.error}")
    return eval_result.matched_index


# ---------------------------------------------------------------------------
# Branch pruning
# ---------------------------------------------------------------------------

def _reachable_through(
    nodes_by_id: Dict[str, Dict[str, Any]],
    start_ids: Iterable[str],
) -> Set[str]:
    """Return all node ids reachable from any of ``start_ids`` (inclusive)."""
    seen: Set[str] = set()
    stack = list(start_ids)
    while stack:
        nid = stack.pop()
        if nid in seen or nid not in nodes_by_id:
            continue
        seen.add(nid)
        for c in _outgoing(nodes_by_id[nid]):
            stack.append(c["targetId"])
    return seen


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

async def execute_run(
    *,
    run_id: str,
    nodes: List[Dict[str, Any]],
    file_paths: List[str],
    file_names: List[str],
    config: Config,
) -> Dict[str, Any]:
    """
    Execute a workflow run end-to-end.

    Updates ``run_store`` as the run progresses. Returns a dict with the
    aggregated per-node results once the run finishes.

    Raises ``WorkflowCancelled`` if cancellation is requested.
    """
    nodes_by_id = _index_nodes(nodes)
    order = _topological_order(nodes)

    upload_node_ids = [n["id"] for n in nodes if n.get("type") == "upload"]
    aggregated: Dict[str, Any] = {}

    # Track nodes that were ruled out by an upstream condition branch.
    pruned: Set[str] = set()

    def cancel_check() -> None:
        if run_store.is_cancel_requested(run_id):
            raise WorkflowCancelled()

    # We process files one at a time across the whole graph so OCR caches
    # naturally scope to a single file. This matches the previous frontend
    # behaviour and keeps per-file results visible.
    per_file_results: List[Dict[str, Any]] = []

    for file_index, (file_path, file_name) in enumerate(zip(file_paths, file_names)):
        cancel_check()
        run_store.log(run_id, f"Processing file {file_index + 1}/{len(file_paths)}: {file_name}")

        node_results: Dict[str, Any] = {}
        ocr_cache: Dict[str, Any] = {}

        # Mark upload nodes complete (only on first file to avoid repeats).
        for uid in upload_node_ids:
            node_results[uid] = {"files": [file_name]}
            if file_index == 0:
                run_store.update_node(
                    run_id,
                    uid,
                    status="completed",
                    started_at=run_store.get(run_id)["startedAt"] or 0,
                    finished_at=run_store.get(run_id)["startedAt"] or 0,
                    output_summary=_summarise({"files": [file_name]}),
                )

        for node_id in order:
            cancel_check()
            node = nodes_by_id[node_id]
            ntype = node.get("type")

            if ntype == "upload":
                continue

            # Skip pruned branches and inactive nodes.
            if node_id in pruned:
                if file_index == 0:
                    run_store.update_node(run_id, node_id, status="skipped")
                continue
            if node.get("inactive"):
                if file_index == 0:
                    run_store.update_node(
                        run_id,
                        node_id,
                        status="skipped",
                        error="Inactive node — backend not implemented",
                    )
                continue

            # Identify previous result from incoming edges (fallback: last result).
            incoming_source = next(
                (n["id"] for n in nodes if any(c["targetId"] == node_id for c in _outgoing(n))),
                None,
            )
            previous_result = node_results.get(incoming_source) if incoming_source else None

            ctx = NodeContext(
                config=config,
                file_path=file_path,
                file_name=file_name,
                ocr_cache=ocr_cache,
                previous_result=previous_result,
                node_results=node_results,
            )

            if file_index == 0:
                started_at = int(asyncio.get_event_loop().time() * 1000)
                run_store.update_node(run_id, node_id, status="running", started_at=started_at)

            try:
                if ntype == "ocr":
                    result = await _run_parse(node, ctx, parse_formatting=False)
                elif ntype == "parse":
                    result = await _run_parse(node, ctx, parse_formatting=True)
                elif ntype == "classify":
                    result = await _run_classify(node, ctx)
                elif ntype == "extract":
                    result = await _run_extract(node, ctx)
                elif ntype == "split":
                    result = await _run_split(node, ctx)
                elif ntype == "condition":
                    matched_index = _evaluate_condition(node, previous_result)
                    result = {
                        "success": True,
                        "matched_index": matched_index,
                        "is_else": matched_index is None,
                    }
                    # Prune branches: keep only reachable nodes through the matched output.
                    outs = _outgoing(node)
                    chosen_targets = [
                        c["targetId"] for c in outs if c.get("outputIndex") == matched_index
                    ]
                    other_targets = [
                        c["targetId"]
                        for c in outs
                        if c.get("outputIndex") != matched_index
                    ]
                    keep = _reachable_through(nodes_by_id, chosen_targets) if chosen_targets else set()
                    discard = _reachable_through(nodes_by_id, other_targets)
                    pruned.update(t for t in discard if t not in keep)
                else:
                    raise RuntimeError(f"Unsupported node type: {ntype}")

                node_results[node_id] = result
                if file_index == 0:
                    run_store.update_node(
                        run_id,
                        node_id,
                        status="completed",
                        finished_at=int(asyncio.get_event_loop().time() * 1000),
                        output_summary=_summarise(result),
                    )

            except WorkflowCancelled:
                raise
            except Exception as exc:
                if file_index == 0:
                    run_store.update_node(
                        run_id,
                        node_id,
                        status="failed",
                        finished_at=int(asyncio.get_event_loop().time() * 1000),
                        error=str(exc),
                    )
                run_store.log(run_id, f"Node {node.get('label', node_id)} failed: {exc}", level="error", node_id=node_id)
                raise

        per_file_results.append({"fileName": file_name, "results": node_results})

    aggregated["files"] = per_file_results
    return aggregated


async def run_workflow(
    *,
    nodes: List[Dict[str, Any]],
    file_paths: List[str],
    file_names: List[str],
    config: Config,
    workflow_id: Optional[str] = None,
    workflow_name: str = "Ad-hoc workflow",
) -> Dict[str, Any]:
    """
    High-level entry point: create a run record, execute, and return the
    final record.
    """
    record = run_store.create(
        workflow_id=workflow_id,
        workflow_name=workflow_name,
        input_files=list(file_names),
        nodes=[
            {"id": n["id"], "label": n.get("label") or n["id"], "type": n.get("type", "unknown")}
            for n in nodes
        ],
    )
    run_id = record["id"]
    run_store.start(run_id)

    try:
        result = await execute_run(
            run_id=run_id,
            nodes=nodes,
            file_paths=file_paths,
            file_names=file_names,
            config=config,
        )
        run_store.finish(run_id, status="completed")
        return {"run": run_store.get(run_id), "result": result}
    except WorkflowCancelled:
        run_store.finish(run_id, status="cancelled", error="Cancelled by user")
        return {"run": run_store.get(run_id), "result": None}
    except Exception as exc:
        logger.exception("Workflow run %s failed", run_id)
        run_store.finish(run_id, status="failed", error=str(exc))
        return {"run": run_store.get(run_id), "result": None, "error": str(exc)}
