import sqlite3
import json
from typing import Dict, Any

DB_FILE = "bot_data.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                query TEXT,
                videos TEXT,
                page INTEGER,
                cart TEXT
            )
        ''')
        conn.commit()

def get_state(user_id: int) -> Dict[str, Any]:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT query, videos, page, cart FROM user_states WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "query": row[0],
                "videos": json.loads(row[1]),
                "page": row[2],
                "cart": json.loads(row[3])
            }
        else:
            return {
                "query": "",
                "videos": [],
                "page": 0,
                "cart": []
            }

def save_state(user_id: int, state: Dict[str, Any]):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_states (user_id, query, videos, page, cart)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                query=excluded.query,
                videos=excluded.videos,
                page=excluded.page,
                cart=excluded.cart
        ''', (
            user_id,
            state["query"],
            json.dumps(state["videos"]),
            state["page"],
            json.dumps(state["cart"])
        ))
        conn.commit()
