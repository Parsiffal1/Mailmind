# MailMind Demo Flow

This demo is designed for a 4-6 minute portfolio, resume, or interview walkthrough. It shows MailMind as a local-first Gmail intelligence agent with task extraction, AI search/RAG, privacy controls, and a dashboard UI.

## Demo Goal

Show that MailMind can:

1. Pull Gmail messages locally through read-only OAuth.
2. Extract action items and deadlines with Claude.
3. Store normalized emails, tasks, attachments, logs, and RAG status in SQLite.
4. Search indexed Gmail email bodies and PDF attachments through local BGE-M3 embeddings, hybrid retrieval, reranking, and Claude grounded answers.
5. Let the user choose privacy behavior with PII `off` or `rehydrated` mode.

## Demo Setup

Run the backend:

```powershell
python -m mailmind.api
```

Optional worker:

```powershell
python -m mailmind.worker
```

Open:

```text
http://127.0.0.1:8000/
```

Recommended before recording:

- Confirm `.env` has valid `ANTHROPIC_API_KEY`.
- Confirm Gmail OAuth is already completed with `token.json`.
- Keep `MAILMIND_EMBEDDING_PROVIDER=local_bge_m3`.
- Use `MAILMIND_PII_MODE=rehydrated` if you want to demonstrate privacy-aware LLM calls.
- Avoid opening raw email content that contains sensitive information unless you are comfortable showing it.

## Screenshot Assets

The checked-in demo screenshots are generated with `?demo=1`, which renders synthetic sample data instead of real Gmail content.

Current demo screenshots:

- [Tasks overview](demo/screenshots/01_tasks_overview.png)
- [AI search answer](demo/screenshots/02_ai_search_answer.png)
- [Indexed sources](demo/screenshots/03_indexed_sources.png)
- [Settings](demo/screenshots/04_settings.png)
- [Settings privacy and RAG](demo/screenshots/05_settings_privacy_rag.png)

Regenerate screenshots:

```powershell
node scripts\capture_demo_screenshots.mjs
```

## GitHub GIF Assets

The checked-in GIFs are also generated from the synthetic `?demo=1` screenshots, so they are safe to use in a public GitHub README.

Current demo GIFs:

- [Hero AI search demo](demo/gifs/hero_ai_search.gif)
- [Documents and settings demo](demo/gifs/documents_and_settings.gif)
- [Privacy settings demo](demo/gifs/privacy_settings.gif)

Regenerate GIFs after refreshing screenshots:

```powershell
python scripts\create_demo_gifs.py
```

Suggested README embed:

```markdown
![MailMind AI Search Demo](docs/demo/gifs/hero_ai_search.gif)
```

## 5-Minute Walkthrough

### 1. Open With The Problem

Say:

> I built MailMind because important tasks are often buried in unstructured Gmail messages: application deadlines, school forms, reply obligations, attachments, and administrative notices. The goal is not to replace Gmail, but to convert my inbox into a local task and search command center.

Show:

- Dashboard landing on `Tasks`.
- Summary metrics.
- Task list with priority, due date, source sender/subject, and `Done` action.

Mention:

- Local-first personal productivity agent.
- Gmail read-only OAuth.
- SQLite local storage.
- Not a public SaaS.

### 2. Show One-Click Refresh

Click:

```text
Refresh
```

Say:

> Refresh is the one-button workflow. It polls Gmail, updates local email records, re-runs task extraction for the current Gmail limit, and incrementally updates the AI search index for the enabled sources.

Mention:

- Gmail polling is read-only.
- Extraction uses Pydantic validation around Claude output.
- RAG indexing only runs for enabled sources: email bodies, PDFs, or both.

If the refresh takes time:

> The slower parts are external API calls and local embedding generation. I intentionally keep indexing explicit/configurable to avoid surprise cost or latency.

### 3. Explain Task Extraction

Click a task row.

Show:

- Right-side task detail.
- Source email card.
- `Open full email`.
- Attachment status if present.

Say:

> Each task is normalized from an email into a structured record: description, priority, due date, reply requirement, review flag, and source email. I tuned the prompt to reduce false positives from newsletters and ads, and to keep task names short and readable.

Mention:

