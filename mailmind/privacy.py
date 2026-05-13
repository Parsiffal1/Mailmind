from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from .models import EmailRecord


@dataclass(frozen=True)
class PiiConfig:
    enabled: bool = True
    mode: str = "rehydrated"
    redact_names: bool = True
    preserve_dates: bool = True
    redact_logs: bool = True

    @classmethod
    def from_env(cls) -> "PiiConfig":
        mode = os.getenv("MAILMIND_PII_MODE", "rehydrated").strip().lower()
        if mode == "llm_only":
            mode = "rehydrated"
        return cls(
            enabled=_bool_env("MAILMIND_PII_ENABLED", True),
            mode=mode,
            redact_names=_bool_env("MAILMIND_PII_REDACT_NAMES", True),
            preserve_dates=_bool_env("MAILMIND_PII_PRESERVE_DATES", True),
            redact_logs=_bool_env("MAILMIND_PII_REDACT_LOGS", True),
        )


@dataclass(frozen=True)
class RedactionResult:
    text: str
    counts_by_type: dict[str, int] = field(default_factory=dict)
    placeholder_to_value: dict[str, str] = field(default_factory=dict)

    @property
    def redacted_types(self) -> list[str]:
        return sorted(key for key, count in self.counts_by_type.items() if count > 0)


class PiiSession:
    def __init__(self, config: PiiConfig | None = None):
        self.config = config or PiiConfig.from_env()
        self.placeholder_to_value: dict[str, str] = {}
        self._value_to_placeholder: dict[tuple[str, str], str] = {}
        self._counters: dict[str, int] = {}

    @property
    def active(self) -> bool:
        return self.config.enabled and self.config.mode != "off"

    @property
    def rehydrating(self) -> bool:
        return self.active and self.config.mode == "rehydrated"

    def anonymize_text(self, text: str) -> RedactionResult:
        if not self.active or not text:
            return RedactionResult(text=text, counts_by_type={})

        redacted = text
        counts: dict[str, int] = {}

        for pattern in SECRET_PATTERNS:
            redacted = self._replace_pattern(redacted, pattern, "secret", counts)

        replacements = [
            ("ssn", SSN_PATTERN),
            ("email", EMAIL_PATTERN),
            ("phone", PHONE_PATTERN),
            ("id", LABELED_ID_PATTERN),
            ("account", ACCOUNT_PATTERN),
        ]
        for pii_type, pattern in replacements:
            redacted = self._replace_pattern(redacted, pattern, pii_type, counts)

        if self.config.redact_names:
            redacted, count = self._replace_names(redacted)
            _add_count(counts, "person", count)

        return RedactionResult(
            text=redacted,
            counts_by_type={key: value for key, value in counts.items() if value},
            placeholder_to_value=dict(self.placeholder_to_value),
        )

    def anonymize_email(self, email: EmailRecord) -> EmailRecord:
        if not self.active:
            return email
        return email.model_copy(
            update={
                "sender": self.anonymize_text(email.sender).text,
                "subject": self.anonymize_text(email.subject or "").text if email.subject else email.subject,
                "body": self.anonymize_text(email.body).text,
            }
        )

    def rehydrate_text(self, text: str) -> str:
        if not self.rehydrating or not text:
            return text
        restored = text
        for placeholder in sorted(self.placeholder_to_value, key=len, reverse=True):
            restored = restored.replace(placeholder, self.placeholder_to_value[placeholder])
        return restored

    def _replace_pattern(self, text: str, pattern: re.Pattern[str], pii_type: str, counts: dict[str, int]) -> str:
        def replace(match: re.Match[str]) -> str:
            value = match.group(0)
            _add_count(counts, pii_type, 1)
            return self._placeholder(pii_type, value)

        return pattern.sub(replace, text)

    def _replace_names(self, text: str) -> tuple[str, int]:
        count = 0

        def replace(match: re.Match[str]) -> str:
            nonlocal count
            value = match.group(0)
            tokens = value.split()
            if any(token in NAME_STOPWORDS for token in tokens):
                return value
            if _looks_like_date_or_title(value):
                return value
            count += 1
            return self._placeholder("person", value)

        return NAME_PATTERN.sub(replace, text), count

    def _placeholder(self, pii_type: str, value: str) -> str:
        key = (pii_type, value)
        existing = self._value_to_placeholder.get(key)
        if existing:
            return existing
        self._counters[pii_type] = self._counters.get(pii_type, 0) + 1
        placeholder = f"[{pii_type.upper()}_{self._counters[pii_type]}]"
        self._value_to_placeholder[key] = placeholder
        self.placeholder_to_value[placeholder] = value
        return placeholder


SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", re.IGNORECASE),
    re.compile(r"\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_.\-]{8,}['\"]?", re.IGNORECASE),
]
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?:\s*(?:x|ext\.?)\s*\d{1,6})?(?!\w)",
    re.IGNORECASE,
)
LABELED_ID_PATTERN = re.compile(
    r"\b(?:student|employee|account|case|client|member|record)\s*(?:id|number|#)\s*[:#-]?\s*[A-Z0-9-]{5,}\b",
    re.IGNORECASE,
)
ACCOUNT_PATTERN = re.compile(r"\b(?:\d[ -]?){12,19}\b")
NAME_PATTERN = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{1,}){1,2}\b")

NAME_STOPWORDS = {
    "Account",
    "Administration",
    "Admissions",
    "Advisor",
    "Analytics",
    "Application",
    "Assistant",
    "Center",
    "Checklist",
    "College",
    "Department",
    "Disability",
    "Division",
    "Email",
    "Employment",
    "Executive",
    "Financial",
    "Form",
    "Graduate",
    "Guide",
    "Housing",
    "International",
    "Office",
    "Operations",
    "Orientation",
    "Pacific",
    "Payroll",
    "Program",
    "Programs",
    "Registrar",
    "Reminder",
    "School",
    "Services",
    "Student",
    "Subject",
    "Support",
    "Team",
    "University",
    "Verification",
    "Workday",
}


def redact_text(text: str, config: PiiConfig | None = None) -> RedactionResult:
    config = config or PiiConfig.from_env()
    if not config.enabled or config.mode == "off" or not text:
        return RedactionResult(text=text, counts_by_type={})
    return PiiSession(config).anonymize_text(text)


def redact_email_for_llm(email: EmailRecord, config: PiiConfig | None = None) -> EmailRecord:
    return PiiSession(config).anonymize_email(email)


def redact_rag_context(text: str, config: PiiConfig | None = None) -> str:
    return redact_text(text, config).text


def redact_log_message(message: str | None, config: PiiConfig | None = None) -> str | None:
    if message is None:
        return None
    config = config or PiiConfig.from_env()
    if not config.enabled or config.mode == "off" or not config.redact_logs:
        return message
    return redact_text(message, config).text


def _redact_names(text: str) -> tuple[str, int]:
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        value = match.group(0)
        tokens = value.split()
        if any(token in NAME_STOPWORDS for token in tokens):
            return value
        if _looks_like_date_or_title(value):
            return value
        count += 1
        return "[PERSON]"

    return NAME_PATTERN.sub(replace, text), count


def _looks_like_date_or_title(value: str) -> bool:
    lower = value.lower()
    if any(month in lower for month in ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")):
        return True
    if any(term in lower for term in ("chief of staff", "vice president", "student affairs", "paid staff")):
        return True
    return False


def _add_count(counts: dict[str, int], pii_type: str, count: int) -> None:
    if count:
        counts[pii_type] = counts.get(pii_type, 0) + count


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
