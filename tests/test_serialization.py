"""Tests for JSON graph serialization."""

import json
from datetime import datetime, timezone
from pathlib import Path

from context_graph.core.graph import Graph
from context_graph.core.models import Edge, Node
from context_graph.core.serialization import dump_graph, load_graph
from context_graph.storage.memory import MemoryStorage


def _make_graph():
    g = Graph(storage=MemoryStorage())
    g.add_node(Node(id="n1", type="incident", content="Outage", signals={"severity": "P1"}, source="pd"))
    g.add_node(Node(id="n2", type="decision", content={"action": "rollback"}, signals={"service": "api"}))
    g.add_edge(Edge(source_id="n1", target_id="n2", relation="led_to", weight=0.9))
    return g


class TestDumpGraph:
    def test_creates_file(self, tmp_path):
        g = _make_graph()
        path = tmp_path / "out.json"
        dump_graph(g, path)
        assert path.exists()

    def test_valid_json(self, tmp_path):
        g = _make_graph()
        path = tmp_path / "out.json"
        dump_graph(g, path)
        data = json.loads(path.read_text())
        assert "version" in data
        assert "nodes" in data
        assert "edges" in data

    def test_correct_counts(self, tmp_path):
        g = _make_graph()
        path = tmp_path / "out.json"
        dump_graph(g, path)
        data = json.loads(path.read_text())
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1


class TestLoadGraph:
    def test_roundtrip(self, tmp_path):
        original = _make_graph()
        path = tmp_path / "graph.json"
        dump_graph(original, path)

        restored = load_graph(path, storage=MemoryStorage())
        assert restored.get_node("n1") is not None
        assert restored.get_node("n2") is not None

    def test_node_fields_preserved(self, tmp_path):
        original = _make_graph()
        path = tmp_path / "graph.json"
        dump_graph(original, path)

        restored = load_graph(path, storage=MemoryStorage())
        n1 = restored.get_node("n1")
        assert n1.type == "incident"
        assert n1.content == "Outage"
        assert n1.signals == {"severity": "P1"}
        assert n1.source == "pd"

    def test_dict_content_preserved(self, tmp_path):
        original = _make_graph()
        path = tmp_path / "graph.json"
        dump_graph(original, path)

        restored = load_graph(path, storage=MemoryStorage())
        n2 = restored.get_node("n2")
        assert n2.content == {"action": "rollback"}

    def test_edges_preserved(self, tmp_path):
        original = _make_graph()
        path = tmp_path / "graph.json"
        dump_graph(original, path)

        restored = load_graph(path, storage=MemoryStorage())
        related = restored.get_related("n1")
        assert len(related) == 1
        assert related[0].id == "n2"

    def test_edge_weight_preserved(self, tmp_path):
        original = _make_graph()
        path = tmp_path / "graph.json"
        dump_graph(original, path)

        restored = load_graph(path, storage=MemoryStorage())
        edges = restored._storage.get_edges_for_node("n1")
        assert edges[0].weight == 0.9
