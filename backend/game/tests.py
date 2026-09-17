from django.urls import reverse
from io import BytesIO
from tempfile import TemporaryDirectory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import modelform_factory
from PIL import Image
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Quest, QuestObjective, QuestRequirement, Submission, Trader
from .services import approve_submission, reject_submission


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
        self.objective.refresh_from_db()
        self.assertEqual(self.objective.current_amount, 0)

    def test_image_upload_and_absolute_api_urls(self):
        buffer = BytesIO()
        Image.new("RGB", (2, 2)).save(buffer, format="PNG")
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            for instance, directory in [(self.trader, "traders"), (self.quest, "quests")]:
                form_class = modelform_factory(type(instance), fields=["image"])
                invalid = form_class(files={"image": SimpleUploadedFile("bad.png", b"not an image")}, instance=instance)
                self.assertFalse(invalid.is_valid())
                form = form_class(files={"image": SimpleUploadedFile("test.png", buffer.getvalue(), content_type="image/png")}, instance=instance)
                self.assertTrue(form.is_valid(), form.errors)
                form.save()
                self.assertTrue(instance.image.storage.exists(instance.image.name))
                self.assertTrue(instance.image.url.startswith(f"/media/{directory}/"))
            trader = self.client.get(reverse("trader-detail", args=[self.trader.pk])).data
            quest = self.client.get(reverse("quest-detail", args=[self.quest.pk])).data
            self.assertEqual(trader["image"], "http://testserver" + self.trader.image.url)
            self.assertEqual(quest["image"], "http://testserver" + self.quest.image.url)
            quests = self.client.get(reverse("trader-quests", args=[self.trader.pk])).data
            self.assertEqual(quests[0]["image"], quest["image"])

    def test_review_status_is_exposed_and_rejected_submission_can_be_retried(self):
        detail_url = reverse("quest-detail", args=[self.quest.pk])
        submit_url = reverse("objective-submit", args=[self.objective.pk])
        self.assertIsNone(self.client.get(detail_url).data["objectives"][0]["latest_submission"])
        self.client.post(submit_url, {"amount": 1}, format="json")
        detail = self.client.get(detail_url).data
        self.assertEqual(detail["objectives"][0]["latest_submission"]["status"], "pending")
        reject_submission(Submission.objects.get(), "Предмет не передан")
        detail = self.client.get(detail_url).data
        self.assertEqual(detail["objectives"][0]["latest_submission"]["admin_comment"], "Предмет не передан")
        self.assertEqual(detail["objectives"][0]["current_amount"], 0)
        response = self.client.post(submit_url, {"amount": 2}, format="json")
        self.assertEqual(response.status_code, 201)
        approve_submission(Submission.objects.get(pk=response.data["id"]))
        detail = self.client.get(detail_url).data
        self.assertEqual(detail["status"], "active")
        self.assertTrue(detail["objectives"][0]["completed"])
        self.assertEqual(detail["objectives"][0]["latest_submission"]["status"], "approved")

    def test_amount_cannot_exceed_remaining_progress(self):
        response = self.client.post(reverse("objective-submit", args=[self.objective.pk]), {"amount": 3})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Submission.objects.exists())

    def test_admin_review_buttons_update_progress_and_ignore_status_tampering(self):
        admin = get_user_model().objects.create_superuser(username="reviewer", password="test-password")
        self.client.force_login(admin)
        submission = Submission.objects.create(objective=self.objective, amount=2)
        url = reverse("admin:game_submission_change", args=[submission.pk])
        response = self.client.get(url)
        self.assertContains(response, 'name="_approve"')
        self.client.post(url, {"admin_comment": "", "status": "approved", "_save": "Save"})
        submission.refresh_from_db()
        self.assertEqual(submission.status, "pending")
        self.client.post(url, {"admin_comment": "Получено", "_approve": "yes"})
        self.objective.refresh_from_db()
        self.assertTrue(self.objective.completed)
        self.assertEqual(self.objective.current_amount, 2)
        self.client.post(url, {"admin_comment": "Получено", "_approve": "yes"})
        self.objective.refresh_from_db()
        self.assertEqual(self.objective.current_amount, 2)

    def test_admin_reject_preserves_progress_and_returns_comment(self):
        admin = get_user_model().objects.create_superuser(username="reviewer", password="test-password")
        self.client.force_login(admin)
        submission = Submission.objects.create(objective=self.objective, amount=1)
        url = reverse("admin:game_submission_change", args=[submission.pk])
        self.client.post(url, {"admin_comment": "Не получено", "_reject": "yes"})
        submission.refresh_from_db()
        self.objective.refresh_from_db()
        self.assertEqual(submission.status, "rejected")
        self.assertEqual(submission.admin_comment, "Не получено")
        self.assertEqual(self.objective.current_amount, 0)

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

    def test_quest_waits_for_player_after_all_objectives_completed(self):
        submission = Submission.objects.create(objective=self.objective, amount=2)

        approve_submission(submission)
        self.quest.refresh_from_db()

        self.assertEqual(self.quest.status, Quest.Status.ACTIVE)
        url = reverse("quest-complete", args=[self.quest.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Quest.Status.COMPLETED)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.quest.refresh_from_db()
        self.assertEqual(self.quest.status, Quest.Status.COMPLETED)

    def test_cannot_complete_quest_with_unfinished_or_pending_objectives(self):
        url = reverse("quest-complete", args=[self.quest.pk])
        self.assertEqual(self.client.post(url).status_code, 400)
        submission = Submission.objects.create(objective=self.objective, amount=1)
        self.assertEqual(self.client.post(url).status_code, 400)
        approve_submission(submission)
        self.assertEqual(self.client.post(url).status_code, 400)
        self.quest.refresh_from_db()
        self.assertEqual(self.quest.status, Quest.Status.ACTIVE)

    def test_cannot_complete_quest_without_objectives(self):
        self.objective.delete()
        self.assertEqual(self.client.post(reverse("quest-complete", args=[self.quest.pk])).status_code, 400)

    def test_cannot_complete_non_active_quest(self):
        self.objective.completed = True
        self.objective.save()
        for quest_status in [Quest.Status.LOCKED, Quest.Status.AVAILABLE]:
            self.quest.status = quest_status
            self.quest.save()
            self.assertEqual(self.client.post(reverse("quest-complete", args=[self.quest.pk])).status_code, 400)

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

        self.assertEqual(next_quest.status, Quest.Status.LOCKED)
        response = self.client.post(reverse("quest-complete", args=[self.quest.pk]))
        self.assertEqual(response.status_code, 200)
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
