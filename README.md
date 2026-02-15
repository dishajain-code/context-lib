# context-graph

[![CI](https://github.com/dishajain-code/context-lib/actions/workflows/ci.yml/badge.svg)](https://github.com/dishajain-code/context-lib/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

Deterministic memory infrastructure for institutional knowledge. context-graph is a zero-dependency Python library that models decisions, events, and outcomes as a directed graph. It provides a built-in scoring engine for retrieving the most relevant context based on signal overlap, time decay, and graph connectivity. Everything is fully deterministic — same inputs always produce the same outputs.

## Installation

```bash
pip install context-graph
```

## Quick Start

```python
from context_graph import Graph, Node, Edge
from context_graph.storage import MemoryStorage

graph = Graph(storage=MemoryStorage())

# Add nodes representing an incident chain
incident = graph.add_node(Node(
    type="event",
    content="Production API latency spike",
    signals={"service": "api-gateway", "severity": "high"},
))
root_cause = graph.add_node(Node(
    type="signal",
    content="Connection pool exhaustion on primary DB",
    signals={"service": "api-gateway", "component": "database"},
))
decision = graph.add_node(Node(
    type="decision",
    content="Increased pool size from 20 to 100 and added circuit breaker",
    signals={"service": "api-gateway", "action": "config-change"},
))

# Connect them
graph.add_edge(Edge(source_id=incident.id, target_id=root_cause.id, relation="caused_by"))
graph.add_edge(Edge(source_id=root_cause.id, target_id=decision.id, relation="led_to"))

# Later: retrieve relevant context for a similar situation
results = graph.similar_context({"service": "api-gateway", "severity": "high"}, limit=5)
for node in results:
    print(f"[{node.type}] {node.content}")
```

## Scoring

Nodes are ranked by a deterministic formula:

```
effective_score = base_confidence * time_decay * signal_boost * edge_boost
```

| Factor | Description |
|--------|-------------|
| `base_confidence` | The node's stored `confidence_score` (0.0--1.0) |
| `time_decay` | `exp(-decay_rate * age_hours)` — older nodes score lower |
| `signal_boost` | Fraction of query signals matching the node's signals |
| `edge_boost` | `1 + log(1 + edge_count) * edge_weight_factor` |

All parameters are tuneable via `ScoringConfig`.

## Storage Backends

| Backend | Use case | Persistence |
|---------|----------|-------------|
| `MemoryStorage` | Tests, prototyping, ephemeral sessions | In-memory only |
| `SQLiteStorage` | Production, persistent graphs | File-based (`*.db`) |

```python
from context_graph.storage import SQLiteStorage

graph = Graph(storage=SQLiteStorage("my_graph.db"))
```

## Serialization

Export and import full graphs as JSON:

```python
from context_graph.core.serialization import dump_graph, load_graph

dump_graph(graph, "snapshot.json")
graph = load_graph("snapshot.json", storage=MemoryStorage())
```

## Development

```bash
git clone https://github.com/dishajain-code/context-lib.git
cd context-lib
pip install -e ".[dev]"
pytest --cov=context_graph
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## License

[Apache-2.0](LICENSE)
