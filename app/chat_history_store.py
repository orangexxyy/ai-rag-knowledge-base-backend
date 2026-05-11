import os
import sqlite3
from datetime import datetime

# SQLite 数据库文件路径
DB_PATH = "data/chat_history.db"


def init_chat_db() -> None:
    """
    初始化聊天历史数据库。
    如果 data 目录不存在就自动创建；
    如果表不存在就自动建表。
    """
    # 确保 data 目录存在
    os.makedirs("data", exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

        conn.commit()


def get_session_history(session_id: str) -> list[dict]:
    """
    读取某个 session_id 的全部历史消息。
    返回格式保持和现有主链一致：
    [{"role": "...", "content": "..."}, ...]
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT role, content
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,)
        )

        rows = cursor.fetchall()

    history_messages = []
    for role, content in rows:
        history_messages.append({
            "role": role,
            "content": content
        })

    return history_messages


def append_message(session_id: str, role: str, content: str) -> None:
    """
    插入一条消息到数据库。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO chat_messages (session_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                content,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        conn.commit()


def save_turn(session_id: str, question: str, answer: str) -> None:
    """
    一次性保存一轮对话：
    1. 保存 user 问题
    2. 保存 assistant 回答
    """
    append_message(session_id, "user", question)
    append_message(session_id, "assistant", answer)