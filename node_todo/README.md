# node_todo - Sistema de Gestión de Tareas

**Propósito:** Gestión de tareas de alto nivel (ToDo) y generación de propuestas DDS v2 para ejecución gobernada.

**Versión:** 2.2.0  
**Fecha:** 2026-02-02

---

## 📋 Qué ES este componente

`node_todo` ofrece **dos versiones** para gestión de tareas:

### Versión Avanzada (TodoManager + DDSGenerator)
1. **Crear tareas de alto nivel** con título, descripción, archivos afectados y constraints
2. **Traducir tareas en propuestas DDS v2** de forma determinista
3. **Mantener trazabilidad** entre tareas y DDS generados
4. **Gestionar el ciclo de vida** con FSM de 6 estados
5. **Validaciones exhaustivas** (path traversal, FSM, constraints)

### Versión Simplificada (TodoRegistry + TodoToDDSConverter)
1. **Gestión CRUD básica** de tareas
2. **Conversión simple** a propuestas DDS v2
3. **Sin FSM complejo** (solo 3 estados: open, converted, closed)
4. **Código minimalista** para casos de uso simples

**Ambas versiones NO ejecutan código. Solo gestionan tareas y generan propuestas.**

---

## 🚫 Qué NO ES este componente

❌ NO aprueba DDS automáticamente  
❌ NO ejecuta código directamente  
❌ NO toma decisiones sin humano  
❌ NO reemplaza al Programmer  
❌ NO es un agente autónomo  

---

## 🏗️ Arquitectura

### Archivos

```
node_todo/
├── __init__.py              # Exports: TodoManager, DDSGenerator, TodoRegistry, TodoToDDSConverter
├── todo_manager.py          # Versión avanzada: CRUD con FSM
├── dds_generator.py         # Versión avanzada: Traducción con metadatos
├── todos.json               # Persistencia versión avanzada
├── todo_registry.py         # Versión simplificada: CRUD básico
├── todo_to_dds.py           # Versión simplificada: Conversión simple
├── todo.json                # Persistencia versión simplificada
└── README.md                # Este archivo
```

### Componentes - Versión Avanzada

**TodoManager:**
- Responsabilidad: Gestión del ciclo de vida de tareas con FSM
- Operaciones: CRUD, actualización de estados, vinculación con DDS
- Persistencia: `todos.json`
- Estados: pending, draft_generated, approved, completed, failed, cancelled

**DDSGenerator:**
- Responsabilidad: Traducción determinista con metadatos completos
- Operaciones: Generación de DDS, validación, persistencia en `node_dds/dds.json`
- Traducción: Campo a campo, sin IA, sin heurísticas

### Componentes - Versión Simplificada

**TodoRegistry:**
- Responsabilidad: Gestión CRUD básica de tareas
- Operaciones: create, list, get, update_status
- Persistencia: `todo.json`
- Estados: open, converted, closed

**TodoToDDSConverter:**
- Responsabilidad: Conversión simple a propuesta DDS
- Operaciones: generate_dds() retorna dict (NO persiste)
- Constraints: Valores conservadores por defecto

**DDSGenerator:**
- Responsabilidad: Traducción determinista de ToDo a DDS v2 draft
- Operaciones: Generación de DDS, validación, persistencia en `node_dds/dds.json`
- Traducción: Campo a campo, sin IA, sin heurísticas

---

## 🔄 Estados de Tareas

### Máquina de Estados Finita (FSM)

```
pending → draft_generated → approved → completed
   ↓            ↓              ↓
cancelled ← cancelled ← cancelled

failed → pending (retry)
  ↓
cancelled
```

### Estados Válidos

- **`pending`**: Tarea creada, sin DDS asociado
- **`draft_generated`**: DDS draft creado, esperando aprobación humana
- **`approved`**: DDS aprobado por humano (pero no ejecutado aún)
- **`completed`**: DDS ejecutado con éxito
- **`failed`**: DDS ejecutado con error
- **`cancelled`**: Tarea cancelada por humano

### Transiciones Permitidas

| Estado Actual     | Transiciones Permitidas                    |
|-------------------|--------------------------------------------|
| `pending`         | `draft_generated`, `cancelled`             |
| `draft_generated` | `approved`, `pending`, `cancelled`         |
| `approved`        | `completed`, `failed`, `cancelled`         |
| `completed`       | *(estado final)*                           |
| `failed`          | `pending`, `cancelled`                     |
| `cancelled`       | *(estado final)*                           |

