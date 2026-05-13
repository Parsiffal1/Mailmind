import importlib

from fastapi.testclient import TestClient

from mailmind.config import get_settings
from mailmind.db import Database
from mailmind.models import EmailRecord, ExtractedTask, ExtractionResult, Priority


def test_done_endpoint_updates_task_state(tmp_path, monkeypatch):
    db_path = tmp_path / "mailmind.db"
    monkeypatch.setenv("MAILMIND_DB_PATH", str(db_path))

    import mailmind.api as api_module

    importlib.reload(api_module)
    db = Database(get_settings().db_path)
    db.init()
    db.save_email(EmailRecord(id="msg-1", sender="sender@example.com", subject="Subject"))
    task_id = db.save_extraction(
        "msg-1",
        ExtractionResult(
            has_action=True,
            tasks=[ExtractedTask(description="Reply to email", priority=Priority.medium)],
            priority=Priority.medium,
            reason="Action found.",
        ),
    )[0]

    client = TestClient(api_module.app)
    response = client.patch(f"/api/tasks/{task_id}/done")

    assert response.status_code == 200
    assert db.list_tasks() == []

