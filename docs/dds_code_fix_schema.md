# DDS Type: `code_fix` v2 — Schema Specification

**Version**: 2.0  
**Date**: 2026-02-02  
**Status**: Approved for Implementation  

---

## Overview

The `code_fix` DDS type is a specialized variant of DDS v2 designed for **corrective actions** in response to failed executions. It is more restrictive than `code_change` and includes explicit traceability to the failed DDS.

---

## Schema Definition

### Complete Structure

```json
{
  "id": "DDS-FIX-YYYYMMDD-XXX",
  "version": 2,
  "type": "code_fix",
  "project": "<string>",
  "goal": "<string>",
  "instructions": ["<string>"],
  "allowed_paths": ["<string>"],
  "tool": "<string>",
  "constraints": {
    "max_files_changed": "<number>",
    "no_new_dependencies": "<boolean>",
    "no_refactor": "<boolean>"
  },
  "status": "proposed",
  "source_dds": "<string>",
  "error_context": {
    "original_dds": "<string>",
    "error_message": "<string>",
    "failed_at": "<ISO-8601 timestamp>"
  }
}
```

---

## Field Specifications

### Required Fields

| Field             | Type     | Description                                           | Rules                                      |
|-------------------|----------|-------------------------------------------------------|--------------------------------------------|
| `id`              | string   | Unique identifier                                     | Format: `DDS-FIX-YYYYMMDD-XXX`             |
| `version`         | number   | DDS schema version                                    | Must be `2`                                |
| `type`            | string   | DDS type discriminator                                | Must be `"code_fix"`                       |
| `project`         | string   | Project name                                          | Inherited from failed DDS                  |
| `goal`            | string   | Fix objective                                         | Must reference original DDS ID             |
| `instructions`    | array    | Step-by-step fix instructions                         | Conservative, error-focused                |
| `allowed_paths`   | array    | Permitted file paths                                  | **Must not expand** from failed DDS        |
| `tool`            | string   | Execution tool                                        | Inherited from failed DDS                  |
| `constraints`     | object   | Execution constraints                                 | More restrictive than failed DDS           |
| `status`          | string   | Approval status                                       | **Always** `"proposed"`                    |
| `source_dds`      | string   | ID of failed DDS                                      | Must reference existing failed DDS         |
| `error_context`   | object   | Structured error information                          | See below                                  |

### `error_context` Object

| Field             | Type     | Description                                           | Rules                                      |
|-------------------|----------|-------------------------------------------------------|--------------------------------------------|
| `original_dds`    | string   | ID of the DDS that failed                             | Must match `source_dds`                    |
| `error_message`   | string   | Error output from failed execution                    | Max 500 chars, sanitized                   |
| `failed_at`       | string   | Timestamp of failure                                  | ISO-8601 format                            |

---

## Constraints Inheritance Rules

`code_fix` DDS constraints are derived from the failed DDS but **never less restrictive**:

```python
code_fix.constraints.max_files_changed = min(
    failed_dds.constraints.max_files_changed,
    3  # Hard limit for code_fix
)

code_fix.constraints.no_new_dependencies = True  # Always enforced

code_fix.constraints.no_refactor = True  # Always enforced
```

### Constraint Comparison

| Constraint               | `code_change` DDS  | `code_fix` DDS     |
|--------------------------|--------------------|--------------------|
| `max_files_changed`      | Configurable (5+)  | Max 3 (enforced)   |
| `no_new_dependencies`    | Configurable       | Always `true`      |
| `no_refactor`            | Configurable       | Always `true`      |

---

## Validation Rules

Before accepting a `code_fix` DDS:

1. **ID Format**: Must match `DDS-FIX-\d{8}-\d{3}`
2. **Version**: Must be `2`
3. **Type**: Must be `"code_fix"`
4. **Status**: Must be `"proposed"` (never `"approved"` on creation)
5. **Source DDS**: Must reference an existing DDS with `status="failed"`
6. **Allowed Paths**: Must be subset or equal to failed DDS paths (no additions)
7. **Constraints**: Must be equal or more restrictive than failed DDS
8. **Error Context**: All fields required and non-empty
9. **Error Message**: Max 500 characters
10. **No Duplicates**: No existing `code_fix` with same `source_dds`

---

## Example: Complete `code_fix` DDS

### Scenario

Original DDS `DDS-20260202-CODE-001` failed with error:
```
TypeError: unsupported operand type(s) for +: 'int' and 'str'
  File "src/calculator.py", line 42, in calculate
```

### Generated `code_fix` DDS

```json
{
  "id": "DDS-FIX-20260202-001",
  "version": 2,
  "type": "code_fix",
  "project": "ai_system",
  "goal": "Fix execution failure in DDS-20260202-CODE-001: TypeError in calculator.py",
  "instructions": [
    "Analyze error: TypeError at src/calculator.py line 42",
    "Identify type mismatch between int and str operands",
    "Add type conversion or validation before operation",
    "Verify fix resolves error without breaking existing tests"
  ],
  "allowed_paths": [
    "src/calculator.py",
    "tests/test_calculator.py"
  ],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 2,
    "no_new_dependencies": true,
    "no_refactor": true
  },
  "status": "proposed",
  "source_dds": "DDS-20260202-CODE-001",
  "error_context": {
    "original_dds": "DDS-20260202-CODE-001",
    "error_message": "TypeError: unsupported operand type(s) for +: 'int' and 'str'\n  File \"src/calculator.py\", line 42, in calculate\n    result = value1 + value2",
    "failed_at": "2026-02-02T15:30:45.123456"
  }
}
```

