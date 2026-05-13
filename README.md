# MailMind

[中文 README](README.zh-CN.md)

![MailMind brand hero](docs/demo/gifs/mailmind_brand_hero.gif)

MailMind is a local-first Gmail intelligence agent that turns a personal inbox into structured tasks, searchable context, and privacy-aware AI answers. It uses the read-only Gmail API, extracts action items and deadlines with Claude or a mock provider, stores data locally in SQLite, serves a FastAPI + Next.js dashboard, and can send Telegram reminders.

MailMind is open-source local software, not a hosted SaaS. Everyone can clone and run it locally. To connect a real Gmail account, each user creates their own Google OAuth desktop client because Gmail `gmail.readonly` is a restricted scope.

## Features

- Read-only Gmail ingestion with local OAuth browser flow.
- LLM task extraction with Pydantic validation and retry handling.
- SQLite persistence for emails, tasks, attachments, processing logs, and settings.
- One-click refresh that polls Gmail, extracts tasks, refreshes dashboard data, and updates enabled AI search indexes.
- Telegram bot commands: `/list`, `/today`, `/done <id>`, `/search <keyword>`, `/poll`.
- APScheduler worker for optional Gmail polling, daily digests, and deadline reminders.
- Next.js dashboard statically exported and served by FastAPI.
- AI search over email bodies and PDF attachments using local BGE-M3 embeddings, ChromaDB, SQLite FTS5 BM25 hybrid search, parent-child retrieval, reranking, and Claude source-grounded answers.
- PII Guard with `off` and `rehydrated` modes. In rehydrated mode, placeholders are sent to Claude and restored locally for the user.
- Sample/demo mode for screenshots, README GIFs, and local exploration without Gmail credentials.

## Architecture

```text
Gmail API read-only OAuth
        |
        v
FastAPI backend + SQLite
        |
        +--> LLM task extraction -> tasks, deadlines, priorities
        |
        +--> AI search index -> email chunks + PDF chunks -> Chroma + SQLite FTS5
        |
        +--> Next.js dashboard served from FastAPI
        |
        +--> APScheduler worker + Telegram bot
```

## Quick Start: Demo Mode

Demo mode lets you open the dashboard with sample data. It does not need Gmail credentials, Telegram credentials, or a Claude key.

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

Build and run:

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

## Quick Start: Real Gmail Mode

1. Go to Google Cloud Console.
2. Create or select a project.
3. Enable the Gmail API.
4. Configure the Google Auth Platform consent screen for external testing.
5. Create an OAuth client ID with application type `Desktop app`.
6. Download the OAuth client JSON and save it as `credentials.json` in the project root.
7. Add your own Gmail address as a test user in Google Auth Platform.

Then configure `.env`:

```text
MAILMIND_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_key
MAILMIND_GMAIL_CREDENTIALS=credentials.json
MAILMIND_GMAIL_TOKEN=token.json
MAILMIND_POLL_QUERY=newer_than:14d
MAILMIND_POLL_LIMIT=40
```

Run the API:

```powershell
python -m mailmind.api
```

Open `http://127.0.0.1:8000`, click `Refresh`, and complete the browser OAuth flow. MailMind writes `token.json` locally after the first successful login.

## Running Workers and Bot

The dashboard API is enough for manual refresh and demo usage.

Run the optional scheduler worker:

```powershell
python -m mailmind.worker
```

Run the optional Telegram bot:

```powershell
python -m mailmind.bot
```

Telegram requires:

```text
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
MAILMIND_TELEGRAM_NOTIFICATIONS_ENABLED=true
```

## Configuration

Most settings live in `.env` and can also be edited from the dashboard settings page.

