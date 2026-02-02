# Core Philosophy - AI System

## 🧠 Principios Fundamentales

Este documento describe la filosofía de diseño detrás de **AI System**. Para información técnica, ver [README.md](../README.md).

---

## 1. Control Explícito sobre Autonomía

**Decisión**: Los cambios de código requieren aprobación humana explícita mediante DDS.

**Por qué**:
- El código es un activo crítico que no debe modificarse sin supervisión
- La IA es asistente, no decisor
- Los humanos deben mantener el control final

**Implicaciones**:
- No hay "agente autónomo" que decide qué cambiar
- Todo cambio pasa por un proceso de aprobación
- El sistema es deliberadamente conservador

---

## 2. Auditoría Completa como Requisito, No Como Feature

**Decisión**: Toda ejecución queda registrada de forma inmutable.

**Por qué**:
- Sin auditoría, no hay confianza
- Los cambios de código deben ser trazables
- Los errores deben ser investigables

**Implicaciones**:
- `reports.json` es append-only
- Cada DDS registra su estado de ejecución en `dds.json`
- No hay ejecuciones "invisibles"

---

## 3. Aislamiento por Diseño

**Decisión**: Cada ejecución trabaja en workspace efímero con scope limitado.

**Por qué**:
- Prevenir side-effects entre ejecuciones
- Limitar superficie de ataque
- Facilitar debugging (workspace es snapshot completo)

**Implicaciones**:
- Workspaces en `workspaces/{dds_id}/`
- Scoped workspace con solo `allowed_paths`
- Limpieza manual por diseño (permite inspección post-mortem)

---

## 4. Constraints Explícitos sobre Confianza Implícita

**Decisión**: Los DDS incluyen constraints que validan el resultado.

**Por qué**:
- No podemos asumir que la herramienta externa respetará límites
- Los constraints son guardarraíles, no sugerencias
- Mejor detectar violaciones que repararlas después

**Implicaciones**:
- `max_files_changed`, `no_new_dependencies`, `no_refactor`
- Validación post-ejecución con snapshot MD5
- Fallo si constraints no se cumplen

---

## 5. Sin Commits Automáticos

**Decisión**: El sistema nunca hace commits automáticos.

**Por qué**:
- El commit es decisión humana
- Permite revisión manual antes de persistir
- Facilita rollback (simple `git reset`)

**Implicaciones**:
- Flag `--no-auto-commit` en herramientas externas
- Usuario revisa cambios y decide si commitear
- Sistema genera cambios, humano decide si persistir

---

## 6. Herramientas Intercambiables

**Decisión**: El sistema es agnóstico a la herramienta de codificación.

**Por qué**:
- Aider hoy, otra cosa mañana
- Dependencia explícita, no acoplamiento
- Permite testing con mocks

**Implicaciones**:
- `external_tools/` contiene wrappers
- Interface común para cualquier herramienta
- Aider es v1, multi-tool es roadmap v3

---

## 7. Estado Persistido sobre Memoria Volátil

**Decisión**: El estado del sistema se persiste en JSON, no en memoria.

**Por qué**:
- Reiniciabilidad sin pérdida de contexto
- Debugging post-mortem posible
- Sistema puede caerse y retomar

**Implicaciones**:
- `dds.json` persiste estado de cada DDS
- `reports.json` persiste historial
- No hay "estado en memoria" crítico

---

## 8. Documentación como Código de Primera Clase

**Decisión**: La documentación es parte integral del sistema, no "nice to have".

**Por qué**:
- Sistema complejo requiere documentación exhaustiva
- Los usuarios externos no tienen contexto
- Los contribuidores futuros necesitan guía

**Implicaciones**:
- 2,500+ líneas de documentación
- Diagramas ASCII en ARCHITECTURE.md
- README técnico, WHAT_IS_AI_SYSTEM.md conceptual

---

## 9. Heurísticas Explícitas, No Magia

**Decisión**: Las validaciones heurísticas se documentan como tales.

**Por qué**:
- No fingir que tenemos validación AST cuando no la tenemos
- Honestidad técnica genera confianza
- Los usuarios deben conocer limitaciones

**Implicaciones**:
- Constraints documentados como "heurísticos"
- Roadmap claro hacia validación AST (v3.0)
- Limitaciones explícitas en README

---

## 10. Alpha/Beta Honest

**Decisión**: El sistema se presenta como "Alpha/Beta", no como "Production-Ready".

**Por qué**:
- Falta hardening (auth, rate limiting, sandbox OS)
- La honestidad previene expectativas incorrectas
- Permite iteración sin romper promesas

**Implicaciones**:
- Madurez explícita en README
- Roadmap claro con pendientes
- No se vende como "enterprise-ready"

---

## Comparación con Otros Sistemas

### vs. Copilot/Cursor
- **AI System**: Runtime estructurado, aprobación explícita, auditoría
- **Copilot/Cursor**: Chat/sugerencias en tiempo real, inmediatas

### vs. Aider CLI directo
- **AI System**: Wrapper con constraints, auditoría, workspace aislado
- **Aider CLI**: Herramienta directa, sin guardarraíles

### vs. CI/CD
- **AI System**: Generación de código asistida
- **CI/CD**: Ejecución de tests/deploy automatizado

---

## Decisiones NO Tomadas (Aún)

**Roadmap Abierto:**
- Multi-instancia (coordinación distribuida)
- Rollback automático vs manual
- Containerización vs procesos OS
- Dashboard web vs CLI puro
- Multi-tenant vs single-project

Estas decisiones se tomarán según feedback de producción.

---

## Conclusión

AI System es deliberadamente conservador, explícito y auditable.

No busca ser el sistema más "inteligente" o "autónomo", busca ser el más **confiable y controlable**.

**Filosofía resumida**: "Code is critical. AI assists. Humans decide. Everything is audited."
