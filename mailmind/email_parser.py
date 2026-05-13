from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any

from bs4 import BeautifulSoup

from .models import AttachmentMeta, EmailRecord


def decode_body(data: str | None) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="replace")


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return unescape(soup.get_text("\n", strip=True))


def _headers_to_dict(headers: list[dict[str, str]]) -> dict[str, str]:
    return {item.get("name", "").lower(): item.get("value", "") for item in headers}


def _parse_received_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _walk_parts(payload: dict[str, Any]) -> tuple[list[str], list[str], list[AttachmentMeta]]:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[AttachmentMeta] = []
    stack = [payload]

    while stack:
        part = stack.pop()
        filename = part.get("filename") or ""
        body = part.get("body") or {}
        mime_type = part.get("mimeType")
        attachment_id = body.get("attachmentId")

        if filename and attachment_id:
            attachments.append(
                AttachmentMeta(
                    id=attachment_id,
                    filename=filename,
                    mime_type=mime_type,
                    size=body.get("size"),
                )
            )

        data = body.get("data")
        if data and mime_type == "text/plain":
            plain_parts.append(decode_body(data))
        elif data and mime_type == "text/html":
            html_parts.append(html_to_text(decode_body(data)))

        for child in part.get("parts", []) or []:
            stack.append(child)

    return plain_parts, html_parts, attachments


def parse_gmail_message(message: dict[str, Any]) -> EmailRecord:
    payload = message.get("payload") or {}
    headers = _headers_to_dict(payload.get("headers", []) or [])
    plain_parts, html_parts, attachments = _walk_parts(payload)
    body = "\n\n".join(part.strip() for part in plain_parts if part.strip())
    if not body:
        body = "\n\n".join(part.strip() for part in html_parts if part.strip())

    return EmailRecord(
        id=message["id"],
        sender=headers.get("from", ""),
        subject=headers.get("subject"),
        received_at=_parse_received_at(headers.get("date")),
        body=body,
        attachments=attachments,
    )

