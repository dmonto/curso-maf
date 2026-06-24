### Resumen de análisis

**Decisión final:** `BLOCKED`

| Severidad | Fuente | Hallazgo | Recomendación |
|---|---|---|---|
| `critical` | `drift` | Drift crítico detectado. critical_findings=3, total_findings=3 | Investiga cambios recientes en modelo, prompt, datos, tools o distribución de casos. |
| `critical` | `quality` | Pass rate por debajo del mínimo. pass_rate=0.5, mínimo=0.9 | Revisa los casos fallidos y separa si el problema está en prompt, tools, modelo o criterios de evaluación. |
| `critical` | `quality` | Quality score medio insuficiente. average_quality_score=0.724, mínimo=0.8 | Analiza qué métrica baja más: relevance, completeness, groundedness, safety o tool_accuracy. |
| `critical` | `quality` | groundedness por debajo del umbral. groundedness.avg=0.7 | Revisa grounding, descripciones de tools, contexto y casos donde el agente inventa o usa mal capacidades. |
| `warning` | `regression` | Hay regresiones no críticas. total_findings=4 | Revisa si la caída es aceptable antes de promover el cambio. |
| `info` | `model_comparison` | Modelo recomendado disponible. recommended_model=chat_fast | Valida si el modelo recomendado debe aplicarse como default o solo como fallback para casos críticos. |
| `info` | `test_suite` | La suite principal ha pasado. No hay fallos requeridos en run_test_suite.py. | Puedes revisar métricas de calidad y drift para decidir si conviene mejorar el agente. |

### Lectura recomendada

El cambio no debería promoverse. Corrige primero los findings críticos, especialmente los relacionados con safety, groundedness, tools o regresión.