---

## 📖 API Pública

### TodoManager

#### `create_todo(title, description, affected_files, constraints, notes=None) -> str`

Crea una nueva tarea.

**Parámetros:**
- `title` (str): Título claro (≤80 caracteres)
- `description` (str): Descripción detallada con instrucciones paso a paso
- `affected_files` (List[str]): Paths relativos que serán modificados
- `constraints` (Dict): Constraints DDS v2 (debe incluir `max_files_changed`)
- `notes` (str, opcional): Comentarios del humano

**Retorna:** `todo_id` (str) - ID único formato `TODO-YYYYMMDD-XXX`

**Ejemplo:**
```python
from node_todo.todo_manager import TodoManager

tm = TodoManager()
todo_id = tm.create_todo(
    title="Add path traversal validation",
    description="Check for '..' in allowed_paths before creating scoped workspace",
    affected_files=["node_programmer/programmer.py"],
    constraints={
        "max_files_changed": 1,
        "no_new_dependencies": True,
        "no_refactor": False
    }
)
# Retorna: 'TODO-20260202-001'
```

---

#### `get_todo(todo_id) -> Optional[Dict]`

Obtiene un ToDo por su ID.

**Retorna:** Dict con datos del ToDo o None si no existe

**Ejemplo:**
```python
todo = tm.get_todo('TODO-20260202-001')
print(todo['title'])  # "Add path traversal validation"
print(todo['status'])  # "pending"
```

---

#### `list_todos(status=None) -> List[Dict]`

Lista todos los ToDos, opcionalmente filtrados por estado.

**Ejemplo:**
```python
# Listar todos
all_todos = tm.list_todos()

# Listar solo pendientes
pending = tm.list_todos(status='pending')

# Listar completados
completed = tm.list_todos(status='completed')
```

---

#### `update_todo_status(todo_id, new_status) -> bool`

Actualiza el estado de un ToDo (validando FSM).

**Ejemplo:**
```python
# Marcar como completado (si estaba en 'approved')
tm.update_todo_status('TODO-20260202-001', 'completed')

# Cancelar tarea
tm.update_todo_status('TODO-20260202-001', 'cancelled')
```

---

#### `link_dds(todo_id, dds_id) -> bool`

Vincula un DDS a un ToDo.

**Ejemplo:**
```python
tm.link_dds('TODO-20260202-001', 'DDS-20260202-CODE-042')
```

---

### DDSGenerator

#### `generate_dds_from_todo(todo_id) -> str`

Genera un DDS v2 draft desde un ToDo.

**Traducción determinista:**
- `title` → `goal`
- `description` → `instructions` (parseado por líneas)
- `affected_files` → `allowed_paths`
- `constraints` → `constraints`
- `project` → inferido (actualmente: "ai_system")
- `tool` → "aider" (hardcoded)
- `version` → 2
- `type` → "code_change"
- `status` → **"draft"** (NUNCA "approved")

**Retorna:** `dds_id` (str) - ID del DDS generado

**Ejemplo:**
```python
from node_todo.dds_generator import DDSGenerator

gen = DDSGenerator()
dds_id = gen.generate_dds_from_todo('TODO-20260202-001')
# Retorna: 'DDS-20260202-CODE-042'

# El DDS se crea en node_dds/dds.json con status='draft'
# El ToDo se actualiza a status='draft_generated'
```

---

## 📖 API Pública - Versión Simplificada

### TodoRegistry

#### `create_todo(project, title, description, priority="medium") -> str`

Crea un nuevo ToDo.

**Parámetros:**
- `project` (str): Nombre del proyecto
- `title` (str): Título del ToDo
- `description` (str): Descripción detallada
- `priority` (str): Prioridad (low|medium|high). Default: medium

**Retorna:** `todo_id` (str) - ID único formato `TODO-YYYYMMDD-HHMMSS`

**Ejemplo:**
```python
from node_todo import TodoRegistry

registry = TodoRegistry()
todo_id = registry.create_todo(
    project="ai_system",
    title="Add validation",
    description="Implement input validation for DDS",
    priority="high"
)
# Retorna: 'TODO-20260202-143022'
```

