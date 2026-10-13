import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
