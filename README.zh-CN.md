# MailMind

[English README](README.md)

![MailMind brand hero](docs/demo/gifs/mailmind_brand_hero.gif)

MailMind 是一个 local-first 的 Gmail 智能助手。它把个人邮箱里的邮件转换成结构化任务、可搜索知识和带隐私保护的 AI 回答。项目使用 Gmail 只读 API、Claude 或 mock provider 提取任务和 deadline，用 SQLite 本地保存数据，通过 FastAPI + Next.js 提供 dashboard，也可以通过 Telegram 发送提醒。

MailMind 是本地开源软件，不是托管 SaaS。任何人都可以 clone 后本地运行。真实接入 Gmail 时，每个用户需要创建自己的 Google OAuth desktop client，因为 Gmail `gmail.readonly` 属于 restricted scope。

## 功能

- Gmail 只读 OAuth，本地浏览器授权。
- LLM 任务提取，使用 Pydantic 校验结构化输出。
- SQLite 保存 emails、tasks、attachments、processing logs 和 settings。
- 一键 Refresh：拉取 Gmail、提取任务、刷新 dashboard、更新启用的 AI search index。
- Telegram bot：`/list`、`/today`、`/done <id>`、`/search <keyword>`、`/poll`。
- APScheduler worker：可选定时 polling、daily digest、deadline reminders。
- Next.js dashboard，静态导出后由 FastAPI 托管。
- AI search 支持邮件正文和 PDF 附件，使用本地 BGE-M3 embedding、ChromaDB、SQLite FTS5 BM25 hybrid search、parent-child retrieval、reranking 和 Claude source-grounded answers。
- PII Guard 支持 `off` 和 `rehydrated` 两种模式。`rehydrated` 会先把 PII 替换为 placeholder 发给 Claude，再在本地恢复给用户看。
- sample/demo mode：无需 Gmail credentials，也能查看 dashboard 和 README 展示素材。

## 架构

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

## 快速开始：Demo Mode

Demo mode 使用 sample 数据，不需要 Gmail credentials、Telegram credentials 或 Claude key。

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

在 `.env` 里设置：

```text
MAILMIND_LLM_PROVIDER=mock
```

构建并运行：

```powershell
cd dashboard
npm install
npm run build
cd ..

python -m mailmind.api
```

打开：

```text
http://127.0.0.1:8000/?demo=1
```

## 快速开始：真实 Gmail

1. 打开 Google Cloud Console。
2. 创建或选择一个项目。
3. 启用 Gmail API。
4. 配置 Google Auth Platform consent screen，个人项目可使用 external testing。
5. 创建 OAuth client ID，类型选择 `Desktop app`。
6. 下载 OAuth client JSON，保存到项目根目录并命名为 `credentials.json`。
7. 在 Google Auth Platform 里把自己的 Gmail 加为 test user。

然后配置 `.env`：

```text
MAILMIND_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_key
MAILMIND_GMAIL_CREDENTIALS=credentials.json
MAILMIND_GMAIL_TOKEN=token.json
MAILMIND_POLL_QUERY=newer_than:14d
MAILMIND_POLL_LIMIT=40
```

运行 API：

```powershell
python -m mailmind.api
```

打开 `http://127.0.0.1:8000`，点击 `Refresh`，完成浏览器 OAuth 授权。第一次成功登录后，MailMind 会把 `token.json` 写在本地。

## Worker 和 Telegram Bot

只做手动刷新和 dashboard demo 时，启动 API 就够了。

可选启动 scheduler worker：

```powershell
python -m mailmind.worker
```

可选启动 Telegram bot：

```powershell
python -m mailmind.bot
```

Telegram 需要：

```text
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
MAILMIND_TELEGRAM_NOTIFICATIONS_ENABLED=true
```

## 配置

主要配置在 `.env` 中，也可以通过 dashboard settings 页面修改。

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

第一次本地 embedding 会通过 `sentence-transformers` 下载 `BAAI/bge-m3`。如果开启 reranking，第一次 rerank 查询会下载 `BAAI/bge-reranker-base`。

## AI Search 和 RAG

MailMind 可以索引：

- Gmail 邮件正文。
- text-layer PDF 附件。
- 两者同时启用。

检索流程：

1. 邮件/PDF structure-aware chunking。
2. child chunk 用于 embedding 和 search。
3. parent context 用于最终发送给 Claude。
4. Chroma vector retrieval，本地 BGE-M3 embedding。
5. SQLite FTS5 BM25 keyword retrieval。
6. RRF-style fusion、reranking、source grouping、dedupe 和 score aggregation。
7. Claude 基于 source-labeled context 回答。

## PII Guard

MailMind 支持两条隐私路线：

- `off`：Claude 直接看到原文。
- `rehydrated`：MailMind 先把 PII 替换成 placeholder，再发送给 Claude，最后在本地恢复答案。

PII Guard 覆盖 email、phone、SSN、ID-like values、account-like numbers、API keys/tokens/secrets 和保守英文姓名检测。日期默认保留，避免影响 deadline extraction 和 RAG answer。

这只是隐私风险缓解，不是合规认证。本地 SQLite、下载附件、Chroma index 和 FTS index 不会被全局脱敏。

## Demo 素材

![MailMind AI search demo](docs/demo/gifs/hero_ai_search.gif)

- Demo flow: [docs/DEMO_FLOW.md](docs/DEMO_FLOW.md)
- GitHub assets: [docs/demo/GITHUB_ASSETS.md](docs/demo/GITHUB_ASSETS.md)
- Brand storyboard: [docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md](docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md)

重新生成截图和 GIF：

```powershell
node scripts\capture_demo_screenshots.mjs
python scripts\create_demo_gifs.py
python scripts\create_brand_hero_gif.py
```

## RAG Evaluation

把评估问题加入 `eval/rag_eval.json` 后运行：

```powershell
python scripts\eval_rag.py --mode vector --top-k 4
python scripts\eval_rag.py --mode hybrid --top-k 4
```

评估脚本会输出 source recall 和检索到的 source labels。synthetic/hard-negative evaluator 会创建临时本地 index，生成的 index 数据不要提交到 GitHub。

## 安全说明

不要提交：

- `.env`
- `credentials.json`
- `token.json`
- `data/`
- `attachments/`
- `chroma/`
- 本地数据库文件

Gmail `gmail.readonly` 是 restricted OAuth scope。本项目面向本地个人使用。如果你把它做成公开托管产品，需要处理 Google OAuth verification、隐私政策、用户数据删除和可能的安全评估。

## 技术栈

Python, FastAPI, SQLite, APScheduler, Telegram Bot API, Gmail API, Google OAuth, Anthropic Claude, Pydantic, Next.js, React, LangChain, ChromaDB, sentence-transformers, BGE-M3, SQLite FTS5, pdfplumber.

## 简历描述

Built a local-first Gmail intelligence agent that polls Gmail through the read-only Gmail API, extracts action items and deadlines from unstructured email text using an LLM with Pydantic validation, stores normalized tasks in SQLite, and sends proactive reminders through a Telegram bot. Added a Next.js/FastAPI dashboard and an email/PDF RAG system with structure-aware chunking, parent-child retrieval, local BGE-M3 embeddings, ChromaDB, SQLite FTS5 BM25 hybrid search, reranking, Claude source-grounded answers, and PII placeholder rehydration.

## License

MIT
