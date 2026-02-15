"""Deterministic confidence scoring for Context Graph nodes.

Scoring formula
===============
  effective_score = base_confidence * time_decay * signal_boost * edge_boost

Where:
  - base_confidence : the node's stored confidence_score (0.0–1.0)
  - time_decay      : exp(-decay_rate * age_hours)
  - signal_boost    : (matched_signals / query_signals) if query signals provided, else 1.0
  - edge_boost      : 1 + log(1 + edge_count) * edge_weight_factor

All parameters are tuneable via ``ScoringConfig``.  The formula is fully
deterministic — given the same inputs it always produces the same output.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from context_graph.core.models import Edge, Node


@dataclass
class ScoringConfig:
    """Tuneable knobs for the scoring formula.

    Attributes:
        decay_rate: Exponential decay rate per hour. Higher = faster decay.
        edge_weight_factor: How much edge count boosts the score.
        reference_time: Fixed point-in-time for decay calculation.
            Defaults to ``None`` which means "use current UTC time".
    """

    decay_rate: float = 0.001
    edge_weight_factor: float = 0.1
    reference_time: datetime | None = None


def time_decay(node: Node, config: ScoringConfig) -> float:
    """Exponential decay based on node age in hours."""
    now = config.reference_time or datetime.now(timezone.utc)
    age_hours = max((now - node.timestamp).total_seconds() / 3600.0, 0.0)
    return math.exp(-config.decay_rate * age_hours)


def signal_overlap(node: Node, query_signals: Dict[str, Any]) -> float:
    """Fraction of query signals that match the node's signals (0.0–1.0)."""
    if not query_signals:
        return 1.0
    matched = sum(
        1
        for key, value in query_signals.items()
        if key in node.signals and node.signals[key] == value
    )
    return matched / len(query_signals)


def edge_boost(edges: List[Edge], config: ScoringConfig) -> float:
    """Boost factor based on how many edges reference this node."""
    return 1.0 + math.log(1.0 + len(edges)) * config.edge_weight_factor


def compute_score(
    node: Node,
    edges: List[Edge],
    query_signals: Dict[str, Any],
    config: ScoringConfig,
) -> float:
    """Compute the effective score for a node.

    Returns a float >= 0.  Higher is more relevant.
    """
    return (
        node.confidence_score
        * time_decay(node, config)
        * signal_overlap(node, query_signals)
        * edge_boost(edges, config)
    )