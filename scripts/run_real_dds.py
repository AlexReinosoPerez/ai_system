"""
Real DDS Execution — Full pipeline through Router Contract v1

Creates, approves, and executes 3 DDS proposals through dispatch().
Verifies audit trail and execution reports.

This script demonstrates the complete governed flow:
  1. Create DDS via dispatch(DDS_NEW)
  2. List proposed DDS via dispatch(DDS_LIST_PROPOSED)
  3. Approve DDS via dispatch(DDS_APPROVE)
  4. Execute DDS via dispatch(EXECUTE)
  5. Verify via dispatch(EXEC_STATUS)
  6. Dump audit trail
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node_interface.contract import Action, ContractRequest
from node_interface.router import Router

# ──────────────────────────────────────────────
# SETUP
# ──────────────────────────────────────────────

router = Router()
USER_ID = "admin-001"
SOURCE = "cli"

SEPARATOR = "=" * 70


def dispatch(action: Action, payload: dict = {}, label: str = "") -> str:
    """Helper: dispatch and print result."""
    req = ContractRequest(
        action=action,
        payload=payload,
        source=SOURCE,
        user_id=USER_ID,
    )
    resp = router.dispatch(req)
    
    status_icon = "✅" if resp.status == "ok" else "❌"
    print(f"\n{status_icon} [{label or action.value}] (audit: {resp.audit_id})")
    print(f"   Status: {resp.status}")
    print(f"   Read-only: {resp.read_only}")
    
    # Print message, indented
    for line in resp.message.split("\n"):
        print(f"   {line}")
    
    return resp.message


# ──────────────────────────────────────────────
# PHASE 1: System status (sanity check)
# ──────────────────────────────────────────────

print(SEPARATOR)
print("PHASE 1: System Status Check")
print(SEPARATOR)

dispatch(Action.SYSTEM_STATUS, label="system_status")


# ──────────────────────────────────────────────
# PHASE 2: Create 3 DDS proposals
# ──────────────────────────────────────────────

print(f"\n{SEPARATOR}")
print("PHASE 2: Create 3 DDS Proposals")
print(SEPARATOR)

# DDS 1: Noop — simple marker (validates basic pipeline)
dispatch(Action.DDS_NEW, {
    "project": "FitnessAi",
    "title": "Add health check endpoint",
    "description": "Create a /health endpoint that returns system status. This is a marker DDS to validate the pipeline works end-to-end.",
}, label="dds_new_1")

# DDS 2: Noop — logging improvement
dispatch(Action.DDS_NEW, {
    "project": "FitnessAi",
    "title": "Add structured logging",
    "description": "Implement structured JSON logging for the FitnessAi service to improve observability in production.",
}, label="dds_new_2")

# DDS 3: Noop — configuration validation
dispatch(Action.DDS_NEW, {
    "project": "ai_system",
    "title": "Config validation on startup",
    "description": "Add startup validation for all required environment variables. Log warnings for missing optional vars and fail fast for missing required vars.",
}, label="dds_new_3")


# ──────────────────────────────────────────────
# PHASE 3: List proposed DDS (should show 3)
# ──────────────────────────────────────────────

print(f"\n{SEPARATOR}")
print("PHASE 3: List Proposed DDS")
print(SEPARATOR)

dispatch(Action.DDS_LIST_PROPOSED, label="list_proposed")


# ──────────────────────────────────────────────
# PHASE 4: Get proposal IDs and approve them
# ──────────────────────────────────────────────

print(f"\n{SEPARATOR}")
print("PHASE 4: Approve All Proposed DDS")
print(SEPARATOR)

# Load DDS to get IDs
with open("node_dds/dds.json", "r") as f:
    dds_data = json.load(f)

proposed_ids = [
    p["id"] for p in dds_data["proposals"]
    if p.get("status") == "proposed"
]

print(f"\n   Found {len(proposed_ids)} proposed DDS: {proposed_ids}")

for pid in proposed_ids:
    dispatch(Action.DDS_APPROVE, {"proposal_id": pid}, label=f"approve_{pid}")


# ──────────────────────────────────────────────
# PHASE 5: List all DDS (should show 3 approved)
# ──────────────────────────────────────────────

print(f"\n{SEPARATOR}")
print("PHASE 5: Verify All Approved")
print(SEPARATOR)

dispatch(Action.DDS_LIST, label="list_all")


# ──────────────────────────────────────────────
# PHASE 6: Execute all approved DDS
# ──────────────────────────────────────────────

print(f"\n{SEPARATOR}")
print("PHASE 6: Execute All DDS")
print(SEPARATOR)

# Reload to get current approved IDs
with open("node_dds/dds.json", "r") as f:
    dds_data = json.load(f)

approved_ids = [
    p["id"] for p in dds_data["proposals"]
    if p.get("status") == "approved"
]

print(f"\n   Found {len(approved_ids)} approved DDS to execute: {approved_ids}")

for did in approved_ids:
    dispatch(Action.EXECUTE, {"dds_id": did}, label=f"execute_{did}")


# ──────────────────────────────────────────────
# PHASE 7: Check execution status
# ──────────────────────────────────────────────

print(f"\n{SEPARATOR}")
print("PHASE 7: Execution Status")
print(SEPARATOR)

dispatch(Action.EXEC_STATUS, label="exec_status")


# ──────────────────────────────────────────────
# PHASE 8: Dump audit trail
# ──────────────────────────────────────────────

print(f"\n{SEPARATOR}")
print("PHASE 8: Audit Trail")
print(SEPARATOR)

audit_file = "audits/contract_audit.jsonl"
if os.path.exists(audit_file):
    with open(audit_file, "r") as f:
        lines = f.readlines()
    
    print(f"\n   Total audit entries: {len(lines)}")
    print(f"   {'─' * 60}")
    
    for i, line in enumerate(lines, 1):
        entry = json.loads(line)
        icon = "✅" if entry["status"] == "ok" else "❌"
        print(
            f"   {i:2d}. {icon} {entry['action']:20s} | "
            f"source={entry['source']:8s} | "
            f"user={entry['user_id']:10s} | "
            f"read_only={entry['read_only']}"
        )
else:
    print("   ⚠️  No audit file found")


# ──────────────────────────────────────────────
# PHASE 9: Dump execution reports
# ──────────────────────────────────────────────

print(f"\n{SEPARATOR}")
print("PHASE 9: Execution Reports")
print(SEPARATOR)

with open("node_programmer/reports.json", "r") as f:
    reports = json.load(f)

executions = reports.get("executions", [])
print(f"\n   Total execution reports: {len(executions)}")
print(f"   {'─' * 60}")

for i, ex in enumerate(executions, 1):
    icon = "✅" if ex["status"] == "success" else "❌"
    print(f"   {i}. {icon} {ex['dds_id']}")
    print(f"      Type: {ex['action_type']} | Status: {ex['status']}")
    print(f"      At: {ex['executed_at']}")
    print(f"      Notes: {ex['notes'][:100]}")
    print()

print(f"\n{SEPARATOR}")
print("DONE — Full DDS pipeline executed through Router Contract v1")
print(SEPARATOR)