```text
MAILMIND_DB_PATH=data/mailmind.db
MAILMIND_POLL_QUERY=newer_than:14d
MAILMIND_POLL_LIMIT=40

MAILMIND_SCHEDULER_ENABLED=true
MAILMIND_POLL_INTERVAL_MINUTES=15
MAILMIND_DAILY_DIGEST_ENABLED=true
MAILMIND_DAILY_DIGEST_TIME=08:00
MAILMIND_DEADLINE_REMINDERS_ENABLED=true

MAILMIND_RAG_ENABLED=true
MAILMIND_RAG_EMAIL_ENABLED=true
MAILMIND_RAG_PDF_ENABLED=true
MAILMIND_EMBEDDING_PROVIDER=local_bge_m3
MAILMIND_BGE_MODEL=BAAI/bge-m3
MAILMIND_RAG_HYBRID_ENABLED=true
MAILMIND_RAG_RERANK_ENABLED=true

MAILMIND_PII_ENABLED=true
MAILMIND_PII_MODE=rehydrated
```

The first local embedding run downloads `BAAI/bge-m3` through `sentence-transformers`. If reranking is enabled, the first rerank query downloads `BAAI/bge-reranker-base`.

## AI Search and RAG

MailMind can index:

- Gmail email bodies.
- Text-layer PDF attachments.
- Both, depending on settings.

Retrieval uses a hybrid pipeline:

1. Structure-aware email/PDF chunking.
2. Child chunks for embedding and search.
3. Parent context expansion before answer generation.
4. Chroma vector retrieval with local BGE-M3 embeddings.
5. SQLite FTS5 BM25 keyword retrieval.
6. RRF-style fusion, reranking, source grouping, deduplication, and score aggregation.
7. Claude answers with source-labeled context.

## PII Guard

MailMind supports two privacy routes:

- `off`: Claude receives the original text.
- `rehydrated`: MailMind replaces selected PII with local placeholders before sending prompts to Claude, then restores the final answer locally.

PII Guard covers email addresses, phone numbers, SSNs, ID-like values, account-like numbers, API keys/tokens/secrets, and conservative English person names. Dates are preserved so deadline extraction and RAG answers continue to work.

This is privacy risk reduction, not compliance certification. Local SQLite databases, downloaded attachments, Chroma indexes, and FTS indexes are not globally redacted.

## Demo Assets

![MailMind AI search demo](docs/demo/gifs/hero_ai_search.gif)

- Demo flow: [docs/DEMO_FLOW.md](docs/DEMO_FLOW.md)
- GitHub assets: [docs/demo/GITHUB_ASSETS.md](docs/demo/GITHUB_ASSETS.md)
- Brand storyboard: [docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md](docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md)

Regenerate demo screenshots and GIFs:

```powershell
node scripts\capture_demo_screenshots.mjs
python scripts\create_demo_gifs.py
python scripts\create_brand_hero_gif.py
```

## RAG Evaluation

Add evaluation questions to `eval/rag_eval.json`, then run:

```powershell
python scripts\eval_rag.py --mode vector --top-k 4
python scripts\eval_rag.py --mode hybrid --top-k 4
```

The evaluator reports source recall and retrieved source labels. Synthetic and hard-negative evaluators build temporary local indexes and should not be committed with generated index data.

## Security Notes

Never commit:

- `.env`
- `credentials.json`
- `token.json`
- `data/`
- `attachments/`
- `chroma/`
- local database files

Gmail `gmail.readonly` is a restricted OAuth scope. This project is intended for local personal use. If you turn MailMind into a public hosted product, you must handle Google OAuth verification, privacy policy, user data deletion, and any required security assessment.

## Tech Stack

Python, FastAPI, SQLite, APScheduler, Telegram Bot API, Gmail API, Google OAuth, Anthropic Claude, Pydantic, Next.js, React, LangChain, ChromaDB, sentence-transformers, BGE-M3, SQLite FTS5, pdfplumber.

## Resume Description

Built a local-first Gmail intelligence agent that polls Gmail through the read-only Gmail API, extracts action items and deadlines from unstructured email text using an LLM with Pydantic validation, stores normalized tasks in SQLite, and sends proactive reminders through a Telegram bot. Added a Next.js/FastAPI dashboard and an email/PDF RAG system with structure-aware chunking, parent-child retrieval, local BGE-M3 embeddings, ChromaDB, SQLite FTS5 BM25 hybrid search, reranking, Claude source-grounded answers, and PII placeholder rehydration.

## License

MIT
