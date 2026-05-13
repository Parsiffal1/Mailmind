from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Priority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class AttachmentMeta(BaseModel):
    id: str
    filename: str
    mime_type: str | None = None
    size: int | None = None


class EmailRecord(BaseModel):
    id: str
    sender: str
    subject: str | None = None
    received_at: datetime | None = None
    body: str = ""
    attachments: list[AttachmentMeta] = Field(default_factory=list)


class ExtractedDeadline(BaseModel):
    task: str
    due_at: datetime | None = None
    raw_text: str | None = None
    needs_review: bool = False


class ExtractedTask(BaseModel):
    description: str
    due_at: datetime | None = None
    priority: Priority = Priority.medium
    requires_reply: bool = False
    needs_review: bool = False

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("description cannot be empty")
        return value


class ExtractionResult(BaseModel):
    has_action: bool = False
    tasks: list[ExtractedTask] = Field(default_factory=list)
    deadlines: list[ExtractedDeadline] = Field(default_factory=list)
    priority: Priority = Priority.low
    requires_reply: bool = False
    reason: str = ""

    @classmethod
    def from_llm_json(cls, payload: dict[str, Any]) -> "ExtractionResult":
        return cls.model_validate(payload)

