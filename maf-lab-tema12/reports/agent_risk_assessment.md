### Informe de evaluación de riesgos: support_agent

- Entorno: `dev`
- Severidad máxima: `low`
- Score total: `1`
- Hallazgos: `1`

| ID | Categoría | Riesgo | Impacto | Prob. | Score | Severidad | Estado |
|---|---|---|---:|---:|---:|---|---|
| OK-001 | summary | Sin riesgos críticos detectados por reglas básicas | 1 | 1 | 1 | low | mitigated |

### Detalle de hallazgos

#### OK-001 - Sin riesgos críticos detectados por reglas básicas

Categoría: `summary`

Descripción: El perfil declara controles mínimos para identidad, acceso, RAG, datos sensibles, modelo, auditoría y retención.

Impacto: `1`

Probabilidad: `1`

Score: `1`

Severidad: `low`

Controles presentes:
- identity_context
- access_policy
- sensitive_data_guard
- audit_events
- retention_policy
- model_gateway

Recomendación: Revisar manualmente riesgos específicos del caso de uso.
