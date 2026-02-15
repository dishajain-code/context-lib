"""Core data models for Context Graph."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union


def _generate_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Node:
    """A node in the context graph representing a decision, signal, event, or outcome.

    Attributes:
        id: Unique identifier. Auto-generated UUID if not provided.
        type: Category of this node (e.g. "decision", "signal", "event", "outcome").
        content: The node payload — plain text or a JSON-serializable dict.
        signals: Key-value pairs used for similarity matching and retrieval.
        timestamp: When this node was created. Defaults to now (UTC).
        source: Optional origin identifier (e.g. "jira", "slack", "manual").
        confidence_score: Score between 0.0 and 1.0 indicating reliability.
    """

    type: str
    content: Union[str, Dict[str, Any]]
    id: str = field(default_factory=_generate_id)
    signals: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=_now)
    source: Optional[str] = None
    confidence_score: float = 1.0

    def __post_init__(self) -> None:
        if not self.type:
            raise ValueError("Node type must not be empty")
        if not self.content:
            raise ValueError("Node content must not be empty")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(
                f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}"
            )


@dataclass
class Edge:
    """A directed relationship between two nodes in the context graph.

    Attributes:
        source_id: ID of the origin node.
        target_id: ID of the destination node.
        relation: Type of relationship (e.g. "caused_by", "led_to", "related_to").
        weight: Optional strength of the relationship, between 0.0 and 1.0.
        timestamp: When this edge was created. Defaults to now (UTC).
    """

    source_id: str
    target_id: str
    relation: str
    weight: Optional[float] = None
    timestamp: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("Edge source_id must not be empty")
        if not self.target_id:
            raise ValueError("Edge target_id must not be empty")
        if not self.relation:
            raise ValueError("Edge relation must not be empty")
        if self.source_id == self.target_id:
            raise ValueError("Edge source_id and target_id must differ (no self-loops)")
        if self.weight is not None and not 0.0 <= self.weight <= 1.0:
            raise ValueError(
                f"weight must be between 0.0 and 1.0, got {self.weight}"
            )