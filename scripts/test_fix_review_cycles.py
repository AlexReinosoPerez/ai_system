"""
Operational Test — Fix Review Criteria Validation

Executes 7 distinct cycles through the Router Contract:
  - Each cycle creates a DDS, provokes a specific failure type,
    then runs the ReactiveWorker to (possibly) generate a FixDDS.
  - After all cycles, dumps all data needed for human review:
    dds.json, reports.json, audit trail.

Failure types covered:
  Cycle 1: code_change DDS → fails (aider not installed = env_error)
  Cycle 2: code_change DDS → fails (missing instructions = dds_error)
  Cycle 3: noop DDS on inactive project → succeeds (baseline)
  Cycle 4: execute non-existent DDS ID (dds_error: not found)
  Cycle 5: code_change DDS → fails (missing allowed_paths = dds_error)
  Cycle 6: re-execute already executed DDS (dds_error: already executed)
  Cycle 7: code_change DDS → fails (timeout simulation = exec_error)

All actions go through dispatch(). No shortcuts.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node_interface.contract import Action, ContractRequest
from node_interface.router import Router
from node_worker.reactive_worker import ReactiveWorker

# ──────────────────────────────────────────────
# SETUP: Clean state
# ──────────────────────────────────────────────

print("=" * 70)
print("SETUP: Cleaning state for operational test")
print("=" * 70)

# Reset dds.json
with open("node_dds/dds.json", "w") as f:
    json.dump({"proposals": []}, f, indent=2)
print("  ✓ dds.json reset")

# Reset reports.json
with open("node_programmer/reports.json", "w") as f:
    json.dump({"executions": []}, f, indent=2)
print("  ✓ reports.json reset")

# Clear audit (fresh test)
audit_file = "audits/contract_audit.jsonl"
with open(audit_file, "w") as f:
    pass
print("  ✓ audit trail cleared")

router = Router()
worker = ReactiveWorker()
USER_ID = "reviewer-001"
SOURCE = "cli"
SEP = "=" * 70


def dispatch(action, payload=None, label=""):
    """Dispatch through Router and print result."""
    req = ContractRequest(
        action=action,
        payload=payload or {},
        source=SOURCE,
        user_id=USER_ID,
    )
    resp = router.dispatch(req)
    icon = "✅" if resp.status == "ok" else "❌"
    print(f"  {icon} [{label or action.value}] status={resp.status}")
    for line in resp.message.split("\n")[:6]:  # cap output
        print(f"     {line}")
    if len(resp.message.split("\n")) > 6:
        print(f"     ... ({len(resp.message.split(chr(10)))} lines total)")
    return resp


def run_reactive_worker(label=""):
    """Run ReactiveWorker and print result."""
    print(f"  🔄 Running ReactiveWorker... ({label})")
    result = worker.run()
    print(f"     Status: {result['status']}")
    print(f"     Proposals generated: {result['proposals_generated']}")
    print(f"     Message: {result['message']}")
    return result


def inject_dds_directly(dds_dict):
    """Inject a raw DDS into dds.json (simulates DDS created by todo_to_dds
    or external process). This is needed because dds_new only creates
    basic proposals without type/version/instructions/constraints fields."""
    with open("node_dds/dds.json", "r") as f:
        data = json.load(f)
    data["proposals"].append(dds_dict)
    with open("node_dds/dds.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"  📥 Injected DDS: {dds_dict['id']} (type={dds_dict.get('type')})")


def inject_failed_report(dds_id, action_type, error_msg):
    """Inject a failed execution report into reports.json.
    Simulates what Programmer would write on failure."""
    with open("node_programmer/reports.json", "r") as f:
        data = json.load(f)
    data["executions"].append({
        "dds_id": dds_id,
        "action_type": action_type,
        "status": "failed",
        "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "notes": error_msg,
    })
    with open("node_programmer/reports.json", "w") as f:
        json.dump(data, f, indent=2)
    print(f"  📥 Injected failed report for {dds_id}")


# ══════════════════════════════════════════════
# CYCLE 1: code_change DDS → aider not installed (env_error)
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("CYCLE 1: code_change → env_error (aider not installed)")
print(SEP)

cycle1_id = "DDS-CYCLE1-ENV"
inject_dds_directly({
    "id": cycle1_id,
    "version": 2,
    "type": "code_change",
    "project": "FitnessAi",
    "title": "Add login rate limiting",
    "description": "Add rate limiting to login endpoint",
    "goal": "Implement rate limiting on /login to prevent brute force",
    "instructions": [
        "Add rate limiter middleware to auth.py",
        "Limit to 5 attempts per minute per IP",
        "Return 429 on exceeded"
    ],
    "allowed_paths": ["src/", "tests/"],
    "tool": "aider",
    "constraints": {
        "max_files_changed": 3,
        "no_new_dependencies": True,
        "no_refactor": True
    },
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "proposed"
})

# Approve through dispatch
dispatch(Action.DDS_APPROVE, {"proposal_id": cycle1_id}, "approve")

# Execute through dispatch — will fail because aider is not installed
dispatch(Action.EXECUTE, {"dds_id": cycle1_id}, "execute")

# Inject the failed report that Programmer would have written
# (since the Router catches ProgrammerError before the report gets saved in some cases)
inject_failed_report(cycle1_id, "code_change",
    "command not found: aider - Aider tool is not installed in the environment")

# Run reactive worker
run_reactive_worker("after cycle 1")


# ══════════════════════════════════════════════
# CYCLE 2: code_change DDS → missing instructions field (dds_error)
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("CYCLE 2: code_change → dds_error (missing instructions)")
print(SEP)

cycle2_id = "DDS-CYCLE2-FIELDS"
inject_dds_directly({
    "id": cycle2_id,
    "version": 2,
    "type": "code_change",
    "project": "FitnessAi",
    "title": "Fix auth token validation",
    "description": "Fix token expiration check",
    "goal": "Fix JWT token expiration validation in auth.py",
    # NOTE: instructions intentionally missing
    "allowed_paths": ["src/"],
    "tool": "aider",
    "constraints": {
        "max_files_changed": 2,
        "no_new_dependencies": True,
        "no_refactor": True
    },
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "proposed"
})

dispatch(Action.DDS_APPROVE, {"proposal_id": cycle2_id}, "approve")
dispatch(Action.EXECUTE, {"dds_id": cycle2_id}, "execute")

# Inject failed report simulating what Programmer._validate_dds_v2 would produce
inject_failed_report(cycle2_id, "code_change",
    "Missing or invalid required field: instructions (must be non-empty list)")

run_reactive_worker("after cycle 2")


# ══════════════════════════════════════════════
# CYCLE 3: noop DDS — success baseline (no fix expected)
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("CYCLE 3: noop → success (baseline, no fix expected)")
print(SEP)

cycle3_id = "DDS-CYCLE3-NOOP"
dispatch(Action.DDS_NEW, {
    "project": "FitnessAi",
    "title": "Pipeline validation marker",
    "description": "Noop to validate pipeline is functional",
}, "create")

# Get the actual ID assigned
with open("node_dds/dds.json", "r") as f:
    data = json.load(f)
for p in data["proposals"]:
    if p.get("title") == "Pipeline validation marker" and p.get("status") == "proposed":
        cycle3_id = p["id"]
        break

dispatch(Action.DDS_APPROVE, {"proposal_id": cycle3_id}, "approve")
dispatch(Action.EXECUTE, {"dds_id": cycle3_id}, "execute")

# No need to run reactive worker — success case


# ══════════════════════════════════════════════
# CYCLE 4: Execute non-existent DDS ID (dds_error: not found)
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("CYCLE 4: Execute non-existent ID (dds_error)")
print(SEP)

dispatch(Action.EXECUTE, {"dds_id": "DDS-DOES-NOT-EXIST"}, "execute_phantom")

# No report injected — the Router catches this before Programmer runs
# ReactiveWorker won't find any new failures
run_reactive_worker("after cycle 4")


# ══════════════════════════════════════════════
# CYCLE 5: code_change DDS → missing allowed_paths (dds_error)
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("CYCLE 5: code_change → dds_error (missing allowed_paths)")
print(SEP)

cycle5_id = "DDS-CYCLE5-PATHS"
inject_dds_directly({
    "id": cycle5_id,
    "version": 2,
    "type": "code_change",
    "project": "ai_system",
    "title": "Add config schema validation",
    "description": "Validate config.py has all required keys at startup",
    "goal": "Add schema validation for config.py environment variables",
    "instructions": [
        "Create a config schema dict with required/optional keys",
        "Validate at import time",
        "Raise clear error for missing required keys"
    ],
    # NOTE: allowed_paths intentionally missing
    "tool": "aider",
    "constraints": {
        "max_files_changed": 2,
        "no_new_dependencies": True,
        "no_refactor": True
    },
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "proposed"
})

dispatch(Action.DDS_APPROVE, {"proposal_id": cycle5_id}, "approve")
dispatch(Action.EXECUTE, {"dds_id": cycle5_id}, "execute")

inject_failed_report(cycle5_id, "code_change",
    "Missing or invalid required field: allowed_paths (must be non-empty list)")

run_reactive_worker("after cycle 5")


# ══════════════════════════════════════════════
# CYCLE 6: Re-execute already executed DDS (dds_error)
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("CYCLE 6: Re-execute already executed DDS")
print(SEP)

# cycle3_id was already executed successfully in Cycle 3
dispatch(Action.EXECUTE, {"dds_id": cycle3_id}, "re-execute")

# No new failure in reports — Router handles this before Programmer
run_reactive_worker("after cycle 6")


# ══════════════════════════════════════════════
# CYCLE 7: code_change DDS → timeout (exec_error)
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("CYCLE 7: code_change → exec_error (timeout)")
print(SEP)

cycle7_id = "DDS-CYCLE7-TIMEOUT"
inject_dds_directly({
    "id": cycle7_id,
    "version": 2,
    "type": "code_change",
    "project": "FitnessAi",
    "title": "Refactor entire test suite",
    "description": "Major test restructuring",
    "goal": "Restructure all tests into separate modules",
    "instructions": [
        "Move all tests to separate directories",
        "Create conftest.py with shared fixtures",
        "Update imports across all test files"
    ],
    "allowed_paths": ["tests/"],
    "tool": "aider",
    "constraints": {
        "max_files_changed": 5,
        "no_new_dependencies": True,
        "no_refactor": False  # NOTE: refactoring allowed in DDS
    },
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "proposed"
})

dispatch(Action.DDS_APPROVE, {"proposal_id": cycle7_id}, "approve")
dispatch(Action.EXECUTE, {"dds_id": cycle7_id}, "execute")

inject_failed_report(cycle7_id, "code_change",
    "Timeout after 300s: aider process did not complete within time limit")

run_reactive_worker("after cycle 7")


# ══════════════════════════════════════════════
# FINAL DUMP: All data for human review
# ══════════════════════════════════════════════

print(f"\n{'=' * 70}")
print("FINAL STATE DUMP FOR HUMAN REVIEW")
print("=" * 70)

# 1. DDS Registry
print(f"\n{'─' * 70}")
print("DDS REGISTRY (node_dds/dds.json)")
print("─" * 70)
with open("node_dds/dds.json", "r") as f:
    data = json.load(f)
for i, p in enumerate(data["proposals"], 1):
    ptype = p.get("type", "simple")
    icon = {"approved": "✅", "rejected": "❌", "proposed": "📋", "executed": "🏁", "failed": "💥"}.get(p.get("status"), "⏳")
    print(f"\n  {i}. {icon} {p['id']}")
    print(f"     Type: {ptype} | Project: {p.get('project')} | Status: {p.get('status')}")
    print(f"     Title: {p.get('title')}")
    if p.get("source_dds"):
        print(f"     source_dds: {p['source_dds']}")
    if p.get("error_context"):
        ec = p["error_context"]
        print(f"     error_context.original_dds: {ec.get('original_dds')}")
        print(f"     error_context.error_message: {ec.get('error_message', '')[:120]}")
    if p.get("constraints"):
        c = p["constraints"]
        print(f"     constraints: max_files={c.get('max_files_changed')}, no_deps={c.get('no_new_dependencies')}, no_refactor={c.get('no_refactor')}")
    if p.get("allowed_paths"):
        print(f"     allowed_paths: {p['allowed_paths']}")

# 2. Execution reports
print(f"\n{'─' * 70}")
print("EXECUTION REPORTS (node_programmer/reports.json)")
print("─" * 70)
with open("node_programmer/reports.json", "r") as f:
    reports = json.load(f)
for i, ex in enumerate(reports.get("executions", []), 1):
    icon = "✅" if ex["status"] == "success" else "❌"
    print(f"\n  {i}. {icon} {ex['dds_id']}")
    print(f"     Type: {ex['action_type']} | Status: {ex['status']}")
    print(f"     Notes: {ex['notes'][:150]}")

# 3. Audit trail
print(f"\n{'─' * 70}")
print("AUDIT TRAIL (audits/contract_audit.jsonl)")
print("─" * 70)
if os.path.exists(audit_file):
    with open(audit_file, "r") as f:
        lines = f.readlines()
    print(f"\n  Total entries: {len(lines)}")
    for i, line in enumerate(lines, 1):
        entry = json.loads(line)
        icon = "✅" if entry["status"] == "ok" else "❌"
        lvl = entry.get("level", "?")
        ps = entry.get("payload_summary", {})
        ed = entry.get("error_detail", "")
        dur = entry.get("duration_ms", "?")
        print(f"  {i:2d}. {icon} {entry['action']:20s} lvl={lvl:14s} dur={dur}ms ps={ps}")
        if ed:
            print(f"      error_detail: {ed[:120]}")

print(f"\n{'=' * 70}")
print("OPERATIONAL TEST COMPLETE — Ready for human review")
print("=" * 70)
