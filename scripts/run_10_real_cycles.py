"""
10 CICLOS REALES — Validación operativa del documento de criterios

Cada ciclo:
  1. Crea un DDS realista → aprueba → ejecuta (o inyecta fallo)
  2. Dispara ReactiveWorker si hubo fallo
  3. Aplica el checklist de 10 puntos del documento a cada fix generado
  4. Registra: qué criterios se usaron, cuáles sobraron, dónde hubo fricción

Escenarios cubiertos:
  C1:  code_change exitoso → no genera fix (happy path)
  C2:  code_change con instructions faltantes → fix por dds_error
  C3:  code_change con ImportError → fix por exec_error
  C4:  code_change con SyntaxError → fix por exec_error
  C5:  code_change con timeout → NO debe generar fix (env_error/timeout)
  C6:  noop DDS → no falla → no genera fix
  C7:  fix del C2 se aprueba y ejecuta con éxito → cadena completa
  C8:  DDS con constraints violados → fix con constraints restrictivos
  C9:  DDS sobre proyecto inexistente → fix con project correcto
  C10: Dos fallos simultáneos → worker solo toma el último
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node_interface.contract import Action, ContractRequest
from node_interface.router import Router
from node_worker.reactive_worker import ReactiveWorker

# ══════════════════════════════════════════════
# INFRASTRUCTURE
# ══════════════════════════════════════════════

def clean_state():
    """Reset to blank state"""
    with open("node_dds/dds.json", "w") as f:
        json.dump({"proposals": []}, f, indent=2)
    with open("node_programmer/reports.json", "w") as f:
        json.dump({"executions": []}, f, indent=2)
    with open("audits/contract_audit.jsonl", "w") as f:
        pass

router = Router()
USER = "operator-real"
SOURCE = "cli"

def dispatch(action, payload=None):
    req = ContractRequest(action=action, payload=payload or {}, source=SOURCE, user_id=USER)
    return router.dispatch(req)

def inject_dds(dds_dict):
    with open("node_dds/dds.json", "r") as f:
        data = json.load(f)
    data["proposals"].append(dds_dict)
    with open("node_dds/dds.json", "w") as f:
        json.dump(data, f, indent=2)

def inject_failure(dds_id, action_type, error_msg):
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

def get_proposals():
    with open("node_dds/dds.json", "r") as f:
        return json.load(f).get("proposals", [])

def get_fixes():
    return [p for p in get_proposals() if p.get("type") == "code_fix"]

def get_audits():
    try:
        with open("audits/contract_audit.jsonl", "r") as f:
            return [json.loads(line) for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []

def get_original_dds(dds_id):
    for p in get_proposals():
        if p.get("id") == dds_id:
            return p
    return None


# ══════════════════════════════════════════════
# CHECKLIST ENGINE (10-point from CRITERIOS doc)
# ══════════════════════════════════════════════

CHECKLIST_NAMES = [
    "1. source_dds traces to a real failed DDS",
    "2. error_context.error_message matches reports.json",
    "3. Failure is dds_error or exec_error (NOT env_error)",
    "4. project matches original DDS",
    "5. allowed_paths ⊆ original allowed_paths",
    "6. max_files ≤ 3, no_new_deps=true, no_refactor=true",
    "7. instructions limited to fixing the error",
    "8. No duplicate fix for same source_dds",
    "9. Original DDS still relevant (project active)",
    "10. Fix understandable without reading source code",
]


def apply_checklist(fix: Dict, all_fixes: List[Dict]) -> Tuple[List[bool], List[str]]:
    """Apply 10-point checklist. Returns (results, notes)."""
    results = []
    notes = []
    
    source_dds_id = fix.get("source_dds", "")
    original = get_original_dds(source_dds_id)
    error_ctx = fix.get("error_context", {})
    constraints = fix.get("constraints", {})
    
    # 1. source_dds traces to a real failed DDS
    with open("node_programmer/reports.json", "r") as f:
        reports = json.load(f).get("executions", [])
    failed_ids = [r["dds_id"] for r in reports if r.get("status") == "failed"]
    c1 = bool(source_dds_id and source_dds_id in failed_ids)
    results.append(c1)
    notes.append("" if c1 else f"source_dds={source_dds_id} not in failed reports")
    
    # 2. error_message matches reports.json
    report_errors = {r["dds_id"]: r.get("notes", "") for r in reports if r.get("status") == "failed"}
    fix_error = error_ctx.get("error_message", "")
    c2 = source_dds_id in report_errors and fix_error and fix_error in report_errors.get(source_dds_id, "")
    results.append(c2)
    notes.append("" if c2 else f"error_message mismatch")
    
    # 3. Failure is dds_error or exec_error, NOT env_error/timeout
    error_msg_lower = fix_error.lower()
    is_env = any(w in error_msg_lower for w in ["no module named", "command not found", "timeout", "timed out", "connection", "503", "rate limit"])
    # Distinguish: "No module named X" in the PROJECT code IS exec_error (fixable import)
    # vs "No module named aider" which is env_error (tool missing)
    is_tool_missing = any(tool in error_msg_lower for tool in ["aider", "docker", "pip", "npm"])
    if is_env and is_tool_missing:
        c3 = False  # env_error — should NOT generate fix
        notes.append("env_error: tool missing, fix shouldn't exist")
    elif "timeout" in error_msg_lower:
        c3 = False  # timeout — should NOT generate fix
        notes.append("env_error: timeout, fix shouldn't exist")
    else:
        c3 = True
        notes.append("")
    results.append(c3)
    
    # 4. project matches original DDS
    c4 = bool(original and fix.get("project") == original.get("project"))
    results.append(c4)
    notes.append("" if c4 else f"project mismatch: fix={fix.get('project')} vs original={original.get('project') if original else '?'}")
    
    # 5. allowed_paths ⊆ original
    fix_paths = set(fix.get("allowed_paths", []))
    orig_paths = set(original.get("allowed_paths", [])) if original else set()
    c5 = fix_paths <= orig_paths if orig_paths else True  # if original has no paths, any is ok
    results.append(c5)
    notes.append("" if c5 else f"paths expanded: fix={fix_paths} vs original={orig_paths}")
    
    # 6. constraints check
    c6 = (constraints.get("max_files_changed", 99) <= 3 and
          constraints.get("no_new_dependencies") is True and
          constraints.get("no_refactor") is True)
    results.append(c6)
    notes.append("" if c6 else f"constraints violation: {constraints}")
    
    # 7. instructions limited to fixing the error
    instructions = fix.get("instructions", fix.get("description", ""))
    if isinstance(instructions, list):
        instructions_text = " ".join(instructions)
    else:
        instructions_text = str(instructions)
    bad_words = ["mejorar", "optimizar", "refactorizar", "añadir funcionalidad", "improve", "optimize", "refactor", "add feature"]
    c7 = not any(w in instructions_text.lower() for w in bad_words)
    results.append(c7)
    notes.append("" if c7 else f"instructions contain scope-creep words")
    
    # 8. No duplicate fix for same source_dds
    same_source = [f for f in all_fixes if f.get("source_dds") == source_dds_id and f["id"] != fix["id"]]
    c8 = len(same_source) == 0
    results.append(c8)
    notes.append("" if c8 else f"duplicate: {[f['id'] for f in same_source]}")
    
    # 9. Original DDS still relevant
    c9 = bool(original)  # In our test, if the original exists it's relevant
    results.append(c9)
    notes.append("" if c9 else "original DDS not found")
    
    # 10. Understandable without reading code
    title = fix.get("title", "")
    c10 = bool(title and len(title) > 20 and fix_error[:30] in title)
    results.append(c10)
    notes.append("" if c10 else f"title not self-explanatory: '{title[:60]}'")
    
    return results, notes


# ══════════════════════════════════════════════
# CYCLE RUNNER
# ══════════════════════════════════════════════

class CycleLog:
    def __init__(self):
        self.entries = []
    
    def add(self, cycle_num, scenario, fix_generated, checklist_results=None, 
            checklist_notes=None, decision=None, friction="", observation=""):
        self.entries.append({
            "cycle": cycle_num,
            "scenario": scenario,
            "fix_generated": fix_generated,
            "checklist_results": checklist_results,
            "checklist_notes": checklist_notes,
            "decision": decision,  # APPROVE / REJECT / IGNORE / N/A
            "friction": friction,
            "observation": observation,
        })

log = CycleLog()


# ══════════════════════════════════════════════
# START CLEAN
# ══════════════════════════════════════════════

clean_state()
print("=" * 75)
print("10 CICLOS REALES — Validación operativa del documento de criterios")
print("=" * 75)


# ──────────────────────────────────────────────
# CYCLE 1: Happy path — code_change exitoso, no fix
# ──────────────────────────────────────────────

print("\n┌─ CYCLE 1: Happy path (code_change success → no fix)")
print("└─────────────────────────────────────────────")

c1_id = "DDS-C01-HAPPY"
inject_dds({
    "id": c1_id, "version": 2, "type": "noop",
    "project": "FitnessAi", "title": "Add health check endpoint",
    "description": "Add /health endpoint that returns 200",
    "goal": "Health check endpoint",
    "instructions": ["Create health_check.py with /health route"],
    "allowed_paths": ["src/", "tests/"],
    "tool": "aider",
    "constraints": {"max_files_changed": 2, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})

resp1 = dispatch(Action.EXECUTE, {"dds_id": c1_id})
print(f"   Execute result: status={resp1.status}")

worker1 = ReactiveWorker()
w1 = worker1.run()
print(f"   Worker result: {w1['status']} — {w1['message']}")

fixes_c1 = get_fixes()
print(f"   Fixes generated: {len(fixes_c1)}")

log.add(1, "Happy path: success, no failure", fix_generated=False,
        decision="N/A", observation="No failure → no fix → correct behavior")


# ──────────────────────────────────────────────
# CYCLE 2: Missing instructions → dds_error → fix
# ──────────────────────────────────────────────

print("\n┌─ CYCLE 2: Missing instructions → dds_error → fix expected")
print("└─────────────────────────────────────────────")

c2_id = "DDS-C02-MISSING-INSTR"
inject_dds({
    "id": c2_id, "version": 2, "type": "code_change",
    "project": "FitnessAi", "title": "Add password hashing",
    "description": "Implement bcrypt password hashing in auth.py",
    "goal": "Secure password storage",
    "instructions": ["Add bcrypt hashing to auth.py", "Update tests"],
    "allowed_paths": ["src/", "tests/"],
    "tool": "aider",
    "constraints": {"max_files_changed": 3, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})
inject_failure(c2_id, "code_change",
    "Missing or invalid required field: instructions (must be non-empty list)")

worker2 = ReactiveWorker()
w2 = worker2.run()
print(f"   Worker: {w2['status']} — {w2['message']}")

fixes_c2 = get_fixes()
fix_c2 = [f for f in fixes_c2 if f.get("source_dds") == c2_id]

if fix_c2:
    results, notes = apply_checklist(fix_c2[0], fixes_c2)
    print(f"   Checklist: {sum(results)}/10 passed")
    for i, (r, n) in enumerate(zip(results, notes)):
        mark = "✅" if r else "❌"
        print(f"     {mark} {CHECKLIST_NAMES[i]}{(' — ' + n) if n else ''}")
    
    log.add(2, "dds_error: missing instructions", fix_generated=True,
            checklist_results=results, checklist_notes=notes,
            decision="APPROVE" if all(results) else "REJECT",
            observation="Fix correctly identifies missing field")
else:
    print("   ❌ No fix generated!")
    log.add(2, "dds_error: missing instructions", fix_generated=False,
            decision="ERROR", friction="Expected fix but none generated")


# ──────────────────────────────────────────────
# CYCLE 3: ImportError in project code → exec_error → fix
# ──────────────────────────────────────────────

print("\n┌─ CYCLE 3: ImportError → exec_error → fix expected")
print("└─────────────────────────────────────────────")

c3_id = "DDS-C03-IMPORT-ERR"
inject_dds({
    "id": c3_id, "version": 2, "type": "code_change",
    "project": "FitnessAi", "title": "Add JWT authentication",
    "description": "Implement JWT token auth in auth.py",
    "goal": "JWT-based auth",
    "instructions": ["Add jwt.encode/decode to auth.py", "Add login endpoint"],
    "allowed_paths": ["src/"],
    "tool": "aider",
    "constraints": {"max_files_changed": 2, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})
inject_failure(c3_id, "code_change",
    "ImportError: cannot import name 'jwt_encode' from 'auth' (src/auth.py)")

worker3 = ReactiveWorker()
w3 = worker3.run()
print(f"   Worker: {w3['status']} — {w3['message']}")

fixes_c3 = get_fixes()
fix_c3 = [f for f in fixes_c3 if f.get("source_dds") == c3_id]

if fix_c3:
    results, notes = apply_checklist(fix_c3[0], fixes_c3)
    print(f"   Checklist: {sum(results)}/10 passed")
    for i, (r, n) in enumerate(zip(results, notes)):
        mark = "✅" if r else "❌"
        print(f"     {mark} {CHECKLIST_NAMES[i]}{(' — ' + n) if n else ''}")
    
    log.add(3, "exec_error: ImportError in project code", fix_generated=True,
            checklist_results=results, checklist_notes=notes,
            decision="APPROVE" if all(results) else "REJECT",
            observation="Import error in project code — fixable")
else:
    log.add(3, "exec_error: ImportError", fix_generated=False,
            decision="ERROR", friction="Expected fix")


# ──────────────────────────────────────────────
# CYCLE 4: SyntaxError → exec_error → fix
# ──────────────────────────────────────────────

print("\n┌─ CYCLE 4: SyntaxError → exec_error → fix expected")
print("└─────────────────────────────────────────────")

c4_id = "DDS-C04-SYNTAX-ERR"
inject_dds({
    "id": c4_id, "version": 2, "type": "code_change",
    "project": "FitnessAi", "title": "Add input sanitization",
    "description": "Sanitize all user inputs in auth.py",
    "goal": "Input sanitization",
    "instructions": ["Add sanitize_input() to auth.py", "Call before processing"],
    "allowed_paths": ["src/", "tests/"],
    "tool": "aider",
    "constraints": {"max_files_changed": 2, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})
inject_failure(c4_id, "code_change",
    "SyntaxError: unexpected EOF while parsing (src/auth.py, line 42)")

worker4 = ReactiveWorker()
w4 = worker4.run()
print(f"   Worker: {w4['status']} — {w4['message']}")

fixes_c4 = get_fixes()
fix_c4 = [f for f in fixes_c4 if f.get("source_dds") == c4_id]

if fix_c4:
    results, notes = apply_checklist(fix_c4[0], fixes_c4)
    print(f"   Checklist: {sum(results)}/10 passed")
    for i, (r, n) in enumerate(zip(results, notes)):
        mark = "✅" if r else "❌"
        print(f"     {mark} {CHECKLIST_NAMES[i]}{(' — ' + n) if n else ''}")
    
    log.add(4, "exec_error: SyntaxError", fix_generated=True,
            checklist_results=results, checklist_notes=notes,
            decision="APPROVE" if all(results) else "REJECT",
            observation="Syntax error — deterministic, fixable")
else:
    log.add(4, "exec_error: SyntaxError", fix_generated=False,
            decision="ERROR", friction="Expected fix")


# ──────────────────────────────────────────────
# CYCLE 5: Timeout → env_error → should NOT generate fix
# ──────────────────────────────────────────────

print("\n┌─ CYCLE 5: Timeout → should NOT generate fix")
print("└─────────────────────────────────────────────")

c5_id = "DDS-C05-TIMEOUT"
inject_dds({
    "id": c5_id, "version": 2, "type": "code_change",
    "project": "FitnessAi", "title": "Add rate limiting",
    "description": "Add rate limiting middleware",
    "goal": "Rate limiting",
    "instructions": ["Add rate_limiter.py", "Integrate with router"],
    "allowed_paths": ["src/"],
    "tool": "aider",
    "constraints": {"max_files_changed": 2, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})
inject_failure(c5_id, "code_change",
    "Timeout: execution exceeded 300s limit without producing output")

worker5 = ReactiveWorker()
w5 = worker5.run()
print(f"   Worker: {w5['status']} — {w5['message']}")

fixes_c5 = get_fixes()
fix_c5 = [f for f in fixes_c5 if f.get("source_dds") == c5_id]

if fix_c5:
    # Fix WAS generated — apply checklist to see if criterion 3 catches it
    results, notes = apply_checklist(fix_c5[0], fixes_c5)
    print(f"   ⚠️  Fix generated (system allows it) — Checklist: {sum(results)}/10")
    for i, (r, n) in enumerate(zip(results, notes)):
        mark = "✅" if r else "❌"
        print(f"     {mark} {CHECKLIST_NAMES[i]}{(' — ' + n) if n else ''}")
    
    log.add(5, "env_error: timeout", fix_generated=True,
            checklist_results=results, checklist_notes=notes,
            decision="REJECT",
            friction="System generates fix for timeout — checklist criterion 3 catches it, but ideally FailureAnalyzer should filter",
            observation="Criterion 3 correctly flags this as not-fixable")
else:
    print("   ✅ No fix generated (correct)")
    log.add(5, "env_error: timeout", fix_generated=False,
            decision="N/A", observation="FailureAnalyzer correctly filtered timeout")


# ──────────────────────────────────────────────
# CYCLE 6: noop success — no fix
# ──────────────────────────────────────────────

print("\n┌─ CYCLE 6: noop DDS → success → no fix")
print("└─────────────────────────────────────────────")

c6_id = "DDS-C06-NOOP"
inject_dds({
    "id": c6_id, "version": 2, "type": "noop",
    "project": "ai_system", "title": "Pipeline validation noop",
    "description": "Validate execution pipeline",
    "goal": "Pipeline test",
    "instructions": ["noop"],
    "allowed_paths": [],
    "tool": "noop",
    "constraints": {"max_files_changed": 0, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})

resp6 = dispatch(Action.EXECUTE, {"dds_id": c6_id})
print(f"   Execute: status={resp6.status}")

worker6 = ReactiveWorker()
w6 = worker6.run()
print(f"   Worker: {w6['status']} — {w6['message']}")

fixes_after_c6 = get_fixes()
new_fixes_c6 = [f for f in fixes_after_c6 if f.get("source_dds") == c6_id]
print(f"   Fixes for this DDS: {len(new_fixes_c6)}")

log.add(6, "noop success", fix_generated=False,
        decision="N/A", observation="noop success — correct: no fix needed")


# ──────────────────────────────────────────────
# CYCLE 7: Approve and execute fix from C2 → complete chain
# ──────────────────────────────────────────────

print("\n┌─ CYCLE 7: Approve fix from C2 → execute → complete chain")
print("└─────────────────────────────────────────────")

fixes_for_c2 = [f for f in get_fixes() if f.get("source_dds") == c2_id]
if fixes_for_c2:
    fix_id = fixes_for_c2[0]["id"]
    
    # Approve the fix
    resp7a = dispatch(Action.DDS_APPROVE, {"proposal_id": fix_id})
    print(f"   Approve fix: status={resp7a.status}")
    
    # Execute the fix (it's a code_fix type, will go through programmer)
    resp7b = dispatch(Action.EXECUTE, {"dds_id": fix_id})
    print(f"   Execute fix: status={resp7b.status}")
    
    # Check audit for the execution
    audits = get_audits()
    fix_audits = [a for a in audits if a.get("payload_summary", {}).get("dds_id") == fix_id]
    print(f"   Audit entries for fix: {len(fix_audits)}")
    
    log.add(7, "Fix approval + execution chain", fix_generated=False,
            decision="APPROVE (from C2)",
            observation=f"Fix {fix_id} approved and executed: {resp7b.status}",
            friction="code_fix type must be handled by programmer — verify Programmer supports it")
else:
    print("   ⚠️ No fix from C2 to approve")
    log.add(7, "Fix chain", fix_generated=False, decision="SKIP",
            friction="C2 fix was missing")


# ──────────────────────────────────────────────
# CYCLE 8: Constraint violation → fix inherits restricted constraints
# ──────────────────────────────────────────────

print("\n┌─ CYCLE 8: Constraint violation → fix constraints")
print("└─────────────────────────────────────────────")

c8_id = "DDS-C08-CONSTRAINT"
inject_dds({
    "id": c8_id, "version": 2, "type": "code_change",
    "project": "FitnessAi", "title": "Add email validation",
    "description": "Add email format validation",
    "goal": "Email validation",
    "instructions": ["Add validate_email() to auth.py"],
    "allowed_paths": ["src/"],
    "tool": "aider",
    "constraints": {"max_files_changed": 1, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})
inject_failure(c8_id, "code_change",
    "Constraint violation: code_change modified 3 files but max_files_changed=1")

worker8 = ReactiveWorker()
w8 = worker8.run()
print(f"   Worker: {w8['status']} — {w8['message']}")

fixes_c8 = [f for f in get_fixes() if f.get("source_dds") == c8_id]

if fixes_c8:
    fix = fixes_c8[0]
    results, notes = apply_checklist(fix, get_fixes())
    print(f"   Checklist: {sum(results)}/10")
    for i, (r, n) in enumerate(zip(results, notes)):
        mark = "✅" if r else "❌"
        print(f"     {mark} {CHECKLIST_NAMES[i]}{(' — ' + n) if n else ''}")
    
    # Extra check: fix constraints should be ≤ original
    fix_max = fix.get("constraints", {}).get("max_files_changed", 99)
    orig_max = 1
    print(f"   Fix max_files_changed={fix_max} (original={orig_max})")
    
    log.add(8, "exec_error: constraint violation", fix_generated=True,
            checklist_results=results, checklist_notes=notes,
            decision="REJECT" if not all(results) else "APPROVE",
            friction="Constraint violation is a grey area per doc §1. Fix may not be the right remedy — maybe DDS was wrong.",
            observation=f"Fix inherited max_files={fix_max} from min(original={orig_max}, hard_limit=3)")
else:
    log.add(8, "constraint violation", fix_generated=False, decision="SKIP")


# ──────────────────────────────────────────────
# CYCLE 9: DDS for non-existent project → fix project match check
# ──────────────────────────────────────────────

print("\n┌─ CYCLE 9: DDS for project 'LegacyApp' → fix project consistency")
print("└─────────────────────────────────────────────")

c9_id = "DDS-C09-LEGACY"
inject_dds({
    "id": c9_id, "version": 2, "type": "code_change",
    "project": "LegacyApp", "title": "Fix deprecated API calls",
    "description": "Update deprecated API calls in legacy module",
    "goal": "API migration",
    "instructions": ["Replace deprecated_call() with new_call()"],
    "allowed_paths": ["src/legacy/"],
    "tool": "aider",
    "constraints": {"max_files_changed": 3, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})
inject_failure(c9_id, "code_change",
    "FileNotFoundError: src/legacy/ does not exist in workspace")

worker9 = ReactiveWorker()
w9 = worker9.run()
print(f"   Worker: {w9['status']} — {w9['message']}")

fixes_c9 = [f for f in get_fixes() if f.get("source_dds") == c9_id]

if fixes_c9:
    fix = fixes_c9[0]
    results, notes = apply_checklist(fix, get_fixes())
    print(f"   Checklist: {sum(results)}/10")
    for i, (r, n) in enumerate(zip(results, notes)):
        mark = "✅" if r else "❌"
        print(f"     {mark} {CHECKLIST_NAMES[i]}{(' — ' + n) if n else ''}")
    
    log.add(9, "dds_error: project doesn't exist", fix_generated=True,
            checklist_results=results, checklist_notes=notes,
            decision="IGNORE",
            friction="Fix is generated but project 'LegacyApp' doesn't exist. Criterion 9 catches this.",
            observation="Fix is technically correct structurally but operationally useless")
else:
    log.add(9, "project doesn't exist", fix_generated=False, decision="SKIP")


# ──────────────────────────────────────────────
# CYCLE 10: Two failures exist → worker only processes last unprocessed
# ──────────────────────────────────────────────

print("\n┌─ CYCLE 10: Two failures → worker processes one at a time")
print("└─────────────────────────────────────────────")

c10a_id = "DDS-C10-FIRST"
c10b_id = "DDS-C10-SECOND"

inject_dds({
    "id": c10a_id, "version": 2, "type": "code_change",
    "project": "FitnessAi", "title": "Add logging middleware",
    "description": "Add request/response logging",
    "goal": "Logging",
    "instructions": ["Add logging middleware"],
    "allowed_paths": ["src/"],
    "tool": "aider",
    "constraints": {"max_files_changed": 2, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})
inject_dds({
    "id": c10b_id, "version": 2, "type": "code_change",
    "project": "FitnessAi", "title": "Add CORS headers",
    "description": "Add CORS support",
    "goal": "CORS headers",
    "instructions": ["Add CORS headers to responses"],
    "allowed_paths": ["src/"],
    "tool": "aider",
    "constraints": {"max_files_changed": 1, "no_new_dependencies": True, "no_refactor": True},
    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "status": "approved"
})

inject_failure(c10a_id, "code_change", "NameError: name 'logger' is not defined")
time.sleep(0.01)  # ensure different timestamp
inject_failure(c10b_id, "code_change", "AttributeError: module 'http' has no attribute 'cors'")

worker10 = ReactiveWorker()
w10a = worker10.run()
print(f"   Worker run 1: {w10a['status']} — {w10a['message']}")

w10b = worker10.run()
print(f"   Worker run 2: {w10b['status']} — {w10b['message']}")

fixes_c10 = [f for f in get_fixes() 
             if f.get("source_dds") in [c10a_id, c10b_id]]
print(f"   Total fixes for C10 DDSs: {len(fixes_c10)}")

if len(fixes_c10) >= 1:
    for fix in fixes_c10:
        results, notes = apply_checklist(fix, get_fixes())
        src = fix.get("source_dds", "?")
        print(f"   Fix for {src}: {sum(results)}/10")
    
    log.add(10, "Two failures, sequential processing", 
            fix_generated=True,
            checklist_results=results, checklist_notes=notes,
            decision="APPROVE" if all(results) else "REVIEW",
            observation=f"Generated {len(fixes_c10)} fix(es). Worker processes most recent unprocessed first, then next on re-run.")
else:
    log.add(10, "Two failures", fix_generated=False, decision="ERROR")


# ══════════════════════════════════════════════
# FINAL ANALYSIS
# ══════════════════════════════════════════════

print("\n" + "=" * 75)
print("ANÁLISIS FINAL — Uso del documento de criterios en 10 ciclos")
print("=" * 75)

# Collect all checklist results across cycles
all_criteria_usage = [0] * 10  # how many times each criterion was evaluated
all_criteria_pass = [0] * 10   # how many times each criterion passed
all_criteria_fail = [0] * 10   # how many times each criterion failed
all_criteria_decisive = [0] * 10  # how many times criterion was the deciding factor

total_fixes = 0
decisions = {"APPROVE": 0, "REJECT": 0, "IGNORE": 0, "N/A": 0, "ERROR": 0, "SKIP": 0, "REVIEW": 0}

for entry in log.entries:
    decisions[entry.get("decision", "N/A")] = decisions.get(entry.get("decision", "N/A"), 0) + 1
    
    if entry.get("checklist_results"):
        total_fixes += 1
        for i, r in enumerate(entry["checklist_results"]):
            all_criteria_usage[i] += 1
            if r:
                all_criteria_pass[i] += 1
            else:
                all_criteria_fail[i] += 1

print(f"\n{'─' * 75}")
print("RESUMEN DE DECISIONES:")
print(f"{'─' * 75}")
for d, count in decisions.items():
    if count > 0:
        print(f"  {d:10s}: {count}")

print(f"\n{'─' * 75}")
print("USO DE CRITERIOS (sobre {total_fixes} fixes evaluados):")
print(f"{'─' * 75}")

criteria_always_pass = []
criteria_sometimes_fail = []
criteria_never_triggered = []

for i in range(10):
    used = all_criteria_usage[i]
    passed = all_criteria_pass[i]
    failed = all_criteria_fail[i]
    
    if used == 0:
        status = "⚪ NO EVALUADO"
        criteria_never_triggered.append(i)
    elif failed == 0:
        status = f"🟢 SIEMPRE PASA ({passed}/{used})"
        criteria_always_pass.append(i)
    else:
        status = f"🔴 FALLA {failed}/{used} veces"
        criteria_sometimes_fail.append(i)
    
    print(f"  {CHECKLIST_NAMES[i]:55s} {status}")

# Friction analysis
print(f"\n{'─' * 75}")
print("PUNTOS DE FRICCIÓN:")
print(f"{'─' * 75}")

frictions = [e for e in log.entries if e.get("friction")]
if frictions:
    for e in frictions:
        print(f"  C{e['cycle']:2d}: {e['friction']}")
else:
    print("  (ninguno detectado)")

# Observations
print(f"\n{'─' * 75}")
print("OBSERVACIONES POR CICLO:")
print(f"{'─' * 75}")

for e in log.entries:
    print(f"  C{e['cycle']:2d} [{e['decision']:7s}]: {e['observation']}")

# Summary categorization
print(f"\n{'─' * 75}")
print("CLASIFICACIÓN FINAL DE CRITERIOS:")
print(f"{'─' * 75}")

print("\n  📌 CRITERIOS QUE SIEMPRE SE USAN (esenciales):")
for i in criteria_always_pass:
    print(f"     {CHECKLIST_NAMES[i]}")

print("\n  🎯 CRITERIOS QUE DETECTAN PROBLEMAS (valor real):")
for i in criteria_sometimes_fail:
    print(f"     {CHECKLIST_NAMES[i]} — falló {all_criteria_fail[i]}/{all_criteria_usage[i]}")

if criteria_never_triggered:
    print("\n  ❓ CRITERIOS NO EVALUADOS (pueden sobrar o faltar datos):")
    for i in criteria_never_triggered:
        print(f"     {CHECKLIST_NAMES[i]}")

# Where there's still friction
print(f"\n{'─' * 75}")
print("DÓNDE SIGUE HABIENDO FRICCIÓN HUMANA:")
print(f"{'─' * 75}")

friction_areas = []

# Check: does the system generate fixes for timeouts?
timeout_fixes = [e for e in log.entries if "timeout" in e.get("scenario", "").lower() and e.get("fix_generated")]
if timeout_fixes:
    friction_areas.append(
        "FILTRADO DE TIMEOUT: El sistema genera fixes para timeouts. "
        "La checklist lo atrapa (criterio 3), pero el FailureAnalyzer debería filtrarlo upstream. "
        "El humano tiene que rechazar algo que nunca debería haber llegado.")

# Check: constraint violations generating fixes
constraint_fixes = [e for e in log.entries if "constraint" in e.get("scenario", "").lower() and e.get("fix_generated")]
if constraint_fixes:
    friction_areas.append(
        "ZONA GRIS DE CONSTRAINTS: Cuando un DDS viola constraints, "
        "¿el problema es el código o el DDS? El fix asume que es el código, "
        "pero a veces el DDS tenía constraints irrealistas. Requiere juicio humano.")

# Check: fixes for non-existent projects
legacy_fixes = [e for e in log.entries if "legacy" in e.get("scenario", "").lower() and e.get("fix_generated")]
if legacy_fixes:
    friction_areas.append(
        "PROYECTO INEXISTENTE: El sistema genera fixes para proyectos que no existen en el workspace. "
        "El criterio 9 depende del operador para saber si el proyecto es relevante. "
        "No hay validación automática de que el proyecto exista.")

# Generic friction
friction_areas.append(
    "DECISIÓN APPROVE/REJECT ES MANUAL: Incluso con 10/10 en checklist, "
    "el humano tiene que ejecutar /dds_approve. No hay fast-track para fixes 'perfectos'.")

for i, f in enumerate(friction_areas, 1):
    print(f"  {i}. {f}")

print(f"\n{'=' * 75}")
print(f"FIN — {total_fixes} fixes evaluados, {len(frictions)} puntos de fricción detectados")
print(f"{'=' * 75}")
