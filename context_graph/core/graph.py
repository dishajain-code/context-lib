"""Core Graph class — the primary public API for Context Graph."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from context_graph.core.models import Edge, Node
from context_graph.core.scoring import ScoringConfig, compute_score
from context_graph.storage.base import BaseStorage


class Graph:
    """A deterministic context graph for institutional memory.

    Example::

        from context_graph import Graph, Node
        from context_graph.storage import MemoryStorage

        graph = Graph(storage=MemoryStorage())
        graph.add_node(Node(type="decision", content="Migrated to K8s"))
    """

    def __init__(
        self,
        storage: BaseStorage,
        scoring_config: Optional[ScoringConfig] = None,
        scoring_fn: Optional[
            Callable[[Node, List[Edge], Dict[str, Any], ScoringConfig], float]
        ] = None,
    ) -> None:
        """
        Args:
            storage: Backend that persists nodes and edges.
            scoring_config: Tuneable scoring parameters. Uses defaults if None.
            scoring_fn: Custom scoring function. Falls back to built-in
                ``compute_score`` if None.
        """
        self._storage = storage
        self._scoring_config = scoring_config or ScoringConfig()
        self._scoring_fn = scoring_fn or compute_score

    # ── Node operations ──────────────────────────────────────────────

    def add_node(self, node: Node) -> Node:
        """Add a node to the graph. Returns the node (for chaining / id access)."""
        self._storage.save_node(node)
        return node

    def get_node(self, node_id: str) -> Optional[Node]:
        """Retrieve a node by id, or None if not found."""
        return self._storage.get_node(node_id)

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its edges. Returns True if the node existed."""
        return self._storage.remove_node(node_id)

    # ── Edge operations ──────────────────────────────────────────────

    def add_edge(self, edge: Edge) -> Edge:
        """Add an edge between two existing nodes.

        Raises:
            ValueError: If either endpoint node does not exist in the graph.
        """
        if self._storage.get_node(edge.source_id) is None:
            raise ValueError(f"Source node '{edge.source_id}' not found in graph")
        if self._storage.get_node(edge.target_id) is None:
            raise ValueError(f"Target node '{edge.target_id}' not found in graph")
        self._storage.save_edge(edge)
        return edge

    def remove_edge(self, source_id: str, target_id: str, relation: str) -> bool:
        """Remove a specific edge. Returns True if the edge existed."""
        return self._storage.remove_edge(source_id, target_id, relation)

    # ── Query operations ─────────────────────────────────────────────

    def get_related(self, node_id: str, max_depth: int = 1) -> List[Node]:
        """Return nodes connected to ``node_id`` up to ``max_depth`` hops.

        Args:
            node_id: Starting node.
            max_depth: Maximum traversal depth (default 1 = direct neighbours).

        Returns:
            Deduplicated list of related nodes (excludes the starting node).
        """
        if max_depth < 1:
            return []

        visited: set[str] = {node_id}
        frontier: list[str] = [node_id]
        result: list[Node] = []

        for _ in range(max_depth):
            next_frontier: list[str] = []
            for current_id in frontier:
                for neighbour in self._storage.get_related(current_id):
                    if neighbour.id not in visited:
                        visited.add(neighbour.id)
                        result.append(neighbour)
                        next_frontier.append(neighbour.id)
            frontier = next_frontier
            if not frontier:
                break

        return result

    def similar_context(
        self,
        signals: Dict[str, Any],
        limit: int = 10,
    ) -> List[Node]:
        """Find nodes whose signals best match the query, ranked by score.

        Args:
            signals: Key-value pairs to match against node signals.
            limit: Maximum number of results to return.

        Returns:
            Nodes sorted by descending effective score.
        """
        scored: list[tuple[float, Node]] = []

        for node in self._storage.all_nodes():
            edges = self._storage.get_edges_for_node(node.id)
            score = self._scoring_fn(
                node, edges, signals, self._scoring_config
            )
            if score > 0:
                scored.append((score, node))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [node for _, node in scored[:limit]]

    # ── Confidence management ────────────────────────────────────────

    def update_confidence(self, node_id: str, new_score: float) -> Node:
        """Manually set a node's confidence score.

        Args:
            node_id: Target node.
            new_score: New confidence value (0.0–1.0).

        Raises:
            ValueError: If score is out of range or node doesn't exist.
        """
        if not 0.0 <= new_score <= 1.0:
            raise ValueError(
                f"confidence_score must be between 0.0 and 1.0, got {new_score}"
            )
        node = self._storage.get_node(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' not found in graph")
        node.confidence_score = new_score
        self._storage.save_node(node)
        return node