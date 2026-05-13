from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .config import get_settings, update_env_file
from .db import Database
from .gmail import GmailClient
from .rag_service import index_attachment_by_id, index_email_bodies, make_rag
from .worker import process_once, reextract_current_batch


settings = get_settings()
db = Database(settings.db_path)
db.init()
app = FastAPI(title="MailMind", version="0.1.0")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_OUT = PROJECT_ROOT / "dashboard" / "out"
DASHBOARD_DIST = PROJECT_ROOT / "dashboard" / "dist"

if (DASHBOARD_OUT / "_next").exists():
    app.mount("/_next", StaticFiles(directory=DASHBOARD_OUT / "_next"), name="next_static")
if (DASHBOARD_OUT / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DASHBOARD_OUT / "assets"), name="next_assets")
elif (DASHBOARD_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DASHBOARD_DIST / "assets"), name="assets")


@app.get("/mailmind-logo.svg")
def mailmind_logo():
    logo_path = DASHBOARD_OUT / "mailmind-logo.svg"
    if logo_path.exists():
        return FileResponse(logo_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Logo not built")


class TaskUpdate(BaseModel):
    completed: bool = True


class SettingsUpdate(BaseModel):
    scheduler_enabled: bool
    poll_interval_minutes: int = Field(ge=1, le=1440)
    poll_query: str = Field(min_length=1, max_length=300)
    poll_limit: int = Field(ge=1, le=100)
    daily_digest_enabled: bool
    daily_digest_time: str
    deadline_reminders_enabled: bool
    telegram_notifications_enabled: bool
    llm_provider: str
    anthropic_model: str = Field(min_length=1, max_length=120)
    anthropic_api_key: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    rag_enabled: bool = True
    rag_email_enabled: bool = True
    rag_pdf_enabled: bool = True
    rag_auto_index: bool = False
    embedding_provider: str = "local_bge_m3"
    bge_model: str = Field(default="BAAI/bge-m3", min_length=1, max_length=160)
    voyage_model: str = Field(default="voyage-3.5", min_length=1, max_length=120)
    voyage_api_key: str | None = None
    rag_top_k: int = Field(default=4, ge=1, le=12)
    pii_enabled: bool = True
    pii_mode: str = "rehydrated"
    pii_redact_names: bool = True
    pii_preserve_dates: bool = True
    pii_redact_logs: bool = True

    @field_validator("daily_digest_time")
    @classmethod
    def validate_digest_time(cls, value: str) -> str:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError("Use HH:MM format.")
        hour, minute = int(parts[0]), int(parts[1])
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError("Use HH:MM format.")
        return f"{hour:02d}:{minute:02d}"

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        value = value.lower()
        if value not in {"anthropic", "mock"}:
            raise ValueError("Provider must be anthropic or mock.")
        return value

    @field_validator("embedding_provider")
    @classmethod
    def validate_embedding_provider(cls, value: str) -> str:
        value = value.lower()
        if value not in {"local_bge_m3", "voyage"}:
            raise ValueError("Embedding provider must be local_bge_m3 or voyage.")
        return value

    @field_validator("pii_mode")
    @classmethod
    def validate_pii_mode(cls, value: str) -> str:
        value = value.lower()
        if value == "llm_only":
            value = "rehydrated"
        if value not in {"off", "rehydrated"}:
            raise ValueError("PII mode must be off or rehydrated.")
        return value


class RagQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=12)


@app.get("/", response_class=HTMLResponse)
def dashboard():
    index_path = DASHBOARD_OUT / "index.html"
    if not index_path.exists():
        index_path = DASHBOARD_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return """
    <!doctype html>
    <html lang="en">
      <head><meta charset="utf-8" /><title>MailMind</title></head>
      <body>
        <h1>MailMind dashboard is not built yet.</h1>
        <p>Run <code>npm.cmd install</code> and <code>npm.cmd run build</code> inside the dashboard folder.</p>
      </body>
    </html>
    """


@app.get("/api/tasks")
def tasks(
    include_completed: bool = False,
    search: str | None = None,
    sort: str = "newest",
    requires_reply: bool = False,
    reply_thread: bool = False,
    has_attachments: bool = False,
    needs_review: bool = False,
    due_only: bool = False,
) -> list[dict]:
    return db.list_tasks(
        include_completed=include_completed,
        search=search,
        sort=sort,
        requires_reply=requires_reply,
        reply_thread=reply_thread,
        has_attachments=has_attachments,
        needs_review=needs_review,
        due_only=due_only,
    )


