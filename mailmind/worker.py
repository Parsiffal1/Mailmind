from __future__ import annotations

from datetime import datetime, timezone

from .config import get_settings
from .db import Database
from .extractor import make_extractor
from .gmail import GmailClient
from .notifications import format_digest, format_task_list, iso_hours_from_now, send_telegram_message
from .rag_service import index_attachment_by_id, index_email_bodies


def process_once() -> int:
    settings = get_settings()
    db = Database(settings.db_path)
    db.init()
    gmail = GmailClient(settings.gmail_credentials, settings.gmail_token)
    extractor = make_extractor(settings.llm_provider, settings.anthropic_api_key, settings.anthropic_model)
    processed = 0

    for email in gmail.iter_recent_messages(settings.poll_query, settings.poll_limit):
        if db.email_exists(email.id):
            continue
        db.save_email(email)
        try:
            result = extractor.extract(email)
            task_ids = db.save_extraction(email.id, result)
            processed += 1
            db.log(email.id, "tasks_created", f"Created {len(task_ids)} task(s).")
            if settings.rag_enabled and settings.rag_auto_index:
                if settings.embedding_provider != "voyage" or settings.voyage_api_key:
                    if settings.rag_email_enabled:
                        index_email_bodies(db, settings, changed_only=True)
                    if settings.rag_pdf_enabled:
                        auto_index_email_pdfs(db, settings, email.id)
                else:
                    db.log(email.id, "rag_auto_index_skipped", "VOYAGE_API_KEY is missing.")
            notify_new_high_priority_tasks(db, settings, email.id, task_ids)
        except Exception as exc:
            db.log(email.id, "error", str(exc))
    return processed


def auto_index_email_pdfs(db: Database, settings, email_id: str) -> int:
    indexed = 0
    email = db.get_email(email_id)
    if not email:
        return 0
    for attachment in email.get("attachments", []):
        filename = attachment.get("filename") or ""
        mime_type = (attachment.get("mime_type") or "").lower()
        if not filename.lower().endswith(".pdf") and mime_type != "application/pdf":
            continue
        result = index_attachment_by_id(db, settings, attachment["id"])
        if result.get("status") == "indexed":
            indexed += 1
    return indexed


def reextract_current_batch() -> dict:
    settings = get_settings()
    db = Database(settings.db_path)
    db.init()
    gmail = GmailClient(settings.gmail_credentials, settings.gmail_token)
    extractor = make_extractor(settings.llm_provider, settings.anthropic_api_key, settings.anthropic_model)
    refreshed = 0
    created_tasks = 0
    preserved_tasks = 0
    errors = 0

    for email in gmail.iter_recent_messages(settings.poll_query, settings.poll_limit):
        db.save_email(email)
        try:
            result = extractor.extract(email)
            if result.has_action and result.tasks:
                task_ids = db.replace_extraction(email.id, result)
                created_tasks += len(task_ids)
                db.log(email.id, "reextracted", f"Recreated {len(task_ids)} task(s) with current prompt.")
            else:
                preserved = db.mark_tasks_for_review(email.id)
                preserved_tasks += preserved
                task_ids = []
                db.log(
                    email.id,
                    "reextract_no_action_preserved",
                    f"Current prompt found no action; preserved {preserved} existing task(s) for review.",
                )
            refreshed += 1
        except Exception as exc:
            errors += 1
            db.log(email.id, "reextract_error", str(exc))

    return {
        "refreshed": refreshed,
        "created_tasks": created_tasks,
        "preserved_tasks": preserved_tasks,
        "errors": errors,
    }


def notify_new_high_priority_tasks(db: Database, settings, email_id: str, task_ids: list[str]) -> bool:
    if not settings.telegram_notifications_enabled:
        db.log(email_id, "notification_skipped", "Telegram notifications are disabled.")
        return False
    tasks = [task for task in db.list_tasks_by_ids(task_ids) if task["priority"] == "high"]
    if not tasks:
        return False
    sent = send_telegram_message(
        settings.telegram_bot_token,
        settings.telegram_chat_id,
        format_digest("New high-priority task detected", tasks, empty="No high-priority tasks."),
    )
    db.log(email_id, "notification_sent" if sent else "notification_skipped", "High-priority task notification.")
    return sent


