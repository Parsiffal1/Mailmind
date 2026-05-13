# MailMind

[English](README.md) | [中文](README.zh.md)

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Local-first](https://img.shields.io/badge/Architecture-Local--first-blue)
![Gmail](https://img.shields.io/badge/Gmail-Read--only%20OAuth-red)

![MailMind brand hero](docs/demo/gifs/mailmind_brand_hero.gif)

MailMind 是一个 local-first 的 Gmail 智能助手，适合那些经常把 deadline、表格、附件、待回复事项和 follow-up 淹没在邮箱里的人。

它通过 Gmail 只读 API 拉取邮件，用 LLM 提取行动项，把数据保存在本地 SQLite，并提供 dashboard、邮件与 PDF 附件的 AI Search、Telegram 提醒，以及带隐私边界的配置能力。

## 为什么是 MailMind

很多邮箱工具要么只停留在规则筛选，要么要求你把整个邮箱交给托管服务。

MailMind 走的是另一条路线：

- **默认 local-first**：数据库、附件和索引都留在你的机器上。
- **理解 Gmail 场景的任务抽取**：从杂乱的邮件线程里提取 deadline、待回复、待处理和待审核事项。
- **带来源依据的 AI Search**：回答会附上 source cards，而不是无依据的聊天式输出。
- **完整的工程展示面**：FastAPI、Next.js、SQLite、Gmail OAuth、scheduler、Telegram、RAG 和隐私边界都放在同一个项目里闭环呈现。

## 你可以用它做什么

- 一键刷新 Gmail，把最近邮件转成结构化任务。
- 跟踪 due date、priority、是否需要回复、是否需要复核。
- 对邮件正文和 text-layer PDF 附件做 hybrid retrieval 搜索。
- 直接提问 inbox 问题，并拿到带来源依据的答案。
- 用 Telegram 跑提醒和轻量交互。
- 在原文直发 LLM 与 PII rehydration 之间切换。
- 用 synthetic sample data 安全演示完整产品，而不用暴露真实邮箱内容。

## 界面预览

仓库内已经包含基于 synthetic sample data 生成的演示素材，因此 GitHub 首页展示的就是实际产品界面，而不是空壳示意图。

![任务总览](docs/demo/screenshots/01_tasks_overview.png)
![AI 搜索答案](docs/demo/screenshots/02_ai_search_answer.png)
![已索引来源](docs/demo/screenshots/03_indexed_sources.png)

## Demo GIF

![MailMind AI search demo](docs/demo/gifs/hero_ai_search.gif)

![MailMind documents and settings demo](docs/demo/gifs/documents_and_settings.gif)

仓库里的 demo GIF 和截图都来自 sample 数据，不包含真实邮件、OAuth token、API key 或私人附件。

## 快速导航

- [这个项目是什么](#这个项目是什么)
- [适合谁使用](#适合谁使用)
- [快速开始：Demo Mode](#快速开始demo-mode)
- [接入真实 Gmail](#接入真实-gmail)
- [核心流程](#核心流程)
- [AI Search 和 RAG](#ai-search-和-rag)
- [隐私模型](#隐私模型)
- [可选服务](#可选服务)
- [仓库结构](#仓库结构)
- [下一步该看什么](#下一步该看什么)
- [项目状态和边界](#项目状态和边界)

## 这个项目是什么

MailMind 是个人生产力工具，不是托管 SaaS。你在自己的电脑上运行它，连接自己的 Gmail OAuth desktop client，数据库、附件和搜索 index 都保存在本地。

这个项目不是一个简单 chatbot demo，而是一个完整的开源 MVP：包含结构化抽取、显式隐私边界、source-grounded RAG、scheduler、可用的 dashboard，以及适合公开展示的 demo mode。

## 适合谁使用

MailMind 特别适合：

- 经常收到学校、招聘、行政、财务、表格类邮件的人；
- 想在 Gmail 之上加一层本地任务系统，但不想把邮箱交给托管服务的人；
- 想学习一个端到端 LLM 工程项目的人；
- 想要一个比普通 chatbot demo 更完整的作品集项目的人。

它不适合作为开箱即用的多人 SaaS。Gmail restricted scope 如果要公开生产使用，需要完成 Google OAuth verification。

## 一次典型刷新会发生什么

```text
Refresh
  -> 通过只读 OAuth 拉取 Gmail
  -> 在本地归一化邮件与附件
  -> 用经过校验的 LLM 输出提取行动项
  -> 更新任务视图和搜索索引
  -> 用检索到的来源回答 inbox 问题
```

## 快速开始：Demo Mode

Demo mode 是最快的体验方式，不需要 Gmail credentials，也不需要付费 API 调用。

### 1）克隆并安装依赖

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

### 2）让 LLM provider 保持在 mock 模式

在 `.env` 里设置：

```text
MAILMIND_LLM_PROVIDER=mock
```

### 3）构建 dashboard 并启动 API

```powershell
cd dashboard
npm install
npm run build
cd ..

python -m mailmind.api
```

### 4）打开 demo 页面

```text
http://127.0.0.1:8000/?demo=1
```

## 接入真实 Gmail

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
ANTHROPIC_API_KEY=your_anthropic_api_key
MAILMIND_GMAIL_CREDENTIALS=credentials.json
MAILMIND_GMAIL_TOKEN=token.json
MAILMIND_POLL_QUERY=newer_than:14d
MAILMIND_POLL_LIMIT=40
```

运行：

```powershell
python -m mailmind.api
```

打开 `http://127.0.0.1:8000`，点击 `Refresh`，完成浏览器 OAuth 授权。第一次登录成功后，MailMind 会在本地写入 `token.json`。

## 核心流程

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

## AI Search 和 RAG

MailMind 可以索引 Gmail 邮件正文、text-layer PDF 附件，或两者同时启用。

检索流程包括：

- structure-aware email/PDF chunking；
- child chunks 用于 embedding 和 search；
- parent context 用于最终发送给 Claude；
- Chroma vector retrieval，本地 BGE-M3 embedding；
- SQLite FTS5 BM25 keyword retrieval；
- fusion、reranking、source grouping、deduplication 和 score aggregation；
- Claude 基于 source-labeled context 回答。

第一次本地 embedding 会通过 `sentence-transformers` 下载 `BAAI/bge-m3`。如果开启 reranking，第一次 rerank 查询会下载 `BAAI/bge-reranker-base`。

## 隐私模型

MailMind 支持两条路线：

- `off`：Claude 直接看到原文。
- `rehydrated`：MailMind 先把选定的 PII 替换成 placeholder，再发送给 Claude，最后在本地恢复答案。

PII Guard 覆盖 email、phone、SSN、ID-like values、account-like numbers、API keys/tokens/secrets 和保守英文姓名检测。日期默认保留，避免影响 deadline extraction 和 RAG answer。

这只是隐私风险缓解，不是合规认证。本地 SQLite、下载附件、Chroma index 和 FTS index 不会被全局脱敏。

## 可选服务

Scheduler worker:

```powershell
python -m mailmind.worker
```

Telegram bot:

```powershell
python -m mailmind.bot
```

Telegram 需要：

```text
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
MAILMIND_TELEGRAM_NOTIFICATIONS_ENABLED=true
```

## 仓库结构

```text
mailmind/          FastAPI 后端、Gmail client、抽取、数据库、RAG、worker、bot
dashboard/         Next.js dashboard，静态导出后由 FastAPI 托管
prompts/           Claude task extraction 和 RAG answer prompts
tests/             parser、database、API、extraction、RAG、privacy 的测试
scripts/           demo asset 生成、RAG evaluation、GitHub 发布辅助脚本
docs/              demo flow、PII 架构、README GIF 和截图
eval/              RAG evaluation seed file 和评估报告
```

## 下一步该看什么

- Demo walkthrough: [docs/DEMO_FLOW.md](docs/DEMO_FLOW.md)
- PII architecture: [docs/PII_ARCHITECTURE.md](docs/PII_ARCHITECTURE.md)
- Security notes: [SECURITY.md](SECURITY.md)
- Demo assets: [docs/demo/GITHUB_ASSETS.md](docs/demo/GITHUB_ASSETS.md)
- Brand GIF storyboard: [docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md](docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md)

## RAG Evaluation

把评估问题加入 `eval/rag_eval.json` 后运行：

```powershell
python scripts\eval_rag.py --mode vector --top-k 4
python scripts\eval_rag.py --mode hybrid --top-k 4
```

评估脚本会输出 source recall 和检索到的 source labels。synthetic/hard-negative evaluator 会创建临时本地 index，生成的 index 数据不要提交到 GitHub。

## 项目状态和边界

MailMind 是一个可以本地运行的 MVP，适合个人使用、作品集展示和继续开发。

当前边界：

- 不是公开托管 SaaS；
- 没有多人账号体系；
- 不支持 scanned PDF OCR；
- 没有完成 Google OAuth restricted-scope 生产审核；
- PII Guard 不声明合规认证；
- 暂未实现 Gmail push notification 实时触发。

## 社区协作

欢迎 issue 和 pull request。适合优先改进的方向包括文档修正、retrieval evaluation cases、UI polish、setup automation，以及更安全的本地隐私默认配置。

请不要在 issue 里贴真实邮件内容、OAuth token、API key 或私人附件。提问题前优先使用 `.github/ISSUE_TEMPLATE/` 中的模板；如果涉及敏感复现信息，请先阅读 [SECURITY.md](SECURITY.md)。

## License

MIT
