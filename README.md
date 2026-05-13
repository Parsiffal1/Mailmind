# MailMind

[English](README.md) | [中文](README.zh.md)

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Local-first](https://img.shields.io/badge/Architecture-Local--first-blue)
![Gmail](https://img.shields.io/badge/Gmail-Read--only%20OAuth-red)

![MailMind brand hero](docs/demo/gifs/mailmind_brand_hero.gif)

MailMind is a local-first Gmail intelligence agent for people who lose deadlines, forms, attachments, and follow-ups inside a crowded inbox.

It reads Gmail through the read-only Gmail API, extracts action items with an LLM, keeps data in local SQLite, and gives you a dashboard, AI search over email bodies and PDF attachments, Telegram reminders, and privacy-aware controls.

## Why MailMind

Most inbox tools either stop at simple rules or ask you to hand your mailbox to a hosted service.

MailMind takes a different route:

- **Local-first by default**: database, attachments, and indexes stay on your machine.
- **Gmail-aware task extraction**: deadlines, reply obligations, review items, and follow-ups are pulled out of noisy email threads.
- **Source-grounded AI search**: answers come with supporting source cards instead of detached chatbot guesses.
- **Portfolio-grade engineering surface**: FastAPI, Next.js, SQLite, Gmail OAuth, scheduler jobs, Telegram actions, RAG, and privacy boundaries in one coherent project.

## What You Can Do With It

- Refresh Gmail and turn recent emails into structured tasks.
- Track due dates, priorities, reply-needed flags, and review-needed flags.
- Search across email bodies and text-layer PDF attachments with hybrid retrieval.
- Ask inbox questions and get answers backed by retrieved sources.
- Run reminder flows through Telegram.
- Choose between raw LLM calls and privacy-aware PII rehydration.
- Demo the whole product safely with synthetic sample data.

## What It Looks Like

MailMind ships with checked-in demo assets generated from synthetic sample data, so the public repo can show the actual product surface without exposing real inbox content.

![Tasks overview](docs/demo/screenshots/01_tasks_overview.png)
![AI search answer](docs/demo/screenshots/02_ai_search_answer.png)
![Indexed sources](docs/demo/screenshots/03_indexed_sources.png)

## Demo GIFs

![MailMind AI search demo](docs/demo/gifs/hero_ai_search.gif)

![MailMind documents and settings demo](docs/demo/gifs/documents_and_settings.gif)

The checked-in demo GIFs and screenshots do not contain real emails, OAuth tokens, API keys, or private attachments.

## Quick Navigation

- [What This Project Is](#what-this-project-is)
- [Who This Is For](#who-this-is-for)
- [Quick Start: Demo Mode](#quick-start-demo-mode)
- [Connect Real Gmail](#connect-real-gmail)
- [Core Workflow](#core-workflow)
- [AI Search and RAG](#ai-search-and-rag)
- [Privacy Model](#privacy-model)
- [Run Optional Services](#run-optional-services)
- [Repository Structure](#repository-structure)
- [What To Read Next](#what-to-read-next)
- [Project Status and Boundaries](#project-status-and-boundaries)

## What This Project Is

MailMind is a personal productivity system, not a hosted SaaS. You run it on your own machine, connect your own Gmail OAuth desktop client, and keep the database, attachments, and search index local.

The project is designed as a serious open-source MVP with production-style decisions: validated LLM outputs, explicit privacy boundaries, source-grounded RAG, scheduler jobs, a usable dashboard, and a safe demo mode for public walkthroughs.

## Who This Is For

MailMind is a strong fit if you:

- receive school, recruiting, admin, finance, or form-heavy emails;
- want a local task layer on top of Gmail without giving a hosted app broad mailbox access;
- want to study an end-to-end LLM application with Gmail OAuth, FastAPI, SQLite, Next.js, Telegram, RAG, and privacy controls;
- want a portfolio project that goes beyond a basic chatbot demo.

It is not meant for multi-user SaaS deployment out of the box. Gmail restricted scopes require Google verification before public production use.

## A Typical Refresh Cycle

```text
Refresh
  -> poll Gmail through read-only OAuth
  -> normalize emails and attachments locally
  -> extract action items with validated LLM output
  -> update task views and search indexes
  -> answer inbox questions with retrieved sources
```

## Quick Start: Demo Mode

Demo mode is the fastest way to see the product without Gmail credentials or paid API calls.

### 1) Clone and install

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

### 2) Keep the LLM provider in mock mode

Set this in `.env`:

```text
MAILMIND_LLM_PROVIDER=mock
```

### 3) Build the dashboard and start the API

```powershell
cd dashboard
npm install
npm run build
cd ..

python -m mailmind.api
```

### 4) Open demo mode

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
ANTHROPIC_API_KEY=your_anthropic_api_key
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
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
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
- Demo assets: [docs/demo/GITHUB_ASSETS.md](docs/demo/GITHUB_ASSETS.md)
- Brand GIF storyboard: [docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md](docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md)

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

Issues and pull requests are welcome. Good first improvements include documentation fixes, retrieval evaluation cases, UI polish, setup automation, and safer local privacy defaults.

Please do not post real email content, OAuth tokens, API keys, or private attachments in issues. Use the issue templates in `.github/ISSUE_TEMPLATE/`, and read [SECURITY.md](SECURITY.md) before sharing any sensitive reproduction details.

## License

MIT
