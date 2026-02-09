# Criterios Humanos de Aceptación / Rechazo de Fixes

> Guía interna de revisión operativa.
> Versión 1.0 — 2026-02-09
> Audiencia: cualquier persona con acceso a auditoría + DDS + fix propuesto.
> No requiere conocimiento del código interno.

---

## 1. Tipología de fallos relevantes

Los fallos en AI System se clasifican en tres categorías operativas según el campo `error_detail` de la auditoría y la categoría asignada por el Router (`dds_error`, `env_error`, `exec_error`).

### Fallos que SÍ deberían generar fixes

| Categoría | Descripción | Ejemplo real |
|-----------|-------------|--------------|
| **dds_error: campos incompletos** | El DDS tiene estructura válida pero le faltan campos que el Programmer necesita (ej. `allowed_paths`, `instructions`). | `"Missing required field 'allowed_paths'"` |
| **exec_error: fallo determinista** | La ejecución falló por un error reproducible en el código del proyecto objetivo (test roto, import faltante, syntax error). | `"Test test_login.py failed: ImportError"` |

### Fallos que NUNCA deberían generar fixes

| Categoría | Descripción | Por qué no |
|-----------|-------------|------------|
| **env_error: herramienta ausente** | Aider no está instalado, Python no disponible, Docker no corre. | No es un problema del DDS ni del código. Es infraestructura. Un fix no puede instalar software. |
| **env_error: red / API caída** | GitHub API devuelve 503, Gmail timeout, rate limit. | Error transitorio. Reintentarlo manualmente es suficiente. |
| **exec_error: timeout** | La ejecución excedió el tiempo límite sin producir output. | No hay información suficiente para diagnosticar la causa. El fix sería especulativo. |
| **dds_error: DDS ya ejecutado** | Se intentó re-ejecutar un DDS con status `executed`. | No es un fallo. Es una operación inválida del operador. |
| **dds_error: DDS no encontrado** | El ID referenciado no existe en `dds.json`. | Error de input humano, no del sistema. |

### Zona gris: requiere juicio caso a caso

| Categoría | Descripción | Criterio |
|-----------|-------------|----------|
| **exec_error: violación de constraints** | La ejecución tocó más archivos de los permitidos o introdujo dependencias. | Si el constraint original era realista → rechazar fix (el DDS estaba mal definido). Si el constraint era demasiado restrictivo → ajustar DDS manualmente, no con fix automático. |

---

## 2. Criterios de APROBACIÓN de un fix

Un FixDDS debe cumplir **todos** los siguientes criterios para ser aprobado.

### 2.1 Trazabilidad directa

- [ ] El campo `source_dds` del FixDDS corresponde exactamente al DDS que falló.
- [ ] El campo `error_context.original_dds` coincide con `source_dds`.
- [ ] El campo `error_context.error_message` describe el error que el operador puede verificar en `reports.json`.

**Si no se puede trazar el fix hasta el fallo original, rechazar.**

### 2.2 Scope acotado

- [ ] `constraints.max_files_changed` ≤ 3 (el generador impone esto, pero verificar).
- [ ] `constraints.no_new_dependencies` es `true`.
- [ ] `constraints.no_refactor` es `true`.
- [ ] `allowed_paths` del fix es un subconjunto de `allowed_paths` del DDS original, o idéntico. Nunca más amplio.

**Si el fix amplía paths, archivos permitidos o dependencias, rechazar.**

### 2.3 Correspondencia causa-efecto

- [ ] Las `instructions` del fix mencionan explícitamente el error que ocurrió (al menos la primera línea del error).
- [ ] Las `instructions` no incluyen acciones que vayan más allá de corregir ese error específico.
- [ ] El `type` del fix es `code_fix`, no `code_change` ni ningún otro tipo.

**Si las instrucciones incluyen mejoras, optimizaciones o cambios fuera del error, rechazar.**

### 2.4 Proyecto correcto

- [ ] El campo `project` del fix coincide con el `project` del DDS original.
- [ ] Si el DDS original era sobre `FitnessAi`, el fix no toca `ai_system` ni otro proyecto.

**Si el fix cruza límites de proyecto, rechazar.**

### 2.5 Status correcto

- [ ] El fix llega con `status: proposed`. Si tiene cualquier otro status, no se revisa.

---

## 3. Criterios de RECHAZO inmediato

Rechazar sin análisis profundo si se cumple **cualquiera** de los siguientes:

| # | Red Flag | Qué indica |
|---|----------|------------|
| 1 | **`allowed_paths` del fix contiene paths que no estaban en el DDS original** | El fix amplía la superficie de ataque. |
| 2 | **`constraints.no_new_dependencies` es `false` o está ausente** | El fix introduce dependencias no autorizadas. |
| 3 | **`constraints.no_refactor` es `false` o está ausente** | El fix disfraza refactoring como corrección. |
| 4 | **`source_dds` vacío, ausente, o no coincide con ningún DDS en `dds.json`** | Fix huérfano. No hay fallo que lo justifique. |
| 5 | **`error_context` vacío o ausente** | Sin contexto de error, el fix no es verificable. |
| 6 | **Las `instructions` mencionan "mejorar", "optimizar", "refactorizar" o "añadir funcionalidad"** | No es un fix. Es una feature disfrazada. |
| 7 | **El `project` del fix difiere del `project` del DDS original** | Cruce de contexto. El fix opera fuera de su dominio. |
| 8 | **El fallo original fue `env_error` (herramienta ausente, red caída)** | No hay código que arreglar. El fix sería inútil. |
| 9 | **Ya existe otro FixDDS con el mismo `source_dds` en estado `proposed` o `approved`** | Duplicado. El sistema no debería generar dos fixes para el mismo fallo (el ReactiveWorker tiene guard para esto, pero verificar). |
| 10 | **`max_files_changed` > 3** | Scope excesivo para un fix. |

