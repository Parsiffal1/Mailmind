import base64
from datetime import timezone

from mailmind.email_parser import decode_body, parse_gmail_message


def b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_decode_body_handles_urlsafe_padding():
    assert decode_body(b64("hello")) == "hello"


def test_parse_plain_text_message():
    message = {
        "id": "msg-1",
        "payload": {
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "Subject", "value": "Submit form"},
                {"name": "Date", "value": "Mon, 11 May 2026 10:00:00 -0700"},
            ],
            "mimeType": "text/plain",
            "body": {"data": b64("Please submit the form by 2026-05-12.")},
        },
    }

    email = parse_gmail_message(message)

    assert email.id == "msg-1"
    assert email.sender == "sender@example.com"
    assert email.subject == "Submit form"
    assert "submit the form" in email.body
    assert email.received_at.tzinfo == timezone.utc


def test_parse_html_message_and_attachment():
    message = {
        "id": "msg-2",
        "payload": {
            "headers": [{"name": "From", "value": "sender@example.com"}],
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {"data": b64("<p>Action <strong>required</strong></p>")},
                },
                {
                    "filename": "offer.pdf",
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "att-1", "size": 123},
                },
            ],
        },
    }

    email = parse_gmail_message(message)

    assert "Action" in email.body
    assert email.attachments[0].filename == "offer.pdf"

