# EFT ARG Backend

Простой Django + DRF backend для ARG-приложения по Escape from Tarkov.

## Требования

- Python 3.12+
- SQLite

## Установка

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py seed
python manage.py runserver
```

API будет доступно по адресу:

```text
http://127.0.0.1:8000/api/
```

Django Admin:

```text
http://127.0.0.1:8000/admin/
```

## Изображения

Аватар торговца и изображение квеста загружаются через поле `Image` в Django Admin.
Файлы хранятся в `backend/media/traders/` и `backend/media/quests/`; API возвращает
их URL в поле `image` (либо `null`, если изображение не задано).
Папка `media/` не входит в git и должна сохраняться вместе с резервной копией базы.
При `DEBUG=True` Django обслуживает `/media/` автоматически; на production этот путь
нужно настроить в веб-сервере или подключить файловое хранилище.

## API endpoints

- `GET /api/traders/`
- `GET /api/traders/{id}/`
- `GET /api/traders/{id}/quests/`
- `GET /api/quests/`
- `GET /api/quests/?status=active`
- `GET /api/quests/?status=available`
- `GET /api/quests/?trader=prapor`
- `GET /api/quests/{id}/`
- `POST /api/quests/{id}/start/`
- `POST /api/quests/{id}/complete/`
- `POST /api/objectives/{id}/submit/`
- `GET /api/progress/`

## Игровой flow

Игрок не меняет прогресс напрямую. Он создает `Submission` для конкретного `QuestObjective`.
Заявка получает статус `pending`. Администратор подтверждает или отклоняет ее в `/admin/`.
При подтверждении сервис увеличивает прогресс objective, завершает objective при достижении
`required_amount`. Когда выполнены все цели, квест остаётся активным и появляется кнопка
«Завершить». Игрок нажимает её без дополнительного подтверждения администратора:
`POST /api/quests/{id}/complete/` завершает квест и открывает зависимые квесты.

### Проверка заявок администратором

1. Для передачи предмета создайте цель с типом `handover_item` и нужным количеством.
2. В активном квесте игрок нажимает «Передать» (для других типов целей: «На проверку»).
   До решения администратора кнопка показывает «Ожидание», прогресс не увеличивается.
3. Откройте `/admin/game/submission/`, затем нужную заявку. Ожидающие заявки идут первыми.
4. Нажмите «Подтвердить передачу» либо заполните `Admin comment` и нажмите «Отклонить заявку».
   Также доступны массовые действия в списке заявок.
5. Интерфейс игрока проверяет состояние выбранного квеста каждые 3 секунды.
   После отказа отображается комментарий и снова доступна отправка.

Каждая цель в детальном ответе API содержит `latest_submission`: последнюю заявку
со статусом, комментарием администратора и временем проверки либо `null`.
Отправлять можно от одного предмета до оставшегося количества. Повторное подтверждение
одной заявки не начисляет прогресс дважды. Прогресс пока общий, без отдельных аккаунтов игроков.
