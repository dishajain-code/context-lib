"""SQLite storage backend — zero-config persistent graph storage.

Uses Python's built-in ``sqlite3`` module, so no extra dependencies are needed.
Data survives process restarts.

Usage::

    from context_graph import Graph
    from context_graph.storage import SQLiteStorage

    graph = Graph(storage=SQLiteStorage("my_graph.db"))
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from context_graph.core.models import Edge, Node
from context_graph.storage.base import BaseStorage

_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"


def _parse_timestamp(raw: str) -> datetime:
    """Parse an ISO timestamp string, ensuring the result is timezone-aware (UTC)."""
    dt = datetime.strptime(raw, _ISO_FORMAT)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _serialize_content(content: str | Dict[str, Any]) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content)


def _deserialize_content(raw: str) -> str | Dict[str, Any]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        return raw
    except (json.JSONDecodeError, TypeError):
        return raw


def _row_to_node(row: sqlite3.Row) -> Node:
    return Node(
        id=row["id"],
        type=row["type"],
        content=_deserialize_content(row["content"]),
        signals=json.loads(row["signals"]),
        timestamp=_parse_timestamp(row["timestamp"]),
        source=row["source"],
        confidence_score=row["confidence_score"],
    )


def _row_to_edge(row: sqlite3.Row) -> Edge:
    weight = row["weight"]
    return Edge(
        source_id=row["source_id"],
        target_id=row["target_id"],
        relation=row["relation"],
        weight=float(weight) if weight is not None else None,
        timestamp=_parse_timestamp(row["timestamp"]),
    )


class SQLiteStorage(BaseStorage):
    """Persistent graph storage backed by a SQLite database file.

    Args:
        db_path: Path to the SQLite database file. Use ``":memory:"`` for
            an in-memory database (useful for testing).
    """

    def __init__(self, db_path: str = "context_graph.db") -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                signals TEXT NOT NULL DEFAULT '{}',
                timestamp TEXT NOT NULL,
                source TEXT,
                confidence_score REAL NOT NULL DEFAULT 1.0
            );

            CREATE TABLE IF NOT EXISTS edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id, relation),
                FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
            """
        )
        self._conn.commit()

    # ── Node operations ──────────────────────────────────────────────

    def save_node(self, node: Node) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO nodes (id, type, content, signals, timestamp, source, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node.id,
                node.type,
                _serialize_content(node.content),
                json.dumps(node.signals),
                node.timestamp.strftime(_ISO_FORMAT),
                node.source,
                node.confidence_score,
            ),
        )
        self._conn.commit()

    def get_node(self, node_id: str) -> Optional[Node]:
        row = self._conn.execute(
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_node(row)

    def remove_node(self, node_id: str) -> bool:
        # Foreign key ON DELETE CASCADE removes associated edges automatically.
        cursor = self._conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def all_nodes(self) -> List[Node]:
        rows = self._conn.execute("SELECT * FROM nodes").fetchall()
        return [_row_to_node(r) for r in rows]

    # ── Edge operations ──────────────────────────────────────────────

    def save_edge(self, edge: Edge) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO edges (source_id, target_id, relation, weight, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                edge.source_id,
                edge.target_id,
                edge.relation,
                edge.weight,
                edge.timestamp.strftime(_ISO_FORMAT),
            ),
        )
        self._conn.commit()

    def get_edges_for_node(self, node_id: str) -> List[Edge]:
        rows = self._conn.execute(
            "SELECT * FROM edges WHERE source_id = ? OR target_id = ?",
            (node_id, node_id),
        ).fetchall()
        return [_row_to_edge(r) for r in rows]

    def get_related(self, node_id: str) -> List[Node]:
        rows = self._conn.execute(
            """
            SELECT DISTINCT n.* FROM nodes n
            INNER JOIN edges e
                ON (e.source_id = ? AND e.target_id = n.id)
                OR (e.target_id = ? AND e.source_id = n.id)
            """,
            (node_id, node_id),
        ).fetchall()
        return [_row_to_node(r) for r in rows]

    def remove_edge(self, source_id: str, target_id: str, relation: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM edges WHERE source_id = ? AND target_id = ? AND relation = ?",
            (source_id, target_id, relation),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def all_edges(self) -> List[Edge]:
        rows = self._conn.execute("SELECT * FROM edges").fetchall()
        return [_row_to_edge(r) for r in rows]

    # ── Query ────────────────────────────────────────────────────────

    def query(self, filters: Dict[str, Any]) -> List[Node]:
        clauses: list[str] = []
        params: list[Any] = []

        if "type" in filters:
            clauses.append("type = ?")
            params.append(filters["type"])
        if "source" in filters:
            clauses.append("source = ?")
            params.append(filters["source"])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM nodes {where}", params
        ).fetchall()

        nodes = [_row_to_node(r) for r in rows]

        # Signal filtering is done in Python since signals are stored as JSON
        if "signals" in filters:
            signal_filter = filters["signals"]
            nodes = [
                n
                for n in nodes
                if all(
                    k in n.signals and n.signals[k] == v
                    for k, v in signal_filter.items()
                )
            ]

        return nodes

    # ── Lifecycle ────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()