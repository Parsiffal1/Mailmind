# MailMind RAG Evaluation Results

Date: 2026-05-13  
Project: MailMind local-first Gmail intelligence agent

## Summary

This report summarizes three retrieval evaluations for the current MailMind RAG system:

- Small synthetic source recall set
- Hard-negative retrieval set
- 50-case expanded synthetic benchmark

The current RAG stack uses:

- Local BGE-M3 embeddings through `sentence-transformers`
- ChromaDB for dense vector retrieval
- SQLite FTS5 BM25 keyword retrieval
- RRF-style hybrid candidate fusion
- BGE reranker over child chunks
- Parent-child retrieval before sending source-labeled context to Claude
- Structure-aware email chunks:
  - `email_metadata`
  - `email_current_message`
  - `email_thread_history`
  - `email_attachment_context`

Overall result: the hybrid system is clearly stronger than vector-only retrieval on the 50-case benchmark, but the remaining weakness is multi-source and attachment-linked retrieval, especially when a follow-up email refers to an attached rule or form.

## No-Lookahead Evaluation Method

For all synthetic datasets, evaluation was done with no answer leakage:

- Indexed only email bodies and PDF attachment text.
- Did not index `expected_answer`, `expected_source_substring`, `misleading_substring`, labels, evaluator notes, or explanations.
- Loaded eval labels only after indexing completed.
- Used temporary Chroma/FTS directories so the real Gmail index was not modified.

Temporary index directories used:

- `data/tmp_synth_chroma_hybrid`
- `data/tmp_synth_chroma_vector`
- `data/tmp_hard_negative_chroma_hybrid`
- `data/tmp_hard_negative_chroma_vector`

## Commands

```powershell
python scripts/eval_synthetic_rag.py --dataset-dir data\tmp_rag_synth_dataset --mode hybrid --top-k 4
python scripts/eval_synthetic_rag.py --dataset-dir data\tmp_rag_synth_dataset --mode vector --top-k 4

python scripts/eval_hard_negatives.py --mode hybrid --top-k 4
python scripts/eval_hard_negatives.py --mode vector --top-k 4

python scripts/eval_synthetic_rag.py --dataset-dir data\tmp_rag_eval_50case --mode hybrid --top-k 4
python scripts/eval_synthetic_rag.py --dataset-dir data\tmp_rag_eval_50case --mode vector --top-k 4
python scripts/eval_synthetic_rag.py --dataset-dir data\tmp_rag_eval_50case --mode hybrid --top-k 8

python -m pytest -q
```

## Dataset 1: Small Synthetic RAG Set

Files:

- `synthetic_mailmind_rag_eval_v1_small.json`
- `rag_eval.json`

Dataset stats:

- 13 cases
- 17 eval questions
- 14 answerable questions
- 3 unanswerable questions
- 9 PDF cases
- 3 conflict-resolution cases

Indexed corpus:

| Source | Count |
| --- | ---: |
| Emails | 18 |
| Email chunks | 47 |
| PDFs | 10 |
| PDF chunks | 17 |

Results:

| Mode | Top-k | Any-source Recall | Full-source Recall |
| --- | ---: | ---: | ---: |
| Hybrid + BM25 + rerank | 4 | 14/14 = 100.00% | 13/14 = 92.86% |
| Vector-only | 4 | 14/14 = 100.00% | 13/14 = 92.86% |

Finding:

- The small set is easy enough that BGE-M3 vector-only already performs well.
- Hybrid and reranking did not improve the aggregate recall score on this dataset.
- Hybrid still produced better-looking rankings for some PDF/page-specific cases.
- The only partial case was a multi-source question where the system retrieved 2 of 3 expected sources.

## Dataset 2: Hard-Negative Set

Files:

- `hard_negative_cases.json`
- `README.md`
- `README.json`

Dataset stats:

- 12 hard-negative cases
- Each case has 1 correct source and at least 2 negative sources
- Covers same-keyword wrong date, wrong sender/context, old policy, version mismatch, footer noise, quoted outdated reply, PDF table wrong row, and similar semantic meaning with wrong entity

Indexed corpus:

| Source | Count |
| --- | ---: |
| Cases | 12 |
| Email sources | 20 |
| Email chunks | 40 |
| PDF sources | 16 |
| PDF chunks | 16 |
| Negative sources | 24 |

