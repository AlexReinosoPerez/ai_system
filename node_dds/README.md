# Node DDS - Decision-Driven System

Sistema de propuestas estructuradas para cambios de código con validación y auditoría.

## 📋 Índice

- [Visión General](#visión-general)
- [Estructura de DDS](#estructura-de-dds)
- [Versiones](#versiones)
- [Workflow](#workflow)
- [Ejemplos](#ejemplos)

## 🎯 Visión General

Node DDS es el sistema de propuestas que define **qué** cambios se deben realizar, mientras que Node Programmer define **cómo** ejecutarlos.

### Principios

- **Explícito sobre implícito**: Todo debe estar documentado
- **Validación antes de ejecución**: Estructura validada antes de procesar
- **Auditable**: Historial completo de propuestas y ejecuciones
- **Versionado**: Soporte para evolución del formato

## 📝 Estructura de DDS

### DDS v1 - touch_file (Legacy)

Acción simple de escritura de archivos:

```json
{
  "id": "DDS-20260202112854",
  "project": "Test",
  "title": "Create test file",
  "type": "touch_file",
  "path": "test_output.txt",
  "content": "Hello World!",
  "status": "approved",
  "created_at": "2026-02-02 11:28:54"
}
```

**Campos:**
- `type`: "touch_file"
- `path`: Ruta relativa del archivo
- `content`: Contenido a escribir
- `status`: "approved" para ejecutar

### DDS v2 - code_change (Actual)

Cambios de código con IA y constraints:

```json
{
  "id": "DDS-20260202-CODE-001",
  "version": 2,
  "type": "code_change",
  "project": "FitnessAi",
  "goal": "Add user authentication",
  "instructions": [
    "Create OAuth2 login endpoint",
    "Add JWT token generation",
    "Implement password hashing"
  ],
  "allowed_paths": [
    "src/auth/",
    "tests/auth/"
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

## 📚 Versiones

### DDS v1 (Legacy)

**Uso:** Operaciones simples de archivos

**Acciones soportadas:**
- `touch_file`: Escribir archivo
- `noop`: Sin operación (testing)

**Limitaciones:**
- Un archivo a la vez
- Sin validación de cambios
- Sin constraints

### DDS v2 (Actual)

**Uso:** Cambios de código con IA

**Características:**
- ✅ Multiple archivos
- ✅ Workspace aislado
- ✅ Constraints configurables
- ✅ Análisis post-ejecución
- ✅ Validación de cambios
- ✅ Integración con herramientas externas

**Campos requeridos:**

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `id` | string | Identificador único | `"DDS-20260202-CODE-001"` |
| `version` | int | Versión (debe ser 2) | `2` |
| `type` | string | Tipo (debe ser "code_change") | `"code_change"` |
| `project` | string | Nombre del proyecto | `"FitnessAi"` |
| `goal` | string | Objetivo del cambio | `"Add user authentication"` |
| `instructions` | array | Pasos específicos | `["Step 1", "Step 2"]` |
| `allowed_paths` | array | Paths permitidos | `["src/", "tests/"]` |
| `tool` | string | Herramienta (debe ser "aider") | `"aider"` |
| `constraints` | object | Restricciones | `{"max_files": 5}` |
| `status` | string | Estado (debe ser "approved") | `"approved"` |

### DDS v3 (Futuro)

**Planeado:**
- Multi-herramienta (Cursor, Claude)
- Dependencias entre DDSs
- Rollback automático
- Validación AST
- Constraints avanzados

## 🔄 Workflow

### 1. Creación de Propuesta

```json
{
  "id": "DDS-20260202-CODE-005",
  "version": 2,
  "type": "code_change",
  "project": "MyProject",
  "goal": "Add logging system",
  "instructions": [
    "Create src/logger.py with Logger class",
    "Add configuration in config/logging.yaml",
    "Update main.py to use logger"
  ],
  "allowed_paths": [
    "src/logger.py",
    "config/logging.yaml",
    "src/main.py"
  ],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 3,
    "no_new_dependencies": false,
    "no_refactor": false
  },
  "status": "pending",
  "created_at": "2026-02-02T15:00:00Z"
}
```

### 2. Aprobación

```json
{
  "status": "approved"  // Change to approved
}
```

### 3. Ejecución

```python
from node_programmer.programmer import Programmer

p = Programmer()
report = p.execute_code_change('DDS-20260202-CODE-005')
```

### 4. Post-Ejecución

El DDS se actualiza con `last_execution`:

```json
{
  "id": "DDS-20260202-CODE-005",
  "status": "approved",
  "last_execution": {
    "status": "success",
    "executed_at": "2026-02-02 15:05:23",
    "notes": "Execution completed. Files changed: 3 (1 created, 2 modified). Constraints: OK"
  }
}
```

## 🔒 Constraints

### max_files_changed / max_files

Limita el número total de archivos modificados (creados + modificados):

```json
{
  "constraints": {
    "max_files_changed": 5
  }
}
```

**Validación:**
```python
total_changed = len(created_files) + len(modified_files)
if total_changed > max_files:
    raise ConstraintViolation("Max files exceeded")
```

### no_new_dependencies

Previene modificaciones en archivos de dependencias:

```json
{
  "constraints": {
    "no_new_dependencies": true
  }
}
```

**Archivos monitoreados:**
- `package.json` (Node.js)
- `requirements.txt` (Python)
- `Cargo.toml` (Rust)
- `go.mod` (Go)
- `pom.xml` (Java/Maven)
- `build.gradle` (Java/Gradle)

### no_refactor

Previene refactorings grandes (heurístico):

```json
{
  "constraints": {
    "no_refactor": true
  }
}
```

**Heurística:**
- Si `created + modified > 3`: Posible refactoring

## 💡 Ejemplos

### Ejemplo 1: Feature Simple

```json
{
  "id": "DDS-20260202-CODE-010",
  "version": 2,
  "type": "code_change",
  "project": "BlogApp",
  "goal": "Add comment functionality to posts",
  "instructions": [
    "Create Comment model in models/comment.py",
    "Add comments endpoint in api/comments.py",
    "Add tests in tests/test_comments.py"
  ],
  "allowed_paths": [
    "models/comment.py",
    "api/comments.py",
    "tests/test_comments.py"
  ],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 3,
    "no_new_dependencies": true,
    "no_refactor": true
  },
  "status": "approved",
  "created_at": "2026-02-02T16:00:00Z"
}
```

### Ejemplo 2: Bugfix

```json
{
  "id": "DDS-20260202-CODE-011",
  "version": 2,
  "type": "code_change",
  "project": "EcommerceAPI",
  "goal": "Fix cart total calculation bug",
  "instructions": [
    "Fix calculation logic in services/cart.py line 45-52",
    "Add edge case tests in tests/test_cart.py"
  ],
  "allowed_paths": [
    "services/cart.py",
    "tests/test_cart.py"
  ],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 2,
    "no_new_dependencies": true,
    "no_refactor": true
  },
  "status": "approved",
  "created_at": "2026-02-02T16:30:00Z"
}
```

### Ejemplo 3: Refactoring Controlado

```json
{
  "id": "DDS-20260202-CODE-012",
  "version": 2,
  "type": "code_change",
  "project": "DataPipeline",
  "goal": "Extract database logic to separate module",
  "instructions": [
    "Create db/connection.py with connection pooling",
    "Create db/queries.py with common queries",
    "Update services/*.py to use new db module",
    "Update tests to mock new db module"
  ],
  "allowed_paths": [
    "db/",
    "services/",
    "tests/"
  ],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 10,
    "no_new_dependencies": false,
    "no_refactor": false
  },
  "status": "approved",
  "created_at": "2026-02-02T17:00:00Z"
}
```

### Ejemplo 4: Nueva Dependencia

```json
{
  "id": "DDS-20260202-CODE-013",
  "version": 2,
  "type": "code_change",
  "project": "WebScraper",
  "goal": "Add rate limiting to API calls",
  "instructions": [
    "Add ratelimit package to requirements.txt",
    "Implement rate limiter in utils/rate_limit.py",
    "Apply rate limiter to api/scraper.py",
    "Add rate limit tests"
  ],
  "allowed_paths": [
    "requirements.txt",
    "utils/rate_limit.py",
    "api/scraper.py",
    "tests/test_rate_limit.py"
  ],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 4,
    "no_new_dependencies": false,
    "no_refactor": true
  },
  "status": "approved",
  "created_at": "2026-02-02T17:30:00Z"
}
```

## 📊 Estados de DDS

### Status Lifecycle

```
pending → approved → executed (success/failed)
   ↓         ↓
