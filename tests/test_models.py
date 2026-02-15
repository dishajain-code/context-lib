"""Tests for Node and Edge data models."""

import pytest
from datetime import datetime, timezone

from context_graph.core.models import Edge, Node


class TestNode:
    def test_create_minimal(self):
        node = Node(type="decision", content="Use Postgres")
        assert node.type == "decision"
        assert node.content == "Use Postgres"
        assert isinstance(node.id, str) and len(node.id) > 0
        assert node.signals == {}
        assert node.source is None
        assert node.confidence_score == 1.0
        assert node.timestamp.tzinfo is not None

    def test_create_with_all_fields(self):
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        node = Node(
            id="n1",
            type="incident",
            content={"summary": "outage", "duration_min": 45},
            signals={"severity": "P1", "service": "payments"},
            timestamp=ts,
            source="pagerduty",
            confidence_score=0.9,
        )
        assert node.id == "n1"
        assert node.content == {"summary": "outage", "duration_min": 45}
        assert node.signals["severity"] == "P1"
        assert node.timestamp == ts
        assert node.source == "pagerduty"
        assert node.confidence_score == 0.9

    def test_unique_ids_auto_generated(self):
        a = Node(type="a", content="a")
        b = Node(type="b", content="b")
        assert a.id != b.id

    def test_empty_type_raises(self):
        with pytest.raises(ValueError, match="type must not be empty"):
            Node(type="", content="something")

    def test_empty_content_raises(self):
        with pytest.raises(ValueError, match="content must not be empty"):
            Node(type="decision", content="")

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValueError, match="confidence_score"):
            Node(type="x", content="x", confidence_score=-0.1)

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValueError, match="confidence_score"):
            Node(type="x", content="x", confidence_score=1.1)

    def test_confidence_boundary_values(self):
        Node(type="x", content="x", confidence_score=0.0)
        Node(type="x", content="x", confidence_score=1.0)


class TestEdge:
    def test_create_minimal(self):
        edge = Edge(source_id="a", target_id="b", relation="caused_by")
        assert edge.source_id == "a"
        assert edge.target_id == "b"
        assert edge.relation == "caused_by"
        assert edge.weight is None
        assert edge.timestamp.tzinfo is not None

    def test_create_with_weight(self):
        edge = Edge(source_id="a", target_id="b", relation="led_to", weight=0.8)
        assert edge.weight == 0.8

    def test_empty_source_raises(self):
        with pytest.raises(ValueError, match="source_id must not be empty"):
            Edge(source_id="", target_id="b", relation="r")

    def test_empty_target_raises(self):
        with pytest.raises(ValueError, match="target_id must not be empty"):
            Edge(source_id="a", target_id="", relation="r")

    def test_empty_relation_raises(self):
        with pytest.raises(ValueError, match="relation must not be empty"):
            Edge(source_id="a", target_id="b", relation="")

    def test_self_loop_raises(self):
        with pytest.raises(ValueError, match="must differ"):
            Edge(source_id="a", target_id="a", relation="r")

    def test_weight_below_zero_raises(self):
        with pytest.raises(ValueError, match="weight"):
            Edge(source_id="a", target_id="b", relation="r", weight=-0.1)

    def test_weight_above_one_raises(self):
        with pytest.raises(ValueError, match="weight"):
            Edge(source_id="a", target_id="b", relation="r", weight=1.5)

    def test_weight_boundary_values(self):
        Edge(source_id="a", target_id="b", relation="r", weight=0.0)
        Edge(source_id="a", target_id="b", relation="r", weight=1.0)
