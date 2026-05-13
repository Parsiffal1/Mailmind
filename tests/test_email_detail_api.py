import importlib

from fastapi.testclient import TestClient

from mailmind.db import Database
from mailmind.models import EmailRecord


def test_email_detail_returns_saved_body(tmp_path, monkeypatch):
    db_path = tmp_path / "mailmind.db"
    monkeypatch.setenv("MAILMIND_DB_PATH", str(db_path))

    import mailmind.api as api_module

    importlib.reload(api_module)
    db = Database(db_path)
    db.init()
    db.save_email(
        EmailRecord(
            id="msg-1",
            sender="sender@example.com",
            subject="Subject",
            body="Full email body",
        )
    )

    client = TestClient(api_module.app)
    response = client.get("/api/emails/msg-1")

    assert response.status_code == 200
    assert response.json()["body"] == "Full email body"
    assert response.json()["attachments"] == []

