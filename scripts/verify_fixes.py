"""
Verification Test — Confirms all 5 problems are solved

Runs the same 7 cycles as the original test but verifies:
  P1: FixDDS has source_dds, error_context, constraints, allowed_paths persisted
  P2: Fix IDs are unique (microsecond precision)
  P3: FailureAnalyzer doesn't re-propose for already-handled failures
  P4: Business errors (DDS not found, not approved) produce status=error in audit
  P5: Error category is captured in audit error_detail
"""

import json
import os
import sys
import time
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
print("VERIFICATION TEST: Confirming all 5 problems are fixed")
print("=" * 70)

with open("node_dds/dds.json", "w") as f:
    json.dump({"proposals": []}, f, indent=2)
with open("node_programmer/reports.json", "w") as f:
    json.dump({"executions": []}, f, indent=2)
with open("audits/contract_audit.jsonl", "w") as f:
    pass

router = Router()
worker = ReactiveWorker()
USER_ID = "verifier-001"
SOURCE = "cli"
SEP = "=" * 70
PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ PASS: {name}")
    else:
        FAIL += 1
        print(f"  ❌ FAIL: {name} — {detail}")


def dispatch(action, payload=None, label=""):
    req = ContractRequest(action=action, payload=payload or {}, source=SOURCE, user_id=USER_ID)
    return router.dispatch(req)


def inject_dds(dds_dict):
    with open("node_dds/dds.json", "r") as f:
        data = json.load(f)
    data["proposals"].append(dds_dict)
    with open("node_dds/dds.json", "w") as f:
        json.dump(data, f, indent=2)


def inject_failed_report(dds_id, action_type, error_msg):
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


def get_last_audit():
    with open("audits/contract_audit.jsonl", "r") as f:
        lines = f.readlines()
    return json.loads(lines[-1]) if lines else {}


def get_all_audits():
    with open("audits/contract_audit.jsonl", "r") as f:
        return [json.loads(line) for line in f.readlines()]


# ══════════════════════════════════════════════
# TEST 1: P1 — FixDDS persists all extended fields
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("TEST 1: P1 — FixDDS persists source_dds, error_context, constraints, allowed_paths")
print(SEP)

