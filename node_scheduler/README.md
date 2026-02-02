# node_scheduler

Scheduler nocturno para ejecución automática de DDS aprobados.

## Propósito

Ejecuta DDS con `status="approved"` de forma secuencial y segura, sin intervención manual.

## Características

- **Ejecución secuencial**: Un DDS a la vez, nunca en paralelo
- **Stop on error**: Ante el primer fallo, detiene la cola
- **Estado persistido**: Actualiza DDS a `executed` o `failed`
- **Sin reintentos**: No reintenta DDS fallidos automáticamente
- **Determinista**: Ordena por ID antes de ejecutar

## Uso

### Desde Python

```python
from node_scheduler import Scheduler

scheduler = Scheduler()
result = scheduler.run()

print(result['status'])    # 'completed' | 'stopped_on_error'
print(result['executed'])  # Número de DDS ejecutados
print(result['failed'])    # Número de DDS fallidos
```

### Desde Cron

```bash
# Ejecutar diariamente a las 2 AM
0 2 * * * cd /path/to/ai_system && python3 -c "from node_scheduler import Scheduler; Scheduler().run()"
```

## Estados DDS

El scheduler transiciona estados de la siguiente forma:

- `approved` → `executed` (si ejecución exitosa)
- `approved` → `failed` (si ejecución falla)

**Importante**: Un DDS con `status="failed"` NO será reintentado por el scheduler.

## Comportamiento ante Errores

Si un DDS falla:
1. Se marca como `failed`
2. El scheduler se detiene inmediatamente
3. Los DDS restantes quedan como `approved`
4. Se logea el error completo

Esto permite revisar el problema antes de continuar.

## Logging

El scheduler registra:
- Inicio y fin de ejecución
- Cada DDS procesado
- Errores de ejecución
- Estado final del scheduler

Ver logs en `audits/` para auditoría completa.
