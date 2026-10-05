from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("game", "0005_initialize_player")]

    operations = [
        migrations.RemoveField(model_name="submission", name="telegram_message_id"),
        migrations.RemoveField(model_name="submission", name="telegram_status"),
    ]