---

#### `list_todos(status=None) -> List[Dict]`

Lista todos los ToDos, opcionalmente filtrados por estado.

**Ejemplo:**
```python
# Listar todos
all_todos = registry.list_todos()

# Listar solo abiertos
open_todos = registry.list_todos(status="open")
```

---

#### `get_todo_by_id(todo_id) -> Optional[Dict]`

Obtiene un ToDo por su ID.

**Retorna:** Dict del ToDo o None si no existe

**Ejemplo:**
```python
todo = registry.get_todo_by_id(todo_id)
print(todo["title"])   # "Add validation"
print(todo["status"])  # "open"
```

---

#### `update_status(todo_id, new_status) -> bool`

Actualiza el estado de un ToDo.

**Parámetros:**
- `new_status`: Nuevo estado (open|converted|closed)

**Retorna:** True si se actualizó, False si no se encontró

**Ejemplo:**
```python
result = registry.update_status(todo_id, "converted")
# True
```

---

### TodoToDDSConverter

#### `generate_dds(todo) -> Dict`

Genera una propuesta DDS v2 desde un ToDo.

**Estructura generada:**
- `status`: **"proposed"** (NUNCA "approved")
- `allowed_paths`: ["src/", "tests/"] (por defecto)
- `constraints`: Valores conservadores
  - `max_files_changed`: 5
  - `no_new_dependencies`: True
  - `no_refactor`: True

**Retorna:** Dict con estructura DDS v2 (NO persiste automáticamente)

**Ejemplo:**
```python
from node_todo import TodoToDDSConverter

todo = registry.get_todo_by_id(todo_id)
converter = TodoToDDSConverter()
dds_proposal = converter.generate_dds(todo)

# dds_proposal es un dict con status="proposed"
# NO se ejecuta automáticamente
# NO se persiste automáticamente
print(dds_proposal["status"])  # "proposed"
print(dds_proposal["metadata"]["source_todo"])  # todo_id
```

---

## 🔄 Comparación de Versiones

| Característica | Versión Avanzada | Versión Simplificada |
|----------------|------------------|----------------------|
| **Estados** | 6 (FSM completo) | 3 (básicos) |
| **Validaciones** | Path traversal, FSM, constraints | Básicas (priority, status) |
| **Persistencia DDS** | Automática en node_dds/dds.json | Manual (retorna dict) |
| **Metadatos** | Completos | Básicos |
| **Complejidad** | Alta | Baja |
| **Uso recomendado** | Producción, control total | Prototipos, casos simples |

---

## 🔄 Flujo Completo - Versión Simplificada

### PASO 1: Crear ToDo

```python
from node_todo import TodoRegistry

registry = TodoRegistry()
todo_id = registry.create_todo(
    project="ai_system",
    title="Fix bug in validation",
    description="Add check for empty strings",
    priority="high"
)
# Estado inicial: "open"
```

### PASO 2: Convertir a Propuesta DDS

```python
from node_todo import TodoToDDSConverter

todo = registry.get_todo_by_id(todo_id)
converter = TodoToDDSConverter()
dds_proposal = converter.generate_dds(todo)

# dds_proposal["status"] == "proposed"
# NO se ejecuta ni se aprueba automáticamente
```

### PASO 3: Actualizar Estado del ToDo

```python
# Marcar como convertido
registry.update_status(todo_id, "converted")
```

### PASO 4: Revisión y Aprobación Manual (fuera de node_todo)

```python
# El humano revisa dds_proposal
# El humano decide si aprobar o no
# Si aprueba, escribe manualmente en node_dds/dds.json
# y cambia status="proposed" → status="approved"
```

### PASO 5: Cerrar ToDo tras Ejecución

```python
# Tras ejecutar el DDS exitosamente
registry.update_status(todo_id, "closed")
```

---

## 📊 Estados - Versión Simplificada

### Estados Válidos

- **`open`**: ToDo recién creado, sin convertir
- **`converted`**: Propuesta DDS generada (pero no ejecutada)
- **`closed`**: Completado o descartado

### Transiciones Permitidas

```
open → converted → closed
  ↓                  ↑
  └──────────────────┘
```

No hay validación FSM estricta en esta versión. Cualquier transición es permitida.

---

## 🔄 Flujo Completo: ToDo → DDS Ejecutado

