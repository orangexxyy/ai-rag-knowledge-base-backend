import sqlite3

# 【可直接复制】
# 清理演示用 session_id，避免反复测试产生的历史记录影响面试展示

DB_PATH = "data/chat_history.db"

DEMO_PREFIXES = [
    "demo_company_",
    "demo_pharma_",
    "interview_company_",
    "interview_pharma_",
]

with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()

    for prefix in DEMO_PREFIXES:
        cursor.execute(
            """
            DELETE FROM chat_messages
            WHERE session_id LIKE ?
            """,
            (prefix + "%",)
        )

    conn.commit()

print("演示 session 历史已清理完成")