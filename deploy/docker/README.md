# Деплой на сервер через Docker Compose

Compose управляет тремя контейнерами: Django/Gunicorn, Node/Nitro и Caddy.
На сервере не нужны отдельные Python, Node, Supervisor или Nginx.
Миграции и сбор статики выполняются при запуске backend; Caddy ждёт готовности
приложения и обслуживает сайт, API, изображения и админку по HTTPS.

## Первый запуск

1. Установите [Docker Engine с Compose](https://docs.docker.com/engine/install/ubuntu/)
   на Linux-сервер. Проверьте `docker version` и `docker compose version`.
   У пользователя должен быть доступ к Docker; иначе команды выполняются через sudo.
2. Направьте DNS-запись A домена на IP сервера. AAAA добавляйте только при работающем
   IPv6. Откройте TCP **80 и 443** в firewall сервера и панели провайдера.
   Сохраните SSH-доступ. Порты 3000 и 8000 не публикуются.
3. Скопируйте проект на сервер или клонируйте репозиторий с этими изменениями.
   Если там уже запущен прежний `eft-arg` через systemd, остановите и отключите его.
   Порты 80 и 443 должны быть свободны от других веб-серверов.
4. Из корня проекта создайте настройки:

```bash
cp .env.example .env
chmod 600 .env
openssl rand -hex 32
```

В `.env` задайте свой `DOMAIN` без протокола, пути и порта, например
`DOMAIN=arg.example.com`. В `SECRET_KEY` вставьте результат openssl.
Файл `.env` не включается в Git или образы; `deploy/.env` относится к прежнему
запуску и Docker его не использует. Сохраните серверный `.env` для обновлений.

```bash
docker compose up -d --build --wait --wait-timeout 180
docker compose exec backend python manage.py createsuperuser
```

Откройте `https://ВАШ_ДОМЕН` и `https://ВАШ_ДОМЕН/admin/`.
В Docker-варианте админка доступна через HTTPS с обычной авторизацией Django.
Выпуск сертификата может занять дополнительное время: `docker compose logs caddy`.
При первом запуске база пустая; добавьте данные через админку или перенесите их ниже.
Для новой демонстрационной базы можно один раз выполнить
`docker compose exec backend python manage.py seed`. На существующей базе seed
не запускайте: он обновляет тестовые квесты. Прогресс пока общий для всех игроков.

## Управление и обновление

```bash
docker compose ps
docker compose logs --tail=100 -f
docker compose stop
docker compose up -d --wait
```

Контейнеры работают независимо от терминала и Codex. После перезагрузки сервера
они запускаются автоматически, если запущена служба Docker и контейнеры не были
остановлены вручную. Для выключения достаточно `docker compose stop`.

Для обновления сначала создайте backup по следующему разделу. Затем обновите код
(например `git pull`) и выполните `docker compose up -d --build --wait`.
Если изменился `deploy/docker/Caddyfile`, выполните `docker compose restart caddy`.
Короткий перерыв в доступности во время обновления допустим для этой схемы.

База, media и статика хранятся в томе `eft-arg_app_data`, сертификаты в отдельных
томах Caddy. Пересборка и `docker compose down` сохраняют данные.
**Не используйте `docker compose down -v`: эта команда удаляет тома с данными.**

## Резервная копия

Из корня проекта, до обновления. Остановка исключает запись в SQLite и media
во время копирования. Архив содержит базу и изображения, но не секрет из `.env`.

```bash
mkdir -p backups
chmod 700 backups
docker compose stop
docker compose run --rm -T --no-deps --entrypoint tar backend \
  -czf - -C /data . > "backups/data-$(date +%Y%m%d-%H%M%S).tar.gz"
docker compose up -d --wait
```

Проверьте архив через `tar -tzf backups/ИМЯ_АРХИВА.tar.gz` и храните копию вне сервера.
Для восстановления в остановленный стек (заменяет файлы из архива):

```bash
docker compose stop
docker compose run --rm -T --no-deps --entrypoint tar backend \
  -xzf - -C /data < backups/ИМЯ_АРХИВА.tar.gz
docker compose up -d --wait
```

Восстанавливайте в пустой том или сохраните копию текущего тома перед восстановлением.
При откате на старую базу используйте соответствующую ей версию кода.

## Перенос текущей базы с MacBook

Остановите прежний запуск: `backend/.venv/bin/python deploy/manage.py stop`.
Скопируйте `backend/db.sqlite3` и папку `backend/media` на сервер в те же пути
внутри проекта. Они не попадают в Docker-образ и не переносятся через Git.
Следующие команды выполняйте на сервере только при первом переносе, до создания
новых игровых данных в контейнере; при повторном переносе сначала сделайте backup.

```bash
docker compose build
docker compose stop
docker compose run --rm --no-deps --user root --entrypoint sh \
  -v "$PWD/backend:/import:ro" backend -c \
  'cp /import/db.sqlite3 /data/db.sqlite3 && mkdir -p /data/media && cp -R /import/media/. /data/media/ && chown -R 10001:10001 /data'
docker compose up -d --wait
```

Если загрузок ещё нет, создайте пустую `backend/media` перед импортом.
Существующие учётные записи администраторов перенесутся вместе с базой.
На MacBook для запуска контейнеров потребуется Docker Desktop или другой Docker
runtime. Конфигурация выше предназначена для сервера с настоящим доменом и HTTPS.
