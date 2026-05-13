from datetime import datetime, timezone

from mailmind.db import Database
from mailmind.models import AttachmentMeta, EmailRecord, ExtractedTask, ExtractionResult, Priority


def test_duplicate_email_is_skipped(tmp_path):
    db = Database(tmp_path / "mailmind.db")
    db.init()
    email = EmailRecord(id="msg-1", sender="sender@example.com", subject="Subject")

    assert db.save_email(email) is True
    assert db.save_email(email) is False
    assert db.email_exists("msg-1") is True


def test_save_extraction_and_mark_done(tmp_path):
    db = Database(tmp_path / "mailmind.db")
    db.init()
    email = EmailRecord(id="msg-1", sender="sender@example.com", subject="Subject")
    db.save_email(email)
    result = ExtractionResult(
        has_action=True,
        tasks=[
            ExtractedTask(
                description="Submit form",
                due_at=datetime(2026, 5, 12, 23, 59, tzinfo=timezone.utc),
                priority=Priority.high,
            )
        ],
        priority=Priority.high,
        reason="Deadline found.",
    )

    task_ids = db.save_extraction("msg-1", result)
    tasks = db.list_tasks()

    assert len(task_ids) == 1
    assert tasks[0]["due_at"].startswith("2026-05-12")
    assert db.mark_task_done(task_ids[0]) is True
    assert db.list_tasks() == []


def test_replace_extraction_removes_old_tasks(tmp_path):
    db = Database(tmp_path / "mailmind.db")
    db.init()
    db.save_email(EmailRecord(id="msg-1", sender="sender@example.com", subject="Subject"))
    first = ExtractionResult(
        has_action=True,
        tasks=[ExtractedTask(description="Old task", priority=Priority.medium)],
        priority=Priority.medium,
        reason="Old.",
    )
    second = ExtractionResult(
        has_action=True,
        tasks=[ExtractedTask(description="New task", priority=Priority.high)],
        priority=Priority.high,
        reason="New.",
    )

    db.save_extraction("msg-1", first)
    task_ids = db.replace_extraction("msg-1", second)
    tasks = db.list_tasks()

    assert len(task_ids) == 1
    assert len(tasks) == 1
    assert tasks[0]["description"] == "New task"


def test_mark_tasks_for_review_preserves_existing_tasks(tmp_path):
    db = Database(tmp_path / "mailmind.db")
    db.init()
    db.save_email(EmailRecord(id="msg-1", sender="sender@example.com", subject="Subject"))
    db.save_extraction(
        "msg-1",
        ExtractionResult(
            has_action=True,
            tasks=[ExtractedTask(description="Keep task", priority=Priority.medium)],
            priority=Priority.medium,
            reason="Old.",
        ),
    )

    assert db.mark_tasks_for_review("msg-1") == 1
    tasks = db.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["description"] == "Keep task"
    assert tasks[0]["needs_review"] == 1


def test_task_sorting_and_filters(tmp_path):
    db = Database(tmp_path / "mailmind.db")
    db.init()
    db.save_email(
        EmailRecord(
            id="old",
            sender="old@example.com",
            subject="Re: Old",
            received_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            attachments=[AttachmentMeta(id="att-1", filename="file.pdf")],
        )
    )
    db.save_email(
        EmailRecord(
            id="new",
            sender="new@example.com",
            subject="New",
            received_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
        )
    )
    db.save_extraction(
        "old",
        ExtractionResult(
            has_action=True,
            tasks=[ExtractedTask(description="Old high", priority=Priority.high, requires_reply=True)],
            priority=Priority.high,
            reason="Old.",
        ),
    )
    db.save_extraction(
        "new",
        ExtractionResult(
            has_action=True,
            tasks=[ExtractedTask(description="New low", priority=Priority.low)],
            priority=Priority.low,
            reason="New.",
        ),
    )

    assert [task["description"] for task in db.list_tasks(sort="newest")] == ["New low", "Old high"]
    assert [task["description"] for task in db.list_tasks(sort="priority")] == ["Old high", "New low"]
    assert [task["description"] for task in db.list_tasks(requires_reply=True)] == ["Old high"]
    assert [task["description"] for task in db.list_tasks(reply_thread=True)] == ["Old high"]
    assert [task["description"] for task in db.list_tasks(has_attachments=True)] == ["Old high"]
