### Gate de gobierno de pipeline: maf_support_agent_pipeline

- Entorno objetivo: `prod`
- Estado: `fail`
- Checks ejecutados: `9`
- Bloqueantes: `1`

| Check | Estado | Severidad | Título | Recomendación |
|---|---|---|---|---|
| PIPE-FILE-001 | pass | info | Fichero requerido: config/agent_risk_profile.json | Sin acción. |
| PIPE-FILE-001 | pass | info | Fichero requerido: config/retention_policies.json | Sin acción. |
| PIPE-FILE-001 | pass | info | Fichero requerido: reports/evaluation_summary.json | Sin acción. |
| PIPE-EVAL-002 | pass | info | Número mínimo de casos de evaluación | Sin acción. |
| PIPE-EVAL-003 | pass | info | Tasa mínima de éxito | Sin acción. |
| PIPE-RISK-002 | pass | low | Severidad máxima de riesgo | Sin acción. |
| PIPE-CMP-002 | fail | critical | Resultado de cumplimiento | Completa controles y evidencias pendientes. |
| PIPE-MODEL-002 | pass | info | Alias de modelo permitidos por entorno | Sin acción. |
| PIPE-RET-001 | pass | info | Retención de transcripciones completas | Sin acción. |

### Detalle de checks

#### PIPE-FILE-001 - Fichero requerido: config/agent_risk_profile.json

- Estado: `pass`
- Severidad: `info`
- Descripción: El fichero requerido existe.
- Recomendación: Sin acción.

Metadata:
```json
{
  "file_path": "config/agent_risk_profile.json"
}
```

#### PIPE-FILE-001 - Fichero requerido: config/retention_policies.json

- Estado: `pass`
- Severidad: `info`
- Descripción: El fichero requerido existe.
- Recomendación: Sin acción.

Metadata:
```json
{
  "file_path": "config/retention_policies.json"
}
```

#### PIPE-FILE-001 - Fichero requerido: reports/evaluation_summary.json

- Estado: `pass`
- Severidad: `info`
- Descripción: El fichero requerido existe.
- Recomendación: Sin acción.

Metadata:
```json
{
  "file_path": "reports/evaluation_summary.json"
}
```

#### PIPE-EVAL-002 - Número mínimo de casos de evaluación

- Estado: `pass`
- Severidad: `info`
- Descripción: Casos ejecutados: 12. Mínimo requerido: 10.
- Recomendación: Sin acción.

Metadata:
```json
{
  "cases_run": 12,
  "min_cases_run": 10
}
```

#### PIPE-EVAL-003 - Tasa mínima de éxito

- Estado: `pass`
- Severidad: `info`
- Descripción: Pass rate: 91.67%. Mínimo requerido: 80.00%.
- Recomendación: Sin acción.

Metadata:
```json
{
  "pass_rate": 0.9167,
  "min_pass_rate": 0.8
}
```

#### PIPE-RISK-002 - Severidad máxima de riesgo

- Estado: `pass`
- Severidad: `low`
- Descripción: Severidad máxima detectada: low.
- Recomendación: Sin acción.

Metadata:
```json
{
  "highest_severity": "low"
}
```

#### PIPE-CMP-002 - Resultado de cumplimiento

- Estado: `fail`
- Severidad: `critical`
- Descripción: Hallazgos bloqueantes: 5.
- Recomendación: Completa controles y evidencias pendientes.

Metadata:
```json
{
  "blocking_findings": 5
}
```

#### PIPE-MODEL-002 - Alias de modelo permitidos por entorno

- Estado: `pass`
- Severidad: `info`
- Descripción: Todos los alias expuestos están permitidos.
- Recomendación: Sin acción.

Metadata:
```json
{
  "allowed_model_aliases": [
    "chat_default",
    "chat_fast"
  ],
  "exposed_model_aliases": [
    "chat_default",
    "chat_fast"
  ],
  "not_allowed": []
}
```

#### PIPE-RET-001 - Retención de transcripciones completas

- Estado: `pass`
- Severidad: `info`
- Descripción: El perfil no conserva transcripciones completas en este entorno.
- Recomendación: Sin acción.

Metadata:
```json
{
  "stores_full_transcripts": false,
  "allow_full_transcripts": false
}
```
