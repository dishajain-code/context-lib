# context-graph

Deterministic memory infrastructure for institutional knowledge.

## Installation

```bash
pip install context-graph
```

## Quick start

```python
from context_graph import Graph, Node
from context_graph.storage import MemoryStorage

graph = Graph(storage=MemoryStorage())
graph.add_node(Node(type="decision", content="Migrated to K8s"))
```

## License

Apache-2.0
