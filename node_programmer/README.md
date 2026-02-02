# Node Programmer

Motor de ejecución para propuestas DDS (Decision-Driven System) con workspace aislado y análisis post-ejecución.

## 📋 Índice

- [Visión General](#visión-general)
- [Arquitectura](#arquitectura)
- [Pipeline de Ejecución](#pipeline-de-ejecución)
- [DDS v2 Specification](#dds-v2-specification)
- [Seguridad](#seguridad)
- [API Reference](#api-reference)
- [Ejemplos](#ejemplos)

## 🎯 Visión General

Node Programmer es el motor de ejecución que transforma propuestas DDS en cambios de código reales, manteniendo:

- **Aislamiento**: Workspaces efímeros por DDS
- **Control**: Solo archivos en `allowed_paths` modificables
- **Auditoría**: Historial completo de ejecuciones
- **Validación**: Constraints y análisis post-ejecución
- **Seguridad**: Sin commits, path validation, change detection

## 🏗️ Arquitectura

```
node_programmer/
├── programmer.py              # Motor principal (8-phase pipeline)
├── execution_report.py        # Data structure for reports
├── external_tools/
│   └── aider_runner.py       # Aider integration (v2.1)
├── workspaces/               # Ephemeral workspaces per DDS
│   └── DDS-{id}/
│       ├── {project_files}   # Full project copy
│       └── _scoped/          # Only allowed_paths
├── sandbox/                  # Test area (v1 compatibility)
└── reports.json              # Execution history
```

## 🔄 Pipeline de Ejecución

### PHASE 1: Estructura y Aislamiento
- Crea directorios `workspaces/` y `external_tools/`
- Inicializa estructura del sistema

### PHASE 2: Validación DDS v2
Valida 9 campos requeridos:
- `version` = 2
- `type` = "code_change"
- `project` (string no vacío)
- `goal` (string no vacío)
- `instructions` (lista no vacía)
- `allowed_paths` (lista no vacía)
- `tool` = "aider"
- `constraints` (dict)
- `status` = "approved"

### PHASE 3: Workspace Efímero
- Crea `workspaces/{dds_id}/`
- Copia proyecto completo al workspace
- Busca proyecto en múltiples ubicaciones

### PHASE 4: Scoped Workspace
- Crea `workspaces/{dds_id}/_scoped/`
- Copia **solo** archivos en `allowed_paths`
- Validación de path traversal
- Herramienta externa solo ve `_scoped/`

### PHASE 5: Construcción de Prompt
Genera prompt estructurado:
```
GOAL: {goal}

INSTRUCTIONS:
- {instruction 1}
- {instruction 2}

CONSTRAINTS:
- Max files: {max_files}
- No new dependencies: {true/false}
- No refactor: {true/false}

RULES:
- Only modify files in allowed paths
- Do not commit changes
- Stop after completing instructions
```

### PHASE 6: Invocación de Herramienta
Ejecuta Aider con:
```bash
aider --no-auto-commit --yes --message "{prompt}" {allowed_paths...}
```
- `cwd`: apunta a `_scoped/`
- Sin commits automáticos
- Captura stdout/stderr/returncode

### PHASE 7: Análisis Post-Ejecución

#### Snapshot de Archivos
Crea MD5 hash de todos los archivos antes de la ejecución:
```python
{
  "src/main.py": "5d41402abc4b2a76b9719d911017c592",
  "tests/test_main.py": "7d793037a0760186574b0282f2f435e7"
}
```

#### Detección de Cambios
Compara snapshots y detecta:
- **Creados**: Archivos nuevos
- **Modificados**: Hash diferente
- **Eliminados**: Ya no existen

#### Validación de Constraints
Valida contra reglas del DDS:

1. **max_files_changed**: 
   ```python
   total_changed = len(created) + len(modified)
   if total_changed > max_files:
       violation = True
   ```

2. **no_new_dependencies**:
   ```python
   dependency_files = [
       'package.json', 'requirements.txt', 'Cargo.toml',
       'go.mod', 'pom.xml', 'build.gradle'
   ]
   if any(f in modified for f in dependency_files):
       violation = True
   ```

3. **no_refactor**:
   ```python
   # Heuristic: > 3 files changed suggests refactoring
   if len(created) + len(modified) > 3:
       violation = True
   ```

### PHASE 8: Persistencia y Cierre

#### Persistencia en reports.json (append-only)
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

#### Actualización de dds.json
Añade campo `last_execution` al DDS:
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

#### Prevención de Re-ejecución
- DDSs con `last_execution.status == "success"` no se re-ejecutan
- Prevención mediante estado persistido (no lock transaccional)
- DDSs fallidos pueden re-ejecutarse para corrección

#### Resumen de Usuario
```
============================================================
DDS Execution Report: DDS-20260202-CODE-001
============================================================
Status: SUCCESS
Executed at: 2026-02-02 12:51:24

Changes Detected:
  - Created: 2 files
  - Modified: 1 files
  - Deleted: 0 files

Constraints Validation: ✓ PASSED

Notes: Execution completed. Files changed: 3 (2 created, 1 modified). Constraints: OK
============================================================
```

## 📝 DDS v2 Specification

### Estructura Completa

```json
{
  "id": "DDS-YYYYMMDD-CODE-XXX",
  "version": 2,
  "type": "code_change",
  "project": "ProjectName",
  "goal": "Clear description of what needs to be achieved",
  "instructions": [
    "Step-by-step instruction 1",
    "Step-by-step instruction 2",
    "Step-by-step instruction 3"
  ],
  "allowed_paths": [
    "src/",
    "tests/",
    "docs/api.md"
  ],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 5,
    "no_new_dependencies": true,
    "no_refactor": true
  },
  "status": "approved",
  "created_at": "2026-02-02T12:00:00Z"
}
```

### Campos Requeridos

| Campo | Tipo | Descripción | Validación |
|-------|------|-------------|------------|
| `id` | string | Identificador único | `DDS-YYYYMMDD-CODE-XXX` |
| `version` | int | Versión DDS | Debe ser `2` |
| `type` | string | Tipo de cambio | Debe ser `"code_change"` |
| `project` | string | Nombre del proyecto | No vacío |
| `goal` | string | Objetivo del cambio | No vacío |
| `instructions` | array | Pasos a ejecutar | Lista no vacía |
| `allowed_paths` | array | Paths permitidos | Lista no vacía |
| `tool` | string | Herramienta a usar | Debe ser `"aider"` |
| `constraints` | object | Restricciones | Diccionario |
| `status` | string | Estado del DDS | Debe ser `"approved"` |

### Constraints Disponibles

```python
{
  "max_files_changed": int,      # Máximo de archivos modificables (created + modified)
  "max_files": int,               # Alias de max_files_changed
  "no_new_dependencies": bool,    # Bloquea cambios en package.json, requirements.txt, etc.
  "no_refactor": bool            # Heuristic: bloquea cambios en >3 archivos
}
```

## 🔐 Seguridad

### Aislamiento de Workspace

```python
# Cada DDS tiene su propio workspace
workspaces/
├── DDS-001/
│   ├── src/         # Full project
│   └── _scoped/     # Only allowed_paths
└── DDS-002/
    ├── src/
    └── _scoped/
```

### Path Validation

```python
def _validate_sandbox_path(self, relative_path: str) -> Path:
    # 1. Rechaza paths absolutos
    if os.path.isabs(relative_path):
        raise ProgrammerError("Absolute paths not allowed")
    
    # 2. Rechaza path traversal (..)
    if '..' in relative_path:
        raise ProgrammerError("Path traversal not allowed")
    
    # 3. Verifica que esté dentro del sandbox
    target_abs = (sandbox_abs / relative_path).resolve()
    try:
        target_abs.relative_to(sandbox_abs)
    except ValueError:
        raise ProgrammerError("Path outside sandbox")
```

### Sin Commits

```bash
# Aider ejecutado con --no-auto-commit
aider --no-auto-commit --yes --message "prompt" paths...
```

### Change Detection

```python
# MD5 hash snapshot antes y después
before = {"src/main.py": "abc123..."}
after = {"src/main.py": "def456..."}

if before["src/main.py"] != after["src/main.py"]:
    modified.append("src/main.py")
```

## 🔌 API Reference

### Programmer Class

```python
class Programmer:
    """Executes approved DDS proposals with controlled actions"""
    
    def __init__(self):
        """Initialize programmer"""
        
    def execute_code_change(self, dds_id: str) -> ExecutionReport:
        """
        Execute DDS v2 code_change proposal (PHASE 2-8)
        
        Args:
            dds_id: DDS identifier
            
        Returns:
            ExecutionReport with execution details
            
        Raises:
            ProgrammerError: If execution fails or already executed
        """
```

### ExecutionReport

```python
@dataclass
class ExecutionReport:
    """Represents a DDS execution report"""
    
    dds_id: str
    action_type: str        # 'code_change', 'touch_file', 'noop'
    status: str             # 'success', 'failed'
    executed_at: str        # 'YYYY-MM-DD HH:MM:SS'
    notes: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
```

### Aider Runner

```python
def run_aider(workspace_path: str, allowed_paths: List[str], prompt: str) -> Dict:
    """
    Execute Aider within scoped workspace
    
    Args:
        workspace_path: Absolute path to _scoped/ directory
        allowed_paths: List of paths where Aider operates
        prompt: Instructions for Aider
        
    Returns:
        {
            'returncode': int,    # 0 = success
            'stdout': str,        # command output
            'stderr': str,        # error output
            'success': bool       # returncode == 0
        }
    """
```

## 💡 Ejemplos

### Ejemplo 1: Ejecución Simple (Low-level API)

⚠️ **Nota**: Este es el API interno. En producción se usa via router/interface.

```python
from node_programmer.programmer import Programmer

# Initialize
p = Programmer()

# Execute DDS
report = p.execute_code_change('DDS-20260202-CODE-001')

# Check result
if report.status == 'success':
    print(f"✅ Execution successful")
    print(f"Notes: {report.notes}")
else:
    print(f"❌ Execution failed")
    print(f"Notes: {report.notes}")
```

### Ejemplo 2: DDS v2 Completo

```json
{
  "id": "DDS-20260202-CODE-002",
  "version": 2,
  "type": "code_change",
  "project": "FitnessAi",
  "goal": "Add user authentication endpoint",
  "instructions": [
    "Create src/auth/login.py with OAuth2 login function",
    "Add tests in tests/test_auth.py",
    "Update src/api/routes.py to include /auth/login endpoint"
  ],
  "allowed_paths": [
    "src/auth/",
    "src/api/routes.py",
    "tests/"
  ],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 5,
    "no_new_dependencies": false,
    "no_refactor": true
  },
  "status": "approved",
  "created_at": "2026-02-02T14:30:00Z"
}
```

### Ejemplo 3: Verificar Estado de Ejecución

```python
import json
from pathlib import Path

# Check reports.json
reports_file = Path('node_programmer/reports.json')
with open(reports_file, 'r') as f:
    data = json.load(f)

# Get executions for specific DDS
dds_id = 'DDS-20260202-CODE-001'
executions = [e for e in data['executions'] if e['dds_id'] == dds_id]

for exec in executions:
    print(f"Status: {exec['status']}")
    print(f"Executed at: {exec['executed_at']}")
    print(f"Notes: {exec['notes']}")
```

### Ejemplo 4: Error Handling

```python
from node_programmer.programmer import Programmer, ProgrammerError

p = Programmer()

try:
    report = p.execute_code_change('DDS-20260202-CODE-001')
except ProgrammerError as e:
    if "already executed" in str(e):
        print("DDS already executed successfully")
    elif "not found" in str(e):
        print("DDS not found or not approved")
    else:
        print(f"Execution failed: {e}")
```

## 🧪 Testing

### Test de Integración Completa

```bash
python3 -c "
from node_programmer.programmer import Programmer

p = Programmer()
report = p.execute_code_change('DDS-TEST-001')

print(f'Status: {report.status}')
print(f'DDS ID: {report.dds_id}')
print(f'Notes: {report.notes}')
"
```

### Test de Aider Runner

```bash
python3 -c "
from node_programmer.external_tools.aider_runner import run_aider
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    result = run_aider(tmpdir, ['test.py'], 'Add hello world')
    print(f'Success: {result[\"success\"]}')
    print(f'Return code: {result[\"returncode\"]}')
"
```

## 📊 Métricas y Monitoreo

### reports.json Stats

```python
import json
from collections import Counter

with open('node_programmer/reports.json', 'r') as f:
    data = json.load(f)

# Count by status
statuses = Counter(e['status'] for e in data['executions'])
print(f"Success: {statuses['success']}")
print(f"Failed: {statuses['failed']}")

# Count by action_type
actions = Counter(e['action_type'] for e in data['executions'])
print(f"Code changes: {actions['code_change']}")
```

## 🚧 Limitaciones Conocidas

1. **Constraint Heuristics**: Validaciones basadas en heurísticas simples
   - `no_refactor` usa threshold de 3 archivos (no análisis AST)
   - `no_new_dependencies` solo detecta archivos conocidos por nombre
   - **Roadmap v3.0**: Validación AST para mayor precisión

2. **Tool Support**: Solo Aider soportado actualmente
   - Arquitectura preparada para multi-tool
   - **Roadmap v3.0**: Cursor, Claude Code

3. **Rollback**: No hay rollback automático
   - Workspace manual cleanup requerido
   - **Roadmap v2.2**: Rollback automático en constraints violated

4. **Concurrency**: No hay soporte para ejecuciones paralelas
   - Un DDS a la vez por diseño actual
   - **Roadmap v2.2**: Queue system con ejecución paralela

5. **Estado no es lock distribuido**: 
   - Prevención de re-ejecución mediante estado persistido
   - No usa locks transaccionales ni distribuidos
   - Adecuado para single-instance, necesita coordinación para multi-instance

## 🗺️ Roadmap

### v2.2 (Próximo)
- 🔲 Rollback automático
- 🔲 Ejecución paralela de DDSs
- 🔲 Métricas avanzadas (tiempo, líneas, complejidad)
- 🔲 Workspace cleanup automático

### v3.0 (Futuro)
- 🔲 Multi-tool support (Cursor, Claude)
- 🔲 AST-based constraint validation
- 🔲 Sandbox containerizado (Docker)
- 🔲 Streaming de ejecución en vivo

## 📚 Referencias

- [Aider Documentation](https://aider.chat/)
- [DDS v2 Specification](../node_dds/README.md)
- [Claude System](../claude_system/README.md)

## 🤝 Contribución

Ver [Contributing Guidelines](../CONTRIBUTING.md)

## 📄 Licencia

MIT - Ver [LICENSE](../LICENSE)
