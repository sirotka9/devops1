import os
from uuid import uuid4

import redis
from flask import Flask, Response, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest


app = Flask(__name__)
app.json.ensure_ascii = False

http_requests = Counter("http_requests_total", "Количество запросов к API")
http_errors = Counter("http_errors_total", "Количество ответов API с кодом 4xx или 5xx")

db = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
    password=os.getenv("REDIS_PASSWORD") or None,
    socket_connect_timeout=2,
    socket_timeout=2,
)


@app.after_request
def count_requests(response):
    if request.path.startswith("/api/"):
        http_requests.inc()
        if response.status_code >= 400:
            http_errors.inc()
    return response


@app.get("/health")
def health():
    try:
        db.ping()
    except redis.RedisError:
        return {"status": "error", "message": "Redis недоступен"}, 503
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)


@app.get("/")
def index():
    return {"message": "API заметок", "notes_url": "/api/notes"}


@app.get("/api/notes")
def get_notes():
    notes = db.hgetall("notes")
    return jsonify([{"id": note_id, "text": text} for note_id, text in notes.items()])


@app.post("/api/notes")
def add_note():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        return {"error": "Передайте JSON с текстовым полем text"}, 400

    text = data["text"].strip()
    if not text:
        return {"error": "Текст заметки не должен быть пустым"}, 400

    note_id = str(uuid4())
    db.hset("notes", note_id, text)
    return {"id": note_id, "text": text}, 201


@app.delete("/api/notes/<note_id>")
def delete_note(note_id):
    if db.hdel("notes", note_id) == 0:
        return {"error": "Заметка не найдена"}, 404
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("APP_PORT", "8080")))
