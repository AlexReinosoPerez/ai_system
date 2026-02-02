# AI System

Runtime para ejecutar cambios de código estructurados mediante propuestas DDS (Decision-Driven System).

> 💡 **¿Es esto para ti?** Lee [WHAT_IS_AI_SYSTEM.md](WHAT_IS_AI_SYSTEM.md) para entender qué es (y qué NO es) este sistema.

## 🎯 Qué es AI System

**AI System** es un motor de ejecución que transforma propuestas de cambio estructuradas (DDS) en código real, con garantías de:

- **Aislamiento**: Workspaces efímeros por ejecución
- **Control**: Solo archivos explícitamente permitidos son modificables
- **Auditoría**: Historial completo de ejecuciones y cambios
- **Validación**: Análisis post-ejecución con constraints configurables
- **Seguridad**: Sin commits automáticos, detección de cambios, prevención de path traversal

## 🚫 Qué NO es AI System

- ❌ **No es un agente autónomo**: Requiere aprobación humana explícita
- ❌ **No es un chat/copilot**: No genera código en tiempo real
- ❌ **No es un framework de desarrollo**: Es runtime de ejecución
- ❌ **No reemplaza CI/CD**: Es complementario, no sustituto

## 💡 Problema que Resuelve

Ejecutar cambios de código asistidos por IA de forma **controlada, auditable y reversible**, sin:
- Commits sorpresa
- Modificaciones fuera de scope
- Pérdida de trazabilidad
- Ejecución sin validación

**Casos de uso:**
- Features pequeños/medianos con scope bien definido
- Bugfixes con paths específicos
- Refactorings controlados
- Cambios documentados y auditables

## 🏗️ Arquitectura - Componentes Core

### Runtime Components (Production)

- **`node_programmer/`**: Motor de ejecución DDS v2
  - `programmer.py`: Pipeline completo de ejecución (8 fases)
  - `external_tools/aider_runner.py`: Integración con Aider (v2.1)
  - `execution_report.py`: Estructura de reportes
  - `workspaces/`: Workspaces efímeros por DDS
  - `sandbox/`: Área de pruebas aislada (v1 compatibility)
  - `reports.json`: Historial de ejecuciones

- **`node_dds/`**: Gestión de propuestas
  - `dds.json`: Almacén de propuestas aprobadas
  - Soporte DDS v1 (touch_file) y v2 (code_change)

- **`shared/`**: Módulos compartidos
  - `config.py`: Configuración centralizada
  - `logger.py`: Sistema de logging unificado

- **`node_interface/`**: Interfaces de comunicación
  - `telegram_bot.py`: Bot de Telegram (opcional)
  - `router.py`: Enrutador de comandos

- **`audits/`**: Logs y auditorías del sistema

> 💡 **Filosofía de diseño**: Ver [docs/philosophy.md](docs/philosophy.md) para principios y decisiones arquitectónicas.

### Development-Only Components

- **`claude_system/`**: **(Development-only)** Framework interno para el desarrollo asistido por IA.
  - Define roles, prompts y workflow de trabajo
  - **NO es necesario para ejecutar ai_system en producción**
  - Usado únicamente durante el desarrollo del propio repositorio
  - Ver [claude_system/README.md](claude_system/README.md) para metodología de desarrollo

## 🚀 Programmer v2.1 - Pipeline de Ejecución

### Fases del Pipeline

1. **PHASE 1**: Estructura y aislamiento (workspace, external_tools)
2. **PHASE 2**: Validación DDS v2 (9 campos requeridos)
3. **PHASE 3**: Creación de workspace efímero (copia de proyecto)
4. **PHASE 4**: Workspace scoped (solo allowed_paths)
5. **PHASE 5**: Construcción de prompt controlado
6. **PHASE 6**: Invocación de herramienta externa (Aider)
7. **PHASE 7**: Análisis post-ejecución (snapshot, cambios, constraints)
8. **PHASE 8**: Persistencia y cierre (reports.json, dds.json, resumen)

