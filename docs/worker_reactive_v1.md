# Worker Reactivo v1 — Architectural Specification

**Status**: Draft  
**Version**: 1.0.0  
**Date**: 2026-02-02  
**Author**: Architecture Team  

---

## 1. Purpose

Define a **Reactive Worker** that detects execution failures and generates corrective DDS proposals **without autonomous execution**.

This specification establishes hard boundaries to preserve the human-governed execution model of ai_system.

---

## 2. Scope

### In Scope

- **Failure detection**: Monitor execution reports for `status=failed`
- **Corrective proposal generation**: Create DDS with `type=code_fix`
- **Stop-on-failure semantics**: Worker halts after first correction proposal
- **Human approval requirement**: All generated DDS have `status=proposed`

### Out of Scope

- Autonomous execution of corrections
- Multi-step reasoning or planning
- Retry logic without human approval
- Parallel processing of failures
- Root cause analysis beyond error message parsing

---

## 3. Architecture

### 3.1 Position in System

```
┌──────────────────────────────────────────────────────────┐
│                      ai_system                           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐      ┌──────────────┐                 │
│  │   Human     │──────▶│ DDS Registry │                 │
│  │  Approval   │       │ (proposed)   │                 │
│  └─────────────┘       └──────────────┘                 │
│         │                      │                         │
│         │ approve              │                         │
│         ▼                      ▼                         │
│  ┌─────────────┐       ┌──────────────┐                │
│  │  Scheduler  │───────▶│  Programmer  │                │
│  │             │        │   v2.1       │                │
│  └─────────────┘        └──────────────┘                │
│         │                      │                         │
│         │                      │ reports.json            │
│         │                      ▼                         │
│         │               ┌──────────────┐                │
│         │               │  Execution   │                │
│         │               │   Reports    │                │
│         │               └──────────────┘                │
│         │                      │                         │
│         │                      │ monitor                 │
│         │                      ▼                         │
│         │               ┌──────────────┐                │
│         └───────────────│   Worker     │                │
│                         │  Reactive    │                │
│                         │    v1        │                │
│                         └──────────────┘                │
│                                │                         │
│                                │ generates               │
│                                ▼                         │
│                         ┌──────────────┐                │
│                         │ DDS code_fix │                │
│                         │ (proposed)   │                │
│                         └──────────────┘                │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 3.2 Execution Flow

1. **Scheduler** executes approved DDS via **Programmer**
2. **Programmer** writes execution result to `reports.json`
3. **Worker Reactive** reads `reports.json` (passive monitoring)
4. **If `status=failed`**:
   - Worker generates DDS with `type=code_fix`, `status=proposed`
   - Worker writes to `dds.json`
   - Worker **stops** (stop-on-failure)
5. **Human** reviews proposed correction
6. **Human** approves or rejects correction DDS
7. **Scheduler** executes approved correction (next run)

---

## 4. DDS Type: `code_fix`

### 4.1 Schema Extension

```json
{
  "id": "DDS-FIX-YYYYMMDD-XXX",
  "version": 2,
  "type": "code_fix",
  "project": "<same as failed DDS>",
  "goal": "Fix execution failure: <original DDS id>",
  "instructions": [
    "Analyze error: <error message>",
    "Identify root cause in affected files",
    "Apply minimal fix to resolve error",
    "Verify fix doesn't break existing tests"
  ],
  "allowed_paths": ["<same as failed DDS>"],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 3,
    "no_new_dependencies": true,
    "no_refactor": true
  },
  "status": "proposed",
  "source_dds": "<failed DDS id>",
  "error_context": {
    "original_dds": "<failed DDS id>",
    "error_message": "<truncated error from report>",
    "failed_at": "<timestamp>"
  }
}
```

### 4.2 Field Definitions

- **`type`**: `"code_fix"` (new type, distinct from `code_change`)
- **`source_dds`**: ID of the DDS that failed
- **`error_context`**: Structured error information
  - `original_dds`: Failed DDS ID
  - `error_message`: First 500 chars of error from report
  - `failed_at`: Timestamp of failure
- **`goal`**: Must reference original DDS explicitly
- **`instructions`**: Conservative, error-focused steps
- **`allowed_paths`**: Inherited from failed DDS (no expansion)
- **`constraints`**: More restrictive than original DDS

### 4.3 Inheritance Rules

| Field              | Inheritance Rule                          |
|--------------------|-------------------------------------------|
| `project`          | Copy from failed DDS                      |
| `allowed_paths`    | Copy from failed DDS (no additions)       |
| `tool`             | Copy from failed DDS                      |
| `constraints`      | Min(`failed_dds.constraints`, v1_limits)  |
| `status`           | Always `"proposed"` (never `"approved"`)  |

---

## 5. Worker Reactive v1 Specification

### 5.1 Responsibilities

1. **Monitor**: Read `reports.json` for new failures
2. **Detect**: Identify `status=failed` executions
3. **Generate**: Create `code_fix` DDS proposals
4. **Persist**: Write to `dds.json`
5. **Stop**: Halt after first proposal generation

### 5.2 Trigger Conditions

Worker activates when:
- `reports.json` contains an execution with `status=failed`
- No existing `code_fix` DDS exists for that failed DDS ID
- Failed DDS has `type=code_change` or `type=code_fix` (not `touch_file`)

### 5.3 Stop Conditions

Worker stops when:
- First `code_fix` DDS is generated
- No failures detected in `reports.json`
- Error parsing `reports.json` or `dds.json`

### 5.4 Non-features (Explicit)

- ❌ Does NOT execute corrections
- ❌ Does NOT retry automatically
- ❌ Does NOT analyze multiple failures in one run
- ❌ Does NOT learn from past failures
- ❌ Does NOT escalate to human proactively
- ❌ Does NOT modify Programmer behavior
- ❌ Does NOT run continuously (invoked explicitly)

---

## 6. Constraints

### 6.1 Hard Limits

- **Max correction DDS per run**: 1
- **Max files changed in correction**: 3
- **Max error message length**: 500 chars
- **No new dependencies**: Always `true`
- **No refactor**: Always `true`

### 6.2 Validation Rules

Before generating `code_fix` DDS:
1. Failed DDS must exist in `dds.json`
2. Failed DDS must have `status=failed`
3. No existing `code_fix` DDS with same `source_dds`
4. Error message must be non-empty
5. `allowed_paths` must be valid (no path traversal)

---

## 7. Integration Points

### 7.1 With Programmer

- **Read-only**: Worker never modifies Programmer state
- **Passive monitoring**: Worker polls `reports.json`, does not hook into Programmer
- **No execution**: Worker does not call `Programmer.execute()`

### 7.2 With Scheduler

- **Decoupled**: Worker is NOT called by Scheduler
- **Human-triggered**: Worker invoked manually or via cron (separate from Scheduler)
- **No automatic retry**: Scheduler treats `code_fix` DDS like any other approved DDS

### 7.3 With DDS Registry

- **Write-only for proposals**: Worker writes `code_fix` DDS to `dds.json`
- **Read for deduplication**: Worker checks if `code_fix` already exists for failed DDS

---

## 8. Execution Model

### 8.1 Invocation

```bash
# Manual invocation
python -c "from node_worker import ReactiveWorker; ReactiveWorker().run()"

