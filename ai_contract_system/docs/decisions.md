# Architectural and System Decisions

## Purpose

This document records **significant architectural and system-level decisions**
that govern how work is performed under `claude_system`.

It captures **why** decisions were made, not just **what** was chosen.

Decisions recorded here are:
- explicit
- versioned
- binding

They must not be silently overridden.

---

## Decision Record Format

Each decision must include:

- **Context**  
  The situation or problem that required a decision.

- **Decision**  
  The explicit choice that was made.

- **Rationale**  
  Why this option was chosen over alternatives.

- **Consequences**  
  Trade-offs, constraints, and implications.

---

## Decision 001 — Repository as Single Source of Truth

**Context**  
AI tools do not have reliable memory and may infer or hallucinate context.

**Decision**  
The repository is the **only authoritative source of truth**.  
Only versioned files define rules, decisions, and behavior.

**Rationale**  
Version control provides determinism, auditability, and traceability.

**Consequences**  
- All important information must be written down.
- Upfront documentation effort increases.
- Drift and ambiguity are minimized.

---

## Decision 002 — Single AI Agent Model

**Context**  
Multi-agent systems introduce coordination complexity and inconsistent state.

**Decision**  
The system uses **one logical AI agent** (Claude).

**Rationale**  
A single agent simplifies reasoning, control, and accountability.

**Consequences**  
- Roles (architect, verifier, etc.) are modes, not agents.
- Parallel autonomous behavior is intentionally avoided.

---

## Decision 003 — Explicit Workflow States

**Context**  
Unstructured AI-assisted workflows lead to scope creep and confusion.

**Decision**  
All work follows explicit states:

THINKING → PLANNED → EXECUTING → VERIFYING → CLOSED


**Rationale**  
State separation enforces discipline and clarity.

**Consequences**  
- Tool usage is restricted per state.
- Handoffs must be explicit.
- Shortcuts are disallowed.

---

## Decision 004 — Plan-First Execution

**Context**  
Direct implementation often leads to rework and hidden assumptions.

**Decision**  
No execution may begin without an approved plan.

**Rationale**  
Planning reduces errors and clarifies intent before code is written.

**Consequences**  
- Initial progress may feel slower.
- Overall quality and predictability improve.

---

## Decision 005 — Explicit Claude ↔ Copilot Handoff

**Context**  
Ambiguous responsibility between reasoning and execution leads to errors.

**Decision**  
Execution is delegated to Copilot **only** after Claude emits an explicit
handoff phrase.

**Rationale**  
Clear authority transfer prevents accidental decision-making during execution.

**Consequences**  
- Copilot never initiates work.
- Claude must explicitly relinquish control.

---

## Decision 006 — Verification as Definition of Done

**Context**  
Subjective completion leads to inconsistent quality.

**Decision**  
`scripts/verify.sh` is the **only definition of “done”**.

**Rationale**  
Objective verification is enforceable and repeatable.

**Consequences**  
- Verification must be maintained.
- Work cannot be claimed complete without passing verification.

---

## Decision 007 — Minimal CI as Enforcement Only

**Context**  
CI pipelines can become overly complex and brittle.

**Decision**  
CI is used solely to enforce verification by running `scripts/verify.sh`.

**Rationale**  
CI should block failures, not introduce logic or decisions.

**Consequences**  
- CI configuration remains simple.
- All intelligence stays in the repository and workflow.

---

## Decision 008 — No Automatic Memory

**Context**  
Automatic AI memory introduces uncontrolled state and drift.

**Decision**  
All memory is explicit, curated, and versioned.

**Rationale**  
Intentional memory preserves correctness and accountability.

**Consequences**  
- Memory must be reviewed before inclusion.
- No reliance on chat history or implicit learning.

---

## Decision 009 — Obsidian as Non-Binding Thinking Space

**Context**  
Design and exploration require freedom from immediate constraints.

**Decision**  
Obsidian is used for free-form thinking and research only.

**Rationale**  
Separating thinking from decision-making prevents accidental authority.

**Consequences**  
- Obsidian content must be promoted manually.
- AI never obeys Obsidian content directly.

---

## Decision 010 — MCP as Infrastructure, Not Intelligence

**Context**  
Direct tool invocation by AI can be unsafe and opaque.

**Decision**  
MCP tools are allowed only as **explicit, constrained infrastructure**.

**Rationale**  
MCP improves safety and observability without adding autonomy.

**Consequences**  
- MCP tools are observational or mechanical.
- Decisions remain human-approved and contract-driven.

---

## Change Policy

- New decisions must be appended, never rewritten.
- Existing decisions must not be silently overridden.
- Conflicting decisions require an explicit superseding record.

---

## Guiding Principle

> Decisions exist to reduce future thinking.
> If a decision is not written, it does not exist.