def daily_digest() -> list[dict]:
    settings = get_settings()
    db = Database(settings.db_path)
    db.init()
    return db.list_due_tasks(iso_hours_from_now(48))


def run_daily_digest() -> int:
    settings = get_settings()
    db = Database(settings.db_path)
    db.init()
    if not settings.daily_digest_enabled:
        db.log(None, "daily_digest_skipped", "Daily digest is disabled.")
        return 0
    if not settings.telegram_notifications_enabled:
        db.log(None, "daily_digest_skipped", "Telegram notifications are disabled.")
        return 0
    tasks = daily_digest()
    sent = send_telegram_message(
        settings.telegram_bot_token,
        settings.telegram_chat_id,
        format_digest("MailMind daily deadline digest", tasks, empty="No deadlines in the next 48 hours."),
    )
    db.log(None, "daily_digest_sent" if sent else "daily_digest_skipped", f"{len(tasks)} task(s) in digest.")
    return len(tasks)


def mark_24h_notifications() -> list[dict]:
    settings = get_settings()
    db = Database(settings.db_path)
    db.init()
    tasks = db.list_unnotified_24h(iso_hours_from_now(24))
    db.mark_notified_24h([task["id"] for task in tasks])
    return tasks


def run_24h_reminders() -> int:
    settings = get_settings()
    db = Database(settings.db_path)
    db.init()
    if not settings.deadline_reminders_enabled:
        db.log(None, "deadline_24h_skipped", "Deadline reminders are disabled.")
        return 0
    if not settings.telegram_notifications_enabled:
        db.log(None, "deadline_24h_skipped", "Telegram notifications are disabled.")
        return 0
    tasks = mark_24h_notifications()
    if not tasks:
        db.log(None, "deadline_24h_empty", "No 24-hour deadline reminders due.")
        return 0
    sent = send_telegram_message(
        settings.telegram_bot_token,
        settings.telegram_chat_id,
        format_digest("24-hour deadline warning", tasks, empty="No deadlines due in the next 24 hours."),
    )
    db.log(None, "deadline_24h_sent" if sent else "deadline_24h_skipped", f"{len(tasks)} task(s) due within 24 hours.")
    return len(tasks)


def main() -> None:
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError as exc:  # pragma: no cover - exercised in configured runtime
        raise RuntimeError("Install APScheduler with `pip install -r requirements.txt`.") from exc

    settings = get_settings()
    Database(settings.db_path).init()
    if not settings.scheduler_enabled:
        print("MailMind scheduler is disabled. Running one Gmail poll and exiting.")
        processed = process_once()
        print(f"Processed {processed} new email(s).")
        return

    scheduler = BlockingScheduler(timezone=str(datetime.now(timezone.utc).astimezone().tzinfo))
    poll_interval = max(1, settings.poll_interval_minutes)
    scheduler.add_job(process_once, IntervalTrigger(minutes=poll_interval), id="gmail_poll", replace_existing=True)
    if settings.daily_digest_enabled:
        digest_hour, digest_minute = parse_digest_time(settings.daily_digest_time)
        scheduler.add_job(
            run_daily_digest,
            CronTrigger(hour=digest_hour, minute=digest_minute),
            id="daily_digest",
            replace_existing=True,
        )
    if settings.deadline_reminders_enabled:
        scheduler.add_job(run_24h_reminders, IntervalTrigger(hours=1), id="deadline_24h", replace_existing=True)
    print(f"MailMind worker started. Polling Gmail every {poll_interval} minute(s).")
    process_once()
    scheduler.start()


def parse_digest_time(value: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = value.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (ValueError, AttributeError):
        return 8, 0
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return 8, 0
    return hour, minute


if __name__ == "__main__":
    main()
