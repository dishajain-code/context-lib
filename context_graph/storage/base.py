"""Abstract base class for Context Graph storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from context_graph.core.models import Edge, Node


class BaseStorage(ABC):
    """Interface that all storage backends must implement."""

    @abstractmethod
    def save_node(self, node: Node) -> None:
        """Persist a node. Overwrites if a node with the same id exists."""

    @abstractmethod
    def save_edge(self, edge: Edge) -> None:
        """Persist an edge."""

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[Node]:
        """Return a node by id, or None if not found."""

    @abstractmethod
    def get_edges_for_node(self, node_id: str) -> List[Edge]:
        """Return all edges where the given node is source or target."""

    @abstractmethod
    def get_related(self, node_id: str) -> List[Node]:
        """Return all nodes directly connected to the given node."""

    @abstractmethod
    def query(self, filters: Dict[str, Any]) -> List[Node]:
        """Return nodes matching the given filter criteria.

        Supported filter keys:
            - type: match node type exactly
            - source: match node source exactly
            - signals: dict of key-value pairs that must all be present in node signals
        """

    @abstractmethod
    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its connected edges. Return True if the node existed."""

    @abstractmethod
    def remove_edge(self, source_id: str, target_id: str, relation: str) -> bool:
        """Remove a specific edge. Return True if the edge existed."""

    @abstractmethod
    def all_nodes(self) -> List[Node]:
        """Return all nodes in storage."""

    @abstractmethod
    def all_edges(self) -> List[Edge]:
        """Return all edges in storage."""