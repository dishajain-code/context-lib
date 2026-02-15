"""In-memory storage backend using adjacency lists."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from context_graph.core.models import Edge, Node
from context_graph.storage.base import BaseStorage


class MemoryStorage(BaseStorage):
    """In-memory graph storage backed by dicts and adjacency lists.

    Suitable for development, testing, and small graphs (up to ~10k nodes).
    All data is lost when the process exits.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        # adjacency list: node_id -> list of edges (both directions)
        self._adj: Dict[str, List[Edge]] = defaultdict(list)

    def save_node(self, node: Node) -> None:
        self._nodes[node.id] = node

    def save_edge(self, edge: Edge) -> None:
        # Avoid duplicate edges
        for existing in self._adj[edge.source_id]:
            if (
                existing.source_id == edge.source_id
                and existing.target_id == edge.target_id
                and existing.relation == edge.relation
            ):
                return
        self._adj[edge.source_id].append(edge)
        self._adj[edge.target_id].append(edge)

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def get_edges_for_node(self, node_id: str) -> List[Edge]:
        return list(self._adj.get(node_id, []))

    def get_related(self, node_id: str) -> List[Node]:
        related: List[Node] = []
        seen: set[str] = set()
        for edge in self._adj.get(node_id, []):
            neighbor_id = (
                edge.target_id if edge.source_id == node_id else edge.source_id
            )
            if neighbor_id not in seen:
                node = self._nodes.get(neighbor_id)
                if node is not None:
                    related.append(node)
                    seen.add(neighbor_id)
        return related

    def query(self, filters: Dict[str, Any]) -> List[Node]:
        results: List[Node] = []
        for node in self._nodes.values():
            if not self._matches(node, filters):
                continue
            results.append(node)
        return results

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        del self._nodes[node_id]
        # Collect all neighbor ids that share edges with this node
        neighbors: set[str] = set()
        for edge in self._adj.get(node_id, []):
            other = edge.target_id if edge.source_id == node_id else edge.source_id
            neighbors.add(other)
        # Remove edges from neighbor adjacency lists
        for neighbor in neighbors:
            self._adj[neighbor] = [
                e
                for e in self._adj[neighbor]
                if e.source_id != node_id and e.target_id != node_id
            ]
            if not self._adj[neighbor]:
                del self._adj[neighbor]
        # Remove this node's adjacency entry
        self._adj.pop(node_id, None)
        return True

    def remove_edge(self, source_id: str, target_id: str, relation: str) -> bool:
        found = False

        def _filter(edges: List[Edge]) -> List[Edge]:
            nonlocal found
            kept: List[Edge] = []
            for e in edges:
                if (
                    e.source_id == source_id
                    and e.target_id == target_id
                    and e.relation == relation
                ):
                    found = True
                else:
                    kept.append(e)
            return kept

        if source_id in self._adj:
            self._adj[source_id] = _filter(self._adj[source_id])
            if not self._adj[source_id]:
                del self._adj[source_id]
        if target_id in self._adj:
            self._adj[target_id] = _filter(self._adj[target_id])
            if not self._adj[target_id]:
                del self._adj[target_id]
        return found

    def all_nodes(self) -> List[Node]:
        return list(self._nodes.values())

    def all_edges(self) -> List[Edge]:
        seen: set[tuple[str, str, str]] = set()
        edges: List[Edge] = []
        for edge_list in self._adj.values():
            for edge in edge_list:
                key = (edge.source_id, edge.target_id, edge.relation)
                if key not in seen:
                    seen.add(key)
                    edges.append(edge)
        return edges

    @staticmethod
    def _matches(node: Node, filters: Dict[str, Any]) -> bool:
        if "type" in filters and node.type != filters["type"]:
            return False
        if "source" in filters and node.source != filters["source"]:
            return False
        if "signals" in filters:
            for key, value in filters["signals"].items():
                if key not in node.signals or node.signals[key] != value:
                    return False
        return True