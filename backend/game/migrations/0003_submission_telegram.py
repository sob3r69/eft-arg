from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("game", "0002_quest_image_alter_trader_image")]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="telegram_message_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="submission",
            name="telegram_status",
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
