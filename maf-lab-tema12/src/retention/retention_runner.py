from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.retention.classifier import classify_audit_event
from src.retention.policy import RetentionAction, RetentionPolicy, load_retention_policies


@dataclass(frozen=True)
class RetentionDecision:
    line_number: int
    event_type: str
    policy_name: str
    action: RetentionAction
    age_days: int
    expired: bool
    legal_hold: bool
    reason: str


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def event_age_days(event: dict[str, Any], now: datetime) -> int:
    timestamp = parse_timestamp(event["timestamp_utc"])

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    return max(0, (now - timestamp).days)


def has_legal_hold(event: dict[str, Any]) -> bool:
    metadata = event.get("metadata") or {}
    return bool(metadata.get("legal_hold"))


def make_retention_plan(
    *,
    input_path: Path,
    policies: dict[str, RetentionPolicy] | None = None,
    now: datetime | None = None,
) -> list[RetentionDecision]:
    policies = policies or load_retention_policies()
    now = now or datetime.now(timezone.utc)

    decisions: list[RetentionDecision] = []

    if not input_path.exists():
        return decisions

    with input_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            event = json.loads(line)
            policy_name = classify_audit_event(event)
            policy = policies[policy_name]
            age = event_age_days(event, now)
            legal_hold = has_legal_hold(event)

            expired = age >= policy.retention_days and not legal_hold

            if policy.action == RetentionAction.NEVER_STORE:
                expired = True

            reason = (
                "legal_hold_active"
                if legal_hold
                else "retention_expired"
                if expired
                else "within_retention"
            )

            decisions.append(
                RetentionDecision(
                    line_number=line_number,
                    event_type=event.get("event_type", "unknown"),
                    policy_name=policy_name,
                    action=policy.action,
                    age_days=age,
                    expired=expired,
                    legal_hold=legal_hold,
                    reason=reason,
                )
            )

    return decisions


def compact_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    Conserva solo campos mínimos.

    Útil para memoria o eventos antiguos donde queremos mantener evidencia
    sin conservar contenido operativo.
    """
    return {
        "timestamp_utc": event.get("timestamp_utc"),
        "event_type": event.get("event_type"),
        "run_id": event.get("run_id"),
        "session_id": event.get("session_id"),
        "turn_id": event.get("turn_id"),
        "tenant_id": event.get("tenant_id"),
        "user_id_hash": event.get("user_id_hash") or event.get("user_id"),
        "agent_name": event.get("agent_name"),
        "action": event.get("action"),
        "allowed": event.get("allowed"),
        "retention_compacted": True,
    }


def apply_retention(
    *,
    input_path: Path,
    output_path: Path,
    archive_path: Path,
    purge_log_path: Path,
    policies: dict[str, RetentionPolicy] | None = None,
    dry_run: bool = True,
) -> list[RetentionDecision]:
    policies = policies or load_retention_policies()
    decisions = make_retention_plan(input_path=input_path, policies=policies)

    if dry_run:
        return decisions

    output_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    purge_log_path.parent.mkdir(parents=True, exist_ok=True)

    archive_records: list[dict[str, Any]] = []
    kept_records: list[dict[str, Any]] = []
    purge_records: list[dict[str, Any]] = []

    decision_by_line = {decision.line_number: decision for decision in decisions}

    with input_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            event = json.loads(line)
            decision = decision_by_line[line_number]

            if not decision.expired:
                kept_records.append(event)
                continue

            if decision.action == RetentionAction.DELETE:
                purge_records.append(
                    {
                        "line_number": line_number,
                        "event_type": decision.event_type,
                        "policy_name": decision.policy_name,
                        "action": "deleted",
                        "reason": decision.reason,
                        "purged_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                )
                continue

            if decision.action == RetentionAction.ARCHIVE:
                archive_records.append(compact_event(event))
                purge_records.append(
                    {
                        "line_number": line_number,
                        "event_type": decision.event_type,
                        "policy_name": decision.policy_name,
                        "action": "archived_compacted",
                        "reason": decision.reason,
                        "purged_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                )
                continue

            if decision.action == RetentionAction.COMPACT:
                kept_records.append(compact_event(event))
                purge_records.append(
                    {
                        "line_number": line_number,
                        "event_type": decision.event_type,
                        "policy_name": decision.policy_name,
                        "action": "compacted",
                        "reason": decision.reason,
                        "purged_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                )
                continue

            if decision.action == RetentionAction.NEVER_STORE:
                purge_records.append(
                    {
                        "line_number": line_number,
                        "event_type": decision.event_type,
                        "policy_name": decision.policy_name,
                        "action": "removed_never_store",
                        "reason": decision.reason,
                        "purged_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                )
                continue

            kept_records.append(event)

    with output_path.open("w", encoding="utf-8") as file:
        for record in kept_records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    with archive_path.open("a", encoding="utf-8") as file:
        for record in archive_records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    with purge_log_path.open("a", encoding="utf-8") as file:
        for record in purge_records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    shutil.copy2(input_path, input_path.with_suffix(".jsonl.bak"))

    return decisions