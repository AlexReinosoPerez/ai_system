# Changelog

All notable changes to AI System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-02

### Added

#### Core System
- **Decision-Driven System (DDS v2)**: Structured proposals for code changes
  - DDS v2 schema with version, type, project, goal, instructions, allowed_paths, tool, constraints, status
  - DDS states: proposed → approved/rejected → executed/failed
  - Persistence in `node_dds/dds.json`
  - Full validation and constraint checking

#### ToDo Management
- **node_todo/TodoRegistry**: Human intent tracking
  - CRUD operations for tasks
  - States: open, converted, closed
  - Persistence in `node_todo/todo.json`
  - Priority levels: low, medium, high

- **node_todo/TodoToDDSConverter**: ToDo → DDS proposal translation
  - Deterministic conversion (no AI)
  - Conservative defaults for constraints
  - Generated DDS always have `status="proposed"`
  - Source tracking with `source_todo` field

#### Telegram Interface
- **Commands**:
  - `/todo_list`: List all ToDos
  - `/todo_to_dds <TODO-ID>`: Generate DDS proposal from ToDo
  - `/dds_list_proposed`: List proposed DDS awaiting review
  - `/dds_approve <DDS-ID>`: Approve DDS for execution
  - `/dds_reject <DDS-ID>`: Reject DDS
  - `/execute <DDS-ID>`: Execute approved DDS
  - `/exec_status`: Check last execution status

#### Programmer v2.1
- **8-phase execution pipeline**:
  1. Structure and isolation
  2. DDS v2 validation
  3. Ephemeral workspace creation
  4. Scoped workspace (allowed_paths only)
  5. Controlled prompt construction
  6. External tool invocation (Aider)
  7. Post-execution analysis (snapshot, changes, constraints)
  8. Persistence and closure (reports.json, dds.json)

- **Security features**:
  - Isolated workspaces per execution
  - Path traversal prevention
  - No automatic commits (--no-auto-commit flag)
  - Constraint validation (max_files, no_new_dependencies, no_refactor)
  - MD5 snapshot before/after
  - Change detection

- **Aider integration**: Real code changes via subprocess

#### Scheduler
- **node_scheduler/Scheduler**: Automated execution of approved DDS
  - Sequential processing (one DDS at a time)
  - Stop-on-failure semantics
  - State transitions: approved → executed/failed
  - Suitable for cron jobs

#### Documentation
- **Framework reorganization**: Moved development framework to `docs/framework/`
  - `docs/framework/contract_system/`: Development methodology
  - `docs/framework/philosophy.md`: Design principles
  - README.md now focuses 100% on runtime components

- **Comprehensive documentation**:
  - README.md: System overview and usage
  - WHAT_IS_AI_SYSTEM.md: What it is and what it isn't
  - ARCHITECTURE.md: System diagrams and flows
  - node_programmer/README.md: Programmer pipeline details
  - node_dds/README.md: DDS specification
  - node_todo/README.md: ToDo system documentation
  - node_scheduler/README.md: Scheduler usage

### Guarantees

✅ **No execution without human approval**: All DDS must be explicitly approved  
✅ **No automatic commits**: Code changes never auto-commit  
✅ **Isolated workspaces**: Each execution in separate workspace copy  
✅ **Sequential execution**: No parallel execution of DDS  
✅ **Stop-on-failure**: Scheduler stops on first error  
✅ **Full traceability**: Complete audit trail in reports.json  
✅ **Path validation**: No path traversal attacks  
✅ **Constraint enforcement**: Configurable limits enforced  

### Known Limitations

⚠️ **No rollback**: Failed executions require manual cleanup  
⚠️ **No parallel execution**: One DDS at a time only  
⚠️ **No autonomous planning**: AI doesn't decide what to build  
⚠️ **Heuristic constraints**: Validation based on heuristics, not AST  
⚠️ **No containerization**: Executes in same environment (not sandboxed)  
⚠️ **No rate limiting**: No limits on concurrent executions (v1.0)  

### Technical Stack

- **Language**: Python 3.10+
- **Dependencies**: Standard library only for core components
- **External tools**: Aider (optional, for real code execution)
- **Interfaces**: Telegram Bot API
- **Storage**: JSON files (todos.json, dds.json, reports.json)

---

## [2.2.0] - 2026-02-02 (Pre-release)

### Added - ToDo System

#### node_todo/ Component
- **TodoManager**: CRUD de tareas de alto nivel
  - `create_todo()`: Crear tareas con título, descripción, archivos, constraints
  - `get_todo()`: Obtener tarea por ID
  - `list_todos()`: Listar tareas (filtro opcional por estado)
  - `update_todo_status()`: Actualizar estado con validación FSM
  - `link_dds()`: Vincular DDS a tarea
  - Estados: pending, draft_generated, approved, completed, failed, cancelled
  - Persistencia en `todos.json`

