from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Quest, QuestObjective, QuestRequirement, Submission, Trader
from .services import approve_submission


class GameFlowTests(APITestCase):
    def setUp(self):
        self.trader = Trader.objects.create(name="Прапор", slug="prapor")
        self.quest = Quest.objects.create(
            trader=self.trader,
            title="Поиски",
            slug="search",
            status=Quest.Status.ACTIVE,
        )
        self.objective = QuestObjective.objects.create(
            quest=self.quest,
            type=QuestObjective.Type.FIND_ITEM,
            title="Найти предмет",
            required_amount=2,
        )

    def test_create_submission(self):
        url = reverse("objective-submit", args=[self.objective.pk])
        response = self.client.post(url, {"amount": 1, "comment": "Нашел"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Submission.objects.count(), 1)
        self.assertEqual(response.data["status"], Submission.Status.PENDING)

    def test_approve_submission_increases_objective_progress(self):
        submission = Submission.objects.create(objective=self.objective, amount=1)

        approve_submission(submission)
        self.objective.refresh_from_db()

        self.assertEqual(self.objective.current_amount, 1)
        self.assertFalse(self.objective.completed)

    def test_repeated_approve_does_not_increase_progress_twice(self):
        submission = Submission.objects.create(objective=self.objective, amount=1)

        approve_submission(submission)
        approve_submission(submission)
        self.objective.refresh_from_db()

        self.assertEqual(self.objective.current_amount, 1)

    def test_objective_completion(self):
        submission = Submission.objects.create(objective=self.objective, amount=2)

        approve_submission(submission)
        self.objective.refresh_from_db()

        self.assertEqual(self.objective.current_amount, 2)
        self.assertTrue(self.objective.completed)
        self.assertIsNotNone(self.objective.completed_at)

    def test_quest_completion_when_all_objectives_completed(self):
        submission = Submission.objects.create(objective=self.objective, amount=2)

        approve_submission(submission)
        self.quest.refresh_from_db()

        self.assertEqual(self.quest.status, Quest.Status.COMPLETED)

    def test_locked_quest_becomes_available_after_requirements_completed(self):
        next_quest = Quest.objects.create(
            trader=self.trader,
            title="Следующий",
            slug="next",
            status=Quest.Status.LOCKED,
        )
        QuestRequirement.objects.create(quest=next_quest, required_quest=self.quest)
        submission = Submission.objects.create(objective=self.objective, amount=2)

        approve_submission(submission)
        next_quest.refresh_from_db()

        self.assertEqual(next_quest.status, Quest.Status.AVAILABLE)

    def test_cannot_create_submission_for_completed_objective(self):
        self.objective.completed = True
        self.objective.current_amount = 2
        self.objective.save()

        url = reverse("objective-submit", args=[self.objective.pk])
        response = self.client.post(url, {"amount": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_create_submission_for_non_active_quest(self):
        self.quest.status = Quest.Status.AVAILABLE
        self.quest.save()

        url = reverse("objective-submit", args=[self.objective.pk])
        response = self.client.post(url, {"amount": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_start_locked_quest(self):
        self.quest.status = Quest.Status.LOCKED
        self.quest.save()

        url = reverse("quest-start", args=[self.quest.pk])
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pending_submission_blocks_duplicate_pending_submission(self):
        Submission.objects.create(objective=self.objective, amount=1)

        url = reverse("objective-submit", args=[self.objective.pk])
        response = self.client.post(url, {"amount": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
