from datetime import datetime, timezone

from mailmind.db import Database
from mailmind.models import EmailRecord, ExtractedTask, ExtractionResult, Priority


def seed_due_task(db: Database) -> str:
    db.save_email(EmailRecord(id="msg-1", sender="sender@example.com", subject="Deadline"))
    return db.save_extraction(
        "msg-1",
        ExtractionResult(
            has_action=True,
            tasks=[
                ExtractedTask(
                    description="Submit the form",
                    due_at=datetime(2026, 5, 12, 23, 59, tzinfo=timezone.utc),
                    priority=Priority.high,
                )
            ],
            priority=Priority.high,
            reason="Deadline found.",
        ),
    )[0]


def test_run_daily_digest_sends_telegram(tmp_path, monkeypatch):
    db_path = tmp_path / "mailmind.db"
    monkeypatch.setenv("MAILMIND_DB_PATH", str(db_path))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")

    db = Database(db_path)
    db.init()
    seed_due_task(db)

    sent_messages = []

    def fake_send(token, chat_id, text):
        sent_messages.append((token, chat_id, text))
        return True

    import mailmind.worker as worker

    monkeypatch.setattr(worker, "send_telegram_message", fake_send)

    assert worker.run_daily_digest() == 1
    assert sent_messages
    assert "MailMind daily deadline digest" in sent_messages[0][2]
    assert "Submit the form" in sent_messages[0][2]


def test_run_24h_reminders_marks_tasks_after_send(tmp_path, monkeypatch):
    db_path = tmp_path / "mailmind.db"
    monkeypatch.setenv("MAILMIND_DB_PATH", str(db_path))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")

    db = Database(db_path)
    db.init()
    task_id = seed_due_task(db)
    sent_messages = []

    def fake_send(token, chat_id, text):
        sent_messages.append(text)
        return True

    import mailmind.worker as worker

    monkeypatch.setattr(worker, "send_telegram_message", fake_send)

    assert worker.run_24h_reminders() == 1
    assert "24-hour deadline warning" in sent_messages[0]
    assert db.list_tasks_by_ids([task_id])[0]["notified_24h"] == 1
    assert worker.run_24h_reminders() == 0

