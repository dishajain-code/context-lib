"""Tests for MemoryStorage backend."""

from context_graph.core.models import Edge, Node
from context_graph.storage.memory import MemoryStorage


def _make_storage_with_nodes():
    """Helper: returns a storage with 3 connected nodes."""
    s = MemoryStorage()
    n1 = Node(id="n1", type="incident", content="Outage", signals={"severity": "P1", "service": "payments"}, source="pagerduty")
    n2 = Node(id="n2", type="root_cause", content="Pool exhaustion", signals={"service": "payments"}, source="postmortem")
    n3 = Node(id="n3", type="decision", content="Add timeout", signals={"service": "payments"}, source="github")
    for n in (n1, n2, n3):
        s.save_node(n)
    s.save_edge(Edge(source_id="n1", target_id="n2", relation="caused_by"))
    s.save_edge(Edge(source_id="n2", target_id="n3", relation="resolved_by"))
    return s


class TestSaveAndGetNode:
    def test_save_and_retrieve(self):
        s = MemoryStorage()
        node = Node(id="x", type="event", content="deploy")
        s.save_node(node)
        assert s.get_node("x") is node

    def test_get_missing_returns_none(self):
        s = MemoryStorage()
        assert s.get_node("missing") is None

    def test_overwrite_existing(self):
        s = MemoryStorage()
        s.save_node(Node(id="x", type="a", content="old"))
        s.save_node(Node(id="x", type="a", content="new"))
        node = s.get_node("x")
        assert node is not None and node.content == "new"


class TestSaveAndGetEdge:
    def test_save_and_retrieve_edges(self):
        s = _make_storage_with_nodes()
        edges = s.get_edges_for_node("n1")
        assert len(edges) == 1
        assert edges[0].relation == "caused_by"

    def test_edges_indexed_both_directions(self):
        s = _make_storage_with_nodes()
        # n2 is target of n1->n2 and source of n2->n3
        edges = s.get_edges_for_node("n2")
        assert len(edges) == 2

    def test_duplicate_edge_ignored(self):
        s = _make_storage_with_nodes()
        s.save_edge(Edge(source_id="n1", target_id="n2", relation="caused_by"))
        edges = s.get_edges_for_node("n1")
        assert len(edges) == 1

    def test_edges_for_unconnected_node(self):
        s = MemoryStorage()
        assert s.get_edges_for_node("nope") == []


class TestGetRelated:
    def test_direct_neighbours(self):
        s = _make_storage_with_nodes()
        related = s.get_related("n1")
        assert len(related) == 1
        assert related[0].id == "n2"

    def test_middle_node_has_two_neighbours(self):
        s = _make_storage_with_nodes()
        related = s.get_related("n2")
        ids = {n.id for n in related}
        assert ids == {"n1", "n3"}

    def test_unconnected_node(self):
        s = MemoryStorage()
        s.save_node(Node(id="lone", type="x", content="alone"))
        assert s.get_related("lone") == []


class TestQuery:
    def test_filter_by_type(self):
        s = _make_storage_with_nodes()
        results = s.query({"type": "incident"})
        assert len(results) == 1
        assert results[0].id == "n1"

    def test_filter_by_source(self):
        s = _make_storage_with_nodes()
        results = s.query({"source": "github"})
        assert len(results) == 1
        assert results[0].id == "n3"

    def test_filter_by_signals(self):
        s = _make_storage_with_nodes()
        results = s.query({"signals": {"severity": "P1"}})
        assert len(results) == 1
        assert results[0].id == "n1"

    def test_combined_filters(self):
        s = _make_storage_with_nodes()
        results = s.query({"type": "incident", "signals": {"severity": "P1"}})
        assert len(results) == 1

    def test_no_match(self):
        s = _make_storage_with_nodes()
        assert s.query({"type": "nonexistent"}) == []

    def test_empty_filter_returns_all(self):
        s = _make_storage_with_nodes()
        assert len(s.query({})) == 3


class TestRemoveNode:
    def test_remove_existing(self):
        s = _make_storage_with_nodes()
        assert s.remove_node("n1") is True
        assert s.get_node("n1") is None

    def test_remove_cascades_edges(self):
        s = _make_storage_with_nodes()
        s.remove_node("n2")
        assert s.get_edges_for_node("n1") == []
        assert s.get_edges_for_node("n3") == []

    def test_remove_missing_returns_false(self):
        s = MemoryStorage()
        assert s.remove_node("nope") is False


class TestRemoveEdge:
    def test_remove_existing(self):
        s = _make_storage_with_nodes()
        assert s.remove_edge("n1", "n2", "caused_by") is True
        assert s.get_edges_for_node("n1") == []

    def test_remove_missing_returns_false(self):
        s = _make_storage_with_nodes()
        assert s.remove_edge("n1", "n2", "no_such_relation") is False


class TestAllNodesEdges:
    def test_all_nodes(self):
        s = _make_storage_with_nodes()
        assert len(s.all_nodes()) == 3

    def test_all_edges(self):
        s = _make_storage_with_nodes()
        assert len(s.all_edges()) == 2
