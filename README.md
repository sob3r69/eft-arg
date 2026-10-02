# Escape Protocol: запуск и деплой

**Для Linux-сервера используйте [Docker Compose](deploy/docker/README.md).**
Настройка Telegram-бота описана в Docker-инструкции.
На сервере нужны только Docker с Compose и домен. Запуск: `docker compose up -d --build`.
Инструкция ниже описывает альтернативный запуск без Docker, настроенный для MacBook.

Production-схема для macOS и Linux:

```text
браузер -> Caddy :8080 -> Nitro 127.0.0.1:3000 (сайт)
                     -> Gunicorn 127.0.0.1:8000 (Django API)
                     -> backend/media и backend/staticfiles
```

Supervisor запускает три процесса в фоне, перезапускает их при сбое и ограничивает
размер логов. SQLite и изображения остаются в `backend/db.sqlite3` и `backend/media/`.
Прогресс общий для всех посетителей, отдельных аккаунтов игроков пока нет.

## Первый запуск

Нужны Node.js 24 LTS, Python 3.12+ и Caddy в PATH. На macOS Caddy устанавливается
командой `brew install caddy`. На Linux установите Caddy из официального пакета.
Все команды ниже выполняются из корня репозитория.

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r deploy/requirements.txt
backend/.venv/bin/python deploy/manage.py init
backend/.venv/bin/python deploy/manage.py allow-host 192.168.1.10
backend/.venv/bin/python deploy/manage.py build
backend/.venv/bin/python deploy/manage.py start
```

Если окружение уже создано через uv и в нём нет pip, для установки зависимостей:

```bash
uv pip install --python backend/.venv/bin/python -r deploy/requirements.txt
```

Вместо `192.168.1.10` укажите IP компьютера в своей сети. `init` создаёт
`deploy/.env` с уникальным секретом и правами 600; повторный запуск секрет не меняет.
Production-параметры из этого файла имеют приоритет над `backend/.env`.
Сборка устанавливает фронтенд строго по package-lock, сохраняет копию существующей
SQLite в `.runtime/backups/`, выполняет миграции и collectstatic. Seed автоматически
не запускается, чтобы не менять существующие квесты и прогресс.

Сайт: http://localhost:8080. С другого устройства в той же сети:
http://192.168.1.10:8080. Админка: http://localhost:8080/admin/.
На период HTTP-тестирования Caddy разрешает админку только с самого MacBook.

## Управление

Для Telegram-бота при запуске через Supervisor добавьте в `deploy/.env`
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` и `TELEGRAM_REVIEWER_IDS` по инструкции
для Docker, затем выполните `restart`. Бот работает отдельным процессом; его лог:
`.runtime/telegram.log`.

```bash
backend/.venv/bin/python deploy/manage.py status
backend/.venv/bin/python deploy/manage.py stop
backend/.venv/bin/python deploy/manage.py start
backend/.venv/bin/python deploy/manage.py restart
```

Логи: `.runtime/backend.log`, `.runtime/frontend.log`, `.runtime/proxy.log`.
После изменения конфигурации используйте `restart`. Для обновления приложения:
`stop`, затем `build`, затем `start`. Команда `build` отказывается перезаписывать
активную сборку. Python-зависимости обновляйте установкой `deploy/requirements.txt`.
При неуспешной сборке не запускайте приложение до исправления ошибки.

Фоновый запуск переживает закрытие терминала. Автозапуск после перезагрузки MacBook
не установлен: выполните `start`. Во время теста MacBook должен оставаться включённым
и подключённым к сети; сон прервёт доступ. При необходимости держите запущенным
`caffeinate -i` в отдельном терминале. Закрытие крышки может всё равно усыпить Mac.

## Доступ из интернета через роутер

1. Закрепите за MacBook адрес `192.168.1.10` в DHCP-настройках роутера.
2. Создайте правило Port Forwarding / NAT: **TCP, внешний порт 8080 ->
   192.168.1.10, внутренний порт 8080**. UDP не нужен.
3. Добавьте публичный WAN IPv4 роутера или DNS-имя в Django, без протокола и порта:

```bash
backend/.venv/bin/python deploy/manage.py allow-host YOUR_PUBLIC_IP
backend/.venv/bin/python deploy/manage.py restart
```

4. Дайте тестировщикам `http://YOUR_PUBLIC_IP:8080`. Для проверки используйте
   мобильный интернет: доступ к собственному публичному IP из домашней сети
   зависит от NAT loopback роутера.
5. Если macOS Firewall включён, разрешите входящие соединения для Caddy.
   Порты **3000 и 8000 не пробрасывайте**: они слушают только loopback.

Нужен публичный адрес у провайдера. При CGNAT проброс на домашнем роутере сам по себе
не работает: запросите публичный IP или используйте туннель. WAN-адрес из диапазонов
10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 или 100.64.0.0/10 указывает на NAT выше
вашего роутера. При динамическом публичном IP удобнее DDNS; его имя также добавьте
через `allow-host`. Внешний доступ нужно проверить после настройки роутера.

## Перенос на Linux

Скопируйте исходники и, при остановленном приложении, `backend/db.sqlite3`,
`backend/media/` и `deploy/.env` на сервер. Виртуальное окружение, `node_modules`
и сборку с macOS не переносите: создайте окружение и выполните установку и `build`
на Linux. Сохраните копию базы и медиа до переноса. Автоматический backup при build
включает только SQLite; изображения резервируйте отдельно.

Для автозапуска есть шаблон `deploy/eft-arg.service`. Он предполагает пользователя
`eft-arg`, каталог `/opt/eft-arg`, Node и Caddy в `/usr/bin` или `/usr/local/bin`.
Пользователь сервиса должен владеть каталогом приложения и иметь доступ на запись
к SQLite, media и `.runtime`. При другом расположении поправьте шаблон.
Остановите ручной запуск перед запуском systemd; не запускайте параллельно второй
сервис Caddy на тех же портах.

```bash
sudo cp deploy/eft-arg.service /etc/systemd/system/eft-arg.service
sudo systemctl daemon-reload
sudo systemctl enable --now eft-arg
sudo systemctl status eft-arg
```

Для обновления под systemd сначала `sudo systemctl stop eft-arg`, затем установка
зависимостей и `build` от пользователя `eft-arg`, затем `sudo systemctl start eft-arg`.

Для HTTPS укажите домен в `SITE_ADDRESS` (например `https://arg.example.com`),
добавьте домен в `ALLOWED_HOSTS`, включите `SESSION_COOKIE_SECURE=True` и
`CSRF_COOKIE_SECURE=True`. Направьте DNS на сервер, откройте TCP 80 и 443 для Caddy
и выдайте бинарнику право слушать порты ниже 1024 (например через capabilities
systemd). Текущий шаблон сервиса рассчитан на непривилегированный HTTP-порт 8080.
Для редиректа HTTP -> HTTPS удалите `auto_https disable_redirects` из Caddyfile.
Доступ к админке остаётся локальным; с Linux-сервера используйте SSH-туннель
`ssh -L 8080:127.0.0.1:8080 user@server` и http://localhost:8080/admin/.
Если на сервере включены secure cookies, для админки потребуется HTTPS-доступ
через домен и отдельное ограничение доступа (VPN или список разрешённых адресов).

Основа сборки: [официальная инструкция TanStack Start / Nitro](https://tanstack.com/start/latest/docs/framework/react/guide/hosting).
