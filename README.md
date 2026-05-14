[English](README.md) | [中文](README.zh.md)

<div align="center">
  <h1>MailMind</h1>
  <p><em>A local-first Gmail assistant that turns your personal inbox into a searchable, actionable, privacy-aware workspace.</em></p>
  <p>
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" />
    <img src="https://img.shields.io/badge/Architecture-Local--first-blue" alt="Architecture: Local-first" />
    <img src="https://img.shields.io/badge/Gmail-Read--only%20OAuth-red" alt="Gmail: Read-only OAuth" />
    <img src="https://img.shields.io/badge/AI%20Search-RAG%20enabled-7c3aed" alt="AI Search: RAG enabled" />
  </p>
  <p><strong>MailMind is a local-first Gmail assistant that automatically organizes tasks, deadlines, and reply reminders from your personal inbox, and supports RAG-based AI Search across email bodies and PDF attachments.</strong></p>
  <p>
    It includes optional PII privacy protection to keep sensitive email information from leaking to cloud LLMs. The system is built on Gmail read-only OAuth, LLM + Pydantic, SQLite, FastAPI, Next.js, and hybrid RAG, with an emphasis on local data storage, RAG-based AI question answering, and configurable PII privacy protection.
  </p>
  <p>
    <a href="#interface-preview">Interface preview</a> ·
    <a href="#install">Install</a> ·
    <a href="#what-it-gives-you">What it gives</a> ·
    <a href="#how-it-works">How it works</a> ·
    <a href="#ai-search-and-rag">AI Search</a> ·
    <a href="#privacy-model">Privacy</a> ·
    <a href="#read-next">Read next</a>
  </p>
</div>

```bash
git clone https://github.com/Parsiffal1/Mailmind.git && cd Mailmind
```

---

<p align="center">
  <img src="docs/assets/mailmind-hero.gif" alt="MailMind hero animation" width="100%">
</p>

<div align="center">
  <sub>▲ Hero animation made with <a href="https://github.com/alchaincyf/huashu-design/tree/master">huashu-design</a></sub>
</div>

## Interface preview

![Tasks overview](docs/demo/screenshots/01_tasks_overview.png)
![AI search answer](docs/demo/screenshots/02_ai_search_answer.png)

The checked-in screenshots do not contain real emails, OAuth tokens, API keys, or private attachments.

## Install

If you want the shortest safe path, start in demo mode first. It shows the real product flow without needing Gmail credentials or paid model calls.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set this in `.env`:

```text
MAILMIND_LLM_PROVIDER=mock
```

Then build the dashboard and start the API:

```bash
cd dashboard
npm install
npm run build
cd ..
python -m mailmind.api
```

Open:

```text
http://127.0.0.1:8000/?demo=1
```

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
cd dashboard
npm install
npm run build
cd ..
python -m mailmind.api
```

Set:

```text
MAILMIND_LLM_PROVIDER=mock
```

## What it gives you

- **Structured tasks from messy threads**: due dates, reply-needed items, follow-ups, and review items are pulled out of recent email.
- **A working dashboard instead of a raw inbox**: see what needs action now without rereading everything.
- **Source-grounded inbox search**: answers come with retrieved evidence instead of detached chatbot guesses.
- **Local-first storage**: email metadata, indexes, and workflow state stay on your machine by default.
- **Optional Telegram reminders**: use the same extracted task layer to push reminders outside the inbox.
- **Optional privacy controls**: use configurable PII protection to reduce the chance of sensitive email content being sent to cloud LLMs.

## Connect real Gmail

1. Open Google Cloud Console.
2. Create or select a project.
3. Enable the Gmail API.
4. Configure the consent screen for external testing.
5. Create an OAuth client ID with application type `Desktop app`.
6. Download the OAuth client JSON and save it as `credentials.json` in the project root.
7. Add your Gmail address as a test user.

Then configure `.env`:

```text
MAILMIND_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_a...key
MAILMIND_GMAIL_CREDENTIALS=credentials.json
MAILMIND_GMAIL_TOKEN=token.json
MAILMIND_POLL_QUERY=newer_than:14d
MAILMIND_POLL_LIMIT=40
```

Run:

```bash
python -m mailmind.api
```

Open `http://127.0.0.1:8000`, click `Refresh`, and complete the browser OAuth flow. MailMind writes `token.json` locally after the first successful login.

## How it works

```text
Refresh
  -> poll Gmail through read-only OAuth
  -> normalize emails and attachments locally
  -> extract action items with validated LLM output
  -> update task views and search indexes
  -> answer inbox questions with retrieved sources
```

