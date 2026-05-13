# Contributing to MailMind

Thanks for taking a look at MailMind. This project is a local-first Gmail intelligence agent, so contributions should preserve the core constraints: read-only Gmail access, local storage by default, explicit privacy boundaries, and no committed user data.

## Good First Contributions

- Improve setup instructions for Windows, macOS, or Linux.
- Add tests around Gmail parsing, extraction validation, RAG retrieval, or PII handling.
- Add synthetic RAG evaluation cases.
- Polish dashboard UI states.
- Improve demo scripts or README assets.
- Add safer setup checks for missing `.env`, Gmail credentials, or dashboard build output.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cd dashboard
npm install
npm run build
cd ..

python -m pytest -q
```

For demo-only development, set:

```text
MAILMIND_LLM_PROVIDER=mock
```

## Pull Request Checklist

Before opening a PR:

- Run `python -m pytest -q`.
- Run `npm run build` inside `dashboard/` if frontend files changed.
- Do not commit `.env`, `credentials.json`, `token.json`, `data/`, `attachments/`, or `chroma/`.
- Do not include real Gmail content, real attachments, API keys, OAuth tokens, or personal data.
- Update README or docs when behavior changes.

## Security and Privacy

MailMind touches private inbox data. Keep changes conservative around Gmail scopes, LLM prompts, local persistence, and RAG indexing. If a change sends more data to an external provider, document it clearly and make it configurable where practical.
