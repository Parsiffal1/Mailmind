# MailMind

[English](README.md) | [中文](README.zh.md)

![MailMind brand hero](docs/demo/gifs/mailmind_brand_hero.gif)

MailMind is a local-first Gmail intelligence agent for people who lose tasks, deadlines, forms, and follow-ups inside a busy inbox.

It reads Gmail with the read-only Gmail API, extracts action items with an LLM, stores everything locally in SQLite, and gives you a dashboard, Telegram reminders, and source-grounded AI search across email bodies and PDF attachments.

## What This Project Is

MailMind is a personal productivity system, not a hosted SaaS. You run it on your own machine, connect your own Gmail OAuth desktop client, and keep the database, attachments, and search index local.

The project is designed as a portfolio-grade open-source MVP with production-style architecture decisions: validated LLM outputs, explicit privacy boundaries, source-grounded RAG, scheduler jobs, and a dashboard that can be used without real Gmail data through demo mode.

## Who This Is For

MailMind is useful if you:

- receive school, recruiting, admin, finance, or form-heavy emails;
- want a local task layer on top of Gmail without giving a hosted app broad mailbox access;
- want to study an end-to-end LLM application with Gmail OAuth, FastAPI, SQLite, Next.js, Telegram, RAG, and privacy controls;
- need a concrete resume project that goes beyond a basic chatbot.

It is not meant for multi-user SaaS deployment out of the box. Gmail restricted scopes require Google verification before public production use.

## What You Get

- A one-click refresh workflow that polls Gmail, extracts tasks, updates the dashboard, and indexes enabled AI search sources.
- Structured tasks with priority, due date, reply flag, review flag, source email, and completion state.
- AI search over Gmail bodies and text-layer PDF attachments with local BGE-M3 embeddings, ChromaDB, SQLite FTS5 BM25 hybrid search, parent-child retrieval, reranking, and Claude answers with source cards.
- Optional Telegram commands: `/list`, `/today`, `/done <id>`, `/search <keyword>`, `/poll`.
- Optional scheduler jobs for polling, daily digests, and deadline reminders.
- PII Guard with `off` and `rehydrated` modes. Rehydrated mode sends placeholders to Claude and restores the answer locally.
- Sample/demo mode for public screenshots and README GIFs without exposing real Gmail data.

## Demo

![MailMind AI search demo](docs/demo/gifs/hero_ai_search.gif)

The checked-in demo assets are generated from synthetic sample data. They do not contain real emails, OAuth tokens, API keys, or attachments.

## Quick Start: Demo Mode

Demo mode is the fastest way to see the product without Gmail credentials or paid API calls.

Windows PowerShell:

```powershell
git clone https://github.com/Parsiffal1/Mailmind.git
cd Mailmind

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
```

macOS/Linux:

```bash
git clone https://github.com/Parsiffal1/Mailmind.git
cd Mailmind

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

Set this in `.env`:

```text
MAILMIND_LLM_PROVIDER=mock
```

Build the dashboard and start the API:

```powershell
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

## Connect Real Gmail

1. Open Google Cloud Console.
2. Create or select a project.
3. Enable the Gmail API.
4. Configure Google Auth Platform consent screen for external testing.
5. Create an OAuth client ID with application type `Desktop app`.
6. Download the OAuth client JSON and save it as `credentials.json` in the project root.
7. Add your Gmail address as a test user in Google Auth Platform.

Then configure `.env`:

```text
MAILMIND_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_key
MAILMIND_GMAIL_CREDENTIALS=credentials.json
MAILMIND_GMAIL_TOKEN=token.json
MAILMIND_POLL_QUERY=newer_than:14d
MAILMIND_POLL_LIMIT=40
```

Run:

```powershell
python -m mailmind.api
```

Open `http://127.0.0.1:8000`, click `Refresh`, and complete the browser OAuth flow. MailMind writes `token.json` locally after the first successful login.

## Core Workflow

```text
Gmail readonly OAuth
        |
        v
FastAPI backend + SQLite
        |
        +--> LLM task extraction -> tasks, deadlines, priorities
        |
        +--> AI search index -> email chunks + PDF chunks
        |                         -> Chroma vector search + SQLite FTS5
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

The first local embedding run downloads `BAAI/bge-m3` through `sentence-transformers`. If reranking is enabled, the first rerank query downloads `BAAI/bge-reranker-base`.

## Privacy Model

MailMind supports two routes:

- `off`: Claude receives original text.
- `rehydrated`: MailMind replaces selected PII with local placeholders before sending prompts to Claude, then restores the final answer locally.

PII Guard covers email addresses, phone numbers, SSNs, ID-like values, account-like numbers, API keys/tokens/secrets, and conservative English person names. Dates are preserved so deadline extraction and RAG answers still work.

This is privacy risk reduction, not compliance certification. SQLite databases, downloaded attachments, Chroma indexes, and FTS indexes remain local but are not globally redacted.

## Run Optional Services

Scheduler worker:

```powershell
python -m mailmind.worker
```

Telegram bot:

```powershell
python -m mailmind.bot
```

Telegram requires:

```text
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
MAILMIND_TELEGRAM_NOTIFICATIONS_ENABLED=true
```

## Repository Structure

```text
mailmind/          FastAPI backend, Gmail client, extraction, database, RAG, worker, bot
dashboard/         Next.js dashboard exported and served by FastAPI
prompts/           Claude prompt files for task extraction and RAG answers
tests/             Unit tests for parser, database, API, extraction, RAG, privacy
scripts/           Demo asset generation, RAG evaluation, GitHub publishing helper
docs/              Demo flow, PII architecture, README GIFs and screenshots
eval/              Small RAG evaluation seed file and evaluation report
```

## What To Read Next

- Demo walkthrough: [docs/DEMO_FLOW.md](docs/DEMO_FLOW.md)
- PII architecture: [docs/PII_ARCHITECTURE.md](docs/PII_ARCHITECTURE.md)
- Security notes: [SECURITY.md](SECURITY.md)
- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Demo assets: [docs/demo/GITHUB_ASSETS.md](docs/demo/GITHUB_ASSETS.md)

## RAG Evaluation

Add evaluation questions to `eval/rag_eval.json`, then run:

```powershell
python scripts\eval_rag.py --mode vector --top-k 4
python scripts\eval_rag.py --mode hybrid --top-k 4
```

The evaluator reports source recall and retrieved source labels. Synthetic and hard-negative evaluators build temporary local indexes and should not be committed with generated index data.

## Project Status and Boundaries

MailMind is a working local MVP. It is suitable for personal local use, portfolio review, and further development.

Current boundaries:

- not a public hosted SaaS;
- no multi-user account model;
- no OCR for scanned PDFs;
- no production Google OAuth restricted-scope verification;
- no compliance claim for PII handling;
- no real-time Gmail push notifications yet.

## Community

Issues and pull requests are welcome. Good first contributions include documentation fixes, new tests, retrieval evaluation cases, UI polish, and safer setup automation.

Please do not post real email content, OAuth tokens, API keys, or private attachments in issues.

## License

MIT