rejected   cancelled
```

**Estados:**
- `pending`: Propuesta creada, esperando aprobación
- `approved`: Aprobada para ejecución
- `rejected`: Rechazada (no se ejecutará)
- `cancelled`: Cancelada antes de ejecutar
- `executed`: Solo en `last_execution.status`

### Last Execution

Después de ejecutar, el DDS contiene:

```json
{
  "last_execution": {
    "status": "success",  // or "failed"
    "executed_at": "2026-02-02 12:51:24",
    "notes": "Execution details..."
  }
}
```

## 🔐 Seguridad

### Validaciones

1. **Status check**: Solo `approved` puede ejecutarse
2. **Path validation**: `allowed_paths` validados contra traversal
3. **Tool validation**: Solo herramientas whitelisteadas
4. **Constraint enforcement**: Validación post-ejecución

### Prevención de Re-ejecución

DDSs con `last_execution.status == "success"` no se re-ejecutan automáticamente:

```python
if dds.get('last_execution', {}).get('status') == 'success':
    raise ProgrammerError("DDS already executed successfully")
```

**Nota técnica**: Esto es prevención mediante estado persistido, no un lock transaccional o distribuido. Adecuado para single-instance deployments.

## 🧪 Testing

### Validar DDS v2

```python
from node_programmer.programmer import Programmer

p = Programmer()

# This will validate the DDS structure
try:
    p._validate_dds_v2(dds)
    print("✅ DDS v2 valid")
except ProgrammerError as e:
    print(f"❌ Validation failed: {e}")
```

### Crear DDS de Test

```json
{
  "id": "DDS-TEST-001",
  "version": 2,
  "type": "code_change",
  "project": "TestProject",
  "goal": "Test execution",
  "instructions": ["Do nothing"],
  "allowed_paths": ["test.py"],
  "tool": "aider",
  "constraints": {},
  "status": "approved",
  "created_at": "2026-02-02T00:00:00Z"
}
```

## 📚 Referencias

- [Node Programmer Documentation](../node_programmer/README.md)
- [Aider Documentation](https://aider.chat/)
- [Claude System](../claude_system/README.md)

## 🗺️ Roadmap

### v2.1 (Próximo)
- 🔲 Validación de schema JSON
- 🔲 Templates de DDS
- 🔲 DDS groups (ejecutar múltiples DDSs)

### v3.0 (Futuro)
- 🔲 Dependencias entre DDSs
- 🔲 Conditional execution
- 🔲 Rollback policies
- 🔲 Multi-tool support

## 🤝 Contribución

Ver [Contributing Guidelines](../CONTRIBUTING.md)

## 📄 Licencia

MIT - Ver [LICENSE](../LICENSE)
