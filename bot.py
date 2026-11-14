import asyncio
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from dotenv import load_dotenv

import db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "90"))
MAX_ALERTS = int(os.getenv("MAX_ALERTS", "10"))

COINGECKO = "https://api.coingecko.com/api/v3/simple/price"

# ticker -> coingecko id
COINS = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "ton": "the-open-network",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "doge": "dogecoin",
    "ada": "cardano",
    "trx": "tron",
    "ltc": "litecoin",
    "matic": "matic-network",
    "dot": "polkadot",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("pricebot")

router = Router()

HELP = (
    "<b>Crypto Price Alert Bot</b>\n\n"
    "<b>Commands</b>\n"
    "/price &lt;coin&gt; — current price, e.g. <code>/price btc</code>\n"
    "/alert &lt;coin&gt; &lt;above|below&gt; &lt;usd&gt; — e.g. <code>/alert eth above 4200</code>\n"
    "/alerts — list your active alerts\n"
    "/del &lt;id&gt; — delete one alert\n"
    "/delall — delete all your alerts\n"
    f"\nMax {MAX_ALERTS} active alerts per user. "
    f"Prices are checked every {CHECK_INTERVAL}s (CoinGecko)."
)


async def fetch_prices(session: aiohttp.ClientSession, tickers: list[str]) -> dict:
    """Return {ticker: usd_price} for the given tickers."""
    ids = {COINS[t] for t in tickers if t in COINS}
    if not ids:
        return {}
    params = {"ids": ",".join(sorted(ids)), "vs_currencies": "usd"}
    async with session.get(
        COINGECKO, params=params, timeout=aiohttp.ClientTimeout(total=20)
    ) as resp:
        resp.raise_for_status()
        raw = await resp.json()

    id_to_ticker = {COINS[t]: t for t in tickers if t in COINS}
    out = {}
    for cg_id, payload in raw.items():
        ticker = id_to_ticker.get(cg_id)
        if ticker and "usd" in payload:
            out[ticker] = float(payload["usd"])
    return out


def money(value: float) -> str:
    if value >= 1:
        return f"${value:,.2f}"
    return f"${value:,.6f}"


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(HELP)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP)


@router.message(Command("price"))
async def cmd_price(message: Message, command: CommandObject) -> None:
    args = (command.args or "").strip().lower()
    if not args:
        await message.answer("Usage: <code>/price btc</code>", parse_mode="HTML")
        return

    ticker = args.split()[0]
    if ticker not in COINS:
        await message.answer(
            "Unknown coin. Supported: <code>" + ", ".join(sorted(COINS)) + "</code>",
            parse_mode="HTML",
        )
        return

    try:
        async with aiohttp.ClientSession() as session:
            prices = await fetch_prices(session, [ticker])
    except Exception:
        log.exception("price fetch failed")
        await message.answer("Price source is temporarily unavailable. Try again in a minute.")
        return

    price = prices.get(ticker)
    if price is None:
        await message.answer("Could not fetch that price right now.")
        return

    await message.answer(
        f"<b>{ticker.upper()}</b> = {money(price)}", parse_mode="HTML"
    )


@router.message(Command("alert"))
async def cmd_alert(message: Message, command: CommandObject) -> None:
    parts = (command.args or "").split()
    if len(parts) != 3:
        await message.answer(
            "Usage: <code>/alert btc above 120000</code>\n"
            "Direction must be <code>above</code> or <code>below</code>.",
            parse_mode="HTML",
        )
        return

    ticker, direction, raw_target = parts[0].lower(), parts[1].lower(), parts[2]
    if ticker not in COINS:
        await message.answer("Unknown coin. Try <code>/help</code>.", parse_mode="HTML")
        return
    if direction not in ("above", "below"):
        await message.answer("Direction must be <code>above</code> or <code>below</code>.", parse_mode="HTML")
        return

    try:
        target = float(raw_target.replace(",", ""))
    except ValueError:
        await message.answer("Target must be a number, e.g. <code>120000</code>.", parse_mode="HTML")
        return
    if target <= 0:
        await message.answer("Target must be greater than zero.")
        return

    count = await db.count_alerts(message.chat.id)
    if count >= MAX_ALERTS:
        await message.answer(
            f"You already have {count} alerts (limit {MAX_ALERTS}). "
            "Delete one with <code>/del &lt;id&gt;</code>.",
            parse_mode="HTML",
        )
        return

    alert_id = await db.add_alert(message.chat.id, ticker, direction, target)
    await message.answer(
        f"✅ Alert <b>#{alert_id}</b> created: {ticker.upper()} "
        f"{direction} <b>{money(target)}</b>",
        parse_mode="HTML",
    )


@router.message(Command("alerts"))
async def cmd_alerts(message: Message) -> None:
    rows = await db.list_alerts(message.chat.id)
    if not rows:
        await message.answer("You have no active alerts. Create one with /alert.")
        return

    lines = ["<b>Your alerts</b>"]
    for row in rows:
        lines.append(
            f"#{row['id']} — {row['coin'].upper()} {row['direction']} "
            f"{money(row['target'])}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("del"))
async def cmd_del(message: Message, command: CommandObject) -> None:
    raw = (command.args or "").strip()
    if not raw.isdigit():
        await message.answer("Usage: <code>/del 3</code>", parse_mode="HTML")
        return

    deleted = await db.delete_alert(message.chat.id, int(raw))
    if deleted:
        await message.answer(f"Deleted alert #{raw}.")
    else:
        await message.answer("No alert with that id (or it is not yours).")


@router.message(Command("delall"))
async def cmd_delall(message: Message) -> None:
    removed = await db.delete_all_alerts(message.chat.id)
    await message.answer(f"Deleted {removed} alert(s).")


async def alert_worker(bot: Bot) -> None:
    """Background loop: check every active alert against live prices."""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                alerts = await db.all_active_alerts()
                if alerts:
                    tickers = sorted({a["coin"] for a in alerts})
                    prices = await fetch_prices(session, tickers)
                    for alert in alerts:
                        price = prices.get(alert["coin"])
                        if price is None:
                            continue
                        hit = (
                            price >= alert["target"]
                            if alert["direction"] == "above"
                            else price <= alert["target"]
                        )
                        if not hit:
                            continue
                        try:
                            await bot.send_message(
                                alert["chat_id"],
                                f"🔔 <b>Alert #{alert['id']} triggered</b>\n"
                                f"{alert['coin'].upper()} is {alert['direction']} "
                                f"{money(alert['target'])} → now <b>{money(price)}</b>",
                                parse_mode="HTML",
                            )
                        except Exception:
                            log.exception("failed to notify chat %s", alert["chat_id"])
                        await db.deactivate_alert(alert["id"])
            except Exception:
                log.exception("alert worker iteration failed")

            await asyncio.sleep(CHECK_INTERVAL)


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is missing. Copy .env.example to .env and fill it in.")

    await db.init()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    worker = asyncio.create_task(alert_worker(bot))
    log.info("bot started, checking prices every %ss", CHECK_INTERVAL)
    try:
        await dp.start_polling(bot)
    finally:
        worker.cancel()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
