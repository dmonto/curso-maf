### Informe de cumplimiento: support_agent

- Framework: `agentic_compliance_baseline`
- Versión: `1.0`
- Entorno: `dev`
- Resultado global: `REVIEW_REQUIRED`
- Hallazgos bloqueantes: `5`

| Requisito | Dominio | Estado | Severidad | Controles pendientes | Evidencias pendientes |
|---|---|---|---|---|---|
| CMP-ID-001 | identity | partial | high | session_audit | - |
| CMP-ACC-001 | access | partial | critical | - | access_decision |
| CMP-DATA-001 | sensitive_data | partial | critical | - | sensitive_detection |
| CMP-RAG-001 | rag | partial | high | - | rag_retrieval |
| CMP-MODEL-001 | model_exposure | partial | high | - | model_exposure_decision |
| CMP-AUD-001 | audit | pass | high | - | - |
| CMP-RET-001 | retention | pass | medium | - | - |
| CMP-RISK-001 | risk | pass | high | - | - |

### Detalle

#### CMP-ID-001 - Identidad trazable por interacción

- Estado: `partial`
- Severidad si falta: `high`
- Controles presentes: `identity_context`
- Controles pendientes: `session_audit`
- Evidencias presentes: `session_started`
- Evidencias pendientes: `-`
- Recomendación: Completar controles pendientes y generar evidencias verificables antes de promover el agente a un entorno superior.

#### CMP-ACC-001 - Control de acceso granular

- Estado: `partial`
- Severidad si falta: `critical`
- Controles presentes: `access_policy`
- Controles pendientes: `-`
- Evidencias presentes: `-`
- Evidencias pendientes: `access_decision`
- Recomendación: Completar controles pendientes y generar evidencias verificables antes de promover el agente a un entorno superior.

#### CMP-DATA-001 - Protección de datos sensibles

- Estado: `partial`
- Severidad si falta: `critical`
- Controles presentes: `sensitive_data_guard`
- Controles pendientes: `-`
- Evidencias presentes: `user_message_received`
- Evidencias pendientes: `sensitive_detection`
- Recomendación: Completar controles pendientes y generar evidencias verificables antes de promover el agente a un entorno superior.

#### CMP-RAG-001 - RAG con fuentes trazables y filtradas

- Estado: `partial`
- Severidad si falta: `high`
- Controles presentes: `rag_filters`
- Controles pendientes: `-`
- Evidencias presentes: `-`
- Evidencias pendientes: `rag_retrieval`
- Recomendación: Completar controles pendientes y generar evidencias verificables antes de promover el agente a un entorno superior.

#### CMP-MODEL-001 - Control de exposición del modelo

- Estado: `partial`
- Severidad si falta: `high`
- Controles presentes: `model_gateway`
- Controles pendientes: `-`
- Evidencias presentes: `-`
- Evidencias pendientes: `model_exposure_decision`
- Recomendación: Completar controles pendientes y generar evidencias verificables antes de promover el agente a un entorno superior.

#### CMP-AUD-001 - Auditoría estructurada de interacciones

- Estado: `pass`
- Severidad si falta: `high`
- Controles presentes: `audit_events`
- Controles pendientes: `-`
- Evidencias presentes: `tool_call, assistant_response_generated`
- Evidencias pendientes: `-`
- Recomendación: Mantener control y evidencias en revisiones periódicas.

#### CMP-RET-001 - Política de retención aplicada

- Estado: `pass`
- Severidad si falta: `medium`
- Controles presentes: `retention_policy`
- Controles pendientes: `-`
- Evidencias presentes: `retention_purge`
- Evidencias pendientes: `-`
- Recomendación: Mantener control y evidencias en revisiones periódicas.

#### CMP-RISK-001 - Evaluación de riesgos documentada

- Estado: `pass`
- Severidad si falta: `high`
- Controles presentes: `risk_assessment`
- Controles pendientes: `-`
- Evidencias presentes: `reports/agent_risk_assessment.json`
- Evidencias pendientes: `-`
- Recomendación: Mantener control y evidencias en revisiones periódicas.