Results:

| Mode | Top-k | Correct Top-1 | Correct in Top-k | Correct Beats Visible Negatives | No Misleading Rank-1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hybrid + BM25 + rerank | 4 | 10/12 = 83.33% | 12/12 = 100.00% | 10/12 = 83.33% | 10/12 = 83.33% |
| Vector-only | 4 | 11/12 = 91.67% | 12/12 = 100.00% | 10/12 = 83.33% | 10/12 = 83.33% |

Important cases:

| Case | Result | Notes |
| --- | --- | --- |
| `HN005` | Weak for hybrid | Reranker ranked a semantically similar `International_Hiring_FAQ` source above the correct `Employment_Record_Guide` source. |
| `HN012` | Weak for both modes | The old `CPT_Request_Checklist_v3` or a generic follow-up email can outrank the current `CPT_Request_Checklist_v4` source. |
| `HN008` | Source-level pass, row-level risk | The correct and misleading table rows are on the same PDF page, so source-level recall passes even though row-level reasoning remains hard. |

Finding:

- Retrieval recall is strong: correct source appeared in top-4 for all 12 cases.
- Hybrid is not automatically better than vector-only on every hard-negative set.
- The current reranker can overvalue semantically similar sources if the query does not explicitly anchor version, entity, or attachment relationship.
- This validates the need for source-aware reranking and attachment-aware parent linking.

## Dataset 3: 50-Case Expanded Benchmark

Files:

- `synthetic_mailmind_rag_eval_v2_50case_expanded.json`
- `rag_eval.json`
- `README.md`
- `README.json`

Dataset stats:

| Metric | Count |
| --- | ---: |
| Cases | 50 |
| Eval questions | 97 |
| Answerable questions | 91 |
| Unanswerable questions | 6 |
| PDF cases | 32 |
| Email-only cases | 18 |
| Multi-source items | 16 |
| Conflict-resolution items | 8 |
| Hard items | 81 |

Indexed corpus:

| Source | Count |
| --- | ---: |
| Emails | 66 |
| Email chunks | 164 |
| PDFs | 32 |
| PDF chunks | 68 |

### Top-k = 4 Results

| Mode | Top-1 Source Recall | Any-source Recall | Full-source Recall | MRR |
| --- | ---: | ---: | ---: | ---: |
| Hybrid + BM25 + rerank | 60/91 = 65.93% | 67/91 = 73.63% | 56/91 = 61.54% | 0.690 |
| Vector-only | 44/91 = 48.35% | 53/91 = 58.24% | 42/91 = 46.15% | 0.522 |

Interpretation:

- Hybrid is clearly stronger on the larger benchmark.
- Compared with vector-only, hybrid improved:
  - Top-1 source recall by 17.58 percentage points
  - Any-source recall by 15.39 percentage points
  - Full-source recall by 15.39 percentage points
  - MRR from 0.522 to 0.690

### Hybrid Top-k = 8 Results

| Mode | Top-k | Top-1 Source Recall | Any-source Recall | Full-source Recall | MRR |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hybrid + BM25 + rerank | 8 | 60/91 = 65.93% | 74/91 = 81.32% | 64/91 = 70.33% | 0.703 |

Interpretation:

- Increasing top-k from 4 to 8 improves recall but not top-1 ranking.
- This means the system often has the right source somewhere nearby, but the ranking and parent-source aggregation are not always strong enough.

### Tag Breakdown, Hybrid Top-k = 4

| Tag | Top-1 | Any-source | Full-source |
| --- | ---: | ---: | ---: |
| `source_grounding` | 54/77 | 61/77 | 54/77 |
| `pdf_attachment` | 34/58 | 40/58 | 29/58 |
| `email_body` | 26/33 | 27/33 | 27/33 |
| `multi_source` | 15/32 | 20/32 | 9/32 |
| `parent_child` | 15/32 | 20/32 | 9/32 |
| `reranking` | 14/29 | 16/29 | 12/29 |
| `bm25_keyword` | 25/26 | 25/26 | 25/26 |
| `conflict_resolution` | 7/13 | 8/13 | 8/13 |
| `vector_semantic` | 12/12 | 12/12 | 12/12 |
| `hard_negative` | 6/6 | 6/6 | 6/6 |
| `unanswerable` | 0/6 | 0/6 | 0/6 |

