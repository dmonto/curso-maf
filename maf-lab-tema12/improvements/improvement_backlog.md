### Backlog de mejora continua

| ID | Prioridad | Severidad | Owner | Mejora | Estado |
|---|---:|---|---|---|---|
| IMP-002 | 37.5 | `critical` | `agent-owner` | Pass rate por debajo del mínimo | `proposed` |
| IMP-003 | 37.5 | `critical` | `agent-owner` | Quality score medio insuficiente | `proposed` |
| IMP-004 | 37.5 | `critical` | `rag/context` | groundedness por debajo del umbral | `proposed` |
| IMP-006 | 37.5 | `critical` | `ops` | Drift crítico detectado | `proposed` |
| IMP-005 | 13.5 | `warning` | `release-owner` | Hay regresiones no críticas | `proposed` |
| IMP-006 | 13.5 | `warning` | `prompt` | Mejorar completitud de respuestas | `proposed` |
| IMP-007 | 2.0 | `info` | `architecture` | Revisar routing de modelos según benchmark | `proposed` |

### Detalle de mejoras

#### IMP-002 · Pass rate por debajo del mínimo

**Owner:** `agent-owner`  
**Fuente:** `quality`  
**Severidad:** `critical`  
**Prioridad:** `37.5`

**Hipótesis:** Si corregimos el problema detectado en quality, mejorará la calidad del agente sin introducir regresiones críticas.

**Cambio propuesto:** Revisa los casos fallidos y separa si el problema está en prompt, tools, modelo o criterios de evaluación.

**Criterios de aceptación:**
- La suite offline pasa correctamente.
- La evaluación online no introduce fallos críticos.
- No aparece regresión crítica frente a baseline.

#### IMP-003 · Quality score medio insuficiente

**Owner:** `agent-owner`  
**Fuente:** `quality`  
**Severidad:** `critical`  
**Prioridad:** `37.5`

**Hipótesis:** Si corregimos el problema detectado en quality, mejorará la calidad del agente sin introducir regresiones críticas.

**Cambio propuesto:** Analiza qué métrica baja más: relevance, completeness, groundedness, safety o tool_accuracy.

**Criterios de aceptación:**
- La suite offline pasa correctamente.
- La evaluación online no introduce fallos críticos.
- No aparece regresión crítica frente a baseline.

#### IMP-004 · groundedness por debajo del umbral

**Owner:** `rag/context`  
**Fuente:** `quality`  
**Severidad:** `critical`  
**Prioridad:** `37.5`

**Hipótesis:** Si corregimos el problema detectado en quality, mejorará la calidad del agente sin introducir regresiones críticas.

**Cambio propuesto:** Revisa grounding, descripciones de tools, contexto y casos donde el agente inventa o usa mal capacidades.

**Criterios de aceptación:**
- La suite offline pasa correctamente.
- La evaluación online no introduce fallos críticos.
- No aparece regresión crítica frente a baseline.
- groundedness.avg >= 0.85.

#### IMP-006 · Drift crítico detectado

**Owner:** `ops`  
**Fuente:** `drift`  
**Severidad:** `critical`  
**Prioridad:** `37.5`

**Hipótesis:** Si corregimos el problema detectado en drift, mejorará la calidad del agente sin introducir regresiones críticas.

**Cambio propuesto:** Investiga cambios recientes en modelo, prompt, datos, tools o distribución de casos.

**Criterios de aceptación:**
- La suite offline pasa correctamente.
- La evaluación online no introduce fallos críticos.
- No aparece regresión crítica frente a baseline.

#### IMP-005 · Hay regresiones no críticas

**Owner:** `release-owner`  
**Fuente:** `regression`  
**Severidad:** `warning`  
**Prioridad:** `13.5`

**Hipótesis:** Si corregimos el problema detectado en regression, mejorará la calidad del agente sin introducir regresiones críticas.

**Cambio propuesto:** Revisa si la caída es aceptable antes de promover el cambio.

**Criterios de aceptación:**
- La suite offline pasa correctamente.
- La evaluación online no introduce fallos críticos.
- No aparece regresión crítica frente a baseline.

#### IMP-006 · Mejorar completitud de respuestas

**Owner:** `prompt`  
**Fuente:** `quality_metrics`  
**Severidad:** `warning`  
**Prioridad:** `13.5`

**Hipótesis:** La métrica completeness está en 0.45. Si ajustamos la capa prompt, debería superar 0.85.

**Cambio propuesto:** Añadir checklist mínimo de respuesta para incidencias de soporte.

**Criterios de aceptación:**
- completeness.avg >= 0.85.
- average_quality_score >= 0.80.
- Sin regresiones críticas.

#### IMP-007 · Revisar routing de modelos según benchmark

**Owner:** `architecture`  
**Fuente:** `model_comparison`  
**Severidad:** `info`  
**Prioridad:** `2.0`

**Hipótesis:** El benchmark recomienda chat_fast. Usar routing por tipo de tarea puede mejorar coste, latencia o calidad.

**Cambio propuesto:** Documentar qué modelo usar para consulta simple, borrador de ticket, acción sensible y fallback.

**Criterios de aceptación:**
- README actualizado con tabla de routing.
- check_model_comparison.py ejecutado sin fallos críticos.
- No hay regresiones tras aplicar el cambio.