- Prompt is conservative.
- Reply-thread filtering is separate from generic "please reply" language.
- Completed tasks are updated in SQLite.

### 4. Show AI Search / RAG

Use the AI search bar.

Example questions:

```text
What documents mention housing verification?
```

```text
Which emails require a reply?
```

```text
Summarize tasks with attachments.
```

Say:

> AI Search is backed by retrieval, not just direct prompting. It indexes email bodies and PDF attachments, retrieves candidate child chunks through vector search plus SQLite FTS5/BM25, reranks them, groups them into parent contexts, and then sends source-labeled evidence to Claude.

Mention:

- Local BGE-M3 embeddings.
- Chroma vector store.
- SQLite FTS5/BM25 hybrid retrieval.
- BGE reranking.
- Parent-child retrieval.
- Source cards show where the answer came from.

### 5. Show Documents / Indexed Sources

Click:

```text
Documents
```

Show:

- PDF source count.
- Email source count.
- Indexed chunks.
- PDF attachment rows.
- `Index enabled sources`.

Say:

> The RAG sources are configurable. I can index only Gmail email bodies, only PDF attachments, or both. This matters because PDFs can be slower and more expensive to process, while email-body search is useful for inbox-level questions.

Mention:

- Text-layer PDF only.
- No OCR in v1.
- Duplicate attachment bug was fixed by stable attachment IDs and preserving Gmail attachment IDs only for download.

### 6. Show Settings

Click:

```text
Settings
```

Show:

- Scheduler.
- LLM extraction.
- PII Guard.
- AI Search Sources.

Say:

> Settings are user-facing and write back to `.env`. The user can control scheduled polling, Telegram push, model credentials, AI search source types, embedding provider, and PII behavior.

For PII:

> The PII mode has two routes. Off sends original text to Claude. Rehydrated mode replaces detected PII with placeholders before Claude sees it, then restores the final answer locally so the user can still read the result.

Mention:

- Regex/rules-based PII detector.
- Request-scoped placeholder mapping.
- No persistent mapping table.
- SQLite and Chroma remain local and unredacted.
- This is privacy risk reduction, not compliance certification.

### 7. Close With Engineering Summary

Say:

> The core engineering work here is the end-to-end pipeline: Gmail ingestion, validated LLM extraction, SQLite persistence, scheduled jobs, Telegram actions, RAG indexing and retrieval, source-grounded answers, and privacy-aware prompt boundaries. The project is intentionally scoped as a local-first MVP rather than a public SaaS because Gmail restricted scopes would require Google verification for public distribution.

## Short Resume Pitch

Use this if you only have 30 seconds:

> MailMind is a local-first Gmail intelligence agent. It polls Gmail through the read-only Gmail API, extracts action items and deadlines with Claude and Pydantic validation, stores normalized tasks in SQLite, and provides a Next.js/FastAPI dashboard with Telegram reminders. I also added an AI search layer over email bodies and PDF attachments using local BGE-M3 embeddings, Chroma, SQLite FTS5/BM25 hybrid retrieval, reranking, parent-child retrieval, source-grounded Claude answers, and optional PII rehydration.

## What Not To Overclaim

Do not claim:

- Public SaaS readiness.
- Full Gmail production OAuth verification.
- Complete PII anonymization or compliance certification.
- OCR support for scanned PDFs.
- Multi-user account isolation.
- Real-time Gmail push notifications.

Accurate framing:

- Local-first personal productivity agent.
- Read-only Gmail OAuth.
- Text-layer PDF RAG.
- Privacy-aware LLM-boundary pseudonymization.
- Portfolio-grade MVP with production-style architecture decisions.

## Optional Recording Structure

Recommended video sections:

| Time | Scene | What to show |
| --- | --- | --- |
| 0:00-0:30 | Problem | Inbox tasks are buried in unstructured emails |
| 0:30-1:30 | Dashboard | Tasks, priorities, due dates, source email |
| 1:30-2:10 | Refresh | One-click Gmail + extraction + indexing |
| 2:10-3:10 | AI Search | Ask a question and show cited sources |
| 3:10-4:00 | Documents | Indexed email/PDF sources |
| 4:00-5:00 | Settings | PII mode, RAG source toggles, local-first controls |
| 5:00-5:30 | Wrap | Stack and engineering highlights |