### Tag Breakdown, Vector-only Top-k = 4

| Tag | Top-1 | Any-source | Full-source |
| --- | ---: | ---: | ---: |
| `source_grounding` | 39/77 | 48/77 | 41/77 |
| `pdf_attachment` | 30/58 | 35/58 | 24/58 |
| `email_body` | 14/33 | 18/33 | 18/33 |
| `multi_source` | 12/32 | 15/32 | 4/32 |
| `parent_child` | 12/32 | 15/32 | 4/32 |
| `reranking` | 11/29 | 15/29 | 11/29 |
| `bm25_keyword` | 17/26 | 19/26 | 19/26 |
| `conflict_resolution` | 5/13 | 8/13 | 8/13 |
| `vector_semantic` | 9/12 | 9/12 | 9/12 |
| `hard_negative` | 3/6 | 3/6 | 3/6 |
| `unanswerable` | 0/6 | 0/6 | 0/6 |

### Tag Breakdown, Hybrid Top-k = 8

| Tag | Top-1 | Any-source | Full-source |
| --- | ---: | ---: | ---: |
| `source_grounding` | 54/77 | 66/77 | 61/77 |
| `pdf_attachment` | 34/58 | 46/58 | 36/58 |
| `email_body` | 26/33 | 28/33 | 28/33 |
| `multi_source` | 15/32 | 26/32 | 16/32 |
| `parent_child` | 15/32 | 26/32 | 16/32 |
| `reranking` | 14/29 | 18/29 | 13/29 |
| `bm25_keyword` | 25/26 | 26/26 | 26/26 |
| `conflict_resolution` | 7/13 | 8/13 | 8/13 |
| `vector_semantic` | 12/12 | 12/12 | 12/12 |
| `hard_negative` | 6/6 | 6/6 | 6/6 |
| `unanswerable` | 0/6 | 0/6 | 0/6 |

## Main Failure Patterns

### 1. Multi-source Questions

Full-source recall for `multi_source` was low:

- Hybrid top-k=4: 9/32
- Hybrid top-k=8: 16/32

This means the system often finds one relevant source but not all required sources. These questions usually require combining:

- Follow-up email
- Referenced attachment
- Older/corrected message
- PDF page with actual rule text

### 2. Parent-child Attachment Linking

The `parent_child` tag follows the same pattern as `multi_source`:

- Hybrid top-k=4 full-source: 9/32
- Hybrid top-k=8 full-source: 16/32

Common failure:

- The query mentions "this form", "underlying rule", "the attachment", or "follow-up".
- The retriever finds the follow-up email but does not reliably pull the linked attachment parent context.

### 3. Attachment Rule Questions

Many misses occurred on questions like:

- "What is the underlying rule stated in the attachment?"
- "What additional timing or submission detail is given in the attachment?"
- "What concrete instruction is actually present in the current attachment?"

This suggests the system needs stronger attachment-aware boosting when the query explicitly asks about attachment contents.

### 4. Conflict Resolution

Conflict-resolution results are moderate:

- Hybrid top-k=4 full-source: 8/13
- Hybrid top-k=8 full-source: 8/13

Top-k does not fix these cases, so the issue is ranking and source interpretation, not candidate count.

### 5. Unanswerable Questions

The retrieval evaluator does not directly measure refusal quality because it only checks source recall. The unanswerable rows correctly have zero expected source substrings, but answer-level evaluation is still needed to know whether Claude refuses unsupported questions.

## Engineering Conclusions

The current RAG implementation is no longer naive chunking. It already has:

- Structure-aware email chunking
- Parent-child context reconstruction
- Dense retrieval
- BM25 retrieval
- Hybrid fusion
- Reranking
- Source-grounded answer prompting

However, the evaluation shows the next meaningful improvements should be:

1. Attachment-aware parent linking
   - If a retrieved email has attachment filenames, boost or include those attachment chunks.
   - If the query mentions "attachment", "form", "guide", "checklist", "PDF", "underlying rule", or "this form", retrieve attached PDF parents alongside the email.

2. Source-aware reranking
   - Add features beyond reranker score:
     - source type match
     - attachment intent match
     - recency/current/corrected signals
     - version number signals such as `v2`, `v3`, `v4`, `current`, `updated`, `corrected`
     - exact phrase coverage

