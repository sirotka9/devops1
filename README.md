# API заметок

Учебный проект по DevOps, уровни 1 и 2. Приложение позволяет добавлять,
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

Девять тестов проверяют HTTP-ответы, добавление, просмотр, удаление заметок,
ошибочные запросы, состояние приложения и счётчики метрик.
В тестах Redis заменяется mock-объектом,
поэтому отдельный сервер Redis для них не нужен.

Workflow `.github/workflows/ci.yaml` запускается после push и при pull request:
получает исходный код, устанавливает зависимости, запускает тесты
и собирает Docker image. История запусков находится во вкладке **Actions**
репозитория GitHub: https://github.com/sirotka9/devops1/actions.
Изменения проекта видны в истории коммитов.

## Уровень 2 — Kubernetes

Нужны запущенный Docker, `kind` и `kubectl`. На macOS установить
недостающие инструменты можно командой `brew install kind kubectl`.
Локальный кластер создаётся внутри Docker:

```bash
kind create cluster --name devops --config kind.yaml
kubectl config use-context kind-devops
docker build --provenance=false -t devops-notes:level2 .
kind load docker-image devops-notes:level2 --name devops
kubectl apply -f k8s/namespace.yaml
```

Флаг `--provenance=false` убирает дополнительные метаданные сборки,
которые могут мешать загрузке локального образа в kind.

Создайте локальный файл с паролем Redis:

```bash
cp .env.k8s.example .env.k8s
```

Замените значение `REDIS_PASSWORD` в `.env.k8s` на свой пароль.
Этот файл исключён из Git. Kubernetes Secret создаётся из него:

```bash
kubectl -n devops create secret generic redis-secret \
  --from-env-file=.env.k8s --dry-run=client -o yaml | kubectl apply -f -
```

В `k8s/secret.yaml.example` показана структура Secret без настоящего пароля.
ConfigMap содержит порт приложения и адрес Redis. Secret передаёт пароль
в приложение и Redis через переменные окружения.

Создайте конфигурацию мониторинга и запустите сервисы:

```bash
kubectl -n devops create configmap prometheus-config \
  --from-file=monitoring/prometheus.yaml \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n devops create configmap grafana-config \
  --from-file=monitoring/datasource.yaml \
  --from-file=monitoring/dashboards.yaml \
  --from-file=monitoring/notes.json \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/
kubectl -n devops rollout status deployment/redis
kubectl -n devops rollout status deployment/app
kubectl -n devops rollout status deployment/prometheus
kubectl -n devops rollout status deployment/grafana
```

Адреса для локального кластера:

| Сервис | Адрес |
| --- | --- |
| Приложение | http://localhost:8088 |
| Prometheus | http://localhost:9090 |
| Grafana dashboard | http://localhost:3000/d/notes |

Grafana открывается без входа с правами просмотра. Порты привязаны к localhost.
Запуск через Compose из уровня 1 остаётся доступен на порту 8080 отдельно.
Заметки в Compose и Kubernetes хранятся в разных экземплярах Redis.

### Состояние приложения

Основные файлы Kubernetes: `app.yaml`, `redis.yaml`, `prometheus.yaml`
и `grafana.yaml`. В каждом находятся Deployment и Service соответствующего
сервиса. Для приложения также есть ConfigMap, для Redis — хранилище.
Значения по умолчанию не дублируются: одна реплика, `targetPort` совпадает
с `port`, интервал проверок состояния — 10 секунд.

`GET /health` проверяет соединение с Redis: HTTP 200 и `{"status":"ok"}`,
если Redis доступен; HTTP 503, если соединение потеряно.

`readinessProbe` обращается к `/health`. Если проверка не проходит,
Kubernetes прекращает направлять запросы через Service к этому Pod.
`livenessProbe` обращается к `/`, проверяя сам HTTP-сервер.
После трёх неудачных проверок Kubernetes перезапускает контейнер приложения.
Недоступность Redis сама по себе не вызывает перезапуск приложения.

### Мониторинг

Prometheus каждые пять секунд получает `/metrics` приложения.
Источник данных и dashboard Grafana загружаются из файлов автоматически.
Dashboard показывает два значения:

- `http_requests_total` — количество запросов к `/api/` с момента запуска приложения.
- `http_errors_total` — количество ответов `/api/` с кодами 4xx и 5xx.

Проверки состояния и сбор метрик не увеличивают эти счётчики.
После перезапуска приложения счётчики начинаются с нуля.
История мониторинга в этом учебном варианте не сохраняется при пересоздании
Pod Prometheus. Dashboard остаётся в Git и загружается снова.

### Демонстрация

```bash
kubectl -n devops get pods
curl http://localhost:8088/health
curl -X POST http://localhost:8088/api/notes \
  -H 'Content-Type: application/json' -d '{"text":"Изучить Kubernetes"}'
curl http://localhost:8088/api/notes
curl -i -X POST http://localhost:8088/api/notes \
  -H 'Content-Type: application/json' -d '{"text":""}'
```

Последний запрос возвращает HTTP 400 и увеличивает счётчик ошибок.
Через несколько секунд новые значения появятся в Grafana.

Для проверки readiness временно остановите Redis:

```bash
kubectl -n devops scale deployment/redis --replicas=0
kubectl -n devops get pods
kubectl -n devops describe pod -l app=notes
kubectl -n devops scale deployment/redis --replicas=1
kubectl -n devops rollout status deployment/redis
kubectl -n devops rollout status deployment/app
curl http://localhost:8088/health
```

Через несколько проверок Pod приложения будет `0/1`, а в событиях появится
ошибка readiness. После восстановления Redis приложение снова станет `1/1`.
Заметки Redis сохраняются в PersistentVolumeClaim `redis-data`.

Pod — экземпляр приложения с контейнером. Deployment поддерживает нужное
число Pod и создаёт новый при удалении старого. Service даёт постоянный
адрес для доступа к Pod. ConfigMap хранит обычные настройки, Secret — пароль.
Secret не шифрует пароль сам по себе, поэтому настоящий пароль не хранится в Git.

### Обновление и остановка

После изменения кода пересоберите образ, загрузите его в кластер
и перезапустите приложение:

```bash
docker build --provenance=false -t devops-notes:level2 .
kind load docker-image devops-notes:level2 --name devops
kubectl -n devops rollout restart deployment/app
kubectl -n devops rollout status deployment/app
```

Остановка всех четырёх сервисов с сохранением заметок:

```bash
kubectl -n devops scale deployment app redis prometheus grafana --replicas=0
```

Для повторного запуска выполните ту же команду с `--replicas=1`.
`kind delete cluster --name devops` удаляет весь кластер, включая заметки
и локальные данные мониторинга.
