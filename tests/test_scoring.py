"""Tests for the confidence scoring module."""

import math
from datetime import datetime, timedelta, timezone

from context_graph.core.models import Edge, Node
from context_graph.core.scoring import (
    ScoringConfig,
    compute_score,
    edge_boost,
    signal_overlap,
    time_decay,
)

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _node(hours_ago=0, confidence=1.0, signals=None):
    return Node(
        type="event",
        content="test",
        timestamp=_NOW - timedelta(hours=hours_ago),
        signals=signals or {},
        confidence_score=confidence,
    )


def _config(**kwargs):
    return ScoringConfig(reference_time=_NOW, **kwargs)


class TestTimeDecay:
    def test_no_decay_for_new_node(self):
        node = _node(hours_ago=0)
        assert time_decay(node, _config()) == 1.0

    def test_decay_increases_with_age(self):
        young = time_decay(_node(hours_ago=1), _config())
        old = time_decay(_node(hours_ago=100), _config())
        assert young > old

    def test_higher_rate_decays_faster(self):
        node = _node(hours_ago=10)
        slow = time_decay(node, _config(decay_rate=0.001))
        fast = time_decay(node, _config(decay_rate=0.1))
        assert slow > fast

    def test_formula_is_deterministic(self):
        node = _node(hours_ago=24)
        cfg = _config(decay_rate=0.01)
        expected = math.exp(-0.01 * 24)
        assert time_decay(node, cfg) == expected


class TestSignalOverlap:
    def test_full_match(self):
        node = _node(signals={"a": 1, "b": 2})
        assert signal_overlap(node, {"a": 1, "b": 2}) == 1.0

    def test_partial_match(self):
        node = _node(signals={"a": 1})
        assert signal_overlap(node, {"a": 1, "b": 2}) == 0.5

    def test_no_match(self):
        node = _node(signals={"c": 3})
        assert signal_overlap(node, {"a": 1, "b": 2}) == 0.0

    def test_empty_query_returns_one(self):
        node = _node(signals={"a": 1})
        assert signal_overlap(node, {}) == 1.0

    def test_value_mismatch(self):
        node = _node(signals={"a": 1})
        assert signal_overlap(node, {"a": 999}) == 0.0


class TestEdgeBoost:
    def test_no_edges(self):
        assert edge_boost([], _config()) == 1.0

    def test_more_edges_higher_boost(self):
        one = edge_boost([Edge(source_id="a", target_id="b", relation="r")], _config())
        three = edge_boost(
            [Edge(source_id="a", target_id=f"b{i}", relation="r") for i in range(3)],
            _config(),
        )
        assert three > one > 1.0

    def test_weight_factor_scales_boost(self):
        edges = [Edge(source_id="a", target_id="b", relation="r")]
        low = edge_boost(edges, _config(edge_weight_factor=0.01))
        high = edge_boost(edges, _config(edge_weight_factor=1.0))
        assert high > low


class TestComputeScore:
    def test_all_factors_combined(self):
        node = _node(hours_ago=0, confidence=1.0, signals={"a": 1})
        edges = [Edge(source_id="x", target_id="y", relation="r")]
        score = compute_score(node, edges, {"a": 1}, _config())
        # confidence=1 * decay=1 * overlap=1 * edge_boost>1
        assert score > 1.0

    def test_zero_overlap_gives_zero(self):
        node = _node(signals={"a": 1})
        score = compute_score(node, [], {"b": 2}, _config())
        assert score == 0.0

    def test_zero_confidence_gives_zero(self):
        node = _node(confidence=0.0, signals={"a": 1})
        score = compute_score(node, [], {"a": 1}, _config())
        assert score == 0.0

    def test_higher_confidence_ranks_higher(self):
        low = _node(confidence=0.3, signals={"a": 1})
        high = _node(confidence=0.9, signals={"a": 1})
        cfg = _config()
        assert compute_score(high, [], {"a": 1}, cfg) > compute_score(low, [], {"a": 1}, cfg)
