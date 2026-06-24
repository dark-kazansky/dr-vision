"""
Workflow Definition Store — Persist and load workflow definitions.

Converts between:
- Canvas DSL (user_canvas table) → WorkflowDefinition (durable engine)
- WorkflowDefinition → Canvas DSL (for saving back)

Also provides startup loading: reads all published canvases and registers
them with the scheduler so the recovery orchestrator can resume workflows.
"""

import logging
from typing import Any, Dict, List, Optional

import asyncpg

from services.workflow_engine.models import (
    ActivityDefinition,
    WorkflowDefinition,
)
from services.workflow_engine.retry_policy import ocr_policy

logger = logging.getLogger(__name__)


# =============================================================================
# Canvas DSL → WorkflowDefinition converter
# =============================================================================


def canvas_dsl_to_definition(
    canvas_id: str,
    title: str,
    dsl: Dict[str, Any],
    description: str = "",
    timeout_seconds: int = 3600,
) -> WorkflowDefinition:
    """
    Convert a user_canvas DSL to a WorkflowDefinition.

    DSL structure:
    {
        "components": {
            "node_id": {
                "obj": {"component_name": "ParseProcessor", "params": {"tier": "Normal", ...}},
                "downstream": ["node_id2"],
                "upstream": ["node_id0"],
            }
        },
        "path": ["node_id1", "node_id2", "node_id3"],
        "graph": {"nodes": [...], "edges": [...]},
    }
    """
    components = dsl.get("components", {})
    path = dsl.get("path", [])
    graph_nodes = dsl.get("graph", {}).get("nodes", [])

    # Build a lookup for graph node data (label, form/config)
    node_data_map: Dict[str, Dict[str, Any]] = {}
    for gn in graph_nodes:
        node_data_map[gn.get("id", "")] = gn.get("data", {})

    activities: List[ActivityDefinition] = []

    for node_id in path:
        comp = components.get(node_id)
        if comp is None:
            continue

        obj = comp.get("obj", {})
        component_name = obj.get("component_name", "")
        params = obj.get("params", {})
        upstream = comp.get("upstream", [])

        # Derive activity_type from component_name
        # e.g., "ParseProcessor" → "parse", "ClassifyProcessor" → "classify"
        activity_type = _component_name_to_type(component_name)

        # Get label from graph node data
        gn_data = node_data_map.get(node_id, {})
        label = gn_data.get("label", "") or component_name

        # Extract config (params minus "tier")
        tier = params.get("tier", "Normal")
        config = {k: v for k, v in params.items() if k != "tier"}
        config["tier"] = tier

        # Build depends_on from upstream (only nodes that are in path)
        depends_on = [u for u in upstream if u in components]

        activities.append(ActivityDefinition(
            activity_id=node_id,
            activity_type=activity_type,
            label=label,
            config=config,
            timeout_seconds=300,
            retry_policy=ocr_policy(),
            queue_name="default",
            depends_on=depends_on,
        ))

    return WorkflowDefinition(
        workflow_id=canvas_id,
        name=title,
        description=description,
        activities=activities,
        timeout_seconds=timeout_seconds,
    )


