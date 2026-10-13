import unittest
from unittest.mock import patch

import redis

from app import app


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.patcher = patch("app.db")
        self.db = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["notes_url"], "/api/notes")

    def test_get_notes(self):
        self.db.hgetall.return_value = {"1": "Первая заметка"}
        response = self.client.get("/api/notes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [{"id": "1", "text": "Первая заметка"}])

    def test_add_note(self):
        response = self.client.post("/api/notes", json={"text": " Новая заметка "})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["text"], "Новая заметка")
        self.db.hset.assert_called_once_with(
            "notes", response.json["id"], "Новая заметка"
        )

    def test_invalid_note(self):
        for data in ({}, {"text": " "}, {"text": 12}, []):
            with self.subTest(data=data):
                response = self.client.post("/api/notes", json=data)
                self.assertEqual(response.status_code, 400)
        self.db.hset.assert_not_called()

    def test_delete_note(self):
        self.db.hdel.return_value = 1
        response = self.client.delete("/api/notes/1")
        self.assertEqual(response.status_code, 204)
        self.db.hdel.assert_called_once_with("notes", "1")

    def test_delete_missing_note(self):
        self.db.hdel.return_value = 0
        response = self.client.delete("/api/notes/missing")
        self.assertEqual(response.status_code, 404)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})

    def test_health_without_redis(self):
        self.db.ping.side_effect = redis.ConnectionError()
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)

    def test_metrics(self):
        before = self.client.get("/metrics").text
        values = dict(line.split() for line in before.splitlines() if not line.startswith("#"))
        self.client.post("/api/notes", json={"text": ""})
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            f"http_requests_total {float(values['http_requests_total']) + 1}", response.text
        )
        self.assertIn(
            f"http_errors_total {float(values['http_errors_total']) + 1}", response.text
        )


if __name__ == "__main__":
    unittest.main()