@app.patch("/api/tasks/{task_id}/done")
def mark_done(task_id: str) -> dict:
    if not db.mark_task_done(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True, "task_id": task_id}


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, update: TaskUpdate) -> dict:
    if not update.completed:
        raise HTTPException(status_code=400, detail="Only completion updates are supported in v0.1.")
    return mark_done(task_id)


@app.get("/api/emails")
def emails() -> list[dict]:
    return db.list_emails()


@app.get("/api/emails/{email_id}")
def email_detail(email_id: str) -> dict:
    email = db.get_email(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    if not email.get("body"):
        current = get_settings()
        try:
            gmail = GmailClient(current.gmail_credentials, current.gmail_token)
            full_email = gmail.get_message(email_id)
            db.update_email_body(email_id, full_email.body)
            email = db.get_email(email_id)
        except Exception as exc:
            db.log(email_id, "email_body_fetch_error", str(exc))
            email["body_fetch_error"] = str(exc)
    return email


@app.get("/api/logs")
def logs(limit: int = 100) -> list[dict]:
    return db.list_logs(limit=limit)


@app.get("/api/stats")
def stats() -> dict:
    tasks = db.list_tasks(include_completed=True)
    emails = db.list_emails()
    open_tasks = [task for task in tasks if not task["completed"]]
    return {
        "emails": len(emails),
        "tasks": len(tasks),
        "open_tasks": len(open_tasks),
        "high_priority_open": len([task for task in open_tasks if task["priority"] == "high"]),
    }


@app.get("/api/settings")
def read_settings() -> dict:
    current = get_settings()
    return {
        "scheduler_enabled": current.scheduler_enabled,
        "poll_interval_minutes": current.poll_interval_minutes,
        "poll_query": current.poll_query,
        "poll_limit": current.poll_limit,
        "daily_digest_enabled": current.daily_digest_enabled,
        "daily_digest_time": current.daily_digest_time,
        "deadline_reminders_enabled": current.deadline_reminders_enabled,
        "telegram_notifications_enabled": current.telegram_notifications_enabled,
        "llm_provider": current.llm_provider,
        "anthropic_model": current.anthropic_model,
        "anthropic_api_key_configured": bool(current.anthropic_api_key),
        "telegram_bot_token_configured": bool(current.telegram_bot_token),
        "telegram_chat_id_configured": bool(current.telegram_chat_id),
        "rag_enabled": current.rag_enabled,
        "rag_email_enabled": current.rag_email_enabled,
        "rag_pdf_enabled": current.rag_pdf_enabled,
        "rag_auto_index": current.rag_auto_index,
        "embedding_provider": current.embedding_provider,
        "bge_model": current.bge_model,
        "voyage_model": current.voyage_model,
        "voyage_api_key_configured": bool(current.voyage_api_key),
        "rag_top_k": current.rag_top_k,
        "pii_enabled": current.pii_enabled,
        "pii_mode": current.pii_mode,
        "pii_redact_names": current.pii_redact_names,
        "pii_preserve_dates": current.pii_preserve_dates,
        "pii_redact_logs": current.pii_redact_logs,
    }


@app.put("/api/settings")
def save_settings(update: SettingsUpdate) -> dict:
    current = get_settings()
    next_token = (update.telegram_bot_token or current.telegram_bot_token or "").strip()
    next_chat_id = (update.telegram_chat_id or current.telegram_chat_id or "").strip()
    if update.telegram_notifications_enabled and (not next_token or not next_chat_id):
        raise HTTPException(
            status_code=400,
            detail="Telegram notifications require TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.",
        )

    env_updates = {
        "MAILMIND_SCHEDULER_ENABLED": update.scheduler_enabled,
        "MAILMIND_POLL_INTERVAL_MINUTES": update.poll_interval_minutes,
        "MAILMIND_POLL_QUERY": update.poll_query,
        "MAILMIND_POLL_LIMIT": update.poll_limit,
        "MAILMIND_DAILY_DIGEST_ENABLED": update.daily_digest_enabled,
        "MAILMIND_DAILY_DIGEST_TIME": update.daily_digest_time,
        "MAILMIND_DEADLINE_REMINDERS_ENABLED": update.deadline_reminders_enabled,
        "MAILMIND_TELEGRAM_NOTIFICATIONS_ENABLED": update.telegram_notifications_enabled,
        "MAILMIND_LLM_PROVIDER": update.llm_provider,
        "MAILMIND_ANTHROPIC_MODEL": update.anthropic_model,
        "MAILMIND_RAG_ENABLED": update.rag_enabled,
        "MAILMIND_RAG_EMAIL_ENABLED": update.rag_email_enabled,
        "MAILMIND_RAG_PDF_ENABLED": update.rag_pdf_enabled,
        "MAILMIND_RAG_AUTO_INDEX": update.rag_auto_index,
        "MAILMIND_EMBEDDING_PROVIDER": update.embedding_provider,
        "MAILMIND_BGE_MODEL": update.bge_model,
        "MAILMIND_VOYAGE_MODEL": update.voyage_model,
        "MAILMIND_RAG_TOP_K": update.rag_top_k,
        "MAILMIND_PII_ENABLED": update.pii_enabled,
        "MAILMIND_PII_MODE": update.pii_mode,
        "MAILMIND_PII_REDACT_NAMES": update.pii_redact_names,
        "MAILMIND_PII_PRESERVE_DATES": update.pii_preserve_dates,
        "MAILMIND_PII_REDACT_LOGS": update.pii_redact_logs,
    }
    if update.anthropic_api_key:
        env_updates["ANTHROPIC_API_KEY"] = update.anthropic_api_key.strip()
    if update.telegram_bot_token:
        env_updates["TELEGRAM_BOT_TOKEN"] = update.telegram_bot_token.strip()
    if update.telegram_chat_id:
        env_updates["TELEGRAM_CHAT_ID"] = update.telegram_chat_id.strip()
    if update.voyage_api_key:
        env_updates["VOYAGE_API_KEY"] = update.voyage_api_key.strip()

    update_env_file(env_updates)
    return {"ok": True, "settings": read_settings()}


@app.post("/api/poll")
def poll() -> dict:
    return {"processed": process_once()}


@app.post("/api/sync")
def sync_mailmind() -> dict:
    processed = process_once()
    reextract_result = reextract_current_batch()
    current = get_settings()
    if current.rag_enabled and (current.rag_email_enabled or current.rag_pdf_enabled):
        rag_result = index_rag_documents(rebuild=False)
    else:
        rag_result = _disabled_rag_result()
    db.log(
        None,
        "sync_completed",
        (
            f"Processed {processed} new email(s). "
            f"Refreshed extraction for {reextract_result['refreshed']} email(s). "
            f"Indexed {rag_result['emails']['indexed']} email body/bodies and "
            f"{rag_result['pdfs']['indexed']} PDF(s). "
            f"{rag_result['failed']} indexing failure(s)."
        ),
    )
    return {
        "emails_processed": processed,
        "extraction": reextract_result,
        "rag": rag_result,
        "tasks": stats(),
    }


def _disabled_rag_result() -> dict:
    return {
        "pdfs": {"indexed": 0, "skipped": 0, "failed": 0, "errors": [], "disabled": True},
        "emails": {"indexed": 0, "skipped": 0, "failed": 0, "chunks": 0, "errors": [], "disabled": True},
        "indexed": 0,
        "skipped": 0,
        "failed": 0,
        "chunks": 0,
        "errors": [],
        "disabled": True,
    }


@app.post("/api/reextract")
def reextract() -> dict:
    return reextract_current_batch()


@app.get("/api/attachments")
def attachments() -> list[dict]:
    return db.list_attachments()


@app.get("/api/rag/status")
def rag_status() -> dict:
    current = get_settings()
    attachment_stats = db.attachment_stats()
    email_stats = db.email_body_stats()
    total_chunks = (
        (attachment_stats.get("chunks") or 0 if current.rag_pdf_enabled else 0)
        + (email_stats.get("email_chunks") or 0 if current.rag_email_enabled else 0)
    )
    return {
        "enabled": current.rag_enabled,
        "email_enabled": current.rag_email_enabled,
        "pdf_enabled": current.rag_pdf_enabled,
        "auto_index": current.rag_auto_index,
        "embedding_provider": current.embedding_provider,
        "bge_model": current.bge_model,
        "voyage_api_key_configured": bool(current.voyage_api_key),
        "anthropic_api_key_configured": bool(current.anthropic_api_key),
        "collection": "mailmind_attachments",
        "chroma_dir": str(current.chroma_dir),
        "top_k": current.rag_top_k,
        "hybrid_enabled": current.rag_hybrid_enabled,
        "vector_candidates": current.rag_vector_candidates,
        "bm25_candidates": current.rag_bm25_candidates,
        "rerank_enabled": current.rag_rerank_enabled,
        "rerank_model": current.rag_rerank_model,
        **attachment_stats,
        **email_stats,
        "chunks": total_chunks,
    }


@app.post("/api/attachments/index")
def index_pdf_attachments(rebuild: bool = False) -> dict:
    current = get_settings()
    if not current.rag_enabled:
        raise HTTPException(status_code=400, detail="RAG is disabled in settings.")
    if not current.rag_pdf_enabled:
        return {"indexed": 0, "skipped": 0, "failed": 0, "errors": [], "disabled": True}
    if current.embedding_provider == "voyage" and not current.voyage_api_key:
        raise HTTPException(status_code=400, detail="VOYAGE_API_KEY is required before indexing PDFs.")
    indexed = skipped = failed = 0
    errors: list[dict] = []
    for attachment in db.list_pdf_attachments():
        if not rebuild and attachment.get("indexed"):
            skipped += 1
            continue
        try:
            result = index_one_attachment(attachment["id"])
            if result["status"] == "indexed":
                indexed += 1
            elif result["status"] == "skipped":
                skipped += 1
            else:
                failed += 1
                errors.append({"id": attachment["id"], "error": result.get("error")})
        except Exception as exc:
            failed += 1
            errors.append({"id": attachment["id"], "error": str(exc)})
    return {"indexed": indexed, "skipped": skipped, "failed": failed, "errors": errors}


@app.post("/api/rag/index")
def index_rag_documents(rebuild: bool = False) -> dict:
    current = get_settings()
    if not current.rag_enabled:
        raise HTTPException(status_code=400, detail="RAG is disabled in settings.")
    if not current.rag_email_enabled and not current.rag_pdf_enabled:
        raise HTTPException(status_code=400, detail="Enable at least one AI search source in settings.")
    if current.embedding_provider == "voyage" and not current.voyage_api_key:
        raise HTTPException(status_code=400, detail="VOYAGE_API_KEY is required before indexing documents.")

    pdf_result = (
        index_pdf_attachments(rebuild=rebuild)
        if current.rag_pdf_enabled
        else {"indexed": 0, "skipped": 0, "failed": 0, "errors": [], "disabled": True}
    )
    email_result = (
        index_email_bodies(db, current, changed_only=not rebuild)
        if current.rag_email_enabled
        else {"indexed": 0, "skipped": 0, "failed": 0, "chunks": 0, "errors": [], "disabled": True}
    )
    return {
        "pdfs": pdf_result,
        "emails": email_result,
        "indexed": pdf_result["indexed"] + email_result["indexed"],
        "skipped": pdf_result["skipped"] + email_result["skipped"],
        "failed": pdf_result["failed"] + email_result["failed"],
        "chunks": email_result["chunks"] + sum(
            attachment.get("chunk_count") or 0
            for attachment in db.list_pdf_attachments()
            if attachment.get("indexed")
        ),
        "errors": pdf_result["errors"] + email_result["errors"],
    }


@app.post("/api/attachments/{attachment_id}/index")
def index_attachment(attachment_id: str) -> dict:
    current = get_settings()
    if not current.rag_enabled:
        raise HTTPException(status_code=400, detail="RAG is disabled in settings.")
    if not current.rag_pdf_enabled:
        raise HTTPException(status_code=400, detail="PDF attachment search is disabled in settings.")
    if current.embedding_provider == "voyage" and not current.voyage_api_key:
        raise HTTPException(status_code=400, detail="VOYAGE_API_KEY is required before indexing PDFs.")
    attachment = db.get_attachment(attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return index_attachment_by_id(db, current, attachment_id)


@app.post("/api/rag/ask")
def ask_rag(question: RagQuestion) -> dict:
    current = get_settings()
    if not current.rag_enabled:
        raise HTTPException(status_code=400, detail="RAG is disabled in settings.")
    if not current.rag_email_enabled and not current.rag_pdf_enabled:
        raise HTTPException(status_code=400, detail="Enable at least one AI search source in settings.")
    try:
        answer = make_rag(current).ask(question.question, top_k=question.top_k or current.rag_top_k)
    except Exception as exc:
        db.log(None, "rag_ask_error", str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "answer": answer.answer,
        "sources": [source.__dict__ for source in answer.sources],
    }


def index_one_attachment(attachment_id: str) -> dict:
    current = get_settings()
    try:
        return index_attachment_by_id(db, current, attachment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def main() -> None:
    import uvicorn

    uvicorn.run("mailmind.api:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
