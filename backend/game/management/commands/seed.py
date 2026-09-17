from django.core.management.base import BaseCommand

from game.models import Item, Location, Quest, QuestObjective, QuestRequirement, Trader


class Command(BaseCommand):
    help = "Create sample trader, quests and objectives for local development."

    def handle(self, *args, **options):
        trader, _ = Trader.objects.update_or_create(
            slug="prapor",
            defaults={
                "name": "Прапор",
                "description": "Тестовый торговец для ARG MVP.",
                "available": True,
                "sort_order": 0,
            },
        )
        item, _ = Item.objects.update_or_create(
            slug="sealed-envelope",
            defaults={
                "name": "Запечатанный конверт",
                "description": "Тестовый предмет для проверки objective find_item.",
                "image": "/images/items/sealed-envelope.png",
            },
        )
        location, _ = Location.objects.update_or_create(
            slug="woods-bunker",
            defaults={
                "name": "Бункер на Лесу",
                "description": "Тестовая локация для проверки objective visit_location.",
                "image": "/images/locations/woods-bunker.png",
            },
        )
        quest, _ = Quest.objects.update_or_create(
            slug="test-search",
            defaults={
                "trader": trader,
                "title": "Тестовый квест",
                "description": "Найти предмет и посетить контрольную точку.",
                "status": Quest.Status.AVAILABLE,
                "sort_order": 0,
            },
        )
        follow_up_quest, _ = Quest.objects.update_or_create(
            slug="test-follow-up",
            defaults={
                "trader": trader,
                "title": "Следующий тестовый квест",
                "description": "Откроется после завершения тестового квеста.",
                "status": Quest.Status.LOCKED,
                "sort_order": 1,
            },
        )
        QuestRequirement.objects.get_or_create(quest=follow_up_quest, required_quest=quest)

        QuestObjective.objects.update_or_create(
            quest=quest,
            sort_order=0,
            defaults={
                "type": QuestObjective.Type.FIND_ITEM,
                "title": "Найти запечатанный конверт",
                "description": "Передать заявку после нахождения предмета.",
                "required_amount": 1,
                "item": item,
                "metadata": {"hint": "Проверь тайник у дороги."},
            },
        )
        QuestObjective.objects.update_or_create(
            quest=quest,
            sort_order=1,
            defaults={
                "type": QuestObjective.Type.VISIT_LOCATION,
                "title": "Посетить бункер",
                "description": "Подтвердить посещение контрольной точки.",
                "required_amount": 1,
                "location": location,
                "metadata": {"map": "woods", "location_code": "bunker_01"},
            },
        )

        self.stdout.write(self.style.SUCCESS("Seed data created."))
