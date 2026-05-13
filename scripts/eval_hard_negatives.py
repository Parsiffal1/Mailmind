from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mailmind.config import get_settings
from mailmind.rag_service import make_rag


def clean_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.:-]+", "_", value).strip("_")


def parse_pdf_label(label: str) -> tuple[str, int]:
    match = re.search(r"(.+?\.pdf)(?:\s+p\.(\d+))?", label, flags=re.IGNORECASE)
    if not match:
        return label, 1
    return match.group(1), int(match.group(2) or 1)


def source_subject(case_id: str, source: dict) -> str:
    return f"{case_id} {source['source_label']}"


def add_pdf_source(rag, Document, *, case_id: str, source: dict, role: str) -> int:
    filename, page = parse_pdf_label(source["source_label"])
    attachment_id = clean_id(f"{case_id}:{source['source_label']}:{role}")
    child_id = f"{attachment_id}:{page}:0"
    doc = Document(
        page_content=source["text"],
        metadata={
            "child_id": child_id,
            "source_id": attachment_id,
            "attachment_id": attachment_id,
            "email_id": f"{case_id}:{role}",
            "filename": filename,
            "page": page,
            "document_type": "pdf",
            "subject": source_subject(case_id, source),
            "sender": "synthetic-hard-negative",
            "parent_text": source["text"],
            "source_label": source["source_label"],
            "case_id": case_id,
            "source_role": role,
        },
    )
    existing = rag._store().get(where={"attachment_id": attachment_id})
    existing_ids = existing.get("ids", []) if existing else []
    if existing_ids:
        rag._store().delete(ids=existing_ids)
    rag._delete_fts_by_source(attachment_id)
    rag._store().add_documents([doc], ids=[child_id])
    rag._upsert_fts([doc], [child_id])
    return 1


def add_email_source(rag, *, case_id: str, source: dict, role: str) -> int:
    return rag.index_email(
        email_id=clean_id(f"{case_id}:{source['source_label']}:{role}"),
        subject=source_subject(case_id, source),
        sender="synthetic-hard-negative",
        received_at="2027-01-01T00:00:00Z",
        body=source["text"],
        attachment_filenames=[],
    )


def index_cases(rag, dataset_path: Path) -> dict:
    from langchain_core.documents import Document

    cases = json.loads(dataset_path.read_text(encoding="utf-8"))["hard_negative_cases"]
    stats = {
        "cases": len(cases),
        "email_sources": 0,
        "email_chunks": 0,
        "pdf_sources": 0,
        "pdf_chunks": 0,
        "negative_sources": 0,
    }
    for case in cases:
        sources = [("correct", case["correct_source"])] + [
            (f"negative_{index}", source)
            for index, source in enumerate(case.get("negative_sources", []), start=1)
        ]
        stats["negative_sources"] += max(0, len(sources) - 1)
        for role, source in sources:
            if source["source_type"] == "pdf_attachment":
                stats["pdf_chunks"] += add_pdf_source(rag, Document, case_id=case["case_id"], source=source, role=role)
                stats["pdf_sources"] += 1
            else:
                stats["email_chunks"] += add_email_source(rag, case_id=case["case_id"], source=source, role=role)
                stats["email_sources"] += 1
    return stats


def retrieved_contexts(rag, question: str, *, top_k: int):
    child_docs = rag._hybrid_search(question, top_k=max(top_k, rag.vector_candidates, rag.bm25_candidates))
    return rag._aggregate_parent_contexts(child_docs, top_k=top_k, question=question)