def definition_to_canvas_dsl(definition: WorkflowDefinition) -> Dict[str, Any]:
    """
    Convert a WorkflowDefinition back to canvas DSL format.

    Used when persisting a programmatically-created definition as a canvas.
    """
    components: Dict[str, Any] = {}
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    path: List[str] = []

    for i, activity in enumerate(definition.activities):
        node_id = activity.activity_id
        path.append(node_id)

        # Build component
        component_name = f"{activity.activity_type.capitalize()}Processor"
        params = dict(activity.config)

        components[node_id] = {
            "obj": {
                "component_name": component_name,
                "params": params,
            },
            "downstream": [],
            "upstream": list(activity.depends_on),
        }

        # Build graph node
        nodes.append({
            "id": node_id,
            "type": activity.activity_type,
            "data": {
                "label": activity.label,
                "name": component_name,
                "form": activity.config,
            },
        })

    # Build edges and downstream from depends_on
    for activity in definition.activities:
        for dep_id in activity.depends_on:
            if dep_id in components:
                components[dep_id]["downstream"].append(activity.activity_id)
                edges.append({
                    "id": f"edge_{dep_id}_{activity.activity_id}",
                    "source": dep_id,
                    "target": activity.activity_id,
                })

    # If no explicit dependencies, assume sequential (build edges from path order)
    has_deps = any(a.depends_on for a in definition.activities)
    if not has_deps and len(path) > 1:
        for i in range(len(path) - 1):
            src, tgt = path[i], path[i + 1]
            components[src]["downstream"].append(tgt)
            components[tgt]["upstream"].append(src)
            edges.append({"id": f"edge_{src}_{tgt}", "source": src, "target": tgt})

    return {
        "components": components,
        "graph": {"nodes": nodes, "edges": edges},
        "globals": {
            "sys.query": "",
            "sys.conversation_turns": 0,
            "sys.files": [],
            "sys.history": [],
        },
        "path": path,
        "history": [],
        "variables": {},
    }


# =============================================================================
# Definition Store (load from DB)
# =============================================================================


class DefinitionStore:
    """
    Load and cache workflow definitions from the user_canvas table.

    Used by the scheduler to resolve definitions for recovery.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._cache: Dict[str, WorkflowDefinition] = {}

    async def load_all(self) -> Dict[str, WorkflowDefinition]:
        """
        Load all canvas definitions from DB and convert to WorkflowDefinitions.

        Returns a dict of canvas_id → WorkflowDefinition.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, title, description, dsl FROM user_canvas ORDER BY updated_at DESC"
            )

        self._cache.clear()
        for row in rows:
            try:
                dsl = row["dsl"]
                if isinstance(dsl, str):
                    import json
                    dsl = json.loads(dsl)

                definition = canvas_dsl_to_definition(
                    canvas_id=row["id"],
                    title=row["title"],
                    dsl=dsl,
                    description=row["description"] or "",
                )

                # Only cache if it has activities
                if definition.activities:
                    self._cache[row["id"]] = definition

            except Exception as e:
                logger.debug("Failed to convert canvas %s: %s", row["id"], e)

        logger.info("DefinitionStore: loaded %d definitions from DB", len(self._cache))
        return dict(self._cache)

    async def load_one(self, canvas_id: str) -> Optional[WorkflowDefinition]:
        """Load a single canvas definition."""
        if canvas_id in self._cache:
            return self._cache[canvas_id]

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, title, description, dsl FROM user_canvas WHERE id = $1",
                canvas_id,
            )

        if row is None:
            return None

        dsl = row["dsl"]
        if isinstance(dsl, str):
            import json
            dsl = json.loads(dsl)

        definition = canvas_dsl_to_definition(
            canvas_id=row["id"],
            title=row["title"],
            dsl=dsl,
            description=row["description"] or "",
        )

        if definition.activities:
            self._cache[canvas_id] = definition

        return definition

    def get_cached(self, canvas_id: str) -> Optional[WorkflowDefinition]:
        """Get a definition from cache without DB hit."""
        return self._cache.get(canvas_id)

    @property
    def count(self) -> int:
        return len(self._cache)


# =============================================================================
# Helpers
# =============================================================================

_TYPE_MAP = {
    "parseprocessor": "parse",
    "classifyprocessor": "classify",
    "extractprocessor": "extract",
    "splitprocessor": "split",
    "layoutrecognizeprocessor": "layout_recognize",
    "layout_recognizeprocessor": "layout_recognize",
    "ocrprocessor": "parse",
}


def _component_name_to_type(component_name: str) -> str:
    """Convert a component_name like 'ParseProcessor' to activity type 'parse'."""
    key = component_name.lower().strip()
    if key in _TYPE_MAP:
        return _TYPE_MAP[key]

    # Fallback: strip "Processor" suffix and lowercase
    if key.endswith("processor"):
        return key[: -len("processor")]

    return key or "parse"
