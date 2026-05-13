from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is installed in normal runtime
    load_dotenv = None


if load_dotenv:
    load_dotenv()


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    db_path: Path = field(default_factory=lambda: Path(os.getenv("MAILMIND_DB_PATH", "data/mailmind.db")))
    gmail_credentials: Path = field(
        default_factory=lambda: Path(os.getenv("MAILMIND_GMAIL_CREDENTIALS", "credentials.json"))
    )
    gmail_token: Path = field(default_factory=lambda: Path(os.getenv("MAILMIND_GMAIL_TOKEN", "token.json")))
    poll_query: str = field(default_factory=lambda: os.getenv("MAILMIND_POLL_QUERY", "newer_than:14d"))
    poll_limit: int = field(default_factory=lambda: _int_env("MAILMIND_POLL_LIMIT", 20))
    scheduler_enabled: bool = field(default_factory=lambda: _bool_env("MAILMIND_SCHEDULER_ENABLED", True))
    poll_interval_minutes: int = field(default_factory=lambda: _int_env("MAILMIND_POLL_INTERVAL_MINUTES", 15))
    daily_digest_enabled: bool = field(default_factory=lambda: _bool_env("MAILMIND_DAILY_DIGEST_ENABLED", True))
    daily_digest_time: str = field(default_factory=lambda: os.getenv("MAILMIND_DAILY_DIGEST_TIME", "08:00"))
    deadline_reminders_enabled: bool = field(
        default_factory=lambda: _bool_env("MAILMIND_DEADLINE_REMINDERS_ENABLED", True)
    )
    telegram_notifications_enabled: bool = field(
        default_factory=lambda: _bool_env("MAILMIND_TELEGRAM_NOTIFICATIONS_ENABLED", False)
    )
    llm_provider: str = field(default_factory=lambda: os.getenv("MAILMIND_LLM_PROVIDER", "anthropic").lower())
    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    anthropic_model: str = field(
        default_factory=lambda: os.getenv("MAILMIND_ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    )
    telegram_bot_token: str | None = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN"))
    telegram_chat_id: str | None = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID"))
    attachment_dir: Path = field(default_factory=lambda: Path(os.getenv("MAILMIND_ATTACHMENT_DIR", "attachments")))
    chroma_dir: Path = field(default_factory=lambda: Path(os.getenv("MAILMIND_CHROMA_DIR", "chroma")))
    rag_enabled: bool = field(default_factory=lambda: _bool_env("MAILMIND_RAG_ENABLED", True))
    rag_email_enabled: bool = field(default_factory=lambda: _bool_env("MAILMIND_RAG_EMAIL_ENABLED", True))
    rag_pdf_enabled: bool = field(default_factory=lambda: _bool_env("MAILMIND_RAG_PDF_ENABLED", True))
    rag_auto_index: bool = field(default_factory=lambda: _bool_env("MAILMIND_RAG_AUTO_INDEX", False))
    embedding_provider: str = field(
        default_factory=lambda: os.getenv("MAILMIND_EMBEDDING_PROVIDER", "local_bge_m3").lower()
    )
    bge_model: str = field(default_factory=lambda: os.getenv("MAILMIND_BGE_MODEL", "BAAI/bge-m3"))
    voyage_api_key: str | None = field(default_factory=lambda: os.getenv("VOYAGE_API_KEY"))
    voyage_model: str = field(default_factory=lambda: os.getenv("MAILMIND_VOYAGE_MODEL", "voyage-3.5"))
    rag_top_k: int = field(default_factory=lambda: _int_env("MAILMIND_RAG_TOP_K", 4))
    rag_hybrid_enabled: bool = field(default_factory=lambda: _bool_env("MAILMIND_RAG_HYBRID_ENABLED", True))
    rag_vector_candidates: int = field(default_factory=lambda: _int_env("MAILMIND_RAG_VECTOR_CANDIDATES", 30))
    rag_bm25_candidates: int = field(default_factory=lambda: _int_env("MAILMIND_RAG_BM25_CANDIDATES", 30))
    rag_rerank_enabled: bool = field(default_factory=lambda: _bool_env("MAILMIND_RAG_RERANK_ENABLED", True))
    rag_rerank_model: str = field(default_factory=lambda: os.getenv("MAILMIND_RAG_RERANK_MODEL", "BAAI/bge-reranker-base"))
    pii_enabled: bool = field(default_factory=lambda: _bool_env("MAILMIND_PII_ENABLED", True))
    pii_mode: str = field(default_factory=lambda: os.getenv("MAILMIND_PII_MODE", "rehydrated").lower().replace("llm_only", "rehydrated"))
    pii_redact_names: bool = field(default_factory=lambda: _bool_env("MAILMIND_PII_REDACT_NAMES", True))
    pii_preserve_dates: bool = field(default_factory=lambda: _bool_env("MAILMIND_PII_PRESERVE_DATES", True))
    pii_redact_logs: bool = field(default_factory=lambda: _bool_env("MAILMIND_PII_REDACT_LOGS", True))


def get_settings() -> Settings:
    return Settings()


def env_path() -> Path:
    return Path.cwd() / ".env"


def update_env_file(updates: dict[str, Any], path: Path | None = None) -> None:
    target = path or env_path()
    existing_lines = target.read_text(encoding="utf-8").splitlines() if target.exists() else []
    rendered = {key: _render_env_value(value) for key, value in updates.items() if value is not None}
    seen: set[str] = set()
    next_lines: list[str] = []

    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            next_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in rendered:
            next_lines.append(f"{key}={rendered[key]}")
            seen.add(key)
        else:
            next_lines.append(line)

    for key, value in rendered.items():
        if key not in seen:
            next_lines.append(f"{key}={value}")

    target.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")
    for key, value in rendered.items():
        os.environ[key] = value


def _render_env_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()