- **DDSGenerator**: Traducción determinista ToDo → DDS v2
  - `generate_dds_from_todo()`: Generar DDS draft desde tarea
  - Traducción campo a campo (sin IA, sin heurísticas)
  - DDS generados siempre con `status='draft'` (nunca auto-aprobados)
  - Persistencia en `node_dds/dds.json`
  - Actualización automática de estado de tarea

#### Features
- **Máquina de estados finita (FSM)**: Validación de transiciones de estado
- **Validación de paths**: Prevención de path traversal en affected_files
- **Constraints obligatorios**: `max_files_changed` requerido
- **Trazabilidad completa**: Vinculación ToDo ↔ DDS
- **Formato IDs**: `TODO-YYYYMMDD-XXX` y `DDS-YYYYMMDD-CODE-XXX`

#### Documentation
- **node_todo/README.md**: Documentación completa del componente
  - API pública con ejemplos
  - FSM con estados y transiciones
  - Flujo completo ToDo → DDS → Ejecución
  - Limitaciones explícitas (v1.0)
  - Roadmap (v2.0, v3.0)

### Changed
- **README.md**: Agregado `node_todo/` a Runtime Components
- **CHANGELOG.md**: Agregada sección v2.2.0
- **Documentación Adicional**: Agregado link a node_todo/README.md

### Guarantees
✅ No auto-aprobación de DDS  
✅ No ejecución directa sin aprobación humana  
✅ Validación de paths (no path traversal)  
✅ Estado completo persistido (auditoría)  
✅ Sin dependencias externas nuevas  

### Limitations (v1.0)
❌ Traducción manual (no masiva)  
❌ Actualización manual de estado tras ejecución  
❌ Sin CLI (solo API Python)  
❌ Sin interface web  
❌ Sin templates predefinidos  
❌ Sin dependencias entre tareas  

---

## [2.1.0] - 2026-02-02

### Added - Programmer v2.1

#### Real Aider Integration
- **aider_runner.py**: Real subprocess execution of Aider
  - Command: `aider --no-auto-commit --yes --message "<prompt>" <paths...>`
  - Execution in scoped workspace (`_scoped/`)
  - Capture stdout, stderr, returncode
  - Timeout: 300 seconds (5 minutes)
  - Error handling: TimeoutExpired, FileNotFoundError, generic Exception

#### Return Structure
```python
{
    "returncode": int,    # 0 = success
    "stdout": str,        # command output
    "stderr": str,        # error output
    "success": bool       # returncode == 0
}
```

### Changed
- No longer raises `NotImplementedError` in aider_runner
- Graceful error handling when Aider not installed
- Ready for real code execution when `aider-chat` installed

### Technical Details
- File modified: `node_programmer/external_tools/aider_runner.py` only
- No changes to `programmer.py` or other files
- No new dependencies added
- All existing tests continue to pass

---

## [2.0.0] - 2026-02-02

### Added - Programmer v2 (8 Phases)

#### PHASE 1: Structure and Isolation
- Created `workspaces/` directory for ephemeral workspaces
- Created `external_tools/` directory structure
- Created `aider_runner.py` placeholder

#### PHASE 2: DDS v2 Validation
- `_validate_dds_v2()` method with 9 required field checks:
  - version = 2
  - type = "code_change"
  - project (non-empty string)
  - goal (non-empty string)
  - instructions (non-empty list)
  - allowed_paths (non-empty list)
  - tool = "aider"
  - constraints (dict)
  - status = "approved"

#### PHASE 3: Ephemeral Workspace Creation
- `execute_code_change()` creates `workspaces/{dds_id}/`
- Full project copy to workspace
- Multiple location search for projects

#### PHASE 4: Scoped Workspace
- `_scoped/` subdirectory with only allowed_paths
- Physical isolation of accessible files
- Path traversal validation
- Security: External tools only see `_scoped/`

#### PHASE 5: Controlled Prompt Construction
- `_build_aider_prompt()` method
- Structured format:
  ```
  GOAL: {goal}
  
  INSTRUCTIONS:
  - {instruction_1}
  - {instruction_2}
  
  CONSTRAINTS:
  - Max files: {max_files}
  - No new dependencies: {true/false}
  - No refactor: {true/false}
  
  RULES:
  - Only modify files in allowed paths
  - Do not commit changes
  - Stop after completing instructions
  ```

#### PHASE 6: Mock Tool Invocation
- `run_aider()` call integrated
- NotImplementedError handling
- Workspace prepared for real execution

#### PHASE 7: Post-Execution Analysis
- `_create_workspace_snapshot()`: MD5 hash snapshot of all files
- `_detect_changes()`: Compare before/after snapshots
  - Returns: (created_files, modified_files, deleted_files)
