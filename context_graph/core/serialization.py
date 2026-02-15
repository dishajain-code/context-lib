"""JSON serialization for exporting and importing full graphs.

Usage::

    from context_graph.core.serialization import dump_graph, load_graph

    # Export
    dump_graph(graph, "my_graph.json")

    # Import
    graph = load_graph("my_graph.json", storage=MemoryStorage())
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Union

from context_graph.core.models import Edge, Node
from context_graph.storage.base import BaseStorage

_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"


def _parse_timestamp(raw: str) -> datetime:
    """Parse an ISO timestamp string, ensuring the result is timezone-aware (UTC)."""
    dt = datetime.strptime(raw, _ISO_FORMAT)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _node_to_dict(node: Node) -> Dict[str, Any]:
    return {
        "id": node.id,
        "type": node.type,
        "content": node.content,
        "signals": node.signals,
        "timestamp": node.timestamp.strftime(_ISO_FORMAT),
        "source": node.source,
        "confidence_score": node.confidence_score,
    }


def _edge_to_dict(edge: Edge) -> Dict[str, Any]:
    return {
        "source_id": edge.source_id,
        "target_id": edge.target_id,
        "relation": edge.relation,
        "weight": edge.weight,
        "timestamp": edge.timestamp.strftime(_ISO_FORMAT),
    }


def _dict_to_node(data: Dict[str, Any]) -> Node:
    return Node(
        id=data["id"],
        type=data["type"],
        content=data["content"],
        signals=data.get("signals", {}),
        timestamp=_parse_timestamp(data["timestamp"]),
        source=data.get("source"),
        confidence_score=data.get("confidence_score", 1.0),
    )


def _dict_to_edge(data: Dict[str, Any]) -> Edge:
    return Edge(
        source_id=data["source_id"],
        target_id=data["target_id"],
        relation=data["relation"],
        weight=data.get("weight"),
        timestamp=_parse_timestamp(data["timestamp"]),
    )


def dump_graph(
    graph: Any,
    path: Union[str, Path],
    indent: int = 2,
) -> None:
    """Export all nodes and edges from a graph to a JSON file.

    Args:
        graph: A ``Graph`` instance.
        path: File path to write to.
        indent: JSON indentation level.
    """
    data = {
        "version": "0.1.0",
        "nodes": [_node_to_dict(n) for n in graph._storage.all_nodes()],
        "edges": [_edge_to_dict(e) for e in graph._storage.all_edges()],
    }
    Path(path).write_text(json.dumps(data, indent=indent), encoding="utf-8")


def load_graph(
    path: Union[str, Path],
    storage: BaseStorage,
) -> Any:
    """Load nodes and edges from a JSON file into a new Graph.

    Args:
        path: JSON file previously created by ``dump_graph``.
        storage: Storage backend to load data into.

    Returns:
        A new ``Graph`` instance populated with the loaded data.
    """
    # Import here to avoid circular imports
    from context_graph.core.graph import Graph

    raw = json.loads(Path(path).read_text(encoding="utf-8"))

    for node_data in raw.get("nodes", []):
        storage.save_node(_dict_to_node(node_data))
    for edge_data in raw.get("edges", []):
        storage.save_edge(_dict_to_edge(edge_data))

    return Graph(storage=storage)