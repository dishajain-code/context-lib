"""Abstract base class for Context Graph adapters.

Adapters connect external systems (Slack, Jira, GitHub, etc.) to the graph.
v0.1 provides only the interface — no production adapters are included.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAdapter(ABC):
    """Interface that all external system adapters must implement."""

    @abstractmethod
    def listen(self) -> Any:
        """Start listening for events from the external system.

        Implementation details (polling, webhooks, streaming) are left
        to the concrete adapter.
        """

    @abstractmethod
    def normalize(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a raw event from the external system into the
        Context Graph node format.

        Returns a dict suitable for passing to ``Node(**result)``.
        """

    @abstractmethod
    def emit(self, data: Dict[str, Any]) -> None:
        """Push data back to the external system or downstream consumers."""