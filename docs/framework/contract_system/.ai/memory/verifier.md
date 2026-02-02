# Verifier Memory

This file defines acceptance heuristics beyond mechanical verification.
It helps interpret verify results correctly.

---

## Acceptance principles
- Passing scripts/verify.sh is necessary but not sufficient.
- Tests must assert meaningful behavior, not just execution.

---

## Common verification failures
- Superficial tests that always pass.
- Logic covered by tests that do not assert outcomes.
- verify passing despite unmet functional goals.

---

## Verification mindset
- Treat verify as a quality gate, not a suggestion.
- If something feels wrong despite passing verify, flag it.
