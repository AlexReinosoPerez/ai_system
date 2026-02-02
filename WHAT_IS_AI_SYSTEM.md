# AI System - Qué es y qué NO es

## ✅ Qué ES AI System

### 1. Runtime de Ejecución
AI System es un **motor de ejecución** que:
- Toma propuestas estructuradas (DDS)
- Las valida contra reglas definidas
- Las ejecuta en workspace aislado
- Registra cambios y resultados
- Persiste estado y auditoría

**Analogía**: Es como un motor de workflow para cambios de código.

### 2. Sistema de Control
Proporciona **control explícito** sobre:
- Qué archivos pueden modificarse (`allowed_paths`)
- Cuántos archivos máximo (`max_files_changed`)
- Si se permiten nuevas dependencias (`no_new_dependencies`)
- Si se permite refactoring (`no_refactor`)

**Analogía**: Es como un sistema de permisos granulares para modificaciones.

### 3. Plataforma de Auditoría
Garantiza **trazabilidad completa**:
- Quién aprobó cada DDS
- Qué cambios se ejecutaron
- Cuándo se ejecutó
- Qué constraints se validaron
- Qué archivos cambiaron (created/modified/deleted)

**Analogía**: Es como un sistema de logs de auditoría para cambios de código.

### 4. Abstracción de Herramientas
Actúa como **capa de abstracción** entre:
- DDS (qué hacer)
- Herramientas externas (cómo hacerlo)

Actualmente soporta Aider, diseñado para soportar múltiples herramientas.

**Analogía**: Es como un driver que habla con diferentes herramientas de IA.

---

## ❌ Qué NO ES AI System

### 1. NO es un Agente Autónomo
- ❌ No toma decisiones por sí solo
- ❌ No genera DDSs automáticamente
- ❌ No aprueba propuestas sin intervención humana

**Por qué**: El sistema requiere aprobación explícita humana (`status: "approved"`).

### 2. NO es un Chat/Copilot
- ❌ No genera código en tiempo real
- ❌ No responde a preguntas
- ❌ No sugiere cambios mientras escribes

**Por qué**: El flujo es batch (propuesta → aprobación → ejecución), no interactivo.

### 3. NO es un Framework de Desarrollo
- ❌ No define cómo desarrollas
- ❌ No impone metodología
- ❌ No gestiona tu workflow diario

**Por qué**: Es runtime de ejecución, no tooling de desarrollo.

**Nota**: El framework de desarrollo está en `docs/framework/`, pero es interno/opcional, no parte del runtime.

### 4. NO es un Sistema de CI/CD
- ❌ No ejecuta tests automáticamente
- ❌ No hace deploys
- ❌ No gestiona environments

**Por qué**: Es complementario a CI/CD, no sustituto. Ejecuta cambios, pero no pipelines completos.

### 5. NO es un Lock Transaccional
- ❌ No usa locks distribuidos
- ❌ No garantiza serialización en multi-instance
- ❌ No es un sistema de coordinación distribuida

**Por qué**: Usa estado persistido para prevenir duplicados, no mecanismos de lock. Funciona para single-instance, necesita coordinación para multi-instance.

### 6. NO es un Sandbox OS-Level
- ❌ No ejecuta en contenedores (v2.1)
- ❌ No aísla a nivel de proceso
- ❌ No limita recursos (CPU/memory)

**Por qué**: El aislamiento es a nivel de filesystem (workspace), no de OS. Roadmap v3.0 incluye containerización.

### 7. NO es Zero-Trust
- ❌ No tiene autenticación (v2.1)
- ❌ No tiene autorización granular
- ❌ No tiene rate limiting

**Por qué**: Actualmente confía en que los DDSs aprobados son legítimos. Roadmap v2.2/v3.0 incluye seguridad robusta.

---

## 🎯 Casos de Uso Válidos

### ✅ Casos donde AI System brilla

1. **Features pequeños/medianos con scope claro**
   - "Añadir endpoint de login en src/auth/"
   - "Crear tests para módulo X en tests/X/"
   - Scope bien definido, 2-10 archivos

2. **Bugfixes específicos**
   - "Corregir cálculo en services/cart.py línea 45"
   - Scope quirúrgico, 1-3 archivos

3. **Refactorings controlados**
   - "Extraer lógica de DB a módulo db/"
   - Scope conocido, constraints configurados

4. **Cambios documentados y auditables**
   - Necesitas traza de quién aprobó qué
   - Necesitas historial completo de cambios

### ⚠️ Casos donde AI System NO es la mejor opción

1. **Exploración abierta**
   - "Mejora el código como creas conveniente"
   - Scope indefinido, mejor usar Copilot/Claude directamente

2. **Cambios triviales**
   - "Añade un comentario"
   - Overhead innecesario, mejor editor directo

3. **Prototipado rápido**
   - Experimentación sin constraints
   - Mejor herramientas interactivas

4. **Proyectos sin estructura**
   - Sin paths claros
   - Sin separación de concerns

---

## 🔍 Comparación con Otras Herramientas

