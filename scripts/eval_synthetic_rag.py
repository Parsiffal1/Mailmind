from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mailmind.config import get_settings
from mailmind.rag_service import make_rag


def page_docs_from_markdown(Document, *, email: dict, attachment: dict) -> list:
    docs = []
    pages = str(attachment.get("pdf_markdown") or "").split("---PAGE BREAK---")
    for index, raw_page in enumerate(pages, start=1):
        text = raw_page.strip()
        if not text:
            continue
        attachment_id = attachment["attachment_id"]
        child_id = f"{attachment_id}:{index}:0"
        parent_text = text
        docs.append(
            Document(
                page_content=text,
                metadata={
                    "child_id": child_id,
                    "source_id": attachment_id,
                    "attachment_id": attachment_id,
                    "email_id": email["email_id"],
                    "filename": attachment["filename"],
                    "page": index,
                    "document_type": "pdf",
                    "subject": email.get("subject") or "",
                    "sender": email.get("from") or "",
                    "parent_text": parent_text,
                },
            )
        )
    return docs


def index_corpus(rag, dataset_path: Path) -> dict:
    from langchain_core.documents import Document

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    email_count = 0
    email_chunks = 0
    pdf_count = 0
    pdf_chunks = 0
    for case in dataset["test_cases"]:
        for email in case.get("emails", []):
            attachments = email.get("attachments") or []
            attachment_filenames = [attachment.get("filename", "") for attachment in attachments]
            email_chunks += rag.index_email(
                email_id=email["email_id"],
                subject=email.get("subject"),
                sender=email.get("from"),
                received_at=email.get("sent_at"),
                body=email.get("body_text") or "",
                attachment_filenames=attachment_filenames,
            )
            email_count += 1
            for attachment in attachments:
                if attachment.get("mime_type") != "application/pdf":
                    continue
                docs = page_docs_from_markdown(Document, email=email, attachment=attachment)
                ids = [doc.metadata["child_id"] for doc in docs]
                rag._delete_fts_by_source(attachment["attachment_id"])
                existing = rag._store().get(where={"attachment_id": attachment["attachment_id"]})
                existing_ids = existing.get("ids", []) if existing else []
                if existing_ids:
                    rag._store().delete(ids=existing_ids)
                rag._store().add_documents(docs, ids=ids)
                rag._upsert_fts(docs, ids)
                pdf_count += 1
                pdf_chunks += len(docs)
    return {
        "emails": email_count,
        "email_chunks": email_chunks,
        "pdfs": pdf_count,
        "pdf_chunks": pdf_chunks,
    }


def retrieved_contexts(rag, question: str, *, top_k: int):
    child_docs = rag._hybrid_search(question, top_k=max(top_k, rag.vector_candidates, rag.bm25_candidates))
    return rag._aggregate_parent_contexts(child_docs, top_k=top_k, question=question)


def doc_text(doc) -> str:
    meta = doc.metadata
    return "\n".join(
        [
            str(meta.get("filename") or ""),
            str(meta.get("subject") or ""),
            str(meta.get("sender") or ""),
            str(meta.get("chunk_type") or ""),
            str(meta.get("parent_text") or doc.page_content),
            doc.page_content,
        ]
    )


def doc_label(doc) -> str:
    meta = doc.metadata
    label = str(meta.get("filename") or "Email body")
    subject = str(meta.get("subject") or "")
    page = meta.get("page")
    chunk_type = str(meta.get("chunk_type") or "")
    suffix = f" p.{page}" if page else ""
    return " | ".join(part for part in [label + suffix, subject, chunk_type] if part)


