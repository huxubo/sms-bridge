import sqlite3
from datetime import datetime

class DB:
    def __init__(self, path):
        self.path = path
        self._init_db()

    def _init_db(self):
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                remote TEXT,
                content TEXT,
                direction TEXT,
                created_at TEXT
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                payload TEXT,
                created_at TEXT
            )
        ''')
        con.commit()
        con.close()

    def insert_message(self, remote, content, direction='in'):
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute('INSERT INTO messages(remote, content, direction, created_at) VALUES (?, ?, ?, ?)',
                    (remote, content, direction, datetime.utcnow().isoformat()))
        con.commit()
        con.close()

    def get_messages(self, limit=200):
        con = sqlite3.connect(self.path)
        cur = con.cursor()
        cur.execute('SELECT id, remote, content, direction, created_at FROM messages ORDER BY id DESC LIMIT ?', (limit,))
        rows = cur.fetchall()
        con.close()
        return rows