### vs GitHub Copilot
| Aspecto | AI System | Copilot |
|---------|-----------|---------|
| **Modo** | Batch (propuesta → ejecución) | Interactivo (sugerencias en tiempo real) |
| **Control** | Explícito (allowed_paths, constraints) | Implícito (sugieres, tú decides) |
| **Auditoría** | Completa (reports.json, dds.json) | Limitada (historial de aceptaciones) |
| **Scope** | Multi-archivo con constraints | Single-file principalmente |
| **Aprobación** | Requiere aprobación explícita | Aceptación inline |

**Complementarios**: Usa Copilot para desarrollo diario, AI System para cambios estructurados y auditables.

### vs Cursor
| Aspecto | AI System | Cursor |
|---------|-----------|--------|
| **Modo** | Batch con validación | Interactivo con contexto |
| **Isolation** | Workspace efímero | Proyecto original |
| **Constraints** | Configurables y validados | No tiene |
| **Auditoría** | Completa y persistida | Limitada |
| **Commits** | Controlados (no automáticos) | Depende del usuario |

**Complementarios**: Usa Cursor para desarrollo interactivo, AI System para ejecución controlada.

### vs Aider CLI
| Aspecto | AI System | Aider CLI |
|---------|-----------|-----------|
| **Wrapper** | Sí (AI System usa Aider internamente) | Herramienta directa |
| **Constraints** | Validados post-ejecución | No tiene |
| **Workspace** | Aislado y scoped | Proyecto original |
| **Auditoría** | Completa | Depende de git history |
| **Prevención** | Estado persistido | No tiene |

**Relación**: AI System es un wrapper de Aider (y futuras herramientas) con constraints y auditoría.

---

## 🏗️ Arquitectura Conceptual

```
┌─────────────────────────────────────────────────────────┐
│                     AI SYSTEM                            │
│                                                          │
│  ┌──────────────┐                                       │
│  │   Human      │ 1. Crea/Aprueba DDS                  │
│  └──────┬───────┘                                       │
│         │                                               │
│         ▼                                               │
│  ┌──────────────┐                                       │
│  │   DDS v2     │ 2. Valida estructura                 │
│  │   (proposal) │                                       │
│  └──────┬───────┘                                       │
│         │                                               │
│         ▼                                               │
│  ┌──────────────┐                                       │
│  │  Programmer  │ 3. Ejecuta en workspace aislado      │
│  │   (runtime)  │    - Copia proyecto                  │
│  └──────┬───────┘    - Scoped paths                    │
│         │            - Invoca Aider                     │
│         │            - Detecta cambios                  │
│         ▼            - Valida constraints               │
│  ┌──────────────┐                                       │
│  │   Reports    │ 4. Persiste resultado                │
│  │   + Audit    │    - reports.json                    │
│  └──────────────┘    - dds.json (last_execution)       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Madurez Actual (v2.1 - Feb 2026)

### ✅ Funcionalmente Completo
- Pipeline de ejecución: 100%
- Validación de constraints: 100%
- Auditoría básica: 100%
- Integración Aider: 100%

### ⚠️ Hardening Pendiente
- Autenticación/autorización: 0%
- Rate limiting: 0%
- Containerización: 0%
- Rollback automático: 0%
- Multi-instance coordination: 0%

### 🎯 Recomendación de Uso
- ✅ **Desarrollo interno**: Excelente
- ✅ **Equipos pequeños**: Muy útil
- ⚠️ **Producción enterprise**: Esperar v2.2/v3.0
- ⚠️ **Multi-tenant**: No recomendado (v2.1)

---

## 🤔 ¿Cuándo usar AI System?

### Usa AI System si:
- ✅ Necesitas auditoría completa de cambios
- ✅ Quieres constraints explícitos (paths, files, deps)
- ✅ Trabajas en equipo con aprobaciones
- ✅ Tienes proyectos estructurados (paths claros)
- ✅ Prefieres batch sobre interactivo
- ✅ Necesitas prevenir cambios accidentales

### NO uses AI System si:
- ❌ Necesitas interactividad en tiempo real
- ❌ Proyecto sin estructura clara
- ❌ Cambios triviales o exploración
- ❌ Necesitas autenticación robusta (v2.1)
- ❌ Necesitas multi-tenant (v2.1)
- ❌ Necesitas containerización (v2.1)

---

## 💡 En Resumen

**AI System es:**
- Runtime de ejecución para cambios de código estructurados
- Sistema de control con constraints configurables
- Plataforma de auditoría completa
- Wrapper de herramientas de IA (actualmente Aider)

**AI System NO es:**
- Agente autónomo
- Chat/Copilot interactivo
- Framework de desarrollo
- Sistema CI/CD completo
- Lock transaccional distribuido
- Sandbox OS-level (v2.1)
- Sistema zero-trust (v2.1)

**Usa AI System cuando necesites:**
Control + Auditoría + Validación en cambios de código asistidos por IA.

**NO uses AI System cuando necesites:**
Interactividad + Exploración + Libertad sin constraints.

---

Last Updated: 2026-02-02
