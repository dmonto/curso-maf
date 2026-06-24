from __future__ import annotations

from typing import Any

from src.contracts.registry import (
    ContractValidationError,
    validate_event_payload,
)


class ContractAwareEventPublisher:
    """
    Decorador de EventPublisher.

    Valida el payload antes de delegar en el publicador real.
    """

    def __init__(self, inner_publisher: Any) -> None:
        self.inner_publisher = inner_publisher

    def publish(self, event_type: str, payload: dict, correlation_id: str) -> None:
        try:
            validate_event_payload(
                event_type=event_type,
                payload=payload,
            )
        except ContractValidationError:
            raise

        self.inner_publisher.publish(
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
        )