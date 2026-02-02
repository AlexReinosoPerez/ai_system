# Implementer Memory

This file captures practical implementation patterns and common mistakes
observed during development.

It does NOT override plans, rules, or architectural decisions.

---

## Implementation patterns
- Prefer small, pure functions for business logic.
- Keep changes tightly scoped to the approved plan.
- Write tests alongside logic changes, not after large refactors.

---

## Common mistakes to avoid
- Touching unrelated files “while already here”.
- Refactoring code without an explicit goal.
- Adding defensive code without understanding failure modes.

---

## Practical notes
- Favor readability over cleverness.
- If code feels complex, it probably is.
