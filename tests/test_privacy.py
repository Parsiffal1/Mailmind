import sys
import types

from mailmind.db import Database
from mailmind.extractor import AnthropicExtractor
from mailmind.models import EmailRecord
from mailmind.privacy import PiiConfig, PiiSession, redact_email_for_llm, redact_text
from mailmind.rag import LangChainRagIndex


def test_redact_text_masks_high_risk_pii_and_preserves_dates():
    result = redact_text(
        "Alex Chen email alex@example.edu phone (949) 824-1234 SSN 123-45-6789 "
        "student id: 12345678 token=sk-test123456789 due May 22, 2026.",
        PiiConfig(),
    )

    assert "Alex Chen" not in result.text
    assert "alex@example.edu" not in result.text
    assert "(949) 824-1234" not in result.text
    assert "123-45-6789" not in result.text
    assert "sk-test123456789" not in result.text
    assert "May 22, 2026" in result.text
    assert "[PERSON_1]" in result.text
    assert result.counts_by_type["email"] == 1
    assert result.counts_by_type["phone"] == 1
    assert result.counts_by_type["ssn"] == 1
    assert "secret" in result.counts_by_type


def test_redact_email_for_llm_does_not_mutate_original_email():
    email = EmailRecord(
        id="msg-1",
        sender="Alex Chen <alex@example.edu>",
        subject="SSN verification for May 22, 2026",
        body="Hi Nina Brooks, my SSN is 123-45-6789. Deadline is 2026-05-22.",
    )

    safe = redact_email_for_llm(email, PiiConfig())

    assert "123-45-6789" in email.body
    assert "123-45-6789" not in safe.body
    assert "2026-05-22" in safe.body
    assert "alex@example.edu" not in safe.sender


def test_pii_session_rehydrates_placeholders_locally():
    session = PiiSession(PiiConfig(mode="rehydrated"))
    safe = session.anonymize_text("Alex Chen should email alex@example.edu by May 22, 2026.").text

    assert "Alex Chen" not in safe
    assert "alex@example.edu" not in safe
    assert "[PERSON_1]" in safe
    assert session.rehydrate_text("[PERSON_1] should email [EMAIL_1].") == "Alex Chen should email alex@example.edu."


def test_pii_off_leaves_text_unchanged():
    result = redact_text("Alex Chen email alex@example.edu.", PiiConfig(enabled=False, mode="off"))

    assert result.text == "Alex Chen email alex@example.edu."


def test_anthropic_extractor_sends_redacted_prompt_and_preserves_deadline(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, api_key):
            pass

        class messages:
            @staticmethod
            def create(**kwargs):
                captured["prompt"] = kwargs["messages"][0]["content"]
                return types.SimpleNamespace(
                    content=[
                        types.SimpleNamespace(
                            text='{"has_action": false, "tasks": [], "deadlines": [], "priority": "low", "requires_reply": false, "reason": "none"}'
                        )
                    ]
                )

    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=FakeClient))
    extractor = AnthropicExtractor(api_key="test", model="claude-test", pii_config=PiiConfig())

    email = EmailRecord(
        id="msg-1",
        sender="Nina Brooks <nina@example.edu>",
        subject="Payroll packet",
        body="Alex Chen must submit SSN 123-45-6789 by 2026-05-22.",
    )
    extractor.extract(email)

    assert "123-45-6789" not in captured["prompt"]
    assert "nina@example.edu" not in captured["prompt"]
    assert "Alex Chen" not in captured["prompt"]
    assert "2026-05-22" in captured["prompt"]
    assert "123-45-6789" in email.body


def test_rag_ask_redacts_context_and_returned_source_snippet(monkeypatch, tmp_path):
    captured = {}

    class FakeChatAnthropic:
        def __init__(self, **kwargs):
            pass

        def invoke(self, messages):
            captured["content"] = messages[1].content
            return types.SimpleNamespace(content="[PERSON_1] should use the available source.")

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    monkeypatch.setitem(sys.modules, "langchain_anthropic", types.SimpleNamespace(ChatAnthropic=FakeChatAnthropic))
    monkeypatch.setitem(
        sys.modules,
        "langchain_core.messages",
        types.SimpleNamespace(HumanMessage=FakeMessage, SystemMessage=FakeMessage),
    )

    rag = LangChainRagIndex(
        tmp_path / "chroma",
        embedding_provider="local_bge_m3",
        bge_model="BAAI/bge-m3",
        voyage_api_key=None,
        voyage_model="voyage-3.5",
        anthropic_api_key="test",
        anthropic_model="claude-test",
        pii_config=PiiConfig(),
    )

    class Document:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    doc = Document(
        "Contact Alex Chen at alex@example.edu. SSN 123-45-6789. Due May 22, 2026.",
        {
            "document_type": "pdf",
            "attachment_id": "att-1",
            "email_id": "msg-1",
            "filename": "SSN Verification.pdf",
            "page": 1,
            "parent_text": "Alex Chen email alex@example.edu SSN 123-45-6789 due May 22, 2026.",
        },
    )
    monkeypatch.setattr(rag, "_hybrid_search", lambda question, top_k: [doc])
    monkeypatch.setattr(rag, "_aggregate_parent_contexts", lambda docs, top_k, question=None: docs)

    answer = rag.ask("What is due?", top_k=1)

    assert "123-45-6789" not in captured["content"]
    assert "alex@example.edu" not in captured["content"]
    assert "Alex Chen" not in captured["content"]
    assert "May 22, 2026" in captured["content"]
    assert "Alex Chen should use" in answer.answer
    assert "123-45-6789" in answer.sources[0].snippet


def test_database_log_redacts_message(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILMIND_PII_ENABLED", "true")
    monkeypatch.setenv("MAILMIND_PII_MODE", "rehydrated")
    monkeypatch.setenv("MAILMIND_PII_REDACT_LOGS", "true")
    db = Database(tmp_path / "mailmind.db")
    db.init()

    db.log(None, "error", "Failed for alex@example.edu token=sk-test123456789 SSN 123-45-6789")
    log = db.list_logs(limit=1)[0]

    assert "alex@example.edu" not in log["message"]
    assert "sk-test123456789" not in log["message"]
    assert "123-45-6789" not in log["message"]
    assert "[EMAIL_1]" in log["message"]
