# Framework de Desarrollo (Development-Only)

Esta carpeta contiene **tooling interno** usado durante el desarrollo de `ai_system`.

⚠️ **Importante**: Este contenido **NO es necesario** para ejecutar o usar `ai_system` en producción.

---

## 📁 Contenido

### `contract_system/`

Framework de desarrollo asistido por IA (anteriormente `ai_contract_system/`).

**Qué contiene:**
- Prompts estructurados para roles (Architect, Implementer, Reviewer, Verifier)
- Metodología de trabajo con IA
- Workflow de desarrollo
- Decisiones y glossario del proyecto

**Para qué sirve:**
- Metodología interna para desarrollo del propio `ai_system`
- Prompts reutilizables para trabajar con Claude/Copilot
- Documentación de decisiones arquitectónicas

**No incluye:**
- Código ejecutable
- Runtime components
- APIs de producción

---

### `philosophy.md`

Principios de diseño y decisiones arquitectónicas de `ai_system`.

**Contenido:**
- 10 principios fundamentales
- Comparaciones con otros sistemas (Copilot, Aider, CI/CD)
- Decisiones NO tomadas (roadmap abierto)
- Filosofía: "Code is critical. AI assists. Humans decide. Everything is audited."

---

## 🎯 Uso Recomendado

### Si estás usando ai_system en producción:

❌ **NO necesitas** este contenido  
✅ Lee el [README.md principal](../../README.md)  
✅ Consulta la [documentación de componentes](../../)  

### Si estás contribuyendo al desarrollo de ai_system:

✅ Lee `contract_system/README.md` para metodología  
✅ Consulta `philosophy.md` para principios de diseño  
✅ Usa los prompts en `contract_system/prompts/` para roles  

---

## 📚 Documentación de Producción

La documentación ejecutable y de uso está en:

- **[README.md](../../README.md)**: Introducción y uso del runtime
- **[ARCHITECTURE.md](../../ARCHITECTURE.md)**: Diagramas del sistema
- **[CHANGELOG.md](../../CHANGELOG.md)**: Historia de versiones
- **[WHAT_IS_AI_SYSTEM.md](../../WHAT_IS_AI_SYSTEM.md)**: Qué es y qué NO es
- **[node_programmer/README.md](../../node_programmer/README.md)**: Pipeline de ejecución
- **[node_dds/README.md](../../node_dds/README.md)**: Especificación DDS
- **[node_todo/README.md](../../node_todo/README.md)**: Gestión de tareas

---

## ⚖️ Separación Clara

```
ai_system/
├── Runtime Components (PRODUCCIÓN)
│   ├── node_programmer/
│   ├── node_dds/
│   ├── node_todo/
│   └── shared/
│
└── docs/framework/ (DESARROLLO)
    ├── contract_system/  ← Framework de desarrollo
    └── philosophy.md     ← Principios de diseño
```

**Runtime** = Ejecuta código, gestiona DDS, audita cambios  
**Framework** = Metodología para desarrollar el runtime

---

**Última actualización:** 2026-02-02
