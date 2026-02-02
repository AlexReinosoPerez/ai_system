# Prompt — Copilot → Claude Escalation

## Purpose

This text is used when execution cannot continue safely.

---

## Escalation Conditions

Use this escalation if any of the following occur:
- behavior deviates from the approved plan
- an edge case appears
- tests fail unexpectedly
- scope impact is unclear
- architectural judgment is required

---

## Escalation Text

Execution stopped.

Reason:
- <describe the blocking issue>

Returning control to Claude for analysis.

---

## Rule

After escalation:
- Copilot must stop
- no further code is written
- Claude resumes control in THINKING state
