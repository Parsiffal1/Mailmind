import importlib

from fastapi.testclient import TestClient


def load_api(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MAILMIND_DB_PATH", str(tmp_path / "mailmind.db"))
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    import mailmind.api as api_module

    return importlib.reload(api_module)


def settings_payload(**overrides):
    payload = {
        "scheduler_enabled": True,
        "poll_interval_minutes": 30,
        "poll_query": "newer_than:7d",
        "poll_limit": 10,
        "daily_digest_enabled": True,
        "daily_digest_time": "09:15",
        "deadline_reminders_enabled": True,
        "telegram_notifications_enabled": False,
        "llm_provider": "mock",
        "anthropic_model": "claude-sonnet-4-20250514",
        "anthropic_api_key": "",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "rag_enabled": True,
        "rag_email_enabled": True,
        "rag_pdf_enabled": True,
        "rag_auto_index": False,
        "embedding_provider": "local_bge_m3",
        "bge_model": "BAAI/bge-m3",
        "voyage_model": "voyage-3.5",
        "voyage_api_key": "",
        "rag_top_k": 4,
        "pii_enabled": True,
        "pii_mode": "rehydrated",
        "pii_redact_names": True,
        "pii_preserve_dates": True,
        "pii_redact_logs": True,
    }
    payload.update(overrides)
    return payload


def test_settings_update_writes_env_without_requiring_secrets(tmp_path, monkeypatch):
    api_module = load_api(tmp_path, monkeypatch)
    client = TestClient(api_module.app)

    response = client.put("/api/settings", json=settings_payload())

    assert response.status_code == 200
    body = response.json()["settings"]
    assert body["poll_interval_minutes"] == 30
    assert body["llm_provider"] == "mock"
    assert body["pii_enabled"] is True
    assert body["pii_mode"] == "rehydrated"
    assert body["rag_email_enabled"] is True
    assert body["rag_pdf_enabled"] is True
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "MAILMIND_POLL_INTERVAL_MINUTES=30" in env_text
    assert "MAILMIND_LLM_PROVIDER=mock" in env_text
    assert "MAILMIND_RAG_EMAIL_ENABLED=true" in env_text
    assert "MAILMIND_RAG_PDF_ENABLED=true" in env_text
    assert "MAILMIND_PII_ENABLED=true" in env_text
    assert "MAILMIND_PII_MODE=rehydrated" in env_text


def test_settings_update_accepts_pii_off_mode(tmp_path, monkeypatch):
    api_module = load_api(tmp_path, monkeypatch)
    client = TestClient(api_module.app)

    response = client.put("/api/settings", json=settings_payload(pii_enabled=False, pii_mode="off"))

    assert response.status_code == 200
    body = response.json()["settings"]
    assert body["pii_enabled"] is False
    assert body["pii_mode"] == "off"


def test_telegram_notifications_require_credentials(tmp_path, monkeypatch):
    api_module = load_api(tmp_path, monkeypatch)
    client = TestClient(api_module.app)

    response = client.put(
        "/api/settings",
        json=settings_payload(telegram_notifications_enabled=True),
    )

    assert response.status_code == 400


def test_settings_update_accepts_telegram_credentials(tmp_path, monkeypatch):
    api_module = load_api(tmp_path, monkeypatch)
    client = TestClient(api_module.app)

    response = client.put(
        "/api/settings",
        json=settings_payload(
            telegram_notifications_enabled=True,
            telegram_bot_token="bot-token",
            telegram_chat_id="123",
        ),
    )

    assert response.status_code == 200
    body = response.json()["settings"]
    assert body["telegram_notifications_enabled"] is True
    assert body["telegram_bot_token_configured"] is True
    assert body["telegram_chat_id_configured"] is True
