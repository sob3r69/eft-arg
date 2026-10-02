import logging
import time
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from game.telegram import api_call, handle_update, sync_submissions


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Poll Telegram for submission reviews and sync submission messages"

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stdout.write("Telegram bot disabled: set TELEGRAM_BOT_TOKEN")
            return
        offset = None
        while True:
            try:
                close_old_connections()
                sync_submissions()
                updates = api_call("getUpdates", {
                    "offset": offset,
                    "timeout": 15,
                    "allowed_updates": ["message", "callback_query"],
                }, timeout=25)
                for update in updates:
                    handle_update(update)
                    offset = update["update_id"] + 1
                close_old_connections()
            except KeyboardInterrupt:
                return
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError) as error:
                logger.warning("Telegram bot error: %s", error)
                time.sleep(5)
