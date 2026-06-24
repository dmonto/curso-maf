---
title: Erp Outage
domain: rag
tenant_id: curso-maf
visibility: internal
classification: internal
allowed_groups: support-l1,support-l2
allowed_users: 
denied_groups: 
denied_users: 
owner: it-support
source_type: azure_blob
source_id: blob://curso-ia-blob/rag/erp_outage.md
source_path: rag/erp_outage.md
source_last_modified_utc: 2026-06-18T08:55:04+00:00
---

# Erp Outage

---
title: Procedimiento ante caída del ERP
domain: erp
visibility: internal
---

# Procedimiento ante caída del ERP

Si el ERP no responde, se debe comprobar primero si hay alerta activa de infraestructura.

Si el error es 500 para varios usuarios, se debe escalar a aplicaciones corporativas.

Si afecta a un solo usuario, se debe validar sesión, navegador, permisos y posibles bloqueos de identidad.