---

## Comparison: `code_change` vs `code_fix`

### Example `code_change` DDS (Original)

```json
{
  "id": "DDS-20260202-CODE-001",
  "version": 2,
  "type": "code_change",
  "project": "ai_system",
  "goal": "Add calculator functionality",
  "instructions": [
    "Create calculator module",
    "Implement add, subtract, multiply, divide",
    "Add comprehensive tests"
  ],
  "allowed_paths": [
    "src/",
    "tests/"
  ],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 5,
    "no_new_dependencies": true,
    "no_refactor": false
  },
  "status": "approved"
}
```

### Corresponding `code_fix` DDS (After Failure)

```json
{
  "id": "DDS-FIX-20260202-001",
  "version": 2,
  "type": "code_fix",
  "project": "ai_system",
  "goal": "Fix execution failure in DDS-20260202-CODE-001: TypeError in calculator.py",
  "instructions": [
    "Analyze error: TypeError at src/calculator.py line 42",
    "Identify type mismatch between int and str operands",
    "Add type conversion or validation before operation",
    "Verify fix resolves error without breaking existing tests"
  ],
  "allowed_paths": [
    "src/calculator.py",
    "tests/test_calculator.py"
  ],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 2,
    "no_new_dependencies": true,
    "no_refactor": true
  },
  "status": "proposed",
  "source_dds": "DDS-20260202-CODE-001",
  "error_context": {
    "original_dds": "DDS-20260202-CODE-001",
    "error_message": "TypeError: unsupported operand type(s) for +: 'int' and 'str'\n  File \"src/calculator.py\", line 42, in calculate",
    "failed_at": "2026-02-02T15:30:45.123456"
  }
}
```

### Key Differences

| Aspect              | `code_change`         | `code_fix`                    |
|---------------------|-----------------------|-------------------------------|
| **Purpose**         | Implement new feature | Fix failed execution          |
| **Scope**           | Broad (`src/`)        | Narrow (specific files)       |
| **Constraints**     | Configurable          | Always restrictive            |
| **Status**          | Can be `approved`     | Always `proposed` on creation |
| **Traceability**    | None                  | `source_dds` + `error_context`|
| **Instructions**    | Feature-focused       | Error-focused                 |

---

## Integration with Programmer v2.1

### Compatibility

`code_fix` DDS is **fully compatible** with Programmer v2.1 because:
- Uses same DDS v2 schema structure
- All required fields present
- Constraints are subset of `code_change` constraints
- No new Programmer features required

### Programmer Behavior

When executing `code_fix` DDS:
1. Validates as standard DDS v2
2. Applies `allowed_paths` scoping (phase 4)
3. Enforces `constraints` (phase 7)
4. Writes execution result to `reports.json` (phase 8)
5. Updates DDS `status` to `executed` or `failed` (phase 8)

**No special handling required** — Programmer treats `code_fix` identically to `code_change`.

---

## Security Considerations

### Path Validation

```python
def validate_allowed_paths(code_fix_dds, failed_dds):
    """Ensure code_fix doesn't expand scope beyond failed DDS."""
    for path in code_fix_dds['allowed_paths']:
        # Must be subset of failed DDS paths
        if not any(path.startswith(p) for p in failed_dds['allowed_paths']):
            raise ValidationError(f"Path {path} not in failed DDS scope")
        
        # No path traversal
        if '..' in path or path.startswith('/'):
            raise ValidationError(f"Invalid path: {path}")
```

### Error Message Sanitization

```python
def sanitize_error_message(error_message: str) -> str:
    """Truncate and sanitize error message."""
    # Truncate to 500 chars
    truncated = error_message[:500]
    
    # Remove potential injection vectors
    sanitized = truncated.replace('\x00', '').replace('\r', '\n')
    
    return sanitized
```

---

## State Transitions

```
code_change (approved) ──[execute]──▶ code_change (executed/failed)
                                                │
                                                │ [Worker detects failure]
                                                ▼
                                      code_fix (proposed)
                                                │
                                                │ [Human approves]
                                                ▼
                                      code_fix (approved)
                                                │
                                                │ [Scheduler executes]
                                                ▼
                                      code_fix (executed/failed)
```

### Status Rules

- `code_fix` **always created** with `status="proposed"`
- `code_fix` **never auto-approved** (Worker has no approval authority)
- `code_fix` can transition to `approved` **only via human action**
- `code_fix` execution follows same rules as `code_change`

---

## Rejection Handling

If `code_fix` DDS is rejected by human:
1. Status updated to `"rejected"`
2. Original failed DDS remains `status="failed"`
3. Worker will NOT regenerate same `code_fix` (deduplication by `source_dds`)
4. Human must create new DDS manually if different fix approach needed

---

## Implementation Checklist

- [ ] Add `"code_fix"` to DDS type enum
- [ ] Extend `DDSProposal` class to handle `error_context`
- [ ] Add validation for `code_fix` constraints
- [ ] Implement path subset validation
- [ ] Add error message sanitization
- [ ] Update DDS Registry to support `code_fix`
- [ ] Add deduplication check by `source_dds`
- [ ] Extend Programmer to handle `code_fix` (no changes needed if schema-agnostic)
- [ ] Update documentation in `node_dds/README.md`

---

## Approval

This schema specification is ready for implementation.

**Approved by**: Architecture Team  
**Date**: 2026-02-02  

---

**End of Specification**
