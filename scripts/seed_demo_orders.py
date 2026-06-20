"""演示用：给主演示账号 (13800000001) 插入 3 条不同状态的假订单。

字段 FK 严格，但 design_versions / option_id 可借用 sessions 既有 session_id 占位，
SQLite + foreign_keys=OFF 跳过约束，足够前端 /orders 列表与详情页有内容可看。
"""

import sqlite3
import uuid
from datetime import datetime, timedelta

DB = "f:/python_code/ClayWords/backend/test.db"


def main():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=OFF")

    # 找主演示账号
    user = con.execute(
        "SELECT user_id FROM users WHERE phone_hash="
        "'b1c4769e3ad14f68ea1a96b73bbe5a83d90792f044828c5daf9d908b0738b177'"
    ).fetchone()
    if not user:
        print("Demo user not found, run seed_users.py first")
        return
    user_id = user[0]

    # 找一个该用户的 session
    sess = con.execute(
        "SELECT session_id FROM sessions WHERE user_id=? LIMIT 1", (user_id,)
    ).fetchone()
    session_id = sess[0] if sess else str(uuid.uuid4())

    # 找一家工作室
    studio = con.execute("SELECT studio_id, name FROM studios LIMIT 1").fetchone()
    studio_id = studio[0] if studio else None

    # 清空 demo orders 重跑
    con.execute("DELETE FROM order_logs WHERE order_id IN (SELECT order_id FROM orders WHERE user_id=?)", (user_id,))
    con.execute("DELETE FROM orders WHERE user_id=?", (user_id,))

    now = datetime.utcnow()
    cases = [
        # (title, status, days_ago, price)
        ("玉兔捧月", "producing", 3, 386),
        ("月下垂桂花瓶", "delivered", 18, 468),
        ("望舒香插", "confirmed", 1, 268),
    ]

    for i, (name, status, days_ago, price) in enumerate(cases):
        order_id = str(uuid.uuid4())
        created = now - timedelta(days=days_ago)
        idem = f"demo-{user_id[:8]}-{i}"
        option_id = str(uuid.uuid4())  # 演示，不强外键

        con.execute(
            """INSERT INTO orders
            (order_id, user_id, session_id, option_id, studio_id, status,
             idempotency_key, shipping_name, shipping_phone, shipping_address,
             total_price, workorder_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_id, user_id, session_id, option_id, studio_id, status,
             idem, "陶语演示", "138****0001", "北京市朝阳区某某街道 88 号陶语收",
             price, None, created, created)
        )

        # 写一条状态日志
        log_id = str(uuid.uuid4())
        con.execute(
            """INSERT INTO order_logs
            (id, order_id, from_status, to_status, operator, reason, extra_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (log_id, order_id, None, status, "system", f"演示订单 · {name}", "{}", created)
        )

    con.commit()
    print(f"Seeded {len(cases)} demo orders for user {user_id[:8]}")
    rows = con.execute("SELECT order_id, status, total_price FROM orders WHERE user_id=?", (user_id,)).fetchall()
    for r in rows:
        print(f"  {r[0][:8]} | {r[1]:12s} | ¥{r[2]}")
    con.close()


if __name__ == "__main__":
    main()
