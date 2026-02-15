# Contributing to context-graph

Thanks for your interest in contributing! This document covers the basics.

## Dev Setup

```bash
git clone https://github.com/dishajain-code/context-lib.git
cd context-lib
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest --cov=context_graph
```

All 111 tests should pass with 96%+ coverage before submitting a PR.

## Code Style

- Add type hints to all function signatures.
- Include docstrings for public classes and functions.
- Keep external dependencies at zero — the library is intentionally dependency-free.
- Follow the existing patterns in `context_graph/core/` for new modules.

## Submitting Changes

1. Fork the repository and create a feature branch from `main`.
2. Make your changes and ensure all tests pass.
3. Open a pull request against `main` with a clear description of what changed and why.