### Características de Seguridad

- ✅ **Aislamiento de workspace**: Copia completa del proyecto en workspace efímero
- ✅ **Scoped workspace**: Solo archivos en `allowed_paths` accesibles
- ✅ **Sin commits automáticos**: Flag `--no-auto-commit` en Aider
- ✅ **Validación de paths**: Prevención de path traversal
- ✅ **Constraint validation**: max_files, no_new_dependencies, no_refactor
- ✅ **Detección de cambios**: MD5 hash snapshot antes/después
- ✅ **Prevención de re-ejecución accidental**: Estado persistido en dds.json

### DDS v2 - Estructura

```json
{
  "id": "DDS-YYYYMMDD-CODE-XXX",
  "version": 2,
  "type": "code_change",
  "project": "ProjectName",
  "goal": "Description of the change",
  "instructions": ["Step 1", "Step 2", ...],
  "allowed_paths": ["src/", "tests/"],
  "tool": "aider",
  "constraints": {
    "max_files_changed": 5,
    "no_new_dependencies": true,
    "no_refactor": true
  },
  "status": "approved"
}
```

## 📦 Instalación

### Requisitos

- Python 3.10+
- pip
- git
- [Aider](https://aider.chat/) (opcional, para ejecución real)

### Setup

```bash
# 1. Clonar repositorio
git clone https://github.com/AlexReinosoPerez/ai_system.git
cd ai_system

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. (Opcional) Instalar Aider para ejecución real
pip install aider-chat

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 5. Ejecutar
./run_local.sh
```

## 🔧 Uso

### Modo Recomendado (Alto Nivel)

El uso normal del sistema es mediante **interfaces** (Telegram bot, CLI, router):

```bash
# Via Telegram Bot (si está configurado)
# Enviar DDS → Sistema aprueba → Ejecución automática

# Via CLI (próximamente)
# ai-system execute DDS-20260202-CODE-001

# Via Router (para integraciones)
# El router gestiona el flujo completo
```

**Flujo típico:**
1. Usuario envía DDS v2 (formato JSON)
2. Sistema valida estructura y constraints
3. Usuario aprueba ejecución
4. Programmer ejecuta en workspace aislado
5. Sistema reporta cambios y validaciones

### Uso Avanzado (API Interna)

> ⚠️ **Este ejemplo muestra el uso directo de la API interna del Programmer.**
> No es el modo recomendado para producción. Usar interfaces de alto nivel.

```python
from node_programmer.programmer import Programmer

# Inicializar programmer
p = Programmer()

# Ejecutar DDS aprobado (LOW-LEVEL API)
report = p.execute_code_change('DDS-20260202-CODE-001')

# Revisar resultado
print(f"Status: {report.status}")
print(f"Notes: {report.notes}")
```

**Cuándo usar API interna:**
- Testing unitario del Programmer
- Integración personalizada (no usar interfaces estándar)
- Debugging de pipeline de ejecución

### Resultado de Ejecución

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

## 📊 Sistema de Reportes

### reports.json
Historial append-only de todas las ejecuciones:
```json
{
  "executions": [
    {
      "dds_id": "DDS-20260202-CODE-001",
      "action_type": "code_change",
      "status": "success",
      "executed_at": "2026-02-02 12:51:24",
      "notes": "Execution completed. Files changed: 3..."
    }
  ]
}
```

### dds.json
Estado de ejecución por DDS:
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

## 🧪 Testing

```bash
# Validar estructura del sistema
python3 -c "from node_programmer.programmer import Programmer; p = Programmer()"

# Ejecutar test de DDS
python3 -c "
from node_programmer.programmer import Programmer
p = Programmer()
report = p.execute_code_change('DDS-TEST-001')
print(f'Status: {report.status}')
"
```

## 📚 Documentación Adicional

### Esencial
- **[¿Qué es AI System?](WHAT_IS_AI_SYSTEM.md)**: Qué es y qué NO es (casos de uso, comparaciones)
- **[DDS Specification](node_dds/README.md)**: Cómo crear propuestas DDS v2
- **[CHANGELOG.md](CHANGELOG.md)**: Historia de versiones

### Para Desarrolladores
- **[Programmer Architecture](node_programmer/README.md)**: Pipeline de ejecución detallado
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Diagramas y flujos del sistema
- **[Core Philosophy](docs/philosophy.md)**: Principios de diseño y decisiones arquitectónicas

### Development Framework (Interno)
- **[claude_system/](claude_system/)**: Framework de desarrollo asistido por IA (development-only)
  - Metodología de trabajo con prompts y roles
  - No necesario para ejecutar el runtime en producción

## 🔐 Seguridad y Límites

### Garantías Actuales

✅ **Workspace aislado por DDS**: Cada ejecución trabaja en copia separada
✅ **Scoped workspace con allowed_paths**: Solo paths explícitos accesibles
✅ **Sin commits automáticos**: Herramienta ejecutada con `--no-auto-commit`
✅ **Validación de path traversal**: Rechaza paths con `..` o absolutos
✅ **Constraints configurables**: Límites en archivos, dependencias, refactoring
✅ **Detección de cambios**: Snapshot MD5 antes/después con diff
✅ **Estado persistido**: Registro completo en reports.json (append-only)

### Limitaciones Conocidas

⚠️ **No es un lock transaccional**: El estado persistido previene duplicados por diseño, no mediante locks distribuidos
⚠️ **Constraints heurísticos**: Validaciones basadas en heurísticas (ej: >3 archivos = refactor)
⚠️ **Sin rollback automático**: Requiere gestión manual de cambios fallidos
⚠️ **Sin sandbox OS-level**: Ejecuta en el mismo entorno, no containerizado
⚠️ **Sin rate limiting**: No hay límites de ejecuciones concurrentes (v2.1)

### Pendiente (Roadmap)

- 🔲 Autenticación y autorización
- 🔲 Rate limiting y queue system
- 🔲 Sandbox containerizado (Docker)
- 🔲 Rollback automático
- 🔲 Validación AST (en vez de heurísticas)

## 🗺️ Estado Actual y Roadmap

### v2.1 (Actual - Feb 2026)
- ✅ Integración real Aider
- ✅ Pipeline completo 8 fases
- ✅ Persistencia y reportes
- ✅ Análisis post-ejecución
- ✅ Workspace aislado con scoped paths

**Nivel de madurez**: Alpha/Beta - Funcionalmente completo, pendiente de hardening en producción

### v2.2 (Próximo - Q1 2026)
- 🔲 Rollback automático
- 🔲 Queue system y rate limiting
- 🔲 Métricas de ejecución
- 🔲 DDS templates
- 🔲 Workspace cleanup automático

### v3.0 (Futuro - Q2-Q3 2026)
- 🔲 Multi-herramienta (Cursor, Claude Code)
- 🔲 Validación AST (no heurísticas)
- 🔲 Sandbox containerizado
- 🔲 Multi-proyecto
- 🔲 Sistema de permisos
- 🔲 CI/CD integration
- 🔲 Dashboard web

## 🤝 Contribución

Este proyecto usa un framework de desarrollo interno (claude_system/) que define roles y workflow.

Ver [claude_system/README.md](claude_system/README.md) para metodología de desarrollo.

**Nota**: claude_system es tooling interno, no es necesario para usar AI System en producción.

## 📄 Licencia

MIT

## 👤 Autor

Alex Reinoso Pérez
- GitHub: [@AlexReinosoPerez](https://github.com/AlexReinosoPerez)
- Repository: [ai_system](https://github.com/AlexReinosoPerez/ai_system)
