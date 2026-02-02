# Development Workflow

## Purpose

This document defines the **only valid execution protocol** for AI-assisted work
under this system.

It specifies:
- task states
- allowed tools per state
- mandatory handoffs
- verification requirements

Deviation is not allowed unless explicitly documented in `docs/decisions.md`.

---

## Task State Model

All work progresses through **explicit, linear states**:

THINKING → PLANNED → EXECUTING → VERIFYING → CLOSED


There are no parallel states.
There are no shortcuts.

Each state:
- has a single primary authority
- enables a specific set of actions
- forbids all others

---

## THINKING

**Primary authority:** Claude

**Purpose**
- Understand the problem
- Analyze constraints
- Evaluate options
- Propose a plan

**Allowed actions**
- architectural analysis
- trade-off discussion
- risk identification
- plan drafting

**Forbidden actions**
- writing code
- using Copilot
- running verification
- executing MCP commands

**Required output**
- an explicit plan with ordered steps
- clear intent per step
- expected outcomes
- verification strategy

If uncertainty exists, the plan must not be approved.

---

## PLANNED

**Primary authority:** Claude

**Purpose**
- Finalize and approve the plan
- Freeze scope and decisions
- Prepare for mechanical execution

**Requirements**
- plan is complete
- no architectural uncertainty remains
- all assumptions are explicit or documented

**Mandatory handoff phrase**

Claude must emit the **exact phrase** below to authorize execution:

PLAN APPROVED. Proceed with Copilot.


Without this phrase:
- execution must not begin
- Copilot must not be used

---

## EXECUTING

**Primary authority:** Copilot

**Purpose**
- Mechanical implementation of the approved plan

**Allowed actions**
- writing code
- boilerplate generation
- local refactors strictly required by the plan

**Forbidden actions**
- introducing new abstractions
- changing scope
- altering architecture
- modifying unrelated files
- weakening verification

**Escalation rule**

If any of the following occur:
- unexpected behavior
- unclear impact
- missing information
- deviation from the plan

Execution must stop immediately.

Control returns to **THINKING**.

---

## VERIFYING

**Primary authority:** Claude

**Purpose**
- Objective validation
- Detect regressions
- Ensure closure

**Allowed actions**
- run `scripts/verify.sh`
- analyze failures
- propose minimal fixes
- apply fixes
- rerun verification

**Delegation rule**

Claude may delegate a **specific fix** to Copilot only by explicitly stating:

Implement the following fix using Copilot.
Do not modify anything else.


**Verification discipline**
- verification must be rerun after every fix
- partial success is not acceptable
- explanations do not replace passing verification

---

## CLOSED

**Primary authority:** None

**Entry conditions**
- `scripts/verify.sh` passes locally
- CI verification is expected to pass
- no contractual rules were violated

**Required actions**
- summarize the session into `ai/sessions/`
- note follow-ups if any
- stop all execution

No further changes are allowed in this state.

---

## Tool Usage Matrix

| Tool        | THINKING | PLANNED | EXECUTING | VERIFYING | CLOSED |
|-------------|----------|---------|-----------|-----------|--------|
| Claude      | ✅       | ✅      | ❌        | ✅        | ❌     |
| Copilot    | ❌       | ❌      | ✅        | ⚠️*      | ❌     |
| verify.sh  | ❌       | ❌      | ❌        | ✅        | ❌     |
| MCP Tools  | ❌       | ❌      | ❌        | ✅        | ❌     |

\* Copilot only when explicitly instructed by Claude.

---

## Verification as Closure Gate

Verification is the **only definition of done**.

A task is incomplete if:
- verification fails
- verification was not run
- verification was bypassed
- verification was weakened

CI enforces this mechanically.

---

## Drift Prevention Rules

To prevent workflow drift:
- states must be respected
- handoffs must be explicit
- verification is mandatory
- memory is never automatic

If drift is detected:
- stop
- document the issue
- update the system explicitly

---

## Guiding Rule

> Do not optimize for speed.
> Optimize for correctness and closure.

The workflow exists to make **correct execution the path of least resistance**.
