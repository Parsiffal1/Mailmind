from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .models import EmailRecord, ExtractedTask, ExtractionResult, Priority
from .privacy import PiiConfig, PiiSession


DEFAULT_SYSTEM_PROMPT = """You extract tasks and deadlines from email.
Return only JSON with keys:
has_action, tasks, deadlines, priority, requires_reply, reason.
Be conservative and create tasks only for clear user-specific required actions."""


class TaskExtractor:
    def extract(self, email: EmailRecord) -> ExtractionResult:
        raise NotImplementedError


class MockExtractor(TaskExtractor):
    """Offline extractor for demos and tests when no LLM key is configured."""

    def extract(self, email: EmailRecord) -> ExtractionResult:
        text = f"{email.subject or ''}\n{email.body}".strip()
        action_words = ("deadline", "due", "submit", "complete", "reply", "action required", "please")
        has_action = any(word in text.lower() for word in action_words)
        if not has_action:
            return ExtractionResult(has_action=False, priority=Priority.low, reason="No action language detected.")

        needs_review = any(word in text.lower() for word in ("asap", "end of week", "soon"))
        due_at = _simple_due_date(text)
        task = ExtractedTask(
            description=_summarize_task(email),
            due_at=due_at,
            priority=Priority.high if "urgent" in text.lower() or "deadline" in text.lower() else Priority.medium,
            requires_reply="reply" in text.lower(),
            needs_review=needs_review or due_at is None,
        )
        return ExtractionResult(
            has_action=True,
            tasks=[task],
            deadlines=[],
            priority=task.priority,
            requires_reply=task.requires_reply,
            reason="Mock extractor found action-oriented language.",
        )


class AnthropicExtractor(TaskExtractor):
    def __init__(self, api_key: str, model: str, pii_config: PiiConfig | None = None):
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover - exercised in configured runtime
            raise RuntimeError("Install Anthropic dependency with `pip install -r requirements.txt`.") from exc
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.pii_config = pii_config or PiiConfig.from_env()

    def extract(self, email: EmailRecord) -> ExtractionResult:
        pii_session = PiiSession(self.pii_config)
        safe_email = pii_session.anonymize_email(email)
        prompt = _format_email_prompt(safe_email)
        system_prompt = load_system_prompt()
        last_error: Exception | None = None
        for attempt in range(2):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1200,
                temperature=0,
                system=system_prompt if attempt == 0 else system_prompt + "\nFix the previous invalid JSON/schema.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = _message_text(response)
            try:
                return _rehydrate_extraction_result(
                    ExtractionResult.from_llm_json(_json_from_text(text)),
                    pii_session,
                )
            except Exception as exc:
                last_error = exc
                prompt = f"Previous response was invalid: {exc}\nEmail:\n{_format_email_prompt(safe_email)}"
        raise ValueError(f"LLM extraction failed schema validation: {last_error}")


def make_extractor(provider: str, api_key: str | None, model: str, pii_config: PiiConfig | None = None) -> TaskExtractor:
    if provider == "mock" or not api_key:
        return MockExtractor()
    if provider == "anthropic":
        return AnthropicExtractor(api_key=api_key, model=model, pii_config=pii_config)
    raise ValueError(f"Unsupported LLM provider: {provider}")


def load_system_prompt() -> str:
    prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "task_extraction.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return DEFAULT_SYSTEM_PROMPT


def _format_email_prompt(email: EmailRecord) -> str:
    attachments = ", ".join(a.filename for a in email.attachments) or "none"
    return (
        f"Sender: {email.sender}\n"
        f"Subject: {email.subject or ''}\n"
        f"Received at: {email.received_at.isoformat() if email.received_at else 'unknown'}\n"
        f"Attachments: {attachments}\n\n"
        f"Body:\n{email.body[:12000]}"
    )


def _message_text(response) -> str:
    parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _json_from_text(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return json.loads(text[start : end + 1])


def _rehydrate_extraction_result(result: ExtractionResult, pii_session: PiiSession) -> ExtractionResult:
    if not pii_session.rehydrating:
        return result
    return result.model_copy(
        update={
            "tasks": [
                task.model_copy(
                    update={
                        "description": pii_session.rehydrate_text(task.description),
                    }
                )
                for task in result.tasks
            ],
            "deadlines": [pii_session.rehydrate_text(deadline) for deadline in result.deadlines],
            "reason": pii_session.rehydrate_text(result.reason) if result.reason else result.reason,
        }
    )


def _simple_due_date(text: str) -> datetime | None:
    match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    return datetime(year, month, day, 23, 59, tzinfo=timezone.utc)


def _summarize_task(email: EmailRecord) -> str:
    subject = (email.subject or "Email task").strip()
    return f"Review and act on: {subject}"[:240]
