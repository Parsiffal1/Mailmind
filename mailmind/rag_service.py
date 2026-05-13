from __future__ import annotations

import hashlib
from pathlib import Path

from .db import Database
from .gmail import GmailClient
from .privacy import PiiConfig
from .rag import LangChainRagIndex


def make_rag(settings) -> LangChainRagIndex:
    pii_config = PiiConfig(
        enabled=getattr(settings, "pii_enabled", True),
        mode=getattr(settings, "pii_mode", "rehydrated"),
        redact_names=getattr(settings, "pii_redact_names", True),
        preserve_dates=getattr(settings, "pii_preserve_dates", True),
        redact_logs=getattr(settings, "pii_redact_logs", True),
    )
    return LangChainRagIndex(
        settings.chroma_dir,
        embedding_provider=settings.embedding_provider,
        bge_model=settings.bge_model,
        voyage_api_key=settings.voyage_api_key,
        voyage_model=settings.voyage_model,
        anthropic_api_key=settings.anthropic_api_key,
        anthropic_model=settings.anthropic_model,
        hybrid_enabled=getattr(settings, "rag_hybrid_enabled", True),
        vector_candidates=getattr(settings, "rag_vector_candidates", 10),
        bm25_candidates=getattr(settings, "rag_bm25_candidates", 10),
        rerank_enabled=getattr(settings, "rag_rerank_enabled", True),
        rerank_model=getattr(settings, "rag_rerank_model", "BAAI/bge-reranker-base"),
        pii_config=pii_config,
        email_enabled=getattr(settings, "rag_email_enabled", True),
        pdf_enabled=getattr(settings, "rag_pdf_enabled", True),
    )


def index_attachment_by_id(db: Database, settings, attachment_id: str) -> dict:
    attachment = db.get_attachment(attachment_id)
    if not attachment:
        raise ValueError("Attachment not found")
    attachment_row_id = attachment["id"]
    filename = attachment["filename"] or "attachment.pdf"
    mime_type = (attachment["mime_type"] or "").lower()
    if not filename.lower().endswith(".pdf") and mime_type != "application/pdf":
        db.update_attachment_index(
            attachment_row_id,
            index_status="skipped",
            indexed=False,
            chunk_count=0,
            index_error="Only PDF attachments are supported.",
        )
        return {"status": "skipped", "chunks": 0, "error": "Only PDF attachments are supported."}

    local_path = attachment_local_path(settings.attachment_dir, attachment, attachment_row_id, filename)
    try:
        if not Path(local_path).exists():
            GmailClient(settings.gmail_credentials, settings.gmail_token).download_attachment(
                attachment["email_id"],
                attachment.get("gmail_attachment_id") or attachment_id,
                Path(local_path),
            )
        chunks = make_rag(settings).index_pdf(
            attachment_id=attachment_row_id,
            email_id=attachment["email_id"],
            filename=filename,
            path=Path(local_path),
            subject=attachment.get("subject"),
            sender=attachment.get("sender"),
        )
        if chunks == 0:
            db.update_attachment_index(
                attachment_row_id,
                local_path=local_path,
                index_status="skipped",
                indexed=False,
                chunk_count=0,
                index_error="No text layer detected.",
            )
            db.log(attachment["email_id"], "rag_skipped", f"{filename}: no text layer detected.")
            return {"status": "skipped", "chunks": 0, "error": "No text layer detected."}
        db.update_attachment_index(
            attachment_row_id,
            local_path=local_path,
            index_status="indexed",
            indexed=True,
            chunk_count=chunks,
            index_error=None,
        )
        db.log(attachment["email_id"], "rag_indexed", f"{filename}: indexed {chunks} chunk(s).")
        return {"status": "indexed", "chunks": chunks}
    except Exception as exc:
        db.update_attachment_index(
            attachment_row_id,
            local_path=local_path,
            index_status="failed",
            indexed=False,
            chunk_count=0,
            index_error=str(exc),
        )
        db.log(attachment["email_id"], "rag_index_error", f"{filename}: {exc}")
        return {"status": "failed", "chunks": 0, "error": str(exc)}


def index_email_bodies(db: Database, settings, *, changed_only: bool = True) -> dict:
    indexed = skipped = failed = chunks = 0
    errors: list[dict] = []
    rag = make_rag(settings)
    for email in db.list_emails_for_rag(changed_only=changed_only):
        try:
            body = email.get("body") or ""
            body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            count = rag.index_email(
                email_id=email["id"],
                subject=email.get("subject"),
                sender=email.get("sender"),
                received_at=email.get("received_at"),
                body=body,
                attachment_filenames=email.get("attachment_filenames") or [],
            )
            if count:
                indexed += 1
                chunks += count
                db.mark_email_rag_indexed(email["id"], body_hash, count)
                db.log(email["id"], "rag_email_indexed", f"Email body indexed {count} chunk(s).")
            else:
                skipped += 1
        except Exception as exc:
            failed += 1
            errors.append({"id": email["id"], "error": str(exc)})
            db.log(email["id"], "rag_email_index_error", str(exc))
    return {"indexed": indexed, "skipped": skipped, "failed": failed, "chunks": chunks, "errors": errors}


def safe_filename(email_id: str, attachment_id: str, filename: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in filename)
    suffix = Path(cleaned).suffix or ".pdf"
    stem = Path(cleaned).stem[:80] or "attachment"
    digest = hashlib.sha256(f"{email_id}:{attachment_id}:{filename}".encode("utf-8")).hexdigest()[:16]
    return f"{email_id}_{digest}_{stem}{suffix}"


def attachment_local_path(attachment_dir: Path, attachment: dict, attachment_id: str, filename: str) -> str:
    existing = attachment.get("local_path")
    if existing and Path(existing).exists():
        return str(existing)
    return str(attachment_dir / safe_filename(attachment["email_id"], attachment_id, filename))
