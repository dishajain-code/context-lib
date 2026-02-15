# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-02-15

### Added

- `Graph` public API with node/edge CRUD, traversal (`get_related`), and scored retrieval (`similar_context`).
- `Node` and `Edge` dataclass models with validation.
- Deterministic scoring engine (`compute_score`) with configurable time decay, signal overlap, and edge boost.
- `MemoryStorage` — in-memory storage backend for tests and ephemeral use.
- `SQLiteStorage` — file-based persistent storage backend (zero external dependencies).
- JSON serialization via `dump_graph` / `load_graph`.
- `BaseStorage` abstract class for custom storage backends.
- `BaseAdapter` abstract class for external system integrations.
- PEP 561 `py.typed` marker for inline type annotations.
- Full test suite (111 tests, 96% coverage).