- `_validate_constraints()`: Check DDS constraints
  - max_files_changed validation
  - no_new_dependencies check (package.json, requirements.txt, etc.)
  - no_refactor heuristic (>3 files = refactoring)
  - Returns: (constraints_ok, violations)

#### PHASE 8: Persistence and Closure
- `_save_execution_report()`: Append-only persistence to reports.json
- `_mark_dds_executed()`: Update DDS with last_execution field
- `_check_already_executed()`: Prevent re-execution of successful DDSs
- `_build_user_summary()`: Formatted user-facing report
  ```
  ============================================================
  DDS Execution Report: DDS-ID
  ============================================================
  Status: SUCCESS/FAILED
  Executed at: YYYY-MM-DD HH:MM:SS
  
  Changes Detected:
    - Created: N files
    - Modified: M files
    - Deleted: D files
  
  Constraints Validation: ✓ PASSED / ✗ FAILED
  Violations:
    - violation 1
    - violation 2
  
  Notes: execution details
  ============================================================
  ```

### Security Features
- ✅ Workspace isolation per DDS
- ✅ Scoped workspace with allowed_paths only
- ✅ Path traversal prevention
- ✅ No automatic commits (--no-auto-commit flag)
- ✅ Change detection with MD5 hashing
- ✅ Constraint validation
- ✅ Re-execution prevention for successful DDSs

### Data Structures

#### reports.json
```json
{
  "executions": [
    {
      "dds_id": "DDS-20260202-CODE-001",
      "action_type": "code_change",
      "status": "success",
      "executed_at": "2026-02-02 12:51:24",
      "notes": "Execution completed. Files changed: 3 (2 created, 1 modified). Constraints: OK"
    }
  ]
}
```

#### dds.json (last_execution field)
```json
{
  "id": "DDS-20260202-CODE-001",
  "status": "approved",
  "last_execution": {
    "status": "success",
    "executed_at": "2026-02-02 12:51:24",
    "notes": "Execution completed..."
  }
}
```

---

## [1.0.0] - 2026-02-01

### Added - Programmer v1

#### DDS v1 Support
- `touch_file` action: Write files to sandbox
- `noop` action: No-operation for testing
- Basic sandbox with path validation

#### Security
- Path traversal prevention (..)
- Absolute path rejection
- Sandbox boundary validation
- `allowed_paths` enforcement

#### Execution Reports
- ExecutionReport dataclass
- reports.json persistence
- Execution history tracking

#### Features
- `execute_touch_file()`: Write single file
- `execute_noop()`: No-op execution
- `_validate_sandbox_path()`: Path security validation
- `_validate_allowed_paths()`: Scope validation
- `_is_already_executed()`: Duplicate prevention
- `get_last_report()`: Latest report retrieval

---

## [0.1.0] - 2026-01-30

### Added - Initial Structure

#### Core Modules
- `shared/config.py`: Configuration management
- `shared/logger.py`: Unified logging system
- `node_interface/telegram_bot.py`: Telegram bot interface
- `node_interface/router.py`: Command routing

#### Infrastructure
- Project structure
- Requirements management
- Run scripts (run_local.sh)
- Git repository initialization

#### Documentation
- Development framework: `docs/framework/contract_system/`
  - Roles: Architect, Implementer, Reviewer, Verifier
  - Workflow documentation
  - Decision records
  - Glossary

---

## Types of Changes
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security fixes

---

## Upcoming (Roadmap)

### v2.2 (Next)
- [ ] Automatic rollback on constraint violations
- [ ] Parallel DDS execution
- [ ] Advanced metrics (time, lines, complexity)
- [ ] Automatic workspace cleanup
- [ ] DDS templates

### v3.0 (Future)
- [ ] Multi-tool support (Cursor, Claude Code)
- [ ] AST-based constraint validation
- [ ] Containerized sandbox (Docker)
- [ ] Live execution streaming
- [ ] DDS dependencies
- [ ] Multi-project support
- [ ] CI/CD integration
- [ ] Web dashboard

---

## Installation Notes

### Dependencies
- Python 3.10+
- pip
- git
- aider-chat (optional, for v2.1 real execution)

### Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Optional: Install Aider
pip install aider-chat

# Run system
./run_local.sh
```

---

## Migration Guide

### From v1 to v2
- DDS v1 (touch_file) still supported
- New DDS v2 (code_change) for AI-powered changes
- No breaking changes to v1 API

### From v2.0 to v2.1
- No breaking changes
- aider_runner now executes real commands
- Graceful fallback when Aider not installed
- Same API, enhanced functionality

---

## Contributors
- Alex Reinoso Pérez (@AlexReinosoPerez)

## License
MIT - See LICENSE file for details
