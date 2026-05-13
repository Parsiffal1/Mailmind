from __future__ import annotations

import base64
from pathlib import Path
from typing import Iterable

from .email_parser import parse_gmail_message
from .models import EmailRecord

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
    def __init__(self, credentials_path: Path, token_path: Path):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._build_service()

    def _build_service(self):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover - exercised in configured runtime
            raise RuntimeError("Install Gmail dependencies with `pip install -r requirements.txt`.") from exc

        creds = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Missing Gmail OAuth credentials at {self.credentials_path}. "
                        "Download an OAuth desktop client JSON from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)
            self.token_path.write_text(creds.to_json(), encoding="utf-8")
        return build("gmail", "v1", credentials=creds)

    def iter_recent_messages(self, query: str, limit: int) -> Iterable[EmailRecord]:
        response = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=limit)
            .execute()
        )
        for item in response.get("messages", []):
            raw = (
                self.service.users()
                .messages()
                .get(userId="me", id=item["id"], format="full")
                .execute()
            )
            yield parse_gmail_message(raw)

    def get_message(self, message_id: str) -> EmailRecord:
        raw = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return parse_gmail_message(raw)

    def download_attachment(self, message_id: str, attachment_id: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        raw = (
            self.service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
        data = raw.get("data", "")
        padded = data + "=" * (-len(data) % 4)
        output_path.write_bytes(base64.urlsafe_b64decode(padded.encode("utf-8")))
        return output_path
