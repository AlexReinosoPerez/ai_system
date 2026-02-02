# Assumptions

## Purpose

This document lists all **explicit assumptions** under which the system,
workflow, and contracts are valid.

Assumptions are not decisions.
They are conditions believed to be true at the time of design.

If any assumption becomes invalid:
- related decisions must be re-evaluated
- workflows may need adjustment
- behavior must not silently drift

Nothing in this system relies on hidden assumptions.

---

## Technical Assumptions

- The project uses version control (Git).
- The repository is the authoritative source of truth.
- The execution environment is deterministic or reproducible.
- A Unix-like shell is available (Linux or macOS).
- Scripts in `scripts/` can be executed locally.
- CI environments can run `scripts/verify.sh`.

---

## Tooling Assumptions

- Claude is available as the primary reasoning agent.
- Copilot is available for mechanical code execution.
- Claude and Copilot do not share reliable memory.
- Any perceived continuity across sessions is unreliable.
- MCP tools, if used, are explicitly configured and constrained.

---

## Human Assumptions

- A human is present to:
  - define goals
  - approve plans
  - decide what becomes contract
- The human understands the difference between:
  - thinking (Obsidian)
  - deciding (repository)
  - executing (AI/tools)
- The human enforces discipline when ambiguity appears.

---

## Workflow Assumptions

- Work can be decomposed into discrete tasks.
- Tasks can be executed linearly.
- Mechanical execution can be separated from decision-making.
- Verification can objectively determine task completion.
- Partial completion is not acceptable.

---

## Verification Assumptions

- `scripts/verify.sh` reflects the true definition of “done”.
- Verification failures are meaningful and actionable.
- Verification is faster to fix than to bypass.
- Weakening verification increases long-term cost.

---

## CI Assumptions

- CI faithfully reproduces local verification.
- CI failures indicate real problems.
- CI is trusted as an enforcement mechanism.
- CI does not introduce hidden behavior.

---

## Memory Assumptions

- AI has no reliable long-term memory.
- Any persistent knowledge must be explicit and versioned.
- Memory written automatically is untrusted.
- Curated memory is reviewed and intentional.

---

## Obsidian Assumptions

- Obsidian is used for free-form thinking.
- Obsidian content is allowed to be incomplete or wrong.
- Obsidian is intentionally non-binding.
- Only content promoted into the repository is authoritative.

---

## Scope Assumptions

- The system prioritizes correctness over speed.
- The system favors explicitness over convenience.
- The system is designed for professional software development.
- The system is not optimized for experimentation or research.

---

## Change Policy

If any assumption in this document becomes invalid:

1. Stop execution.
2. Identify affected decisions and workflows.
3. Update this file explicitly.
4. Update `docs/decisions.md` if required.
5. Resume execution only after alignment is restored.

Silent assumption changes are forbidden.

---

## Guiding Principle

> Assumptions are liabilities.
> Making them explicit is how we control them.
