from django.urls import reverse
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import modelform_factory
from PIL import Image
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Quest, QuestObjective, QuestRequirement, Submission, Trader
from .services import approve_submission, reject_submission
from .telegram import handle_update, sync_submissions


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


class TelegramReviewTests(APITestCase):
    def setUp(self):
        trader = Trader.objects.create(name="Прапор", slug="prapor")
        quest = Quest.objects.create(trader=trader, title="Поиски", slug="search", status=Quest.Status.ACTIVE)
        self.objective = QuestObjective.objects.create(
            quest=quest, type=QuestObjective.Type.FIND_ITEM, title="Найти предмет", required_amount=2,
        )
        self.config = self.settings(
            TELEGRAM_BOT_TOKEN="test-token",
            TELEGRAM_CHAT_ID=-100123,
            TELEGRAM_REVIEWER_IDS={42},
        )
        self.config.enable()
        self.addCleanup(self.config.disable)

    @patch("game.telegram.api_call")
    def test_send_and_approve_once(self, api):
        api.return_value = {"message_id": 17}
        submission = Submission.objects.create(objective=self.objective, amount=2)
        sync_submissions()
        submission.refresh_from_db()
        self.assertEqual(submission.telegram_message_id, 17)
        self.assertEqual(api.call_args.args[0], "sendMessage")
        callback = {
            "callback_query": {
                "id": "callback-1", "from": {"id": 42},
                "message": {"message_id": 17, "chat": {"id": -100123}},
                "data": f"approve:{submission.pk}",
            }
        }
        handle_update(callback)
        handle_update(callback)
        self.objective.refresh_from_db()
        self.assertEqual(self.objective.current_amount, 2)
        sync_submissions()
        submission.refresh_from_db()
        self.assertEqual(submission.telegram_status, Submission.Status.APPROVED)
        self.assertEqual(api.call_args.args[0], "editMessageText")

    @patch("game.telegram.api_call")
    def test_reject_and_restrict_reviewers(self, api):
        submission = Submission.objects.create(objective=self.objective, amount=1, telegram_message_id=17)
        callback = {
            "callback_query": {
                "id": "callback-2", "from": {"id": 43},
                "message": {"message_id": 17, "chat": {"id": -100123}},
                "data": f"reject:{submission.pk}",
            }
        }
        handle_update(callback)
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.PENDING)
        callback["callback_query"]["from"]["id"] = 42
        callback["callback_query"]["message"]["chat"]["id"] = -100999
        handle_update(callback)
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.PENDING)
        callback["callback_query"]["message"]["chat"]["id"] = -100123
        callback["callback_query"]["message"]["message_id"] = 18
        handle_update(callback)
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.PENDING)
        callback["callback_query"]["message"]["message_id"] = 17
        handle_update(callback)
        submission.refresh_from_db()
        self.assertEqual(submission.status, Submission.Status.REJECTED)
        self.objective.refresh_from_db()
        self.assertEqual(self.objective.current_amount, 0)

    @patch("game.telegram.api_call")
    def test_admin_review_updates_group_message(self, api):
        submission = Submission.objects.create(
            objective=self.objective, amount=1, telegram_message_id=17,
            telegram_status=Submission.Status.PENDING,
        )
        reject_submission(submission, "Не получено")
        sync_submissions()
        self.assertEqual(api.call_args.args[0], "editMessageText")
        self.assertIn("Не получено", api.call_args.args[1]["text"])


