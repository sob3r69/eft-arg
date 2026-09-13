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
- `POST /api/objectives/{id}/submit/`
- `GET /api/progress/`

## Игровой flow

Игрок не меняет прогресс напрямую. Он создает `Submission` для конкретного `QuestObjective`.
Заявка получает статус `pending`. Администратор подтверждает или отклоняет ее в `/admin/`.
При подтверждении сервис увеличивает прогресс objective, завершает objective при достижении
`required_amount`, завершает quest при выполнении всех objectives и открывает зависимые quests.
