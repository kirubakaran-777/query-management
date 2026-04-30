from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable


class QueryStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_CUSTOMER = "WAITING_CUSTOMER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

    @classmethod
    def from_value(cls, value: str) -> "QueryStatus":
        normalized = value.strip().upper()
        for status in cls:
            if status.value == normalized:
                return status
        raise ValueError(f"Unknown status '{value}'. Allowed: {', '.join(s.value for s in cls)}")


@dataclass
class Response:
    message: str
    author: str | None
    created_at: str

    @classmethod
    def create(cls, message: str, author: str | None = None) -> "Response":
        return cls(message=message, author=author, created_at=_utc_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "author": self.author,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Response":
        return cls(
            message=payload["message"],
            author=payload.get("author"),
            created_at=payload["created_at"],
        )


@dataclass
class StatusChange:
    from_status: str
    to_status: str
    note: str | None
    changed_at: str

    @classmethod
    def create(
        cls,
        from_status: QueryStatus,
        to_status: QueryStatus,
        note: str | None = None,
    ) -> "StatusChange":
        return cls(
            from_status=from_status.value,
            to_status=to_status.value,
            note=note,
            changed_at=_utc_now(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_status": self.from_status,
            "to_status": self.to_status,
            "note": self.note,
            "changed_at": self.changed_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StatusChange":
        return cls(
            from_status=payload["from_status"],
            to_status=payload["to_status"],
            note=payload.get("note"),
            changed_at=payload["changed_at"],
        )


@dataclass
class Query:
    query_id: str
    customer: str
    subject: str
    description: str
    status: QueryStatus
    priority: str
    assignee: str | None
    created_at: str
    updated_at: str
    responses: list[Response] = field(default_factory=list)
    history: list[StatusChange] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        query_id: str,
        customer: str,
        subject: str,
        description: str,
        priority: str,
        assignee: str | None = None,
    ) -> "Query":
        now = _utc_now()
        return cls(
            query_id=query_id,
            customer=customer,
            subject=subject,
            description=description,
            status=QueryStatus.NEW,
            priority=priority,
            assignee=assignee,
            created_at=now,
            updated_at=now,
            responses=[],
            history=[],
        )

    def add_response(self, message: str, author: str | None = None) -> None:
        self.responses.append(Response.create(message, author))
        self.touch()

    def update_status(self, new_status: QueryStatus, note: str | None = None) -> None:
        self.history.append(StatusChange.create(self.status, new_status, note))
        self.status = new_status
        self.touch()

    def touch(self) -> None:
        self.updated_at = _utc_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "customer": self.customer,
            "subject": self.subject,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "assignee": self.assignee,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "responses": [response.to_dict() for response in self.responses],
            "history": [entry.to_dict() for entry in self.history],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Query":
        return cls(
            query_id=payload["query_id"],
            customer=payload["customer"],
            subject=payload["subject"],
            description=payload["description"],
            status=QueryStatus.from_value(payload["status"]),
            priority=payload.get("priority", "MEDIUM"),
            assignee=payload.get("assignee"),
            created_at=payload["created_at"],
            updated_at=payload.get("updated_at", payload["created_at"]),
            responses=[Response.from_dict(item) for item in payload.get("responses", [])],
            history=[StatusChange.from_dict(item) for item in payload.get("history", [])],
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_status_list() -> Iterable[str]:
    return [status.value for status in QueryStatus]
