"""Smoke test: exercises the DB layer and the live price fetch without a Telegram token."""
import asyncio
import os

os.environ["DB_PATH"] = "smoke.db"

import aiohttp
import db
import bot


async def main() -> None:
    # --- DB layer ---
    db.DB_PATH = "smoke.db"
    await db.init()

    alert_id = await db.add_alert(123, "btc", "above", 120000)
    print("inserted alert id:", alert_id)
    print("count:", await db.count_alerts(123))
    print("list:", await db.list_alerts(123))
    print("delete:", await db.delete_alert(123, alert_id))
    print("count after delete:", await db.count_alerts(123))
    await db.delete_all_alerts(123)

    # --- live price fetch ---
    try:
        async with aiohttp.ClientSession() as session:
            prices = await bot.fetch_prices(session, ["btc", "eth", "ton"])
        print("live prices:", {k: bot.money(v) for k, v in prices.items()})
    except Exception as exc:
        print("price fetch failed (network):", type(exc).__name__, exc)

    os.remove("smoke.db") if os.path.exists("smoke.db") else None
    print("SMOKE TEST DONE")


asyncio.run(main())