```text
Gmail read-only OAuth
        |
        v
FastAPI backend + SQLite
        |
        +--> LLM task extraction -> tasks, deadlines, priorities
        |
        +--> AI search index -> email chunks + PDF chunks
        |                       -> Chroma vector search + SQLite FTS5
        |
        +--> Next.js dashboard
        |
        +--> APScheduler worker + Telegram bot
```

## AI Search and RAG

MailMind can index Gmail email bodies, text-layer PDF attachments, or both.

Retrieval uses:

- structure-aware email/PDF chunking;
- child chunks for embedding and search;
- parent context expansion before answer generation;
- Chroma vector retrieval with local BGE-M3 embeddings;
- SQLite FTS5 BM25 keyword retrieval;
- fusion, reranking, source grouping, deduplication, and score aggregation;
- Claude answers with source-labeled context.

Current 50-case post-improvement benchmark (`eval/RAG_EVALUATION_RESULTS.md`):

| Metric | Vector-only | Hybrid after | Improvement |
| --- | ---: | ---: | ---: |
| Top-1 Source Recall | 48.35% | 63.74% | +15.39 pp |
| Any-source Recall@4 | 58.24% | 78.02% | +19.78 pp |
| Full-source Recall@4 | 46.15% | 64.84% | +18.69 pp |
| MRR | 0.522 | 0.691 | +0.169 |

The first local embedding run downloads `BAAI/bge-m3` through `sentence-transformers`. If reranking is enabled, the first rerank query downloads `BAAI/bge-reranker-base`.

## Privacy model

MailMind supports two routes:

- `off`: Claude receives original text.
- `rehydrated`: MailMind replaces selected PII with local placeholders before sending prompts to Claude, then restores the final answer locally.

PII Guard covers email addresses, phone numbers, SSNs, ID-like values, account-like numbers, API keys/tokens/secrets, and conservative English person names. Dates are preserved so deadline extraction and RAG answers still work.

This is privacy risk reduction, not compliance certification. SQLite databases, downloaded attachments, Chroma indexes, and FTS indexes remain local but are not globally redacted.

## Run optional services

Scheduler worker:

```bash
python -m mailmind.worker
```

Telegram bot:

```bash
python -m mailmind.bot
```

Telegram requires:

```text
TELEGRAM_BOT_TOKEN=your_t...ken
TELEGRAM_CHAT_ID=your_chat_id
MAILMIND_TELEGRAM_NOTIFICATIONS_ENABLED=true
```

## Repository structure

```text
mailmind/          FastAPI backend, Gmail client, extraction, database, RAG, worker, bot
dashboard/         Next.js dashboard exported and served by FastAPI
prompts/           Claude prompt files for task extraction and RAG answers
tests/             Unit tests for parser, database, API, extraction, RAG, privacy
scripts/           Demo asset generation, RAG evaluation, GitHub publishing helper
docs/              Demo flow, PII architecture, README assets and screenshots
eval/              Small RAG evaluation seed file and evaluation report
```

## Read next

- PII architecture: [docs/PII_ARCHITECTURE.md](docs/PII_ARCHITECTURE.md)
- Security notes: [SECURITY.md](SECURITY.md)
- Demo assets: [docs/demo/GITHUB_ASSETS.md](docs/demo/GITHUB_ASSETS.md)
- Brand GIF storyboard: [docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md](docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md)

## RAG evaluation

Add evaluation questions to `eval/rag_eval.json`, then run:

```powershell
python scripts\eval_rag.py --mode vector --top-k 4
python scripts\eval_rag.py --mode hybrid --top-k 4
```

The evaluator reports source recall and retrieved source labels. Synthetic and hard-negative evaluators build temporary local indexes and should not be committed with generated index data.

## Project status and boundaries

MailMind is a working local MVP. It is suitable for personal local use and continued development.

Current boundaries:

- not a public hosted SaaS;
- no multi-user account model;
- no OCR for scanned PDFs;
- no production Google OAuth restricted-scope verification;
- no compliance claim for PII handling;
- no real-time Gmail push notifications yet.

## Community

Issues and pull requests are welcome. Good first improvements include documentation fixes, retrieval evaluation cases, UI polish, setup automation, and safer local privacy defaults.

Please do not post real email content, OAuth tokens, API keys, or private attachments in issues. Use the issue templates in `.github/ISSUE_TEMPLATE/`, and read [SECURITY.md](SECURITY.md) before sharing any sensitive reproduction details.

## License

MIT