### FASE 1: Crear Tarea

```python
from node_todo.todo_manager import TodoManager

tm = TodoManager()
todo_id = tm.create_todo(
    title="Add input validation for DDS constraints",
    description="""
    1. Validate max_files_changed >= 1
    2. Validate no_new_dependencies is boolean
    3. Add error messages for invalid constraints
    """,
    affected_files=["node_dds/dds_manager.py"],
    constraints={
        "max_files_changed": 1,
        "no_new_dependencies": True,
        "no_refactor": False
    }
)

print(f"Tarea creada: {todo_id}")
# Estado: pending
```

---

### FASE 2: Generar DDS Draft

```python
from node_todo.dds_generator import DDSGenerator

gen = DDSGenerator()
dds_id = gen.generate_dds_from_todo(todo_id)

print(f"DDS generado: {dds_id}")
# DDS creado en node_dds/dds.json con status='draft'
# ToDo actualizado a status='draft_generated'
```

---

### FASE 3: Revisar y Aprobar DDS (MANUAL)

```bash
# Humano inspecciona el DDS en node_dds/dds.json
# Humano valida: goal, instructions, allowed_paths, constraints

# Humano edita manualmente el archivo JSON:
# Cambiar "status": "draft" → "status": "approved"
```

```python
# Actualizar estado del ToDo tras aprobación manual
tm.update_todo_status(todo_id, 'approved')
```

---

### FASE 4: Ejecutar DDS

```python
from node_programmer.programmer import Programmer

p = Programmer()
report = p.execute_code_change(dds_id)

print(f"Status: {report.status}")
print(f"Notes: {report.notes}")
```

---

### FASE 5: Actualizar ToDo

```python
# Actualización manual tras verificar ejecución
if report.status == "success":
    tm.update_todo_status(todo_id, 'completed')
else:
    tm.update_todo_status(todo_id, 'failed')
```

---

## 📊 Estructura de Datos

### todos.json

```json
{
  "todos": [
    {
      "id": "TODO-20260202-001",
      "title": "Add path traversal validation",
      "description": "Check for '..' in allowed_paths...",
      "affected_files": ["node_programmer/programmer.py"],
      "constraints": {
        "max_files_changed": 1,
        "no_new_dependencies": true,
        "no_refactor": false
      },
      "status": "pending",
      "created_at": "2026-02-02 14:30:00",
      "updated_at": "2026-02-02 14:30:00",
      "linked_dds_ids": [],
      "notes": "High priority security fix"
    }
  ]
}
```

### Campos Obligatorios

- `id`: ID único formato `TODO-YYYYMMDD-XXX`
- `title`: ≤80 caracteres
- `description`: Instrucciones detalladas
- `affected_files`: Lista no vacía de paths relativos
- `constraints`: Debe incluir `max_files_changed`
- `status`: Uno de los estados válidos
- `created_at`: Timestamp creación
- `updated_at`: Timestamp última actualización
- `linked_dds_ids`: Lista de DDS vinculados (puede estar vacía)

### Campos Opcionales

- `notes`: Comentarios del humano

---

## ⚠️ Limitaciones Conocidas

### v1.0 NO incluye:

❌ **Traducción automática masiva**: Un humano debe solicitar traducción por cada ToDo  
❌ **Auto-aprobación de DDS**: El humano siempre revisa y aprueba manualmente  
❌ **Actualización automática de estado**: Tras ejecución, el humano debe actualizar manualmente  
❌ **CLI**: Solo API Python, sin interfaz de línea de comandos  
❌ **Interface web**: No hay UI gráfica  
❌ **Templates de ToDo**: No hay plantillas predefinidas  
❌ **Priorización**: No hay scoring ni recomendaciones  
❌ **Dependencias entre ToDos**: No hay gestión de pre-requisitos  
❌ **Rollback**: No hay reversión automática  
❌ **Notificaciones**: No hay sistema de alertas  
❌ **Multi-usuario**: No hay concurrencia ni locks  

---

## 🗺️ Roadmap

### v2.0 (Futuro)
- Actualización automática de ToDo status basado en DDS execution
- CLI para gestión de ToDos (`ai-system todo create ...`)
- Detección automática de ToDos completados