def evaluate(rag, eval_path: Path, *, top_k: int) -> dict:
    eval_data = json.loads(eval_path.read_text(encoding="utf-8"))["items"]
    rows = []
    answerable = 0
    full_hits = 0
    any_hits = 0
    top1_hits = 0
    reciprocal_rank_sum = 0.0
    refused = 0
    tag_stats: dict[str, dict] = {}
    for item in eval_data:
        docs = retrieved_contexts(rag, item["question"], top_k=top_k)
        doc_texts = [doc_text(doc).lower() for doc in docs]
        haystack = "\n".join(doc_texts)
        expected = [str(value).lower() for value in item.get("expected_source_substrings", [])]
        doc_hit_counts = [sum(1 for value in expected if value in text) for text in doc_texts]
        first_hit_rank = next((index for index, count in enumerate(doc_hit_counts, start=1) if count), None)
        hits = [value for value in expected if value in haystack]
        should_refuse = bool(item.get("should_refuse"))
        if should_refuse:
            refused += 1
        else:
            answerable += 1
            full_hit = bool(expected) and len(hits) == len(expected)
            any_hit = bool(hits)
            top1_hit = doc_hit_counts[0] > 0 if doc_hit_counts else False
            full_hits += int(full_hit)
            any_hits += int(any_hit)
            top1_hits += int(top1_hit)
            reciprocal_rank_sum += (1.0 / first_hit_rank) if first_hit_rank else 0.0
            for tag in item.get("tags", []):
                stat = tag_stats.setdefault(tag, {"total": 0, "any_hits": 0, "full_hits": 0, "top1_hits": 0})
                stat["total"] += 1
                stat["any_hits"] += int(any_hit)
                stat["full_hits"] += int(full_hit)
                stat["top1_hits"] += int(top1_hit)
        rows.append(
            {
                "id": item["id"],
                "question": item["question"],
                "should_refuse": should_refuse,
                "expected_count": len(expected),
                "hit_count": len(hits),
                "full_hit": bool(expected) and len(hits) == len(expected),
                "any_hit": bool(hits),
                "top1_hit": doc_hit_counts[0] > 0 if doc_hit_counts else False,
                "first_hit_rank": first_hit_rank,
                "tags": item.get("tags", []),
                "retrieved": [doc_label(doc) for doc in docs],
            }
        )
    return {
        "rows": rows,
        "answerable": answerable,
        "unanswerable": refused,
        "full_hits": full_hits,
        "any_hits": any_hits,
        "top1_hits": top1_hits,
        "mrr": reciprocal_rank_sum / answerable if answerable else 0.0,
        "full_recall": full_hits / answerable if answerable else 0.0,
        "any_recall": any_hits / answerable if answerable else 0.0,
        "top1_recall": top1_hits / answerable if answerable else 0.0,
        "tag_stats": tag_stats,
    }


def find_corpus_path(dataset_dir: Path, explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path)
    matches = sorted(dataset_dir.glob("synthetic_mailmind_rag_eval*.json"))
    if not matches:
        raise FileNotFoundError(f"No synthetic_mailmind_rag_eval*.json file found in {dataset_dir}")
    return matches[0]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run synthetic MailMind RAG retrieval evaluation.")
    parser.add_argument("--dataset-dir", default="data/tmp_rag_synth_dataset")
    parser.add_argument("--corpus", default=None, help="Optional explicit corpus JSON path.")
    parser.add_argument("--index-dir", default="data/tmp_synth_chroma")
    parser.add_argument("--mode", choices=["hybrid", "vector"], default="hybrid")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--keep-index", action="store_true")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    index_dir = Path(args.index_dir)
    if args.index_dir == parser.get_default("index_dir"):
        index_dir = index_dir.with_name(f"{index_dir.name}_{args.mode}")
    if index_dir.exists() and not args.keep_index:
        shutil.rmtree(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    settings = type(
        "SyntheticSettings",
        (),
        {
            **settings.__dict__,
            "chroma_dir": index_dir,
            "rag_vector_candidates": 30,
            "rag_bm25_candidates": 30,
            "rag_rerank_enabled": args.mode == "hybrid",
            "rag_hybrid_enabled": args.mode == "hybrid",
        },
    )()
    rag = make_rag(settings)
    if args.mode == "vector":
        rag.hybrid_enabled = False
        rag.rerank_enabled = False

    corpus_path = find_corpus_path(dataset_dir, args.corpus)
    corpus_stats = index_corpus(rag, corpus_path)
    result = evaluate(rag, dataset_dir / "rag_eval.json", top_k=args.top_k)

    print(f"Mode: {args.mode}")
    print(f"Corpus: {corpus_path}")
    print(f"Indexed: {corpus_stats}")
    print(f"Answerable questions: {result['answerable']}  Unanswerable questions: {result['unanswerable']}")
    print(f"Top-1 source recall@{args.top_k}: {result['top1_hits']}/{result['answerable']} = {result['top1_recall']:.2%}")
    print(f"Any-source recall@{args.top_k}: {result['any_hits']}/{result['answerable']} = {result['any_recall']:.2%}")
    print(f"Full-source recall@{args.top_k}: {result['full_hits']}/{result['answerable']} = {result['full_recall']:.2%}")
    print(f"MRR@{args.top_k}: {result['mrr']:.3f}")
    print()
    print("Tag breakdown:")
    for tag, stat in sorted(result["tag_stats"].items(), key=lambda item: (-item[1]["total"], item[0])):
        print(
            f"  {tag}: top1={stat['top1_hits']}/{stat['total']} "
            f"any={stat['any_hits']}/{stat['total']} full={stat['full_hits']}/{stat['total']}"
        )
    print()
    for row in result["rows"]:
        if row["should_refuse"]:
            mark = "UNANSWERABLE"
        elif row["full_hit"]:
            mark = "PASS"
        elif row["any_hit"]:
            mark = "PARTIAL"
        else:
            mark = "MISS"
        print(f"[{mark}] {row['id']}: {row['question']}")
        print(f"  expected hits: {row['hit_count']}/{row['expected_count']}")
        for label in row["retrieved"]:
            print(f"  - {label}")


if __name__ == "__main__":
    main()
