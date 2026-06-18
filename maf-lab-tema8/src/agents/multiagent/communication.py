from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class MessageType(StrEnum):
    TASK_REQUEST = "task_request"
    TASK_RESULT = "task_result"
    CLARIFICATION_REQUEST = "clarification_request"
    VALIDATION_REQUEST = "validation_request"
    CONFLICT_REPORT = "conflict_report"
    ERROR = "error"


class MessageStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class InterAgentMessage:
    sender: str
    recipient: str
    message_type: MessageType
    payload: dict[str, Any]

    conversation_id: str
    correlation_id: str
    task_id: str | None = None
    message_id: str = field(default_factory=lambda: str(uuid4()))
    status: MessageStatus = MessageStatus.PENDING
    created_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    constraints: list[str] = field(default_factory=list)
    expected_output: list[str] = field(default_factory=list)


class InMemoryMailbox:
    def __init__(self) -> None:
        self._messages: list[InterAgentMessage] = []

    def publish(self, message: InterAgentMessage) -> InterAgentMessage:
        message.status = MessageStatus.SENT
        self._messages.append(message)
        return message

    def complete(self, message: InterAgentMessage) -> InterAgentMessage:
        message.status = MessageStatus.COMPLETED
        self._messages.append(message)
        return message

    def fail(
        self,
        *,
        original_message: InterAgentMessage,
        error: str,
        sender: str,
    ) -> InterAgentMessage:
        failure = InterAgentMessage(
            sender=sender,
            recipient=original_message.sender,
            message_type=MessageType.ERROR,
            conversation_id=original_message.conversation_id,
            correlation_id=original_message.correlation_id,
            task_id=original_message.task_id,
            payload={
                "original_message_id": original_message.message_id,
                "error": error,
            },
            constraints=[],
            expected_output=["error"],
            status=MessageStatus.FAILED,
        )
        self._messages.append(failure)
        return failure

    def by_correlation_id(self, correlation_id: str) -> list[InterAgentMessage]:
        return [
            message
            for message in self._messages
            if message.correlation_id == correlation_id
        ]

    def trace_as_text(self, correlation_id: str) -> str:
        messages = self.by_correlation_id(correlation_id)

        lines = []
        for message in messages:
            lines.append(
                f"[{message.status}] "
                f"{message.message_type} "
                f"{message.sender} -> {message.recipient} "
                f"task={message.task_id}"
            )

        return "\n".join(lines)