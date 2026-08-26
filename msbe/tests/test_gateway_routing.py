"""
Tests that the gateway resolves request paths to the correct service.
Pure routing-table check; no upstream services need to be running.
"""

import importlib.util
import os
import sys

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
GATEWAY = os.path.join(os.path.dirname(HERE), "gateway")
SHARED_SRC = os.path.join(os.path.dirname(HERE), "shared", "src")
if SHARED_SRC not in sys.path:
    sys.path.insert(0, SHARED_SRC)


@pytest.fixture(scope="module")
def gateway_main():
    # Load gateway/main.py under a unique module name so it does not collide
    # with the orchestrator's main.py in other tests.
    spec = importlib.util.spec_from_file_location(
        "msbe_gateway_main", os.path.join(GATEWAY, "main.py")
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_workflow_runs_routes_to_orchestrator(gateway_main):
    name, _ = gateway_main._resolve_service("/workflow-runs")
    assert name == "orchestrator"


def test_workflows_routes_to_orchestrator(gateway_main):
    name, _ = gateway_main._resolve_service("/workflows/abc")
    assert name == "orchestrator"


def test_parse_routes_to_parser(gateway_main):
    name, _ = gateway_main._resolve_service("/parse")
    assert name == "parser"


def test_classify_text_does_not_match_classify_prefix_first(gateway_main):
    # Order matters: /classify-text comes before /classify in the table.
    name, _ = gateway_main._resolve_service("/classify-text")
    assert name == "classifier"


def test_unknown_path_returns_none(gateway_main):
    assert gateway_main._resolve_service("/nope") is None
