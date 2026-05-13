from __future__ import annotations

from .config import get_settings
from .db import Database
from .notifications import format_task_list, iso_hours_from_now
from .worker import mark_24h_notifications, process_once


settings = get_settings()
db = Database(settings.db_path)
db.init()


async def list_cmd(update, context) -> None:
    await update.message.reply_text(format_task_list(db.list_tasks()))


async def today_cmd(update, context) -> None:
    tasks = db.list_due_tasks(iso_hours_from_now(24))
    await update.message.reply_text(format_task_list(tasks, empty="No tasks due today."))


async def done_cmd(update, context) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /done <task_id>")
        return
    task_id = context.args[0]
    if db.mark_task_done(task_id):
        await update.message.reply_text(f"Marked {task_id} complete.")
    else:
        await update.message.reply_text(f"Task not found: {task_id}")


async def search_cmd(update, context) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /search <keyword>")
        return
    query = " ".join(context.args)
    await update.message.reply_text(format_task_list(db.list_tasks(search=query), empty="No matching tasks."))


async def poll_cmd(update, context) -> None:
    processed = process_once()
    await update.message.reply_text(f"Processed {processed} new email(s).")


async def reminders_job(context) -> None:
    current = get_settings()
    if not current.telegram_notifications_enabled or not current.deadline_reminders_enabled:
        return
    chat_id = current.telegram_chat_id
    if not chat_id:
        return
    tasks = mark_24h_notifications()
    if tasks:
        await context.bot.send_message(chat_id=chat_id, text="24-hour deadline warning:\n\n" + format_task_list(tasks))


def main() -> None:
    try:
        from telegram.ext import Application, CommandHandler
    except ImportError as exc:  # pragma: no cover - exercised in configured runtime
        raise RuntimeError("Install Telegram dependency with `pip install -r requirements.txt`.") from exc

    if not settings.telegram_bot_token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN in .env before starting the bot.")

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("today", today_cmd))
    app.add_handler(CommandHandler("done", done_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("poll", poll_cmd))
    app.job_queue.run_repeating(reminders_job, interval=3600, first=15)
    print("MailMind Telegram bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()
