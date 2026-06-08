import sqlite3
import os

class TodoSkill:
    def __init__(self, db_path="data/assistant.db"):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, completed INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )

    def add_todo(self, title):
        with self._conn() as c:
            cur = c.execute("INSERT INTO todos (title) VALUES (?)", (title,))
            return {"id": cur.lastrowid, "title": title, "completed": False}

    def list_todos(self):
        with self._conn() as c:
            cur = c.execute("SELECT id, title, completed FROM todos ORDER BY id DESC")
            rows = cur.fetchall()
            return [{"id": r[0], "title": r[1], "completed": bool(r[2])} for r in rows]

    def complete_todo(self, todo_id: int):
        with self._conn() as c:
            c.execute("UPDATE todos SET completed=1 WHERE id=?", (todo_id,))
            return c.rowcount > 0