def doc_text(doc) -> str:
    meta = doc.metadata
    return "\n".join(
        [
            str(meta.get("source_label") or ""),
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
    filename = str(meta.get("filename") or "")
    label = str(meta.get("source_label") or "")
    if not label and filename and filename != "Email body":
        label = filename
    if not label:
        label = str(meta.get("subject") or filename or "Email body")
    chunk_type = str(meta.get("chunk_type") or "")
    channel = str(meta.get("retrieval_channel") or "")
    score = meta.get("rerank_score")
    score_text = f" score={float(score):.3f}" if score is not None else ""
    return " | ".join(part for part in [label, chunk_type, channel + score_text] if part)


def first_rank_containing(docs, substring: str) -> int | None:
    target = substring.lower()
    for index, doc in enumerate(docs, start=1):
        if target in doc_text(doc).lower():
            return index
    return None


def evaluate(rag, dataset_path: Path, *, top_k: int) -> dict:
    cases = json.loads(dataset_path.read_text(encoding="utf-8"))["hard_negative_cases"]
    rows = []
    top1 = 0
    in_topk = 0
    beats_negatives = 0
    no_misleading_top1 = 0
    for case in cases:
        docs = retrieved_contexts(rag, case["question"], top_k=top_k)
        expected = case["correct_source"]["expected_substring"]
        correct_rank = first_rank_containing(docs, expected)
        negative_ranks = [
            first_rank_containing(docs, source["misleading_substring"])
            for source in case.get("negative_sources", [])
        ]
        visible_negative_ranks = [rank for rank in negative_ranks if rank is not None]
        best_negative = min(visible_negative_ranks) if visible_negative_ranks else None
        correct_top1 = correct_rank == 1
        correct_in_topk = correct_rank is not None
        correct_beats = correct_rank is not None and (
            best_negative is None or correct_rank < best_negative
        )
        misleading_top1 = bool(visible_negative_ranks and min(visible_negative_ranks) == 1)
        top1 += int(correct_top1)
        in_topk += int(correct_in_topk)
        beats_negatives += int(correct_beats)
        no_misleading_top1 += int(not misleading_top1)
        rows.append(
            {
                "case_id": case["case_id"],
                "question": case["question"],
                "correct_rank": correct_rank,
                "best_negative_rank": best_negative,
                "correct_top1": correct_top1,
                "correct_in_topk": correct_in_topk,
                "correct_beats_negatives": correct_beats,
                "misleading_top1": misleading_top1,
                "retrieved": [doc_label(doc) for doc in docs],
                "why_naive_retrieval_might_fail": case.get("why_naive_retrieval_might_fail", ""),
            }
        )
    total = len(cases)
    return {
        "rows": rows,
        "total": total,
        "top1": top1,
        "in_topk": in_topk,
        "beats_negatives": beats_negatives,
        "no_misleading_top1": no_misleading_top1,
        "top1_rate": top1 / total if total else 0.0,
        "topk_rate": in_topk / total if total else 0.0,
        "beats_negative_rate": beats_negatives / total if total else 0.0,
        "no_misleading_top1_rate": no_misleading_top1 / total if total else 0.0,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Evaluate MailMind RAG against hard-negative source sets.")
    parser.add_argument("--dataset-dir", default="data/tmp_rag_hard_negatives")
    parser.add_argument("--index-dir", default="data/tmp_hard_negative_chroma")
    parser.add_argument("--mode", choices=["hybrid", "vector"], default="hybrid")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--keep-index", action="store_true")
    args = parser.parse_args()

    dataset_path = Path(args.dataset_dir) / "hard_negative_cases.json"
    index_dir = Path(args.index_dir)
    if args.index_dir == parser.get_default("index_dir"):
        index_dir = index_dir.with_name(f"{index_dir.name}_{args.mode}")
    if index_dir.exists() and not args.keep_index:
        shutil.rmtree(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    settings = type(
        "HardNegativeSettings",
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

    stats = index_cases(rag, dataset_path)
    result = evaluate(rag, dataset_path, top_k=args.top_k)

    print(f"Mode: {args.mode}")
    print(f"Indexed: {stats}")
    print(f"Cases: {result['total']}")
    print(f"Correct top-1@{args.top_k}: {result['top1']}/{result['total']} = {result['top1_rate']:.2%}")
    print(f"Correct in top-{args.top_k}: {result['in_topk']}/{result['total']} = {result['topk_rate']:.2%}")
    print(
        f"Correct beats visible negatives@{args.top_k}: "
        f"{result['beats_negatives']}/{result['total']} = {result['beats_negative_rate']:.2%}"
    )
    print(
        f"No misleading source at rank 1: "
        f"{result['no_misleading_top1']}/{result['total']} = {result['no_misleading_top1_rate']:.2%}"
    )
    print()
    for row in result["rows"]:
        if row["correct_top1"]:
            mark = "PASS"
        elif row["correct_in_topk"]:
            mark = "WEAK"
        else:
            mark = "FAIL"
        print(
            f"[{mark}] {row['case_id']}: correct_rank={row['correct_rank']} "
            f"best_negative_rank={row['best_negative_rank']}"
        )
        print(f"  question: {row['question']}")
        for label in row["retrieved"]:
            print(f"  - {label}")


if __name__ == "__main__":
    main()
