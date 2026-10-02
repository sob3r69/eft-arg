import json
from urllib import request

from django.conf import settings
from django.db import models

from .models import Submission
from .services import approve_submission, reject_submission


def api_call(method: str, payload: dict, timeout: int = 25) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=timeout) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {result.get('description')}")
    return result["result"]


def submission_text(submission: Submission) -> str:
    objective = submission.objective
    lines = [
        f"Заявка #{submission.pk}",
        f"Квест: {objective.quest.title}",
        f"Цель: {objective.title}",
        f"Количество: {submission.amount}",
    ]
    if submission.comment:
        lines.append(f"Комментарий: {submission.comment[:1500]}")
    if submission.proof:
        lines.append(f"Доказательство: {submission.proof[:500]}")
    if submission.status != Submission.Status.PENDING:
        status = "Подтверждено" if submission.status == Submission.Status.APPROVED else "Отклонено"
        lines.append(f"Решение: {status}")
        if submission.admin_comment:
            lines.append(f"Причина: {submission.admin_comment[:1000]}")
    return "\n".join(lines)[:4096]


def reply_markup(submission: Submission) -> dict | None:
    if submission.status != Submission.Status.PENDING:
        return None
    return {"inline_keyboard": [[
        {"text": "Подтвердить", "callback_data": f"approve:{submission.pk}"},
        {"text": "Отклонить", "callback_data": f"reject:{submission.pk}"},
    ]]}


def sync_submissions() -> None:
    if not settings.TELEGRAM_CHAT_ID:
        return
    submissions = Submission.objects.select_related("objective__quest").filter(
        status=Submission.Status.PENDING,
        telegram_message_id__isnull=True,
    ).order_by("id")[:20]
    for submission in submissions:
        result = api_call("sendMessage", {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": submission_text(submission),
            "reply_markup": reply_markup(submission),
            "link_preview_options": {"is_disabled": True},
        })
        Submission.objects.filter(pk=submission.pk, telegram_message_id__isnull=True).update(
            telegram_message_id=result["message_id"], telegram_status=submission.status,
        )

    changed = Submission.objects.select_related("objective__quest").filter(
        telegram_message_id__isnull=False,
    ).exclude(status=models.F("telegram_status")).order_by("id")[:20]
    for submission in changed:
        api_call("editMessageText", {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "message_id": submission.telegram_message_id,
            "text": submission_text(submission),
            "link_preview_options": {"is_disabled": True},
        })
        Submission.objects.filter(pk=submission.pk, status=submission.status).update(telegram_status=submission.status)


def handle_update(update: dict) -> None:
    message = update.get("message")
    command = message.get("text", "").split()[0].split("@")[0] if message and message.get("text", "").split() else ""
    if command in {"/id", "/chatid"}:
        value = message.get("from", {}).get("id") if command == "/id" else message.get("chat", {}).get("id")
        if value is not None:
            api_call("sendMessage", {"chat_id": message["chat"]["id"], "text": str(value)})
        return

    callback = update.get("callback_query")
    if not callback:
        return
    callback_id = callback["id"]
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    actor_id = callback.get("from", {}).get("id")
    if chat_id != settings.TELEGRAM_CHAT_ID or actor_id not in settings.TELEGRAM_REVIEWER_IDS:
        api_call("answerCallbackQuery", {"callback_query_id": callback_id, "text": "Нет доступа", "show_alert": True})
        return
    try:
        action, raw_id = callback.get("data", "").split(":", 1)
        if action not in {"approve", "reject"} or not raw_id.isdecimal():
            raise ValueError
        submission = Submission.objects.get(pk=int(raw_id), telegram_message_id=callback["message"]["message_id"])
    except (ValueError, KeyError, Submission.DoesNotExist):
        api_call("answerCallbackQuery", {"callback_query_id": callback_id, "text": "Заявка не найдена", "show_alert": True})
        return

    if submission.status != Submission.Status.PENDING:
        answer = "Заявка уже рассмотрена"
    else:
        updated = approve_submission(submission) if action == "approve" else reject_submission(submission)
        answer = "Подтверждено" if updated.status == Submission.Status.APPROVED else "Отклонено"
    api_call("answerCallbackQuery", {"callback_query_id": callback_id, "text": answer})
