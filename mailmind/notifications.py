from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def format_task(task: dict) -> str:
    due = task.get("due_at") or "no due date"
    review = " [review]" if task.get("needs_review") else ""
    return f"{task['id']} | {task['priority']} | {due}{review}\n{task['description']}\nFrom: {task.get('sender', '')}"


def format_task_list(tasks: list[dict], empty: str = "No open tasks.") -> str:
    if not tasks:
        return empty
    return "\n\n".join(format_task(task) for task in tasks)


def format_digest(title: str, tasks: list[dict], empty: str) -> str:
    return f"{title}\n\n{format_task_list(tasks, empty=empty)}"


def send_telegram_message(token: str | None, chat_id: str | None, text: str) -> bool:
    if not token or not chat_id or not text.strip():
        return False
    payload = urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(request, timeout=20) as response:
        return 200 <= response.status < 300


def iso_hours_from_now(hours: int) -> str:
    from datetime import timedelta

    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