---

## 4. Casos de IGNORAR el fix

Un fix se ignora (ni se aprueba ni se rechaza explícitamente) cuando:

| Caso | Descripción | Por qué ignorar |
|------|-------------|-----------------|
| **Fallo transitorio resuelto** | El DDS falló por timeout o error de red, pero una re-ejecución manual funcionó. | El fix ya no tiene sentido. No hay error que corregir. |
| **Fallo en DDS de prueba** | El DDS era un `noop` o un DDS de validación de pipeline, no un cambio real. | Un fix sobre un noop no tiene valor operativo. |
| **Fix duplicado sobre fallo ya corregido manualmente** | El operador ya corrigió el problema a mano antes de que el ReactiveWorker generara el fix. | El fix es obsoleto. |
| **Fallo en proyecto archivado o pausado** | El proyecto ya no está activo. | No vale la pena revisar ni rechazar. Simplemente no consumir tiempo. |

**Acción práctica**: dejar el fix en `proposed` indefinidamente. No acumula deuda. Si el volumen de fixes ignorados crece, es señal de que el sistema genera demasiado ruido y hay que ajustar el FailureAnalyzer (decisión humana, no automatizable).

---

## 5. Checklist humana de revisión

Seguir en orden. Si algún punto falla, detenerse y rechazar.

| # | Pregunta | Sí / No |
|---|----------|---------|
| 1 | ¿El fix tiene `source_dds` y corresponde a un DDS que realmente falló? | |
| 2 | ¿El `error_context.error_message` describe un error que puedo verificar en `reports.json`? | |
| 3 | ¿El fallo original es de tipo `dds_error` (campos) o `exec_error` (determinista), y NO es `env_error`? | |
| 4 | ¿El `project` del fix coincide con el del DDS original? | |
| 5 | ¿`allowed_paths` del fix es igual o más restrictivo que el del DDS original? | |
| 6 | ¿`max_files_changed` ≤ 3 y `no_new_dependencies` = `true` y `no_refactor` = `true`? | |
| 7 | ¿Las `instructions` se limitan a corregir el error descrito, sin añadir funcionalidad? | |
| 8 | ¿No existe otro fix propuesto o aprobado para el mismo `source_dds`? | |
| 9 | ¿El DDS original sigue siendo relevante (proyecto activo, objetivo vigente)? | |
| 10 | ¿Entiendo qué va a hacer el fix sin necesidad de leer código fuente? | |

**10 SÍ → aprobar.**
**Cualquier NO → rechazar o ignorar según sección 3 y 4.**

---

## 6. Qué NO debe automatizarse todavía

Las siguientes decisiones deben permanecer exclusivamente humanas, sin importar cuánto "acierte" el sistema:

| Decisión | Por qué no automatizar |
|----------|----------------------|
| **Aprobar un FixDDS** | El sistema genera el fix y el sistema lo ejecutaría. Sin humano en el loop, un error en el generador se amplifica sin control. |
| **Decidir si un fallo merece fix o es transitorio** | Requiere contexto que el sistema no tiene: ¿se desplegó algo? ¿hubo cambio de infra? ¿el proyecto está pausado? |
| **Re-ejecutar un DDS que falló** | La re-ejecución puede tener efectos distintos a la primera ejecución si el estado del workspace cambió. |
| **Rechazar un fix y marcar el DDS original como irrecuperable** | Decisión de negocio: ¿se abandona ese cambio o se redefine manualmente? |
| **Aumentar `max_files_changed` o relajar constraints en un fix** | Ampliar scope es una decisión de riesgo. Cada ampliación debe ser explícita y justificada. |
| **Decidir que un tipo de fallo "ya no necesita revisión humana"** | La sobreconfianza es el principal riesgo de los sistemas semi-autónomos. Incluso si 50 fixes fueron correctos, el 51 puede ser destructivo. |
| **Generar un segundo fix cuando el primero falló** | Cadena de fixes (fix del fix) es una señal de que el DDS original está mal definido. Requiere intervención manual. |

---

## Notas operativas

### Dónde encontrar cada dato para la revisión

| Dato | Ubicación |
|------|-----------|
| DDS original | `node_dds/dds.json` → buscar por ID |
| Fix propuesto | `node_dds/dds.json` → buscar por `type: code_fix` y `source_dds` |
| Error original | `node_programmer/reports.json` → último entry con `status: failed` |
| Auditoría del fallo | `audits/contract_audit.jsonl` → buscar por `dds_id` en `payload_summary` y `level: error` |
| Categoría del error | En la auditoría: campo `error_detail`. En el mensaje al operador: línea "Categoría". |

### Flujo de revisión

```
DDS falla
  → reports.json registra status=failed
    → FailureAnalyzer detecta el fallo
      → FixDDSGenerator crea code_fix con status=proposed
        → Operador revisa con esta checklist
          → APROBAR: /dds_approve <fix_id>, luego /execute <fix_id>
          → RECHAZAR: /dds_reject <fix_id>
          → IGNORAR: no hacer nada
```

### Señales de que algo va mal en el sistema

- Se acumulan más de 5 fixes en `proposed` sin revisar → el sistema genera más ruido del que el operador puede absorber.
- Un fix aprobado y ejecutado produce otro fallo → el generador no está diagnosticando correctamente. Detener y revisar manualmente.
- Aparecen fixes con `source_dds` que no existe en `dds.json` → bug en el ReactiveWorker. No aprobar nada hasta investigar.
- Fixes con `allowed_paths` más amplio que el original → bug en FixDDSGenerator. Reportar.