class RewardTests(APITestCase):
    def setUp(self):
        GameFlowTests.setUp(self)
        from decimal import Decimal
        from .models import PlayerProfile
        self.profile, _ = PlayerProfile.objects.get_or_create(pk=1)
        self.profile.rubles = 100
        self.profile.euros = 20
        self.profile.dollars = 30
        self.profile.experience = 9900
        self.profile.save()
        self.trader.reputation = Decimal("1.20")
        self.trader.save()
        self.quest.reputation_reward = Decimal("0.25")
        self.quest.rubles_reward = 500
        self.quest.euros_reward = 10
        self.quest.dollars_reward = 5
        self.quest.experience_reward = 100
        self.quest.save()

    def test_rewards_only_granted_once_at_completion_even_after_status_reset(self):
        from decimal import Decimal
        from .services import complete_quest
        approve_submission(Submission.objects.create(objective=self.objective, amount=2))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.rubles, 100)
        complete_quest(self.quest)
        complete_quest(self.quest)
        self.quest.status = Quest.Status.ACTIVE
        self.quest.save(update_fields=["status"])
        complete_quest(self.quest)
        self.profile.refresh_from_db()
        self.trader.refresh_from_db()
        self.assertEqual((self.profile.rubles, self.profile.euros, self.profile.dollars), (600, 30, 35))
        self.assertEqual(self.profile.experience, 10000)
        self.assertEqual(self.profile.level, 2)
        self.assertEqual(self.trader.reputation, Decimal("1.45"))
        self.quest.refresh_from_db()
        self.assertIsNotNone(self.quest.rewards_granted_at)

    def test_failed_completion_does_not_grant_rewards(self):
        self.assertEqual(self.client.post(reverse("quest-complete", args=[self.quest.pk])).status_code, 400)
        self.profile.refresh_from_db()
        self.trader.refresh_from_db()
        self.assertEqual(self.profile.rubles, 100)
        self.assertEqual(str(self.trader.reputation), "1.20")
        self.assertEqual(self.profile.experience, 9900)

    def test_profile_and_rewards_api(self):
        self.profile.nickname = "Новое имя"
        self.profile.experience_per_level = 1000
        self.profile.save()
        profile = self.client.get(reverse("player-profile")).data
        self.assertEqual(profile["nickname"], "Новое имя")
        self.assertEqual(profile["level"], 10)
        self.assertEqual(profile["rubles"], 100)
        self.assertEqual(self.client.post(reverse("player-profile"), {"rubles": 999}).status_code, 405)
        for url in [reverse("quest-list"), reverse("quest-detail", args=[self.quest.pk]), reverse("trader-quests", args=[self.trader.pk])]:
            data = self.client.get(url).data
            quest = data[0] if isinstance(data, list) else data
            self.assertEqual(quest["reputation_reward"], "0.25")
            self.assertEqual(quest["rubles_reward"], 500)
            self.assertEqual(quest["experience_reward"], 100)
        self.assertEqual(self.client.get(reverse("trader-list")).data[0]["reputation"], "1.20")

    def test_profile_admin_fields_and_validation(self):
        from .models import PlayerProfile
        form_class = modelform_factory(PlayerProfile, fields=["nickname", "rubles", "euros", "dollars", "experience", "experience_per_level", "avatar"])
        values = dict(nickname="Игрок", rubles=1, euros=2, dollars=3, experience=500, experience_per_level=100)
        form = form_class(data=values, instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(self.profile.level, 6)
        self.assertFalse(form_class(data={**values, "experience_per_level": 0}, instance=self.profile).is_valid())
        self.assertFalse(form_class(data={**values, "rubles": -1}, instance=self.profile).is_valid())

    def test_admin_can_edit_profile_and_reputation(self):
        admin = get_user_model().objects.create_superuser(username="editor", password="test-password")
        self.client.force_login(admin)
        response = self.client.post(reverse("admin:game_playerprofile_change", args=[1]), {
            "nickname": "Новое имя", "rubles": 123, "euros": 4, "dollars": 5,
            "experience": 2000, "experience_per_level": 500, "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.nickname, "Новое имя")
        self.assertEqual(self.profile.rubles, 123)
        self.assertEqual(self.profile.level, 5)
        response = self.client.post(reverse("admin:game_trader_change", args=[self.trader.pk]), {
            "name": self.trader.name, "slug": self.trader.slug, "available": "on",
            "reputation": "2.50", "sort_order": 0, "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        self.trader.refresh_from_db()
        self.assertEqual(str(self.trader.reputation), "2.50")

    def test_avatar_upload_and_api_url(self):
        from .models import PlayerProfile
        buffer = BytesIO()
        Image.new("RGB", (2, 2)).save(buffer, format="PNG")
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            form_class = modelform_factory(PlayerProfile, fields=["avatar"])
            form = form_class(files={"avatar": SimpleUploadedFile("avatar.png", buffer.getvalue(), content_type="image/png")}, instance=self.profile)
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
            data = self.client.get(reverse("player-profile")).data
            self.assertEqual(data["avatar"], "http://testserver" + self.profile.avatar.url)
            self.assertTrue(self.profile.avatar.storage.exists(self.profile.avatar.name))
