from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal

from .privacy import PiiConfig, PiiSession


ATTACHMENT_INTENT_TERMS = {
    "attachment",
    "attached",
    "pdf",
    "form",
    "checklist",
    "guide",
    "document",
    "underlying rule",
    "this form",
    "this document",
    "附件",
    "表格",
    "文件",
    "指南",
    "清单",
    "这个表",
    "这份文件",
}

MULTI_SOURCE_TERMS = {
    "all",
    "both",
    "combine",
    "compare",
    "email and attachment",
    "requirements",
    "documents",
    "steps",
    "process",
    "and what",
    "what are",
    "所有",
    "全部",
    "结合",
    "对比",
    "要求",
    "流程",
    "步骤",
}

CONFLICT_INTENT_TERMS = {
    "current",
    "updated",
    "corrected",
    "latest",
    "newer",
    "older",
    "old",
    "previous",
    "replaces",
    "superseded",
    "before the correction",
    "当前",
    "最新",
    "更新",
    "更正",
    "旧",
}

TABLE_INTENT_TERMS = {"table", "row", "column", "cohort", "schedule", "matrix", "表", "行", "列"}

IMPORTANT_KEYWORDS = {
    "i-20",
    "i-94",
    "w-4",
    "glacier",
    "sevis",
    "cpt",
    "opt",
    "dsc",
    "payroll",
    "onboarding",
    "stat 67",
    "workday",
}

CURRENT_TERMS = {"current", "updated", "corrected", "latest", "new", "newer", "revised", "replaces"}
OLD_TERMS = {"old", "outdated", "previous", "superseded", "deprecated", "earlier", "legacy"}


def detect_attachment_intent(query: str) -> bool:
    q = query.lower()
    return any(term.lower() in q for term in ATTACHMENT_INTENT_TERMS)


def detect_multi_source_intent(query: str) -> bool:
    q = query.lower()
    return any(term.lower() in q for term in MULTI_SOURCE_TERMS)


def detect_conflict_intent(query: str) -> bool:
    q = query.lower()
    return any(term.lower() in q for term in CONFLICT_INTENT_TERMS)


def detect_table_intent(query: str) -> bool:
    q = query.lower()
    return any(term.lower() in q for term in TABLE_INTENT_TERMS)


@dataclass(frozen=True)
class RagSource:
    attachment_id: str
    email_id: str
    filename: str
    page: int
    snippet: str
    document_type: str = "pdf"
    chunk_type: str | None = None
    retrieval_channel: str | None = None
    rerank_score: float | None = None
    subject: str | None = None
    sender: str | None = None


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    sources: list[RagSource]


def extract_pdf_text(path: Path) -> list[tuple[int, str]]:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - exercised in configured runtime
        raise RuntimeError("Install PDF dependency with `pip install -r requirements.txt`.") from exc

    pages: list[tuple[int, str]] = []
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((index, text.strip()))
    return pages


QUOTE_PATTERNS = [
    re.compile(r"^On .+ wrote:$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^From:\s+.+$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^-{2,}\s*Original Message\s*-{2,}$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^>.+$", re.MULTILINE),
]


def split_email_thread(body: str) -> tuple[str, str]:
    text = body.strip()
    if not text:
        return "", ""
    positions = [match.start() for pattern in QUOTE_PATTERNS for match in pattern.finditer(text)]
    if not positions:
        return text, ""
    split_at = max(0, min(positions))
    current = text[:split_at].strip()
    history = text[split_at:].strip()
    return current or text, history if current else ""


def compact_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text.strip())


