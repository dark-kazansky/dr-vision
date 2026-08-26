"""
Tests for the orchestrator graph helpers — pure logic, no I/O.
"""

from graph import index_nodes, outgoing, reachable_through, topological_order


def test_topological_order_linear():
    nodes = [
        {"id": "a", "type": "upload", "connections": [{"targetId": "b"}]},
        {"id": "b", "type": "parse", "connections": [{"targetId": "c"}]},
        {"id": "c", "type": "classify"},
    ]
    assert topological_order(nodes) == ["a", "b", "c"]


def test_topological_order_falls_back_when_no_edges():
    nodes = [{"id": "a", "type": "upload"}, {"id": "b", "type": "parse"}]
    assert topological_order(nodes) == ["a", "b"]


def test_topological_order_handles_branching():
    nodes = [
        {"id": "u", "type": "upload", "connections": [{"targetId": "p"}]},
        {"id": "p", "type": "parse", "connections": [{"targetId": "x"}, {"targetId": "y"}]},
        {"id": "x", "type": "classify"},
        {"id": "y", "type": "extract"},
    ]
    order = topological_order(nodes)
    assert order.index("u") < order.index("p")
    assert order.index("p") < order.index("x")
    assert order.index("p") < order.index("y")


def test_reachable_through_set():
    nodes_by_id = {
        "a": {"id": "a", "connections": [{"targetId": "b"}, {"targetId": "c"}]},
        "b": {"id": "b", "connections": [{"targetId": "d"}]},
        "c": {"id": "c"},
        "d": {"id": "d"},
    }
    assert reachable_through(nodes_by_id, ["b"]) == {"b", "d"}
    assert reachable_through(nodes_by_id, ["c"]) == {"c"}


def test_outgoing_normalises_string_form():
    node = {"id": "n", "connections": ["a", {"targetId": "b", "outputIndex": 1}]}
    assert outgoing(node) == [{"targetId": "a"}, {"targetId": "b", "outputIndex": 1}]
