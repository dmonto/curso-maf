from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

from src.vector.azure_ai_search_store import vector_search


Confidence = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ContextChunk:
    source_id: str
    title: str
    domain: str
    path: str
    score: float | None
    reason: str
    text: str


@dataclass(frozen=True)
class ContextPackage:
    original_query: str
    retrieval_query: str
    domain: str | None
    results_count: int
    confidence: Confidence
    context: list[ContextChunk]
    warnings: list[str]


DOMAIN_KEYWORDS: dict[str, set[str]] = {
    "vpn": {"vpn", "red privada", "acceso remoto", "cliente vpn", "teletrabajo"},
    "erp": {"erp", "sistema de gestión", "error 500", "aplicación corporativa"},
    "identity": {"contraseña", "password", "clave", "mfa", "autenticación", "identidad"},
    "teams": {"teams", "reunión", "chat corporativo", "microsoft teams"},
    "support": {"prioridad", "ticket", "incidencia", "sla", "p1", "p2", "p3"},
}


def infer_domain(user_query: str) -> str | None:
    normalized = user_query.lower()

    scores: dict[str, int] = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in normalized)

        if score > 0:
            scores[domain] = score

    if not scores:
        return None

    return max(scores.items(), key=lambda item: item[1])[0]


def rewrite_retrieval_query(
    user_query: str,
    conversation_summary: str | None = None,
    case_state: dict[str, Any] | None = None,
) -> str:
    parts = [user_query.strip()]

    if conversation_summary:
        parts.append(f"Contexto previo: {conversation_summary.strip()}")

    if case_state:
        service = case_state.get("servicio")
        operating_system = case_state.get("sistema_operativo")
        symptom = case_state.get("sintoma")
        affected_users = case_state.get("usuarios_afectados")
        tested_steps = case_state.get("pasos_probados")

        if service:
            parts.append(f"Servicio afectado: {service}")

        if operating_system:
            parts.append(f"Sistema operativo: {operating_system}")

        if symptom:
            parts.append(f"Síntoma: {symptom}")

        if affected_users:
            parts.append(f"Usuarios afectados: {affected_users}")

        if tested_steps:
            parts.append(f"Pasos ya probados: {tested_steps}")

    return " | ".join(parts)


def _score_boost_for_domain(result: dict[str, Any], inferred_domain: str | None) -> float:
    if not inferred_domain:
        return 0.0

    if result.get("domain") == inferred_domain:
        return 0.25

    return 0.0


def _score_boost_for_exact_terms(result: dict[str, Any], query: str) -> float:
    text = f"{result.get('title', '')} {result.get('text', '')}".lower()
    query_terms = set(re.findall(r"[a-záéíóúüñ0-9]{3,}", query.lower()))

    if not query_terms:
        return 0.0

    overlap = sum(1 for term in query_terms if term in text)
    return min(overlap * 0.03, 0.30)


def rerank_results(
    results: list[dict[str, Any]],
    query: str,
    inferred_domain: str | None,
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []

    for result in results:
        base_score = float(result.get("score") or 0.0)

        final_score = (
            base_score
            + _score_boost_for_domain(result, inferred_domain)
            + _score_boost_for_exact_terms(result, query)
        )

        enriched = dict(result)
        enriched["final_score"] = round(final_score, 4)

        ranked.append(enriched)

    ranked.sort(key=lambda item: item["final_score"], reverse=True)

    return ranked


def deduplicate_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_texts: set[str] = set()
    seen_sources: set[str] = set()
    output: list[dict[str, Any]] = []

    for result in results:
        normalized_text = re.sub(r"\s+", " ", result["text"].lower()).strip()
        source_id = result["source_id"]

        text_signature = normalized_text[:180]

        if text_signature in seen_texts:
            continue

        if source_id in seen_sources and len(output) >= 2:
            continue

        seen_texts.add(text_signature)
        seen_sources.add(source_id)
        output.append(result)

    return output


def _make_reason(result: dict[str, Any], inferred_domain: str | None) -> str:
    if inferred_domain and result.get("domain") == inferred_domain:
        return f"Coincide con el dominio detectado: {inferred_domain}."

    return "Resultado recuperado por similitud semántica o coincidencia textual."


def _estimate_confidence(results: list[dict[str, Any]]) -> Confidence:
    if not results:
        return "low"

    best_score = float(results[0].get("final_score") or results[0].get("score") or 0.0)

    if len(results) >= 2 and best_score >= 0.75:
        return "high"

    if best_score >= 0.35:
        return "medium"

    return "low"


def build_context_package(
    user_query: str,
    conversation_summary: str | None = None,
    case_state: dict[str, Any] | None = None,
    explicit_domain: str | None = None,
    top_k_candidates: int = 8,
    max_context_chunks: int = 4,
    hybrid: bool = True,
) -> dict[str, Any]:
    inferred_domain = explicit_domain or infer_domain(user_query)

    retrieval_query = rewrite_retrieval_query(
        user_query=user_query,
        conversation_summary=conversation_summary,
        case_state=case_state,
    )

    candidates = vector_search(
        query=retrieval_query,
        domain=inferred_domain,
        top_k=top_k_candidates,
        hybrid=hybrid,
    )

    ranked = rerank_results(
        results=candidates,
        query=retrieval_query,
        inferred_domain=inferred_domain,
    )

    deduplicated = deduplicate_results(ranked)
    selected = deduplicated[:max_context_chunks]

    context_chunks = [
        ContextChunk(
            source_id=result["source_id"],
            title=result["title"],
            domain=result["domain"],
            path=result["path"],
            score=result.get("score"),
            reason=_make_reason(result, inferred_domain),
            text=result["text"],
        )
        for result in selected
    ]

    warnings: list[str] = []

    if not selected:
        warnings.append("No se han recuperado documentos suficientemente relevantes.")

    if inferred_domain is None:
        warnings.append("No se ha podido inferir un dominio documental claro.")

    confidence = _estimate_confidence(selected)

    package = ContextPackage(
        original_query=user_query,
        retrieval_query=retrieval_query,
        domain=inferred_domain,
        results_count=len(selected),
        confidence=confidence,
        context=context_chunks,
        warnings=warnings,
    )

    return {
        **asdict(package),
        "context": [asdict(chunk) for chunk in context_chunks],
    }