import os
from uuid import uuid4

import redis
from flask import Flask, jsonify, request


app = Flask(__name__)
app.json.ensure_ascii = False

db = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)


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
