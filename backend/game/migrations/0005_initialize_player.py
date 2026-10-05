from django.db import migrations
from django.utils import timezone


def initialize_player(apps, schema_editor):
    apps.get_model("game", "PlayerProfile").objects.get_or_create(pk=1)
    # Previously completed quests must not grant rewards after an admin status reset.
    apps.get_model("game", "Quest").objects.filter(status="completed").update(rewards_granted_at=timezone.now())


class Migration(migrations.Migration):
    dependencies = [("game", "0004_quest_dollars_reward_quest_euros_reward_and_more")]
    operations = [migrations.RunPython(initialize_player, migrations.RunPython.noop)]
