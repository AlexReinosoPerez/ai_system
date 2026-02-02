# node_worker

Worker Reactivo v1: Detección de fallos y generación de propuestas de corrección.

## Propósito

Monitorea ejecuciones fallidas y genera propuestas DDS `type=code_fix` **sin ejecución autónoma**.

## Componentes

### FailureAnalyzer
- Lee `node_programmer/reports.json`
- Detecta ejecuciones con `status=failure`
- Extrae información del fallo
- **NO ejecuta acciones**

### FixDDSGenerator
- Genera DDS `type=code_fix` desde información de fallo
- Hereda constraints del DDS fallido (más restrictivos)
- Crea `status=proposed` (nunca `approved`)
- **NO persiste directamente**

### ReactiveWorker
- Orquesta detección y generación de propuestas
- Verifica duplicados (no regenera si ya existe code_fix)
- Persiste en `dds.json` vía `DDSRegistry`
- **Stop-on-failure**: Se detiene tras primera propuesta

## Uso

### Invocación Manual

```python
from node_worker import ReactiveWorker

worker = ReactiveWorker()
result = worker.run()

print(result['status'])              # 'completed' | 'no_failures' | 'stopped_on_error'
print(result['proposals_generated']) # 0 o 1
print(result['message'])             # Descripción legible
```

### Desde CLI

```bash
python -c "from node_worker import ReactiveWorker; print(ReactiveWorker().run())"
```

### Cron (5 minutos después del Scheduler)

```bash
5 2 * * * cd /app && python -c "from node_worker import ReactiveWorker; ReactiveWorker().run()"
```

## Flujo de Ejecución

1. **Lee `reports.json`**: Obtiene última ejecución
2. **Si `status=failure`**: Procede a generar propuesta
3. **Si ya existe `code_fix`**: Termina sin duplicar
4. **Genera DDS `code_fix`**: Estructura completa según schema
5. **Persiste en `dds.json`**: Via `DDSRegistry.add_proposal()`
6. **Termina**: No ejecuta, no reintenta, no cicla

## Garantías

✅ **No ejecución autónoma**: Solo genera propuestas  
✅ **No aprobación automática**: Siempre `status=proposed`  
✅ **Stop-on-failure**: Un fallo = una propuesta máximo  
✅ **Idempotencia**: No regenera si ya existe propuesta  
✅ **Sin side effects**: Solo escribe a `dds.json`  

## Limitaciones v1

- ❌ No procesa múltiples fallos en una ejecución
- ❌ No reintenta automáticamente
- ❌ No analiza causa raíz más allá del error message
- ❌ No genera múltiples estrategias de corrección
- ❌ No ejecuta ni valida la corrección propuesta

## Ejemplo de Salida

### Éxito (Propuesta Generada)

```python
{
    'status': 'completed',
    'proposals_generated': 1,
    'failed_dds_id': 'DDS-20260202-CODE-001',
    'message': 'Code fix proposed: DDS-FIX-20260202-153045'
}
```

### Sin Fallos

```python
{
    'status': 'no_failures',
    'proposals_generated': 0,
    'failed_dds_id': None,
    'message': 'No failures detected in reports.json'
}
```

### Error

```python
{
    'status': 'stopped_on_error',
    'proposals_generated': 0,
    'failed_dds_id': 'DDS-20260202-CODE-001',
    'message': 'Error: Failed DDS not found: DDS-20260202-CODE-001'
}
```

## Integración con Sistema

- **Programmer**: Lee `reports.json` (pasivo)
- **Scheduler**: No interactúa directamente
- **DDS Registry**: Escribe propuestas `code_fix`
- **Telegram**: No expuesto (futuro v1.1)

## Testing

```bash
# Test de componentes individuales
python -m pytest node_worker/tests/

# Test de integración
python -c "
from node_worker import ReactiveWorker
worker = ReactiveWorker()
result = worker.run()
assert result['status'] in ['completed', 'no_failures', 'stopped_on_error']
print('✅ Worker functional')
"
```

## Logging

El worker registra:
- Inicio y fin de ejecución
- Fallos detectados
- Propuestas generadas
- Errores encontrados

Ver logs en `audits/` para trazabilidad completa.

## Especificaciones

- [Worker Reactivo v1 Spec](../docs/worker_reactive_v1.md)
- [DDS code_fix Schema](../docs/dds_code_fix_schema.md)