### v3.0 (Futuro)
- Templates de ToDo para casos comunes
- Dependencias entre ToDos (pre-requisitos)
- Interface web para gestión visual
- Priorización automática
- Notificaciones

---

## 🔐 Seguridad

### Validaciones Implementadas

✅ **Formato de IDs**: Validación de formato `TODO-YYYYMMDD-XXX`  
✅ **Path traversal**: Rechazo de paths con `..` o absolutos  
✅ **Constraints obligatorios**: `max_files_changed` requerido  
✅ **Transiciones de estado**: FSM valida transiciones permitidas  
✅ **Status draft**: DDS generados siempre con `status='draft'`, nunca auto-aprobados  

### Garantías

✅ No hay auto-aprobación de DDS  
✅ No hay ejecución directa sin aprobación humana  
✅ Todos los paths son validados antes de persistir  
✅ Estado completo persistido en JSON (auditoría completa)  

---

## 🧪 Testing

### Test Básico: Crear y Generar DDS

```python
from node_todo.todo_manager import TodoManager
from node_todo.dds_generator import DDSGenerator

# 1. Crear tarea
tm = TodoManager()
todo_id = tm.create_todo(
    title="Test task",
    description="This is a test",
    affected_files=["test.py"],
    constraints={"max_files_changed": 1}
)

# 2. Verificar creación
todo = tm.get_todo(todo_id)
assert todo['status'] == 'pending'
print(f"✓ ToDo creado: {todo_id}")

# 3. Generar DDS
gen = DDSGenerator()
dds_id = gen.generate_dds_from_todo(todo_id)
print(f"✓ DDS generado: {dds_id}")

# 4. Verificar actualización
todo = tm.get_todo(todo_id)
assert todo['status'] == 'draft_generated'
assert dds_id in todo['linked_dds_ids']
print("✓ ToDo actualizado correctamente")

# 5. Listar todos pendientes
pending = tm.list_todos(status='draft_generated')
assert len(pending) >= 1
print(f"✓ Listado funcional: {len(pending)} ToDos en draft_generated")
```

---

## 📝 Ejemplos Adicionales

### Ejemplo 1: Bugfix Simple

```python
from node_todo.todo_manager import TodoManager

tm = TodoManager()
todo_id = tm.create_todo(
    title="Fix typo in error message",
    description="Change 'Falied' to 'Failed' in programmer.py line 342",
    affected_files=["node_programmer/programmer.py"],
    constraints={
        "max_files_changed": 1,
        "no_new_dependencies": True,
        "no_refactor": False
    },
    notes="Low priority, cosmetic fix"
)
```

### Ejemplo 2: Feature con Múltiples Archivos

```python
todo_id = tm.create_todo(
    title="Add rate limiting to DDS execution",
    description="""
    1. Create rate_limiter.py in shared/
    2. Add rate limit check in programmer.py before execution
    3. Add configuration in config.py
    4. Update tests
    """,
    affected_files=[
        "shared/rate_limiter.py",
        "node_programmer/programmer.py",
        "shared/config.py"
    ],
    constraints={
        "max_files_changed": 3,
        "no_new_dependencies": False,  # Puede requerir librería
        "no_refactor": True
    }
)
```

### Ejemplo 3: Cancelar Tarea

```python
# Listar tareas pendientes
pending = tm.list_todos(status='pending')

# Cancelar una tarea específica
if pending:
    todo_id = pending[0]['id']
    tm.update_todo_status(todo_id, 'cancelled')
    print(f"Tarea {todo_id} cancelada")
```

---

## 🤝 Integración con Sistema Existente

### Relación con otros componentes

```
node_todo/
    ↓ (genera)
node_dds/
    ↓ (ejecuta)
node_programmer/
    ↓ (registra)
node_todo/ (actualización manual de status)
```

**Flujo de datos:**
1. `node_todo` crea tareas en `todos.json`
2. `node_todo` genera DDS draft en `node_dds/dds.json`
3. Humano aprueba DDS (edita JSON manualmente)
4. `node_programmer` ejecuta DDS aprobado
5. Humano actualiza estado de ToDo basado en resultado

---

## 📄 Licencia

MIT (mismo que ai_system)

---

## 👤 Autor

Alex Reinoso Pérez  
GitHub: [@AlexReinosoPerez](https://github.com/AlexReinosoPerez)

---

**Fecha de última actualización:** 2026-02-02