test1_id = "DDS-TEST1-P1"
inject_dds({
    "id": test1_id,
    "version": 2,
    "type": "code_change",
    "project": "FitnessAi",
    "title": "Add input validation",
    "description": "Validate user input on login",
    "goal": "Add input validation",
    "instructions": ["Add validation to auth.py"],
    "allowed_paths": ["src/", "tests/"],
    "tool": "aider",
    "constraints": {"max_files_changed": 3, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})

inject_failed_report(test1_id, "code_change",
    "Missing or invalid required field: instructions (must be non-empty list)")

result = worker.run()

# Read dds.json and find the fix
with open("node_dds/dds.json", "r") as f:
    data = json.load(f)

fix_proposals = [p for p in data["proposals"] if p.get("type") == "code_fix"]
check("Fix was generated", len(fix_proposals) == 1,
      f"Expected 1 fix, got {len(fix_proposals)}")

if fix_proposals:
    fix = fix_proposals[0]
    check("source_dds persisted", fix.get("source_dds") == test1_id,
          f"Got: {fix.get('source_dds')}")
    check("error_context persisted", isinstance(fix.get("error_context"), dict),
          f"Got: {type(fix.get('error_context'))}")
    check("error_context.original_dds correct",
          fix.get("error_context", {}).get("original_dds") == test1_id,
          f"Got: {fix.get('error_context', {}).get('original_dds')}")
    check("constraints persisted", isinstance(fix.get("constraints"), dict),
          f"Got: {type(fix.get('constraints'))}")
    check("constraints.no_new_dependencies is True",
          fix.get("constraints", {}).get("no_new_dependencies") is True)
    check("constraints.no_refactor is True",
          fix.get("constraints", {}).get("no_refactor") is True)
    check("constraints.max_files_changed <= 3",
          fix.get("constraints", {}).get("max_files_changed", 99) <= 3)
    check("allowed_paths persisted", isinstance(fix.get("allowed_paths"), list),
          f"Got: {type(fix.get('allowed_paths'))}")
    check("allowed_paths matches original", fix.get("allowed_paths") == ["src/", "tests/"],
          f"Got: {fix.get('allowed_paths')}")
    check("type is code_fix", fix.get("type") == "code_fix")


# ══════════════════════════════════════════════
# TEST 2: P2 — Fix IDs are unique
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("TEST 2: P2 — Fix IDs have microsecond precision, no collisions")
print(SEP)

# Generate a second failure for a different DDS
test2_id = "DDS-TEST2-P2"
inject_dds({
    "id": test2_id,
    "version": 2,
    "type": "code_change",
    "project": "FitnessAi",
    "title": "Add logging",
    "description": "Add logging",
    "goal": "Add structured logging",
    "instructions": ["Add logging to auth.py"],
    "allowed_paths": ["src/"],
    "tool": "aider",
    "constraints": {"max_files_changed": 2, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})

inject_failed_report(test2_id, "code_change", "ImportError: No module named 'structlog'")

# Need fresh worker for fresh FailureAnalyzer state
worker2 = ReactiveWorker()
result2 = worker2.run()

with open("node_dds/dds.json", "r") as f:
    data = json.load(f)

fix_proposals = [p for p in data["proposals"] if p.get("type") == "code_fix"]
fix_ids = [p["id"] for p in fix_proposals]

check("Two fixes generated", len(fix_proposals) == 2,
      f"Expected 2 fixes, got {len(fix_proposals)}")
check("Fix IDs are unique", len(set(fix_ids)) == len(fix_ids),
      f"IDs: {fix_ids}")
check("Fix IDs have microseconds (6 digits at end)",
      all(len(fid.split("-")[-1]) == 6 and fid.split("-")[-1].isdigit() for fid in fix_ids),
      f"IDs: {fix_ids}")


# ══════════════════════════════════════════════
# TEST 3: P3 — FailureAnalyzer doesn't re-propose
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("TEST 3: P3 — FailureAnalyzer skips already-processed failures")
print(SEP)

# Re-run the same worker (which already processed test1_id failure)
result3 = worker.run()
check("Worker returns no_failures on re-run",
      result3["status"] == "no_failures" or result3["proposals_generated"] == 0,
      f"Got: status={result3['status']}, proposals={result3['proposals_generated']}")

# Verify no new fixes were added
with open("node_dds/dds.json", "r") as f:
    data = json.load(f)
fix_count_after = len([p for p in data["proposals"] if p.get("type") == "code_fix"])
check("No duplicate fixes created", fix_count_after == 2,
      f"Expected 2, got {fix_count_after}")


# ══════════════════════════════════════════════
# TEST 4: P4 — Business errors produce status=error
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("TEST 4: P4 — Business errors (not found, not approved) → status=error in audit")
print(SEP)

# 4a: Execute non-existent DDS
resp4a = dispatch(Action.EXECUTE, {"dds_id": "DDS-PHANTOM"}, "phantom")
check("Phantom DDS → status=error", resp4a.status == "error",
      f"Got: {resp4a.status}")

audit4a = get_last_audit()
check("Audit marks error status", audit4a.get("status") == "error",
      f"Got: {audit4a.get('status')}")
check("Audit has error_detail with category", "dds_error" in audit4a.get("error_detail", ""),
      f"Got: {audit4a.get('error_detail', '')[:100]}")

# 4b: Execute DDS that isn't approved (status=proposed)
test4b_id = "DDS-TEST4B-NOTAPPROVED"
inject_dds({
    "id": test4b_id,
    "project": "ai_system",
    "title": "Test not approved",
    "description": "Should fail",
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "proposed"
})

resp4b = dispatch(Action.EXECUTE, {"dds_id": test4b_id}, "not_approved")
check("Not-approved DDS → status=error", resp4b.status == "error",
      f"Got: {resp4b.status}")

audit4b = get_last_audit()
check("Audit for not-approved has error_detail", "dds_error" in audit4b.get("error_detail", ""),
      f"Got: {audit4b.get('error_detail', '')[:100]}")

# 4c: Re-execute already executed DDS
test4c_id = "DDS-TEST4C-REEXEC"
dispatch(Action.DDS_NEW, {
    "project": "FitnessAi",
    "title": "Re-exec test",
    "description": "Test re-execution",
})

with open("node_dds/dds.json", "r") as f:
    data = json.load(f)
for p in data["proposals"]:
    if p.get("title") == "Re-exec test" and p.get("status") == "proposed":
        test4c_id = p["id"]
        break

dispatch(Action.DDS_APPROVE, {"proposal_id": test4c_id})
dispatch(Action.EXECUTE, {"dds_id": test4c_id})  # first exec → success

resp4c = dispatch(Action.EXECUTE, {"dds_id": test4c_id})  # re-exec → should error
check("Re-exec → status=error", resp4c.status == "error",
      f"Got: {resp4c.status}")

audit4c = get_last_audit()
check("Re-exec audit has error_detail", "dds_error" in audit4c.get("error_detail", ""),
      f"Got: {audit4c.get('error_detail', '')[:100]}")


# ══════════════════════════════════════════════
# TEST 5: P5 — Error category persisted in audit
# ══════════════════════════════════════════════

print(f"\n{SEP}")
print("TEST 5: P5 — Error category visible in audit error_detail")
print(SEP)

all_audits = get_all_audits()
error_audits = [a for a in all_audits if a.get("error_detail")]
check("Error audits contain category prefix",
      all(any(cat in a["error_detail"] for cat in ["dds_error", "env_error", "exec_error", "payload_invalid", "source_denied", "handler_exception"])
          for a in error_audits),
      f"Found {len(error_audits)} error audits")

# Check that the error_detail for phantom DDS contains the category
phantom_audits = [a for a in all_audits if a.get("payload_summary", {}).get("dds_id") == "DDS-PHANTOM"]
if phantom_audits:
    check("Phantom DDS error_detail has [dds_error]",
          "dds_error" in phantom_audits[-1].get("error_detail", ""),
          f"Got: {phantom_audits[-1].get('error_detail', '')[:100]}")


# ══════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════

print(f"\n{'=' * 70}")
print(f"VERIFICATION COMPLETE: {PASS} passed, {FAIL} failed")
print(f"{'=' * 70}")

if FAIL > 0:
    print("\n⚠️  SOME CHECKS FAILED — review output above")
    sys.exit(1)
else:
    print("\n✅ ALL CHECKS PASSED — All 5 problems are solved")
    sys.exit(0)
