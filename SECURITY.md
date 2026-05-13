# Security Policy

MailMind is a local-first personal productivity project. It is not a hosted SaaS service and does not provide a managed security boundary for multiple users.

## Credential Handling

Never commit:

- `.env`
- `credentials.json`
- `token.json`
- local SQLite databases
- downloaded attachments
- Chroma/FTS indexes

Use a Google OAuth desktop client with the minimum Gmail scope used by this project:

```text
https://www.googleapis.com/auth/gmail.readonly
```

Rotate any API key or OAuth credential that is accidentally committed or shared.

## Gmail Data

`gmail.readonly` can expose email bodies, headers, metadata, and attachments. Even though the scope is read-only, Google treats Gmail content scopes as restricted because they provide broad access to private user data.

MailMind stores Gmail-derived data locally in SQLite. PDF attachments are downloaded locally only when PDF indexing is enabled and requested.

If you distribute MailMind as a public hosted product, you must handle Google OAuth verification, restricted-scope review, user consent, privacy policy, deletion requests, and any required security assessment.

## LLM Processing

When `MAILMIND_LLM_PROVIDER=anthropic`, selected email text and retrieved RAG context are sent to Anthropic for task extraction and question answering.

When `MAILMIND_LLM_PROVIDER=mock`, no external LLM call is made for task extraction.

When `MAILMIND_PII_MODE=rehydrated`, MailMind replaces selected sensitive values with local placeholders before sending task extraction prompts and RAG answer prompts to Claude, then restores placeholders locally in the final user-visible answer.

PII Guard is regex/rule-based risk reduction. It is not full anonymization and is not a compliance certification.

## Embeddings and RAG

The default embedding provider is local BGE-M3 through `sentence-transformers`, so email/PDF chunks are embedded locally.

If you switch to a remote embedding provider such as Voyage, indexed chunks are sent to that provider during embedding.

Chroma and SQLite FTS indexes are stored locally and are not globally redacted by PII Guard.

## PII Guard Limits

- `MAILMIND_PII_MODE=off` sends original text to Claude.
- `MAILMIND_PII_MODE=rehydrated` pseudonymizes only the LLM boundary and restores output locally.
- Local SQLite email bodies, downloaded attachments, Chroma indexes, and FTS indexes remain unredacted.
- Dates are preserved by default so deadline extraction continues to work.
- Conservative English names are pseudonymized when `MAILMIND_PII_REDACT_NAMES=true`; ambiguous names, organizations, course names, and non-English names may not be fully detected.
- Processing log messages are pseudonymized when `MAILMIND_PII_REDACT_LOGS=true`.

## Reporting Issues

Open a GitHub issue without including private credentials, raw emails, OAuth tokens, API keys, or real attachments. If a report requires sensitive evidence, redact it before posting.
