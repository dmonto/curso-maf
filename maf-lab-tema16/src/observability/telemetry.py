from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import metrics, trace


logger = logging.getLogger("maf.telemetry")


@dataclass(frozen=True)
class TelemetryConfig:
    enabled: bool
    service_name: str
    connection_string: str | None


def get_telemetry_config() -> TelemetryConfig:
    enabled = os.getenv("TELEMETRY_ENABLED", "true").lower() == "true"

    return TelemetryConfig(
        enabled=enabled,
        service_name=os.getenv("OTEL_SERVICE_NAME", "maf-support-agent"),
        connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
    )


def configure_telemetry() -> None:
    config = get_telemetry_config()

    if not config.enabled:
        logger.info("telemetry_disabled")
        return

    if not config.connection_string:
        logger.warning(
            "telemetry_enabled_but_missing_connection_string"
        )
        return

    os.environ["OTEL_SERVICE_NAME"] = config.service_name

    configure_azure_monitor(
        connection_string=config.connection_string,
    )

    logger.info(
        "telemetry_configured service_name=%s",
        config.service_name,
    )


tracer = trace.get_tracer("maf.agent.runtime")
meter = metrics.get_meter("maf.agent.runtime")

agent_runs_counter = meter.create_counter(
    name="agent_runs_total",
    description="Número total de ejecuciones del agente.",
    unit="1",
)

agent_errors_counter = meter.create_counter(
    name="agent_errors_total",
    description="Número total de errores del agente.",
    unit="1",
)

agent_duration_histogram = meter.create_histogram(
    name="agent_duration_ms",
    description="Duración de ejecuciones del agente.",
    unit="ms",
)

tool_calls_counter = meter.create_counter(
    name="agent_tool_calls_total",
    description="Número total de llamadas a tools.",
    unit="1",
)

rag_retrieval_counter = meter.create_counter(
    name="agent_rag_retrievals_total",
    description="Número total de recuperaciones RAG.",
    unit="1",
)