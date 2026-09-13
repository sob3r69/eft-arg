from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Quest, QuestObjective, Submission


@transaction.atomic
def approve_submission(submission: Submission) -> Submission:
    submission = Submission.objects.select_for_update().select_related("objective__quest").get(pk=submission.pk)

    if submission.status == Submission.Status.APPROVED:
        return submission

    if submission.status != Submission.Status.PENDING:
        return submission

    objective = QuestObjective.objects.select_for_update().select_related("quest").get(pk=submission.objective_id)
    now = timezone.now()

    submission.status = Submission.Status.APPROVED
    submission.reviewed_at = now
    submission.save(update_fields=["status", "reviewed_at"])

    objective.current_amount = min(
        objective.current_amount + submission.amount,
        objective.required_amount,
    )
    update_fields = ["current_amount"]

    if objective.current_amount >= objective.required_amount and not objective.completed:
        objective.completed = True
        objective.completed_at = now
        update_fields.extend(["completed", "completed_at"])

    objective.save(update_fields=update_fields)
    update_quest_status(objective.quest)

    return submission


@transaction.atomic
def reject_submission(submission: Submission, admin_comment: str = "") -> Submission:
    submission = Submission.objects.select_for_update().get(pk=submission.pk)

    if submission.status != Submission.Status.PENDING:
        return submission

    submission.status = Submission.Status.REJECTED
    submission.admin_comment = admin_comment
    submission.reviewed_at = timezone.now()
    submission.save(update_fields=["status", "admin_comment", "reviewed_at"])

    return submission


def update_quest_status(quest: Quest) -> Quest:
    if quest.status == Quest.Status.COMPLETED:
        return quest

    has_objectives = quest.objectives.exists()
    has_incomplete_objectives = quest.objectives.filter(completed=False).exists()

    if has_objectives and not has_incomplete_objectives:
        quest.status = Quest.Status.COMPLETED
        quest.save(update_fields=["status", "updated_at"])
        refresh_available_quests()

    return quest


def refresh_available_quests() -> int:
    changed_count = 0
    locked_quests = Quest.objects.filter(status=Quest.Status.LOCKED).prefetch_related("requirements__required_quest")

    for quest in locked_quests:
        requirements = list(quest.requirements.all())
        if not requirements:
            continue

        requirements_completed = all(
            requirement.required_quest.status == Quest.Status.COMPLETED
            for requirement in requirements
        )

        if requirements_completed:
            quest.status = Quest.Status.AVAILABLE
            quest.save(update_fields=["status", "updated_at"])
            changed_count += 1

    return changed_count


def start_quest(quest: Quest) -> Quest:
    if quest.status != Quest.Status.AVAILABLE:
        raise ValidationError({"detail": "Only available quests can be started."})

    quest.status = Quest.Status.ACTIVE
    quest.save(update_fields=["status", "updated_at"])
    return quest
