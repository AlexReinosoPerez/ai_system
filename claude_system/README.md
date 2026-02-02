# Claude System

## Purpose

`claude_system` is a portable, deterministic framework for AI-assisted software
development.

It defines **how humans, AI models, and tools interact**, with the explicit goal
of eliminating ambiguity, drift, and implicit behavior.

This system does **not** aim to automate decisions.
It exists to ensure that decisions are explicit, execution is mechanical, and
verification is objective.

---

## Core Philosophy

- Humans decide.
- The repository is the single source of truth.
- AI executes under contract.
- Nothing is considered done until verification passes.
- Explicit rules override implicit behavior.

The system is designed so that **the correct path is the easiest path**
(antigravity by design).

---

## What This System Is

- A **contract layer** between humans and AI
- A **workflow definition**, not a codebase
- A **tool-agnostic orchestration model**
- A **reproducible setup** that can be copied between projects

---

## What This System Is Not

- Not an autonomous agent framework
- Not a multi-agent system
- Not a memory automation system
- Not a replacement for human judgment
- Not a substitute for CI/CD

---

## High-Level Architecture

Human
↓
Obsidian (free-form thinking, non-binding)
↓
Repository Contract (this system)
↓
Claude (single AI agent)
↓
Copilot (mechanical execution)
↓
Verification (verify.sh)
↓
CI Enforcement


Only the **repository contract** is authoritative.

---

## Repository as Contract

Everything inside `claude_system` is **binding** for AI-assisted work.

If a rule or decision is not written here, it does not exist.

Authoritative files include:
- `CLAUDE.md` — global AI rules and constraints
- `docs/workflow.md` — execution protocol
- `docs/assumptions.md` — explicit assumptions
- `docs/decisions.md` — architectural decisions
- `docs/glossary.md` — canonical definitions

---

## Roles and Responsibilities

### Human

- Defines goals and priorities
- Approves plans
- Decides what becomes contract
- Curates memory and decisions

### Obsidian

- Free-form thinking and research
- Ideas, drafts, exploration
- Intentionally non-binding
- Never directly obeyed by AI

### Claude (Single Agent)

- Proposes plans
- Performs controlled reasoning
- Verifies work
- Iterates until closure
- Never decides goals or scope

Claude operates strictly under `CLAUDE.md`.

### Copilot

- Mechanical code execution
- Boilerplate and local refactors
- No architectural authority
- No verification responsibility

### Verification

- `scripts/verify.sh` is the single closure gate
- Binary outcome: pass or fail
- Required locally and in CI

### CI

- Mechanical enforcement only
- Blocks merges if verification fails
- Never modifies code
- Never makes decisions

---

## MCP (Optional Infrastructure Layer)

The system supports MCP (Model Context Protocol) tools as **infrastructure**, not
intelligence.

Supported MCP categories:
- Filesystem (read-only)
- Verification/Test execution
- Git inspection (read-only)
- Docker operations

MCP tools:
- may observe
- may execute explicit commands
- must never decide
- must never modify source code directly

---

## Determinism and Drift Control

To prevent drift:
- All rules are explicit
- All decisions are versioned
- No memory is automatic
- No behavior depends on chat history
- CI enforces compliance mechanically

If behavior changes, it must be traceable to a commit.

---

## Portability

`claude_system` is designed to be:
- copied between projects
- version-controlled
- independent of language or stack
- independent of AI provider

Only project-specific rules live outside this directory.

---

## Initialization

The system is initialized via:

```bash
./scripts/init.sh


Guiding Principle

Think freely.
Decide explicitly.
Execute mechanically.
Verify objectively.
Enforce automatically.

This is the foundation of the system.