3. Multi-source expansion
   - After top child retrieval, expand from the top email parent to linked attachments.
   - Expand from attachment hits back to the source email.
   - Use grouped source diversity so top-k is not filled by near-duplicate pages.

4. Table-aware PDF chunking
   - Preserve rows as separate retrievable units.
   - Add row metadata for table-like text.
   - This is important for cases where the correct and misleading answer are on the same PDF page.

5. Answer-level evaluation
   - Add a second eval layer that calls Claude and scores:
     - groundedness
     - citation correctness
     - refusal accuracy
     - whether answer uses misleading source text

## 2026-05-13 Improvement Pass

After the first evaluation pass, MailMind implemented the first retrieval-side improvements from the improvement plan:

- Query intent detection:
  - attachment intent
  - multi-source intent
  - conflict/current intent
  - table intent
- Source-aware scoring after reranking:
  - exact keyword bonus
  - attachment intent bonus
  - current/corrected/revised bonus
  - version bonus
  - source type match bonus
  - attachment link bonus
  - outdated/legacy penalty
- Attachment-aware expansion:
  - email hit -> linked PDF attachment chunks
  - PDF hit -> source email context
- Diversity-aware parent selection:
  - avoids overfilling all context slots with the same parent/source
  - forces PDF context for attachment-oriented questions when possible

### Post-improvement Hard-negative Results

| Mode | Top-k | Correct Top-1 | Correct in Top-k | Correct Beats Visible Negatives | No Misleading Rank-1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hybrid + BM25 + rerank, before | 4 | 10/12 = 83.33% | 12/12 = 100.00% | 10/12 = 83.33% | 10/12 = 83.33% |
| Hybrid + BM25 + rerank, after | 4 | 12/12 = 100.00% | 12/12 = 100.00% | 11/12 = 91.67% | 11/12 = 91.67% |

Hard-negative improvements:

- `HN005` improved: the correct `Employment_Record_Guide.pdf` source now ranks above the semantically similar but wrong `International_Hiring_FAQ` source.
- `HN012` improved: the current `CPT_Request_Checklist_v4.pdf` source now ranks above the older `v3` checklist.
- One table-row style case still has source-level ambiguity because correct and misleading evidence can be on the same PDF page.

### Post-improvement 50-case Results

| Mode | Top-k | Top-1 Source Recall | Any-source Recall | Full-source Recall | MRR |
| --- | ---: | ---: | ---: | ---: | ---: |
| Hybrid before | 4 | 60/91 = 65.93% | 67/91 = 73.63% | 56/91 = 61.54% | 0.690 |
| Hybrid after | 4 | 58/91 = 63.74% | 71/91 = 78.02% | 59/91 = 64.84% | 0.691 |

Tag-level changes on the 50-case benchmark:

| Tag | Before Full-source | After Full-source | Change |
| --- | ---: | ---: | ---: |
| `pdf_attachment` | 29/58 | 32/58 | +3 |
| `multi_source` | 9/32 | 11/32 | +2 |
| `parent_child` | 9/32 | 11/32 | +2 |
| `reranking` | 12/29 | 15/29 | +3 |
| `hard_negative` | 6/6 | 6/6 | 0 |

Interpretation:

- The improvement pass increases source coverage and full-source recall.
- It slightly lowers top-1 source recall on the 50-case benchmark because source-aware expansion can bring a relevant PDF source above the exact email source.
- This is a useful tradeoff for multi-source RAG, but the next tuning pass should separate "top answer source" scoring from "context coverage" selection.

Next tuning target:

- Keep source-aware expansion for context coverage.
- Preserve BGE reranker top-1 more aggressively for simple single-source questions.
- Apply stronger expansion only when attachment, multi-source, or conflict intent is detected.

## Test Status

Unit tests passed:

```text
29 passed
```

## Current Resume-Friendly Claim

Based on these results, it is accurate to describe the RAG part as:

> Built and evaluated a local-first email/PDF RAG system using structure-aware email chunking, parent-child retrieval, local BGE-M3 embeddings, ChromaDB, SQLite FTS5 BM25 hybrid search, reranking, and source-grounded Claude answers. Added synthetic and hard-negative retrieval evaluation harnesses measuring top-1 source recall, source recall@k, full-source recall, MRR, and tag-level failure patterns.
