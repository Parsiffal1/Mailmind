[English](README.md) | [中文](README.zh.md)

<div align="center">
  <h1>MailMind</h1>
  <p><em>一个本地优先的 Gmail 智能助手，把个人邮箱变成可搜索、可执行、可保护隐私的工作台。</em></p>
  <p>
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" />
    <img src="https://img.shields.io/badge/Architecture-Local--first-blue" alt="Architecture: Local-first" />
    <img src="https://img.shields.io/badge/Gmail-Read--only%20OAuth-red" alt="Gmail: Read-only OAuth" />
    <img src="https://img.shields.io/badge/AI%20Search-RAG%20enabled-7c3aed" alt="AI Search: RAG enabled" />
  </p>
  <p><strong>MailMind 是一个本地优先的 Gmail 智能助手，用于从个人邮箱中自动整理任务、截止日期和回复提醒，支持对邮件正文与 PDF 附件进行基于 RAG 的 AI Search。</strong></p>
  <p>
    它内置可选的 PII 隐私保护，用来防止邮件中的敏感信息泄露到云端大模型；系统基于 Gmail read-only OAuth、LLM + Pydantic、SQLite、FastAPI、Next.js 和 hybrid RAG 构建，强调本地数据存储、RAG AI 问答，以及系统可配置的 PII 隐私保护。
  </p>
  <p>
    <a href="#界面预览">界面预览</a> ·
    <a href="#安装">安装</a> ·
    <a href="#你能得到什么">你能得到什么</a> ·
    <a href="#它怎么工作">它怎么工作</a> ·
    <a href="#ai-search-和-rag">AI Search</a> ·
    <a href="#隐私模型">隐私</a> ·
    <a href="#继续阅读">继续阅读</a>
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

## 界面预览

![任务总览](docs/demo/screenshots/01_tasks_overview.png)
![AI 搜索答案](docs/demo/screenshots/02_ai_search_answer.png)

仓库里的截图不包含真实邮件、OAuth token、API key 或私人附件。

## 安装

如果你只是想最快看到产品效果，建议先跑 demo mode。它不需要 Gmail 凭据，也不需要真实模型调用。

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 里设置：

```text
MAILMIND_LLM_PROVIDER=mock
```

然后构建 dashboard 并启动 API：

```bash
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

设置：

```text
MAILMIND_LLM_PROVIDER=mock
```

## 你能得到什么

- **把杂乱线程变成结构化任务**：自动抽出 due date、待回复、follow-up 和待审核事项。
- **一个真正可工作的 dashboard**：不用反复重读整箱邮件，也知道接下来先做什么。
- **带来源依据的 inbox 搜索**：回答会附带检索证据，而不是脱离上下文的聊天式猜测。
- **默认 local-first**：邮件元数据、索引和工作流状态优先保留在你的机器上。
- **可选 Telegram 提醒**：同一层任务抽取结果可以直接变成站外提醒。
- **适合作品集公开展示**：仓库里的演示素材是 synthetic 的，可以安全展示。

## 接入真实 Gmail

1. 打开 Google Cloud Console。
2. 创建或选择一个项目。
3. 启用 Gmail API。
4. 配置 consent screen，个人项目可使用 external testing。
5. 创建 OAuth client ID，类型选择 `Desktop app`。
6. 下载 OAuth client JSON，保存到项目根目录并命名为 `credentials.json`。
7. 在 Google Auth Platform 中把自己的 Gmail 加为 test user。

然后配置 `.env`：

```text
MAILMIND_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_a...key
MAILMIND_GMAIL_CREDENTIALS=credentials.json
MAILMIND_GMAIL_TOKEN=token.json
MAILMIND_POLL_QUERY=newer_than:14d
MAILMIND_POLL_LIMIT=40
```

运行：

```bash
python -m mailmind.api
```

打开 `http://127.0.0.1:8000`，点击 `Refresh`，完成浏览器 OAuth 授权。第一次登录成功后，MailMind 会在本地写入 `token.json`。

## 它怎么工作

```text
Refresh
  -> 通过只读 OAuth 拉取 Gmail
  -> 在本地归一化邮件与附件
  -> 用经过校验的 LLM 输出提取行动项
  -> 更新任务视图和搜索索引
  -> 用检索到的来源回答 inbox 问题
```

```text
Gmail 只读 OAuth
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

当前 50-case post-improvement benchmark（见 `eval/RAG_EVALUATION_RESULTS.md`）：

| 指标 | Vector-only | Hybrid after | 提升 |
| --- | ---: | ---: | ---: |
| Top-1 Source Recall | 48.35% | 63.74% | +15.39 pp |
| Any-source Recall@4 | 58.24% | 78.02% | +19.78 pp |
| Full-source Recall@4 | 46.15% | 64.84% | +18.69 pp |
| MRR | 0.522 | 0.691 | +0.169 |

第一次本地 embedding 会通过 `sentence-transformers` 下载 `BAAI/bge-m3`。如果开启 reranking，第一次 rerank 查询会下载 `BAAI/bge-reranker-base`。

## 隐私模型

MailMind 支持两条路线：

- `off`：Claude 直接看到原文。
- `rehydrated`：MailMind 先把选定的 PII 替换成 placeholder，再发送给 Claude，最后在本地恢复答案。

PII Guard 覆盖 email、phone、SSN、ID-like values、account-like numbers、API keys/tokens/secrets 和保守英文姓名检测。日期默认保留，避免影响 deadline extraction 和 RAG answer。

这只是隐私风险缓解，不是合规认证。本地 SQLite、下载附件、Chroma index 和 FTS index 不会被全局脱敏。

## 可选服务

Scheduler worker:

```bash
python -m mailmind.worker
```

Telegram bot:

```bash
python -m mailmind.bot
```

Telegram 需要：

```text
TELEGRAM_BOT_TOKEN=your_t...ken
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
docs/              demo flow、PII 架构、README 资源和截图
eval/              RAG evaluation seed file 和评估报告
```

## 继续阅读

- PII architecture: [docs/PII_ARCHITECTURE.md](docs/PII_ARCHITECTURE.md)
- Security notes: [SECURITY.md](SECURITY.md)
- Demo assets: [docs/demo/GITHUB_ASSETS.md](docs/demo/GITHUB_ASSETS.md)
- Brand GIF storyboard: [docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md](docs/demo/MAILMIND_BRAND_GIF_STORYBOARD.md)

## RAG evaluation

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
