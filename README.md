# API заметок

Учебный проект по DevOps, уровень 1. Приложение позволяет добавлять,
просматривать и удалять заметки по HTTP. Ответы возвращаются в JSON.

Технологии: Python 3.12, Flask, Redis, Docker, Docker Compose и GitHub Actions.
Redis хранит заметки, Docker запускает приложение в контейнере,
Compose запускает приложение и Redis вместе.

## Запуск

Нужны Git и запущенный Docker с Docker Compose. Получите проект:

```bash
git clone https://github.com/sirotka9/devops1.git devops
cd devops
```

В папке проекта выполните:

```bash
cp .env.example .env
docker compose up -d --build
```

Приложение доступно по адресу http://localhost:8080.
Для запуска с выводом логов в терминал можно использовать `docker compose up`.
Compose сначала ждёт готовности Redis, затем запускает приложение.

## Проверка приложения

Информация о приложении:

```bash
curl http://localhost:8080/
```

Добавление заметки:

```bash
curl -X POST http://localhost:8080/api/notes \
  -H 'Content-Type: application/json' \
  -d '{"text": "Изучить Docker"}'
```

Ответ содержит `id` и `text`. Просмотр всех заметок:

```bash
curl http://localhost:8080/api/notes
```

Удаление заметки (замените `ID` на значение из ответа):

```bash
curl -i -X DELETE http://localhost:8080/api/notes/ID
```

Успешное удаление возвращает HTTP 204. Несуществующая заметка — HTTP 404.
При добавлении пустого текста или неверного JSON возвращается HTTP 400.

## Остановка и логи

```bash
docker compose down
```

Заметки сохраняются в Docker volume `redis_data` и остаются после остановки.
Команда `docker compose down -v` также удалит volume и все заметки.

Просмотр состояния и логов:

```bash
docker compose ps
docker compose logs app
docker compose logs redis
```

## Переменные окружения

Compose читает настройки из `.env`. Этот файл не попадает в Git.
В репозитории есть только `.env.example` с примерами.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| APP_PORT | 8080 | Порт HTTP приложения внутри контейнера и на компьютере |
| REDIS_HOST | redis | Имя сервиса Redis в сети Compose |
| REDIS_PORT | 6379 | Порт Redis внутри сети Compose |

Пароли и токены для локального запуска не нужны. Redis не публикует порт
на компьютер, приложение доступно только через localhost.

Чтобы изменить порт приложения, укажите, например, `APP_PORT=8081` в `.env`
и выполните `docker compose up -d`. Тогда адрес будет http://localhost:8081.
Значения `REDIS_HOST` и `REDIS_PORT` в примере соответствуют сервису Redis
в Compose; менять их при обычном запуске не требуется.

## Docker отдельно

Соберите image — образ с Python, зависимостями и кодом приложения:

```bash
docker build -t devops-notes:level1 .
```

Для проверки через `docker run` сначала запустите Redis через Compose:

```bash
docker compose up -d redis
docker run -d --name notes-demo --network devops_default \
  -p 127.0.0.1:8081:8080 -e REDIS_HOST=redis devops-notes:level1
curl http://localhost:8081/api/notes
docker stop notes-demo
docker rm notes-demo
```

Эти команды предполагают, что папка проекта называется `devops`.
Если имя папки другое, имя сети можно посмотреть через `docker network ls`.

Container — запущенный экземпляр образа. Dockerfile описывает сборку образа.
`-p 127.0.0.1:8081:8080` связывает порт 8081 компьютера с портом 8080 контейнера.
`-e REDIS_HOST=redis` передаёт настройку приложения через окружение.

## Тесты и CI

Локальный запуск тестов (нужен Python 3.12 или новее):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest -v
```

Шесть тестов проверяют HTTP-ответы, добавление, просмотр, удаление заметок
и ошибочные запросы. В тестах Redis заменяется mock-объектом,
поэтому отдельный сервер Redis для них не нужен.

Workflow `.github/workflows/ci.yaml` запускается после push и при pull request:
получает исходный код, устанавливает зависимости, запускает тесты
и собирает Docker image. История запусков находится во вкладке **Actions**
репозитория GitHub: https://github.com/sirotka9/devops1/actions.
Изменения проекта видны в истории коммитов.
