from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mailmind.config import get_settings
from mailmind.rag_service import make_rag


def source_label(doc) -> str:
    meta = doc.metadata
    parts = [
        str(meta.get("filename") or ""),
        str(meta.get("subject") or ""),
        str(meta.get("sender") or ""),
        str(meta.get("chunk_type") or ""),
    ]
    return " | ".join(part for part in parts if part)


def hit_expected(labels: list[str], expected_sources: list[str]) -> bool:
    haystack = "\n".join(labels).lower()
    return any(expected.lower() in haystack for expected in expected_sources)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Evaluate MailMind RAG retrieval source recall.")
    parser.add_argument("--dataset", default="eval/rag_eval.json", help="Path to JSON eval dataset.")
    parser.add_argument("--top-k", type=int, default=None, help="Number of retrieved sources to score.")
    parser.add_argument("--mode", choices=["hybrid", "vector"], default="hybrid")
    args = parser.parse_args()

    settings = get_settings()
    rag = make_rag(settings)
    if args.mode == "vector":
        rag.hybrid_enabled = False
        rag.rerank_enabled = False

    top_k = args.top_k or settings.rag_top_k
    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    hits = 0
    rows = []
    for item in dataset:
        docs = rag._hybrid_search(item["question"], top_k=top_k)
        labels = [source_label(doc) for doc in docs]
        hit = hit_expected(labels, item["expected_sources"])
        hits += int(hit)
        rows.append(
            {
                "question": item["question"],
                "hit": hit,
                "expected": item["expected_sources"],
                "retrieved": labels,
            }
        )

    recall = hits / len(dataset) if dataset else 0
    print(f"Mode: {args.mode}")
    print(f"Recall@{top_k}: {hits}/{len(dataset)} = {recall:.2%}")
    print()
    for row in rows:
        mark = "PASS" if row["hit"] else "MISS"
        print(f"[{mark}] {row['question']}")
        print(f"  expected: {', '.join(row['expected'])}")
        for label in row["retrieved"]:
            print(f"  - {label}")


if __name__ == "__main__":
    main()