class LangChainRagIndex:
    def __init__(
        self,
        persist_dir: Path,
        *,
        embedding_provider: Literal["local_bge_m3", "voyage"],
        bge_model: str,
        voyage_api_key: str | None,
        voyage_model: str,
        anthropic_api_key: str | None,
        anthropic_model: str,
        hybrid_enabled: bool = True,
        vector_candidates: int = 30,
        bm25_candidates: int = 30,
        rerank_enabled: bool = True,
        rerank_model: str = "BAAI/bge-reranker-base",
        collection_name: str = "mailmind_attachments",
        pii_config: PiiConfig | None = None,
        email_enabled: bool = True,
        pdf_enabled: bool = True,
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_provider = embedding_provider
        self.bge_model = bge_model
        self.voyage_api_key = voyage_api_key
        self.voyage_model = voyage_model
        self.anthropic_api_key = anthropic_api_key
        self.anthropic_model = anthropic_model
        self.hybrid_enabled = hybrid_enabled
        self.vector_candidates = vector_candidates
        self.bm25_candidates = bm25_candidates
        self.rerank_enabled = rerank_enabled
        self.rerank_model = rerank_model
        self.collection_name = collection_name
        self.pii_config = pii_config or PiiConfig.from_env()
        self.email_enabled = email_enabled
        self.pdf_enabled = pdf_enabled
        self._vector_store = None
        self._reranker = None
        self.fts_path = self.persist_dir / "rag_fts.sqlite"
        self._init_fts()

    def _embeddings(self):
        if self.embedding_provider == "local_bge_m3":
            return LocalSentenceTransformerEmbeddings(self.bge_model)
        if not self.voyage_api_key:
            raise RuntimeError("VOYAGE_API_KEY is required before indexing or asking PDF questions.")
        try:
            from langchain_voyageai import VoyageAIEmbeddings
        except ImportError as exc:  # pragma: no cover - exercised in configured runtime
            raise RuntimeError("Install LangChain Voyage support with `pip install -r requirements.txt`.") from exc
        return VoyageAIEmbeddings(model=self.voyage_model, voyage_api_key=self.voyage_api_key)

    def _store(self):
        if self._vector_store is None:
            try:
                from langchain_chroma import Chroma
            except ImportError as exc:  # pragma: no cover - exercised in configured runtime
                raise RuntimeError("Install LangChain Chroma support with `pip install -r requirements.txt`.") from exc
            self._vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self._embeddings(),
                persist_directory=str(self.persist_dir),
            )
        return self._vector_store

    def _init_fts(self) -> None:
        with sqlite3.connect(self.fts_path) as conn:
            conn.executescript(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
                    child_id UNINDEXED,
                    source_id UNINDEXED,
                    text,
                    subject,
                    sender,
                    filename,
                    parent_text UNINDEXED,
                    metadata_json UNINDEXED
                );
                """
            )

    def _delete_fts_by_source(self, source_id: str) -> None:
        with sqlite3.connect(self.fts_path) as conn:
            conn.execute("DELETE FROM rag_chunks_fts WHERE source_id = ?", (source_id,))

    def _upsert_fts(self, documents, ids: list[str]) -> None:
        rows = []
        for doc, child_id in zip(documents, ids):
            meta = dict(doc.metadata)
            meta["child_id"] = child_id
            rows.append(
                (
                    child_id,
                    str(meta.get("source_id") or meta.get("attachment_id") or meta.get("email_id") or child_id),
                    doc.page_content,
                    str(meta.get("subject", "")),
                    str(meta.get("sender", "")),
                    str(meta.get("filename", "")),
                    str(meta.get("parent_text") or doc.page_content),
                    json.dumps(meta, ensure_ascii=False),
                )
            )
        with sqlite3.connect(self.fts_path) as conn:
            conn.executemany(
                """
                INSERT INTO rag_chunks_fts (
                    child_id, source_id, text, subject, sender, filename, parent_text, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def _fts_query(self, question: str) -> str:
        tokens = re.findall(r"[\w@.$+-]+", question, flags=re.UNICODE)
        escaped = [token.replace('"', '""') for token in tokens if token.strip()]
        return " OR ".join(f'"{token}"' for token in escaped[:12])

    def _keyword_search(self, question: str, *, k: int):
        query = self._fts_query(question)
        if not query:
            return []
        try:
            from langchain_core.documents import Document
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install LangChain core packages with `pip install -r requirements.txt`.") from exc
        with sqlite3.connect(self.fts_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT child_id, text, parent_text, metadata_json, bm25(rag_chunks_fts) AS bm25_score
                FROM rag_chunks_fts
                WHERE rag_chunks_fts MATCH ?
                ORDER BY bm25_score ASC
                LIMIT ?
                """,
                (query, k),
            ).fetchall()
        docs = []
        for rank, row in enumerate(rows):
            meta = json.loads(row["metadata_json"])
            meta["child_id"] = row["child_id"]
            meta["retrieval_channel"] = "bm25"
            meta["bm25_rank"] = rank
            meta["bm25_score"] = float(row["bm25_score"])
            docs.append(Document(page_content=row["text"], metadata=meta))
        return docs

    def _docs_from_store_get(self, result: dict):
        try:
            from langchain_core.documents import Document
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install LangChain core packages with `pip install -r requirements.txt`.") from exc
        docs = []
        ids = result.get("ids", []) if result else []
        documents = result.get("documents", []) if result else []
        metadatas = result.get("metadatas", []) if result else []
        for index, child_id in enumerate(ids):
            text = documents[index] if index < len(documents) else ""
            meta = dict(metadatas[index] or {}) if index < len(metadatas) else {}
            meta["child_id"] = meta.get("child_id") or child_id
            docs.append(Document(page_content=text, metadata=meta))
        return docs

    def _linked_attachment_docs_for_email(self, question: str, email_id: str, *, k: int = 3):
        if not email_id:
            return []
        try:
            docs = self._store().similarity_search(question, k=max(k * 4, 8), filter={"email_id": email_id})
        except Exception:
            docs = self._docs_from_store_get(self._store().get(where={"email_id": email_id}))
        pdf_docs = [doc for doc in docs if doc.metadata.get("document_type") == "pdf" or doc.metadata.get("attachment_id")]
        if not pdf_docs:
            pdf_docs = [
                doc
                for doc in self._docs_from_store_get(self._store().get(where={"email_id": email_id}))
                if doc.metadata.get("document_type") == "pdf" or doc.metadata.get("attachment_id")
            ]
        expanded = []
        for rank, doc in enumerate(pdf_docs[:k]):
            doc.metadata["child_id"] = self._doc_child_id(doc, rank)
            doc.metadata["retrieval_channel"] = self._append_channel(doc.metadata.get("retrieval_channel"), "linked_attachment")
            doc.metadata["attachment_link_bonus"] = 1.0
            expanded.append(doc)
        return expanded

    def _source_email_docs_for_pdf(self, email_id: str, *, k: int = 1):
        if not email_id:
            return []
        docs = [
            doc
            for doc in self._docs_from_store_get(self._store().get(where={"source_id": f"email:{email_id}"}))
            if doc.metadata.get("document_type") == "email"
        ]
        current_docs = [doc for doc in docs if doc.metadata.get("chunk_type") == "email_current_message"]
        selected = current_docs[:k] or docs[:k]
        for rank, doc in enumerate(selected):
            doc.metadata["child_id"] = self._doc_child_id(doc, rank)
            doc.metadata["retrieval_channel"] = self._append_channel(doc.metadata.get("retrieval_channel"), "source_email")
            doc.metadata["attachment_link_bonus"] = 0.5
        return selected

    def _append_channel(self, existing: str | None, channel: str) -> str:
        channels = set(str(existing or "").split("+")) if existing else set()
        channels.discard("")
        channels.add(channel)
        return "+".join(sorted(channels))

    def _doc_child_id(self, doc, fallback: int) -> str:
        meta = doc.metadata
        if meta.get("child_id"):
            return str(meta["child_id"])
        if meta.get("document_type") == "email":
            return f"email:{meta.get('email_id', '')}:{meta.get('chunk_type', 'chunk')}:{fallback}"
        return f"{meta.get('attachment_id', '')}:{meta.get('page', 0)}:{fallback}"

    def _hybrid_search(self, question: str, *, top_k: int):
        if not self.hybrid_enabled:
            return self._store().similarity_search(question, k=top_k)
        vector_docs = self._store().similarity_search(question, k=max(top_k, self.vector_candidates))
        keyword_docs = self._keyword_search(question, k=max(top_k, self.bm25_candidates))
        candidates: dict[str, dict] = {}

        def ensure_candidate(child_id: str, doc):
            if child_id not in candidates:
                candidates[child_id] = {
                    "doc": doc,
                    "ranks": {},
                    "scores": {},
                    "channels": set(),
                }
            return candidates[child_id]

        for rank, doc in enumerate(vector_docs):
            child_id = self._doc_child_id(doc, rank)
            doc.metadata["child_id"] = child_id
            candidate = ensure_candidate(child_id, doc)
            candidate["ranks"]["vector"] = rank
            candidate["channels"].add("vector")
        for rank, doc in enumerate(keyword_docs):
            child_id = self._doc_child_id(doc, rank)
            doc.metadata["child_id"] = child_id
            candidate = ensure_candidate(child_id, doc)
            candidate["ranks"]["bm25"] = rank
            candidate["scores"]["bm25"] = doc.metadata.get("bm25_score")
            candidate["channels"].add("bm25")

        rrf_k = 60
        docs = []
        for child_id, candidate in candidates.items():
            doc = candidate["doc"]
            ranks = candidate["ranks"]
            channels = sorted(candidate["channels"])
            rrf_score = sum(1.0 / (rrf_k + rank + 1) for rank in ranks.values())
            doc.metadata["child_id"] = child_id
            doc.metadata["retrieval_channel"] = "+".join(channels)
            doc.metadata["vector_rank"] = ranks.get("vector")
            doc.metadata["bm25_rank"] = ranks.get("bm25")
            doc.metadata["bm25_score"] = candidate["scores"].get("bm25")
            doc.metadata["rrf_score"] = rrf_score
            docs.append(doc)
        docs.sort(key=lambda doc: doc.metadata.get("rrf_score", 0.0), reverse=True)
        docs = self._rerank(question, docs)
        docs = self._attachment_aware_expand(question, docs)
        docs = self._source_aware_sort(question, docs)
        return docs[:top_k]

    def _rerank(self, question: str, docs):
        if not self.rerank_enabled or len(docs) <= 1:
            return self._source_aware_sort(question, docs)
        try:
            if self._reranker is None:
                from sentence_transformers import CrossEncoder

                self._reranker = CrossEncoder(self.rerank_model)
            pairs = [(question, self._rerank_text(doc)) for doc in docs]
            scores = self._reranker.predict(pairs)
        except Exception:
            return self._source_aware_sort(question, docs)
        for doc, score in zip(docs, scores):
            doc.metadata["rerank_score"] = float(score)
        return self._source_aware_sort(question, docs)

    def _rerank_text(self, doc) -> str:
        meta = doc.metadata
        return "\n".join(
            [
                f"Type: {meta.get('document_type', '')}",
                f"Filename: {meta.get('filename', '')}",
                f"Subject: {meta.get('subject', '')}",
                f"Chunk: {meta.get('chunk_type', '')}",
                doc.page_content[:1800],
            ]
        )

    def _attachment_aware_expand(self, question: str, docs):
        attachment_intent = detect_attachment_intent(question)
        multi_source = detect_multi_source_intent(question)
        if not attachment_intent and not multi_source:
            return docs
        expanded = list(docs)
        seen = {self._doc_child_id(doc, index) for index, doc in enumerate(expanded)}
        for doc in docs[:12]:
            meta = doc.metadata
            additions = []
            if meta.get("document_type") == "email" and (attachment_intent or meta.get("chunk_type") == "email_attachment_context"):
                additions = self._linked_attachment_docs_for_email(question, str(meta.get("email_id", "")), k=3)
            elif meta.get("document_type") == "pdf" or meta.get("attachment_id"):
                additions = self._source_email_docs_for_pdf(str(meta.get("email_id", "")), k=1)
            for addition in additions:
                child_id = self._doc_child_id(addition, len(seen))
                addition.metadata["child_id"] = child_id
                if child_id in seen:
                    continue
                seen.add(child_id)
                expanded.append(addition)
        return expanded

    def _source_aware_sort(self, question: str, docs):
        if not docs:
            return docs
        rerank_scores = [float(doc.metadata["rerank_score"]) for doc in docs if doc.metadata.get("rerank_score") is not None]
        min_rerank = min(rerank_scores) if rerank_scores else 0.0
        max_rerank = max(rerank_scores) if rerank_scores else 0.0
        versions = [version for doc in docs if (version := self._extract_version_number(self._metadata_text(doc.metadata))) is not None]
        max_version = max(versions) if versions else None
        scored = []
        for rank, doc in enumerate(docs):
            score = self._source_aware_score(
                question,
                doc,
                rank=rank,
                min_rerank=min_rerank,
                max_rerank=max_rerank,
                max_version=max_version,
            )
            doc.metadata["final_score"] = score
            scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _score, doc in scored]

    def _source_aware_score(self, question: str, doc, *, rank: int, min_rerank: float, max_rerank: float, max_version: int | None) -> float:
        meta = doc.metadata
        rerank_score = meta.get("rerank_score")
        if rerank_score is not None and max_rerank != min_rerank:
            base = (float(rerank_score) - min_rerank) / (max_rerank - min_rerank)
        elif rerank_score is not None:
            base = 0.5
        else:
            base = float(meta.get("rrf_score") or 0.0) * 30.0
        text = "\n".join([doc.page_content, str(meta.get("parent_text") or ""), self._metadata_text(meta)])
        score = (
            0.70 * base
            + 0.10 * self._exact_keyword_bonus(question, text)
            + 0.08 * self._attachment_intent_bonus(question, meta)
            + 0.06 * self._recency_current_bonus(question, text, meta)
            + 0.04 * self._version_bonus(question, meta, max_version)
            + 0.02 * self._source_type_match_bonus(question, meta)
            + 0.05 * float(meta.get("attachment_link_bonus") or 0.0)
            - 0.05 * self._outdated_penalty(text, meta)
        )
        return score - rank * 0.0001

    def _metadata_text(self, meta: dict) -> str:
        return " ".join(
            str(meta.get(key) or "")
            for key in ("filename", "subject", "sender", "chunk_type", "document_type")
        )

    def _exact_keyword_bonus(self, query: str, text: str) -> float:
        q = query.lower()
        t = text.lower()
        hits = [keyword for keyword in IMPORTANT_KEYWORDS if keyword in q and keyword in t]
        return min(1.0, 0.25 * len(hits))

    def _attachment_intent_bonus(self, query: str, meta: dict) -> float:
        if not detect_attachment_intent(query):
            return 0.0
        if meta.get("document_type") == "pdf" or str(meta.get("filename") or "").lower().endswith(".pdf"):
            return 1.0
        if meta.get("chunk_type") == "email_attachment_context":
            return 0.4
        return 0.0

    def _recency_current_bonus(self, query: str, text: str, meta: dict) -> float:
        q = query.lower()
        wants_current = any(term in q for term in CURRENT_TERMS) or any(term in q for term in ("当前", "最新", "更新"))
        if not wants_current:
            return 0.0
        t = text.lower()
        filename = str(meta.get("filename") or "").lower()
        score = 0.0
        if any(term in t for term in CURRENT_TERMS):
            score += 0.7
        if any(term in filename for term in CURRENT_TERMS):
            score += 0.3
        return min(1.0, score)

    def _outdated_penalty(self, text: str, meta: dict) -> float:
        t = text.lower()
        filename = str(meta.get("filename") or "").lower()
        penalty = 0.0
        if any(term in t for term in OLD_TERMS):
            penalty += 0.7
        if any(term in filename for term in OLD_TERMS):
            penalty += 0.3
        return min(1.0, penalty)

    def _extract_version_number(self, text: str) -> int | None:
        match = re.search(r"\bv(?:ersion)?[_\s-]*(\d+)\b", text.lower())
        return int(match.group(1)) if match else None

    def _version_bonus(self, query: str, meta: dict, max_version: int | None) -> float:
        if max_version is None or not detect_conflict_intent(query):
            return 0.0
        version = self._extract_version_number(self._metadata_text(meta))
        return 1.0 if version == max_version else 0.0

    def _source_type_match_bonus(self, query: str, meta: dict) -> float:
        if detect_table_intent(query) and str(meta.get("chunk_type") or "").startswith("pdf_table"):
            return 1.0
        if detect_attachment_intent(query) and meta.get("document_type") == "pdf":
            return 1.0
        if "email" in query.lower() and meta.get("document_type") == "email":
            return 1.0
        return 0.0

    def _parent_id(self, doc) -> str:
        meta = doc.metadata
        if meta.get("document_type") == "email":
            return f"email:{meta.get('email_id', '')}"
        return f"pdf:{meta.get('attachment_id', '')}:page:{meta.get('page', 0)}"

    def _aggregate_parent_contexts(self, docs, *, top_k: int, question: str | None = None):
        groups: dict[str, dict] = {}
        for rank, doc in enumerate(docs):
            meta = doc.metadata
            parent_id = self._parent_id(doc)
            parent_score = float(meta.get("final_score") or meta.get("rerank_score") or meta.get("rrf_score") or 0.0)
            group = groups.setdefault(
                parent_id,
                {
                    "doc": doc,
                    "best_rank": rank,
                    "max_score": None,
                    "max_rerank": None,
                    "max_rrf": None,
                    "sum_rrf": 0.0,
                    "sum_score": 0.0,
                    "count": 0,
                    "matched_children": [],
                    "channels": set(),
                },
            )
            rerank_score = meta.get("rerank_score")
            rrf_score = float(meta.get("rrf_score") or 0.0)
            group["count"] += 1
            group["sum_score"] += parent_score
            if group["max_score"] is None or parent_score > group["max_score"]:
                group["max_score"] = parent_score
                group["doc"] = doc
                group["best_rank"] = rank
            if rerank_score is not None and (
                group["max_rerank"] is None or float(rerank_score) > group["max_rerank"]
            ):
                group["max_rerank"] = float(rerank_score)
            elif group["max_rerank"] is None and rrf_score > (group["max_rrf"] or 0.0):
                if group["max_score"] is None:
                    group["doc"] = doc
                    group["best_rank"] = rank
            group["max_rrf"] = max(group["max_rrf"] or 0.0, rrf_score)
            group["sum_rrf"] += rrf_score
            if meta.get("chunk_type"):
                group["matched_children"].append(str(meta["chunk_type"]))
            if meta.get("retrieval_channel"):
                group["channels"].update(str(meta["retrieval_channel"]).split("+"))

        ranked = sorted(
            groups.values(),
            key=lambda group: (
                0.8 * (group["max_score"] or 0.0) + 0.2 * (group["sum_score"] / max(group["count"], 1)),
                group["sum_rrf"],
                -group["best_rank"],
            ),
            reverse=True,
        )
        ranked = self._select_parent_groups(ranked, question=question, top_k=top_k)
        parent_docs = []
        for group in ranked:
            doc = group["doc"]
            doc.metadata["parent_group_score"] = 0.8 * (group["max_score"] or 0.0) + 0.2 * (
                group["sum_score"] / max(group["count"], 1)
            )
            doc.metadata["parent_sum_rrf"] = group["sum_rrf"]
            doc.metadata["matched_child_types"] = sorted(set(group["matched_children"]))
            doc.metadata["retrieval_channel"] = "+".join(sorted(group["channels"])) or doc.metadata.get("retrieval_channel")
            parent_docs.append(doc)
        return parent_docs

    def _select_parent_groups(self, ranked: list[dict], *, question: str | None, top_k: int) -> list[dict]:
        if not question:
            return ranked[:top_k]
        attachment_intent = detect_attachment_intent(question)
        multi_source = detect_multi_source_intent(question)
        conflict_intent = detect_conflict_intent(question)
        if not attachment_intent and not multi_source and not conflict_intent:
            return ranked[:top_k]

        selected = []
        used_parent_ids = set()
        used_attachments = set()
        used_source_types = set()
        for group in ranked:
            doc = group["doc"]
            meta = doc.metadata
            parent_id = self._parent_id(doc)
            if parent_id in used_parent_ids:
                continue
            attachment_id = str(meta.get("attachment_id") or "")
            source_type = str(meta.get("document_type") or "")
            if multi_source and attachment_id and attachment_id in used_attachments and len(selected) >= 2:
                continue
            selected.append(group)
            used_parent_ids.add(parent_id)
            if attachment_id:
                used_attachments.add(attachment_id)
            if source_type:
                used_source_types.add(source_type)
            if len(selected) >= top_k:
                break

        if attachment_intent and "pdf" not in used_source_types:
            for group in ranked:
                doc = group["doc"]
                if doc.metadata.get("document_type") != "pdf":
                    continue
                parent_id = self._parent_id(doc)
                if parent_id in used_parent_ids:
                    continue
                selected.append(group)
                used_parent_ids.add(parent_id)
                break

        if (attachment_intent or multi_source) and "email" not in used_source_types:
            for group in ranked:
                doc = group["doc"]
                if doc.metadata.get("document_type") != "email":
                    continue
                parent_id = self._parent_id(doc)
                if parent_id in used_parent_ids:
                    continue
                selected.append(group)
                break

        return selected[:top_k]

    def index_pdf(
        self,
        *,
        attachment_id: str,
        email_id: str,
        filename: str,
        path: Path,
        subject: str | None = None,
        sender: str | None = None,
    ) -> int:
        pages = extract_pdf_text(path)
        if not pages:
            return 0
        try:
            from langchain_core.documents import Document
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError as exc:  # pragma: no cover - exercised in configured runtime
            raise RuntimeError("Install LangChain core packages with `pip install -r requirements.txt`.") from exc

        documents = [
            Document(
                page_content=text,
                metadata={
                    "attachment_id": attachment_id,
                    "email_id": email_id,
                    "filename": filename,
                    "page": page,
                    "document_type": "pdf",
                    "subject": subject or "",
                    "sender": sender or "",
                },
            )
            for page, text in pages
        ]
        splitter = RecursiveCharacterTextSplitter(chunk_size=1600, chunk_overlap=220)
        chunks = splitter.split_documents(documents)
        ids = [
            f"{attachment_id}:{chunk.metadata.get('page', 0)}:{index}"
            for index, chunk in enumerate(chunks)
        ]
        for chunk, child_id in zip(chunks, ids):
            chunk.metadata["child_id"] = child_id
            chunk.metadata["source_id"] = attachment_id
            chunk.metadata["parent_text"] = chunk.page_content
        store = self._store()
        existing = store.get(where={"attachment_id": attachment_id})
        existing_ids = existing.get("ids", []) if existing else []
        if existing_ids:
            store.delete(ids=existing_ids)
        self._delete_fts_by_source(attachment_id)
        if chunks:
            store.add_documents(chunks, ids=ids)
            self._upsert_fts(chunks, ids)
        return len(chunks)

    def index_email(
        self,
        *,
        email_id: str,
        subject: str | None,
        sender: str | None,
        received_at: str | None,
        body: str,
        attachment_filenames: list[str] | None = None,
    ) -> int:
        text = body.strip()
        if not text:
            return 0
        try:
            from langchain_core.documents import Document
        except ImportError as exc:  # pragma: no cover - exercised in configured runtime
            raise RuntimeError("Install LangChain core packages with `pip install -r requirements.txt`.") from exc

        documents = self._build_email_documents(
            Document=Document,
            email_id=email_id,
            subject=subject,
            sender=sender,
            received_at=received_at,
            body=text,
            attachment_filenames=attachment_filenames or [],
        )
        ids = [f"email:{email_id}:{doc.metadata.get('chunk_type', 'chunk')}:{index}" for index, doc in enumerate(documents)]
        for doc, child_id in zip(documents, ids):
            doc.metadata["child_id"] = child_id
        store = self._store()
        existing = store.get(where={"source_id": f"email:{email_id}"})
        existing_ids = existing.get("ids", []) if existing else []
        if existing_ids:
            store.delete(ids=existing_ids)
        self._delete_fts_by_source(f"email:{email_id}")
        if documents:
            store.add_documents(documents, ids=ids)
            self._upsert_fts(documents, ids)
        return len(documents)

    def _build_email_documents(
        self,
        *,
        Document,
        email_id: str,
        subject: str | None,
        sender: str | None,
        received_at: str | None,
        body: str,
        attachment_filenames: list[str],
    ):
        current, history = split_email_thread(body)
        attachment_text = "\n".join(f"- {name}" for name in attachment_filenames if name)
        parent_text = compact_text(
            "\n".join(
                [
                    f"Subject: {subject or ''}",
                    f"Sender: {sender or ''}",
                    f"Received: {received_at or ''}",
                    f"Attachments: {', '.join(attachment_filenames) if attachment_filenames else 'None'}",
                    "",
                    "Current message:",
                    current,
                    "",
                    "Thread history:",
                    history or "None",
                ]
            )
        )
        base_meta = {
            "source_id": f"email:{email_id}",
            "document_type": "email",
            "attachment_id": "",
            "email_id": email_id,
            "filename": "Email body",
            "page": 0,
            "subject": subject or "",
            "sender": sender or "",
            "received_at": received_at or "",
            "parent_text": parent_text,
        }
        chunk_specs = [
            (
                "email_metadata",
                "\n".join(
                    [
                        f"Subject: {subject or ''}",
                        f"Sender: {sender or ''}",
                        f"Received: {received_at or ''}",
                    ]
                ),
            ),
            (
                "email_current_message",
                "\n".join(
                    [
                        f"Subject: {subject or ''}",
                        f"Sender: {sender or ''}",
                        "Current message:",
                        current,
                    ]
                ),
            ),
        ]
        if history:
            chunk_specs.append(
                (
                    "email_thread_history",
                    "\n".join(
                        [
                            f"Subject: {subject or ''}",
                            f"Sender: {sender or ''}",
                            "Thread history:",
                            history,
                        ]
                    ),
                )
            )
        if attachment_text:
            chunk_specs.append(
                (
                    "email_attachment_context",
                    "\n".join(
                        [
                            f"Subject: {subject or ''}",
                            "Attachment filenames:",
                            attachment_text,
                        ]
                    ),
                )
            )
        return [
            Document(
                page_content=compact_text(content),
                metadata={**base_meta, "chunk_type": chunk_type},
            )
            for chunk_type, content in chunk_specs
            if compact_text(content)
        ]

    def ask(self, question: str, *, top_k: int = 4) -> RagAnswer:
        if not question.strip():
            raise ValueError("Question cannot be empty.")
        if not self.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required before asking PDF questions.")
        try:
            from langchain_anthropic import ChatAnthropic
            from langchain_core.messages import HumanMessage, SystemMessage
        except ImportError as exc:  # pragma: no cover - exercised in configured runtime
            raise RuntimeError("Install LangChain Anthropic support with `pip install -r requirements.txt`.") from exc

        child_docs = self._hybrid_search(question, top_k=max(top_k, self.vector_candidates, self.bm25_candidates))
        child_docs = [
            doc
            for doc in child_docs
            if (
                (doc.metadata.get("document_type") == "email" and self.email_enabled)
                or (doc.metadata.get("document_type") != "email" and self.pdf_enabled)
            )
        ]
        docs = self._aggregate_parent_contexts(child_docs, top_k=top_k, question=question)
        if not docs:
            return RagAnswer(
                answer="I could not find relevant evidence in indexed MailMind data.",
                sources=[],
            )

        pii_session = PiiSession(self.pii_config)
        safe_question = pii_session.anonymize_text(question.strip()).text
        context_blocks: list[str] = []
        sources: list[RagSource] = []
        for index, doc in enumerate(docs, start=1):
            meta = doc.metadata
            raw_snippet = doc.page_content[:700].strip()
            raw_context_text = str(meta.get("parent_text") or raw_snippet)
            snippet = pii_session.anonymize_text(raw_snippet).text
            context_text = pii_session.anonymize_text(raw_context_text).text
            context_blocks.append(
                "\n".join(
                    [
                        f"[Source {index}]",
                        f"Type: {meta.get('document_type', 'pdf')}",
                        f"Matched child chunks: {', '.join(meta.get('matched_child_types') or [str(meta.get('chunk_type', ''))])}",
                        f"Retrieval channels: {meta.get('retrieval_channel', '')}",
                        f"Parent score: {meta.get('parent_group_score', '')}",
                        f"Filename: {meta.get('filename', '')}",
                        f"Email subject: {meta.get('subject', '')}",
                        f"Sender: {meta.get('sender', '')}",
                        f"Page: {meta.get('page', '')}",
                        f"Text: {context_text[:1800].strip()}",
                    ]
                )
            )
            sources.append(
                RagSource(
                    attachment_id=str(meta.get("attachment_id", "")),
                    email_id=str(meta.get("email_id", "")),
                    filename=str(meta.get("filename", "")),
                    page=int(meta.get("page") or 0),
                    snippet=snippet,
                    document_type=str(meta.get("document_type", "pdf")),
                    chunk_type=str(meta.get("chunk_type", "")) or None,
                    retrieval_channel=str(meta.get("retrieval_channel", "")) or None,
                    rerank_score=float(meta["rerank_score"]) if meta.get("rerank_score") is not None else None,
                    subject=str(meta.get("subject", "")) or None,
                    sender=str(meta.get("sender", "")) or None,
                )
            )

        prompt_path = Path("prompts/rag_answer.md")
        system_prompt = (
            prompt_path.read_text(encoding="utf-8")
            if prompt_path.exists()
            else "Answer only from the provided sources. If the sources do not support the answer, say so."
        )
        llm = ChatAnthropic(
            model=self.anthropic_model,
            anthropic_api_key=self.anthropic_api_key,
            temperature=0,
            max_tokens=700,
        )
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=(
                        "Question:\n"
                        f"{safe_question}\n\n"
                        "Retrieved MailMind sources from email bodies and PDF attachments:\n"
                        f"{'\n\n'.join(context_blocks)}"
                    )
                ),
            ]
        )
        if pii_session.rehydrating:
            sources = [
                RagSource(
                    attachment_id=source.attachment_id,
                    email_id=source.email_id,
                    filename=source.filename,
                    page=source.page,
                    snippet=pii_session.rehydrate_text(source.snippet),
                    document_type=source.document_type,
                    chunk_type=source.chunk_type,
                    retrieval_channel=source.retrieval_channel,
                    rerank_score=source.rerank_score,
                    subject=pii_session.rehydrate_text(source.subject or "") or source.subject,
                    sender=pii_session.rehydrate_text(source.sender or "") or source.sender,
                )
                for source in sources
            ]
        return RagAnswer(answer=pii_session.rehydrate_text(str(response.content).strip()), sources=sources)


class LocalSentenceTransformerEmbeddings:
    def __init__(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - exercised in configured runtime
            raise RuntimeError("Install sentence-transformers with `pip install -r requirements.txt`.") from exc
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text])[0]

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()
