# Reviewer Memory

This file records recurring issues and review heuristics.
It helps focus reviews on areas where problems often appear.

---

## Red flags
- Silent exception handling.
- Missing tests for edge cases and failure paths.
- Public APIs without clear documentation.

---

## Review focus areas
- Correctness before style.
- Clarity over clever abstractions.
- Alignment with CLAUDE.md and approved decisions.

---

## Common review findings
- Tests that only assert happy paths.
- Logic changes without corresponding test updates.