# Cron-scheduled (e.g., 5 minutes after Scheduler)
5 2 * * * cd /app && python -c "from node_worker import ReactiveWorker; ReactiveWorker().run()"
```

### 8.2 Return Values

```python
{
    'status': 'completed' | 'no_failures' | 'stopped_on_error',
    'proposals_generated': int,
    'failed_dds_id': str | None,
    'message': str
}
```

### 8.3 Idempotency

Worker is **idempotent**:
- Running multiple times on same failure generates same `code_fix` DDS (deduplication by `source_dds`)
- Safe to invoke repeatedly without side effects

---

## 9. Security Considerations

### 9.1 Privilege Boundaries

- Worker runs with **same privileges** as Programmer (no escalation)
- Worker does NOT bypass human approval
- Worker does NOT modify approved DDS

### 9.2 Input Validation

- **Error messages**: Truncated to 500 chars, sanitized for injection
- **Paths**: Validated against path traversal
- **DDS IDs**: Validated format `DDS-*`

### 9.3 Audit Trail

- All generated `code_fix` DDS logged to `audits/`
- Worker execution logged with timestamp and result
- No automatic deletion of failed DDS (full history preserved)

---

## 10. Failure Modes

### 10.1 Worker Failures

| Failure                     | Behavior                                      |
|-----------------------------|-----------------------------------------------|
| `reports.json` corrupted    | Log error, return `stopped_on_error`          |
| `dds.json` write fails      | Log error, do NOT mark DDS as generated       |
| Invalid failed DDS format   | Skip, log warning, return `no_failures`       |
| Multiple failures detected  | Process first only, stop                      |

### 10.2 Correction Failures

If generated `code_fix` DDS fails execution:
- **No automatic re-correction**: Human must diagnose and create new DDS manually
- **Worker does NOT recurse**: Will not generate `code_fix` for another `code_fix`

---

## 11. Metrics and Observability

### 11.1 Logged Metrics

- `worker_invocations`: Total runs
- `failures_detected`: Count of failed DDS found
- `proposals_generated`: Count of `code_fix` DDS created
- `duplicates_skipped`: Count of already-proposed corrections
- `errors_encountered`: Worker-level errors

### 11.2 Success Criteria

- **Proposal generation**: `code_fix` DDS written to `dds.json`
- **No false positives**: Only generates for actual failures
- **Idempotency**: Same failure always produces same proposal

---

## 12. Future Considerations (Non-committal)

Potential v2 enhancements (NOT in v1):
- Multiple correction strategies (currently: single conservative approach)
- Context enrichment (currently: error message only)
- Confidence scoring (currently: all proposals treated equally)
- Batch processing (currently: one-at-a-time)

---

## 13. Implementation Checklist

- [ ] Create `node_worker/` module
- [ ] Implement `ReactiveWorker` class
- [ ] Add `code_fix` type support to `DDSRegistry`
- [ ] Validate against existing DDS v2 schema
- [ ] Add deduplication logic
- [ ] Implement error truncation and sanitization
- [ ] Add comprehensive logging
- [ ] Write unit tests for failure detection
- [ ] Write integration tests with Programmer/Scheduler
- [ ] Document in README.md
- [ ] Update CHANGELOG.md for v1.1.0

---

## 14. Approval

This specification requires approval from:
- [ ] Architecture Team
- [ ] Security Review
- [ ] Human Oversight (system owner)

Once approved, implementation proceeds under **IMPLEMENTER** role with zero deviation from this contract.

---

**End of Specification**
