# node_todo - Sistema de Gestión de Tareas

**Propósito:** Gestión de tareas de alto nivel (ToDo) y generación de propuestas DDS v2 para ejecución gobernada.

**Versión:** 1.0.0  
**Fecha:** 2026-02-02

---

## 📋 Qué ES este componente

`node_todo` es un sistema de gestión de tareas que permite:

1. **Crear tareas de alto nivel** con título, descripción, archivos afectados y constraints
2. **Traducir tareas en propuestas DDS v2** de forma determinista
3. **Mantener trazabilidad** entre tareas y DDS generados
4. **Gestionar el ciclo de vida** de tareas desde creación hasta completado

**Este componente NO ejecuta código. Solo gestiona tareas y genera propuestas.**

---

## 🚫 Qué NO ES este componente

❌ NO aprueba DDS automáticamente  
❌ NO ejecuta código directamente  
❌ NO toma decisiones sin humano  
❌ NO reemplaza al Programmer  
❌ NO es un agente autónomo  

---

## 🏗️ Arquitectura

```
node_todo/
├── __init__.py           # Exports: TodoManager, DDSGenerator
├── todo_manager.py       # CRUD de tareas, manejo de estados
├── dds_generator.py      # Traducción determinista ToDo → DDS
├── todos.json            # Almacén de tareas
└── README.md             # Este archivo
```

### Componentes

**TodoManager:**
- Responsabilidad: Gestión del ciclo de vida de tareas
- Operaciones: CRUD, actualización de estados, vinculación con DDS
- Persistencia: `todos.json`

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
