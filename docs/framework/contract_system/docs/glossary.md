# Glossary

## Purpose

This glossary defines the **canonical meaning** of terms used throughout
`claude_system`.

If a term appears in:
- `CLAUDE.md`
- `docs/workflow.md`
- `docs/decisions.md`
- prompts
- discussions about the system

its meaning is **exactly** the one defined here.

Ambiguous or overloaded terminology is explicitly forbidden.

---

## Agent

A logical AI entity capable of:
- receiving context
- reasoning under constraints
- choosing actions
- executing tools
- iterating until closure

In this system:
- there is **exactly one agent**
- roles (architect, verifier, etc.) are **modes**, not agents

---

## Claude

The **single AI agent** used in this system.

Claude is responsible for:
- planning
- controlled reasoning
- verification
- enforcing the workflow

Claude never:
- decides goals
- expands scope
- acts autonomously

---

## Copilot

A **mechanical execution assistant**.

Copilot:
- writes code
- performs boilerplate tasks
- applies local refactors

Copilot never:
- reasons architecturally
- validates correctness
- initiates work
- bypasses verification

---

## Contract

Any versioned file in the repository that defines binding rules.

Examples:
- `CLAUDE.md`
- files under `docs/`
- curated files under `ai/`

If something is not part of the contract, it is not authoritative.

---

## Workflow

The explicit, linear execution protocol defined in `docs/workflow.md`.

The workflow:
- defines task states
- restricts tool usage
- enforces handoffs
- prevents drift

Deviation is not allowed unless documented.

---

## Task State

A discrete phase of work execution.

The only valid task states are:
- THINKING
- PLANNED
- EXECUTING
- VERIFYING
- CLOSED

States are mutually exclusive and sequential.

---

## Plan

An explicit, ordered description of intended work.

A plan must include:
- intent per step
- expected outcome
- verification strategy

A plan is required before execution.

---

## Handoff

An explicit transfer of authority between tools.

There are two valid handoffs:
- Claude → Copilot (execution)
- Copilot → Claude (escalation)

Handoffs must be explicit and textual.

---

## Verification

Objective validation that a task is complete.

In this system:
- verification is performed via `scripts/verify.sh`
- verification is binary (pass / fail)
- verification is mandatory

Verification replaces subjective confidence.

---

## Definition of Done

The condition under which work is considered complete.

Definition of done:
- `scripts/verify.sh` passes locally
- CI verification is expected to pass
- no contractual rules were violated

Nothing else qualifies.

---

## CI (Continuous Integration)

A mechanical enforcement system.

CI:
- runs verification
- blocks merges on failure
- does not modify code
- does not make decisions

CI is not intelligent.

---

## MCP (Model Context Protocol)

A protocol for exposing tools to AI in a structured, constrained manner.

In this system:
- MCP provides infrastructure
- MCP does not provide autonomy
- MCP does not add intelligence

---

## MCP Tool

A concrete capability exposed via MCP.

Examples:
- filesystem reader
- test runner
- git inspector
- docker operator

MCP tools:
- act only when explicitly invoked
- do not decide what to do
- do not store memory

---

## Memory

Persistent knowledge intended to survive across sessions.

In this system:
- memory is explicit
- memory is versioned
- memory is curated

There is no automatic memory.

---

## Session Summary

A written record of a completed task execution.

Stored under:
- `ai/sessions/`

A session summary includes:
- goal
- actions taken
- verification result
- follow-ups

---

## Obsidian

An external tool for free-form thinking.

Obsidian:
- is non-binding
- may contain incorrect ideas
- is intentionally decoupled from the contract

Only content promoted into the repository is authoritative.

---

## Drift

Uncontrolled divergence between:
- intended system behavior
- actual system behavior

Drift is prevented by:
- explicit contracts
- verification
- CI enforcement
- disciplined workflows

---

## Determinism

The property that the same inputs produce the same outcomes.

This system aims for determinism by:
- eliminating implicit state
- versioning all rules
- enforcing verification

---

## Antigravity

A design principle where:
- the correct path is the easiest path
- incorrect behavior requires effort

Antigravity is achieved through:
- explicit workflows
- mechanical enforcement
- minimal automation

---

## Guiding Rule

> If a term is unclear, it must be added here.
> Undefined terms are not allowed.
