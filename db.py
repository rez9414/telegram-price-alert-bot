import os

import aiosqlite

DB_PATH = os.getenv("DB_PATH", "alerts.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id    INTEGER NOT NULL,
    coin       TEXT    NOT NULL,
    direction  TEXT    NOT NULL CHECK (direction IN ('above', 'below')),
    target     REAL    NOT NULL,
    active     INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts (active, coin);
CREATE INDEX IF NOT EXISTS idx_alerts_chat ON alerts (chat_id, active);
"""


async def init() -> None:
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.executescript(SCHEMA)
        await conn.commit()


async def add_alert(chat_id: int, coin: str, direction: str, target: float) -> int:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            "INSERT INTO alerts (chat_id, coin, direction, target) VALUES (?, ?, ?, ?)",
            (chat_id, coin, direction, target),
        )
        await conn.commit()
        return int(cur.lastrowid)


async def count_alerts(chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE chat_id = ? AND active = 1", (chat_id,)
        )
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def list_alerts(chat_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT id, coin, direction, target FROM alerts "
            "WHERE chat_id = ? AND active = 1 ORDER BY id",
            (chat_id,),
        )
        return [dict(r) for r in await cur.fetchall()]


async def all_active_alerts() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT id, chat_id, coin, direction, target FROM alerts WHERE active = 1"
        )
        return [dict(r) for r in await cur.fetchall()]


async def delete_alert(chat_id: int, alert_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            "DELETE FROM alerts WHERE id = ? AND chat_id = ?", (alert_id, chat_id)
        )
        await conn.commit()
        return cur.rowcount > 0


async def delete_all_alerts(chat_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("DELETE FROM alerts WHERE chat_id = ?", (chat_id,))
        await conn.commit()
        return cur.rowcount


async def deactivate_alert(alert_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE alerts SET active = 0 WHERE id = ?", (alert_id,))
        await conn.commit()
