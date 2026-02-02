# Architect Memory

This file contains architectural heuristics, discarded approaches,
and recurring design insights.

It does NOT define rules or final decisions.
Authoritative decisions live in docs/decisions.md and CLAUDE.md.

---

## Design heuristics
- Prefer explicit data flow over implicit or global state.
- Introduce abstractions only when they are reused or clearly justified.
- Simpler designs are preferred unless complexity is required by constraints.

---

## Architectural boundaries
- Business logic should remain framework-agnostic.
- IO, persistence, and external services must be isolated at the edges.

---

## Common risks
- Overengineering early solutions.
- Blurring boundaries between validation and domain logic.
- Introducing async or concurrency without a clear need.

---

## Past conclusions
- Async adds complexity and should only be introduced if explicitly required.
