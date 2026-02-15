"""Tests for the Graph class."""

import pytest

from context_graph.core.graph import Graph
from context_graph.core.models import Edge, Node
from context_graph.storage.memory import MemoryStorage


def _make_graph():
    """Helper: returns a graph with 3 connected nodes."""
    g = Graph(storage=MemoryStorage())
    n1 = g.add_node(Node(id="n1", type="incident", content="Outage", signals={"severity": "P1", "service": "payments"}))
    n2 = g.add_node(Node(id="n2", type="root_cause", content="Pool exhaustion", signals={"service": "payments"}))
    n3 = g.add_node(Node(id="n3", type="decision", content="Add timeout", signals={"service": "payments"}))
    g.add_edge(Edge(source_id="n1", target_id="n2", relation="caused_by"))
    g.add_edge(Edge(source_id="n2", target_id="n3", relation="resolved_by"))
    return g


class TestAddAndGetNode:
    def test_add_and_get(self):
        g = Graph(storage=MemoryStorage())
        node = g.add_node(Node(type="event", content="deploy"))
        result = g.get_node(node.id)
        assert result is node

    def test_add_returns_node(self):
        g = Graph(storage=MemoryStorage())
        node = g.add_node(Node(type="event", content="deploy"))
        assert isinstance(node, Node)
        assert node.type == "event"

    def test_get_missing_returns_none(self):
        g = Graph(storage=MemoryStorage())
        assert g.get_node("nope") is None


class TestAddEdge:
    def test_add_valid_edge(self):
        g = _make_graph()
        # edge already added in helper — just verify it works
        related = g.get_related("n1")
        assert len(related) == 1

    def test_add_edge_missing_source_raises(self):
        g = Graph(storage=MemoryStorage())
        g.add_node(Node(id="a", type="x", content="x"))
        with pytest.raises(ValueError, match="Source node"):
            g.add_edge(Edge(source_id="missing", target_id="a", relation="r"))

    def test_add_edge_missing_target_raises(self):
        g = Graph(storage=MemoryStorage())
        g.add_node(Node(id="a", type="x", content="x"))
        with pytest.raises(ValueError, match="Target node"):
            g.add_edge(Edge(source_id="a", target_id="missing", relation="r"))

    def test_add_edge_returns_edge(self):
        g = Graph(storage=MemoryStorage())
        g.add_node(Node(id="a", type="x", content="x"))
        g.add_node(Node(id="b", type="x", content="x"))
        edge = g.add_edge(Edge(source_id="a", target_id="b", relation="r"))
        assert isinstance(edge, Edge)


class TestRemoveNode:
    def test_remove_existing(self):
        g = _make_graph()
        assert g.remove_node("n1") is True
        assert g.get_node("n1") is None

    def test_remove_missing(self):
        g = Graph(storage=MemoryStorage())
        assert g.remove_node("nope") is False


class TestRemoveEdge:
    def test_remove_existing(self):
        g = _make_graph()
        assert g.remove_edge("n1", "n2", "caused_by") is True

    def test_remove_missing(self):
        g = _make_graph()
        assert g.remove_edge("n1", "n2", "nope") is False


class TestGetRelated:
    def test_depth_one(self):
        g = _make_graph()
        related = g.get_related("n1", max_depth=1)
        assert len(related) == 1
        assert related[0].id == "n2"

    def test_depth_two(self):
        g = _make_graph()
        related = g.get_related("n1", max_depth=2)
        ids = {n.id for n in related}
        assert ids == {"n2", "n3"}

    def test_depth_zero_returns_empty(self):
        g = _make_graph()
        assert g.get_related("n1", max_depth=0) == []

    def test_excludes_start_node(self):
        g = _make_graph()
        related = g.get_related("n2", max_depth=1)
        ids = {n.id for n in related}
        assert "n2" not in ids

    def test_no_duplicates_in_results(self):
        g = _make_graph()
        # Add a cycle: n3 -> n1
        g.add_edge(Edge(source_id="n3", target_id="n1", relation="feedback"))
        related = g.get_related("n1", max_depth=3)
        ids = [n.id for n in related]
        assert len(ids) == len(set(ids))


class TestSimilarContext:
    def test_returns_matching_nodes(self):
        g = _make_graph()
        results = g.similar_context(signals={"severity": "P1"})
        # n1 has severity=P1, others don't — n1 should rank first
        assert results[0].id == "n1"

    def test_all_nodes_with_shared_signal(self):
        g = _make_graph()
        results = g.similar_context(signals={"service": "payments"})
        assert len(results) == 3

    def test_no_match_returns_empty(self):
        g = _make_graph()
        results = g.similar_context(signals={"service": "nonexistent"})
        assert results == []

    def test_limit(self):
        g = _make_graph()
        results = g.similar_context(signals={"service": "payments"}, limit=1)
        assert len(results) == 1


class TestUpdateConfidence:
    def test_update_valid(self):
        g = _make_graph()
        node = g.update_confidence("n1", 0.5)
        assert node.confidence_score == 0.5
        fetched = g.get_node("n1")
        assert fetched is not None and fetched.confidence_score == 0.5

    def test_update_missing_node_raises(self):
        g = Graph(storage=MemoryStorage())
        with pytest.raises(ValueError, match="not found"):
            g.update_confidence("nope", 0.5)

    def test_update_invalid_score_raises(self):
        g = _make_graph()
        with pytest.raises(ValueError, match="confidence_score"):
            g.update_confidence("n1", 1.5)

    def test_update_affects_ranking(self):
        g = _make_graph()
        # Lower n1's confidence, n2 should rank higher for shared signal
        g.update_confidence("n1", 0.1)
        results = g.similar_context(signals={"service": "payments"})
        assert results[0].id != "n1"
