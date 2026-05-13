import importlib

from fastapi.testclient import TestClient

from mailmind.db import Database
from mailmind.models import AttachmentMeta, EmailRecord
from mailmind.rag import LangChainRagIndex, RagAnswer, detect_attachment_intent, detect_multi_source_intent
from mailmind.rag_service import index_attachment_by_id, index_email_bodies


def test_attachment_index_status_for_non_pdf_is_skipped(tmp_path):
    db = Database(tmp_path / "mailmind.db")
    db.init()
    db.save_email(
        EmailRecord(
            id="msg-1",
            sender="sender@example.com",
            subject="Subject",
            attachments=[AttachmentMeta(id="att-1", filename="image.png", mime_type="image/png")],
        )
    )
    settings = type("Settings", (), {"attachment_dir": tmp_path / "attachments"})()

    result = index_attachment_by_id(db, settings, "att-1")
    attachment = db.get_attachment("att-1")

    assert result["status"] == "skipped"
    assert attachment["index_status"] == "skipped"
    assert attachment["indexed"] == 0


def test_rag_ask_endpoint_returns_answer_and_sources(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MAILMIND_DB_PATH", str(tmp_path / "mailmind.db"))
    monkeypatch.setenv("MAILMIND_RAG_ENABLED", "true")

    import mailmind.api as api_module

    api_module = importlib.reload(api_module)

    class FakeRag:
        def ask(self, question, top_k=4):
            assert question == "What should I submit?"
            assert top_k == 4
            return RagAnswer(answer="Submit the form. (file.pdf, page 1)", sources=[])

    monkeypatch.setattr(api_module, "make_rag", lambda settings: FakeRag())
    client = TestClient(api_module.app)

    response = client.post("/api/rag/ask", json={"question": "What should I submit?"})

    assert response.status_code == 200
    assert response.json()["answer"].startswith("Submit the form.")


def test_index_email_bodies_indexes_saved_email_text(tmp_path, monkeypatch):
    db = Database(tmp_path / "mailmind.db")
    db.init()
    db.save_email(
        EmailRecord(
            id="msg-1",
            sender="sender@example.com",
            subject="Project update",
            body="The application deadline is Friday. Please reply with the signed form.",
        )
    )

    calls = []

    class FakeRag:
        def index_email(self, **kwargs):
            calls.append(kwargs)
            return 2

    import mailmind.rag_service as rag_service

    monkeypatch.setattr(rag_service, "make_rag", lambda settings: FakeRag())

    result = index_email_bodies(db, object())

    assert result["indexed"] == 1
    assert result["chunks"] == 2
    assert calls[0]["email_id"] == "msg-1"
    assert "signed form" in calls[0]["body"]


def test_index_email_bodies_skips_unchanged_indexed_email(tmp_path, monkeypatch):
    db = Database(tmp_path / "mailmind.db")
    db.init()
    db.save_email(
        EmailRecord(
            id="msg-1",
            sender="sender@example.com",
            subject="Project update",
            body="The application deadline is Friday.",
        )
    )

    class FakeRag:
        def __init__(self):
            self.calls = 0

        def index_email(self, **kwargs):
            self.calls += 1
            return 1

    fake = FakeRag()
    import mailmind.rag_service as rag_service

    monkeypatch.setattr(rag_service, "make_rag", lambda settings: fake)

    first = index_email_bodies(db, object())
    second = index_email_bodies(db, object())

    assert first["indexed"] == 1
    assert second["indexed"] == 0
    assert fake.calls == 1


def test_email_structure_aware_chunks_include_parent_context(tmp_path):
    rag = LangChainRagIndex(
        tmp_path / "chroma",
        embedding_provider="local_bge_m3",
        bge_model="BAAI/bge-m3",
        voyage_api_key=None,
        voyage_model="voyage-3.5",
        anthropic_api_key=None,
        anthropic_model="claude-sonnet-4-20250514",
    )

    class Document:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    docs = rag._build_email_documents(
        Document=Document,
        email_id="msg-1",
        subject="Re: Assignment",
        sender="sender@example.com",
        received_at="2026-05-12T10:00:00",
        body="Please submit the signed form.\n\nOn Mon, Alice wrote:\nPrevious context",
        attachment_filenames=["form.pdf"],
    )

    by_type = {doc.metadata["chunk_type"]: doc for doc in docs}
    assert {"email_metadata", "email_current_message", "email_thread_history", "email_attachment_context"} <= set(by_type)
    assert "Please submit the signed form." in by_type["email_current_message"].page_content
    assert "Previous context" in by_type["email_thread_history"].page_content
    assert "form.pdf" in by_type["email_attachment_context"].page_content
    assert "Thread history:" in by_type["email_current_message"].metadata["parent_text"]


def test_rag_query_intent_detection_handles_attachment_and_multi_source():
    assert detect_attachment_intent("What is the underlying rule in the attached PDF?")
    assert detect_multi_source_intent("What signatures are required and what deadline applies?")


def test_keyword_search_hits_exact_terms(tmp_path):
    rag = LangChainRagIndex(
        tmp_path / "chroma",
        embedding_provider="local_bge_m3",
        bge_model="BAAI/bge-m3",
        voyage_api_key=None,
        voyage_model="voyage-3.5",
        anthropic_api_key=None,
        anthropic_model="claude-sonnet-4-20250514",
        rerank_enabled=False,
    )

    class Document:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    doc = Document(
        "This chunk mentions SSN verification and employment paperwork.",
        {
            "source_id": "email:msg-1",
            "document_type": "email",
            "email_id": "msg-1",
            "subject": "SSN Verification",
            "sender": "sender@example.com",
            "filename": "Email body",
            "chunk_type": "email_current_message",
            "parent_text": "Full parent email context.",
        },
    )
    rag._upsert_fts([doc], ["email:msg-1:email_current_message:0"])

    results = rag._keyword_search("SSN", k=3)

    assert len(results) == 1
    assert results[0].metadata["retrieval_channel"] == "bm25"
    assert "SSN verification" in results[0].page_content


def test_hybrid_rrf_preserves_per_channel_ranks(tmp_path, monkeypatch):
    rag = LangChainRagIndex(
        tmp_path / "chroma",
        embedding_provider="local_bge_m3",
        bge_model="BAAI/bge-m3",
        voyage_api_key=None,
        voyage_model="voyage-3.5",
        anthropic_api_key=None,
        anthropic_model="claude-sonnet-4-20250514",
        rerank_enabled=False,
    )

    class Document:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    shared = Document("SSN verification shared hit", {"child_id": "shared"})
    vector_only = Document("semantic only hit", {"child_id": "vector-only"})
    bm25_shared = Document("SSN verification shared hit", {"child_id": "shared", "bm25_score": -1.5})

    class FakeStore:
        def similarity_search(self, question, k):
            return [vector_only, shared]

    monkeypatch.setattr(rag, "_store", lambda: FakeStore())
    monkeypatch.setattr(rag, "_keyword_search", lambda question, k: [bm25_shared])

    docs = rag._hybrid_search("SSN", top_k=3)
    shared_doc = next(doc for doc in docs if doc.metadata["child_id"] == "shared")

    assert shared_doc.metadata["retrieval_channel"] == "bm25+vector"
    assert shared_doc.metadata["vector_rank"] == 1
    assert shared_doc.metadata["bm25_rank"] == 0
    assert shared_doc.metadata["bm25_score"] == -1.5
    assert shared_doc.metadata["rrf_score"] > docs[-1].metadata["rrf_score"]


def test_parent_context_aggregation_dedupes_children(tmp_path):
    rag = LangChainRagIndex(
        tmp_path / "chroma",
        embedding_provider="local_bge_m3",
        bge_model="BAAI/bge-m3",
        voyage_api_key=None,
        voyage_model="voyage-3.5",
        anthropic_api_key=None,
        anthropic_model="claude-sonnet-4-20250514",
        rerank_enabled=False,
    )

    class Document:
        def __init__(self, page_content, metadata):
            self.page_content = page_content
            self.metadata = metadata

    docs = [
        Document("metadata hit", {"document_type": "email", "email_id": "msg-1", "chunk_type": "email_metadata", "rrf_score": 0.01, "retrieval_channel": "bm25"}),
        Document("body hit", {"document_type": "email", "email_id": "msg-1", "chunk_type": "email_current_message", "rrf_score": 0.02, "rerank_score": 0.8, "retrieval_channel": "vector"}),
        Document("other email", {"document_type": "email", "email_id": "msg-2", "chunk_type": "email_current_message", "rrf_score": 0.03, "rerank_score": 0.4, "retrieval_channel": "vector"}),
    ]

    parents = rag._aggregate_parent_contexts(docs, top_k=2)

    assert len(parents) == 2
    assert parents[0].metadata["email_id"] == "msg-1"
    assert parents[0].metadata["matched_child_types"] == ["email_current_message", "email_metadata"]
    assert parents[0].metadata["retrieval_channel"] == "bm25+vector"
    assert parents[0].metadata["parent_group_score"] == 0.7210000000000001


def test_index_endpoint_requires_voyage_key_only_for_voyage_provider(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MAILMIND_DB_PATH", str(tmp_path / "mailmind.db"))
    monkeypatch.setenv("MAILMIND_RAG_ENABLED", "true")
    monkeypatch.setenv("MAILMIND_EMBEDDING_PROVIDER", "voyage")
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)

    import mailmind.api as api_module

    api_module = importlib.reload(api_module)
    client = TestClient(api_module.app)

    response = client.post("/api/attachments/index")

    assert response.status_code == 400
    assert "VOYAGE_API_KEY" in response.json()["detail"]
