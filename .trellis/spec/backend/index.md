# Backend Development Guidelines

> Best practices for backend development in this project.

---

## Overview

Backend is FastAPI. All model calls (DeepSeek chat, ModelScope embeddings) route through the backend — the frontend never calls model providers directly. Persistence uses ChromaDB for vectors, NetworkX+JSON for knowledge graphs, and local filesystem for materials and exports.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | Done |
| [Database Guidelines](./database-guidelines.md) | ChromaDB, NetworkX+JSON, local storage | Done |
| [Error Handling](./error-handling.md) | Error types, fallback policy, API format | Done |
| [Quality Guidelines](./quality-guidelines.md) | Forbidden patterns, tests, review checklist | Done |
| [Logging Guidelines](./logging-guidelines.md) | Structured logging, levels, safe fields | Done |

---

## How to Fill These Guidelines

For each guideline file:

1. Document your project's **actual conventions** (not ideals)
2. Include **code examples** from your codebase
3. List **forbidden patterns** and why
4. Add **common mistakes** your team has made

The goal is to help AI assistants and new team members understand how YOUR project works.

---

**Language**: All documentation should be written in **English**.
