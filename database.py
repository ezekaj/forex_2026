import aiosqlite
import os

DB_PATH = os.environ.get("DB_PATH", "/data/trading.db")


async def get_db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin TEXT NOT NULL,
                side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
                amount REAL NOT NULL,
                price REAL NOT NULL,
                total_usd REAL NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS portfolio (
                coin TEXT PRIMARY KEY,
                amount REAL NOT NULL DEFAULT 0,
                avg_entry_price REAL NOT NULL DEFAULT 0,
                total_cost REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS portfolio_meta (
                key TEXT PRIMARY KEY,
                value REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                coin TEXT NOT NULL,
                signal TEXT NOT NULL CHECK(signal IN ('buy', 'sell', 'hold')),
                confidence REAL NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_value REAL NOT NULL,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        await db.commit()

        row = await db.execute_fetchall(
            "SELECT value FROM portfolio_meta WHERE key = 'cash_balance'"
        )
        if not row:
            await db.execute(
                "INSERT INTO portfolio_meta (key, value) VALUES ('cash_balance', 10000.0)"
            )
            await db.commit()
    finally:
        await db.close()


async def get_cash_balance() -> float:
    db = await get_db()
    try:
        row = await db.execute_fetchall(
            "SELECT value FROM portfolio_meta WHERE key = 'cash_balance'"
        )
        return row[0][0] if row else 10000.0
    finally:
        await db.close()


async def set_cash_balance(amount: float):
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO portfolio_meta (key, value) VALUES ('cash_balance', ?)",
            (amount,),
        )
        await db.commit()
    finally:
        await db.close()


async def get_positions() -> list:
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT coin, amount, avg_entry_price, total_cost FROM portfolio WHERE amount > 0.00000001"
        )
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def update_position(coin: str, amount_delta: float, cost_delta: float):
    db = await get_db()
    try:
        row = await db.execute_fetchall(
            "SELECT amount, total_cost FROM portfolio WHERE coin = ?", (coin,)
        )
        if row:
            current_amount = row[0][0]
            current_cost = row[0][1]
            new_amount = current_amount + amount_delta
            new_cost = current_cost + cost_delta
            if new_amount < 0.00000001:
                new_amount = 0
                new_cost = 0
            new_avg = new_cost / new_amount if new_amount > 0 else 0
            await db.execute(
                "UPDATE portfolio SET amount = ?, avg_entry_price = ?, total_cost = ? WHERE coin = ?",
                (new_amount, new_avg, new_cost, coin),
            )
        else:
            avg_price = cost_delta / amount_delta if amount_delta > 0 else 0
            await db.execute(
                "INSERT INTO portfolio (coin, amount, avg_entry_price, total_cost) VALUES (?, ?, ?, ?)",
                (coin, amount_delta, avg_price, cost_delta),
            )
        await db.commit()
    finally:
        await db.close()


async def record_trade(coin: str, side: str, amount: float, price: float, total_usd: float):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO trades (coin, side, amount, price, total_usd) VALUES (?, ?, ?, ?, ?)",
            (coin, side, amount, price, total_usd),
        )
        await db.commit()
    finally:
        await db.close()


async def get_trade_history(limit: int = 100) -> list:
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT id, coin, side, amount, price, total_usd, timestamp FROM trades ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def record_snapshot(total_value: float):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO portfolio_snapshots (total_value) VALUES (?)",
            (total_value,),
        )
        await db.commit()
    finally:
        await db.close()


async def get_snapshots(limit: int = 500) -> list:
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT total_value, timestamp FROM portfolio_snapshots ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in reversed(rows)]
    finally:
        await db.close()


async def record_signal(strategy: str, coin: str, signal: str, confidence: float):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO signals (strategy, coin, signal, confidence) VALUES (?, ?, ?, ?)",
            (strategy, coin, signal, confidence),
        )
        await db.commit()
    finally:
        await db.close()


async def get_recent_signals(limit: int = 50) -> list:
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT id, strategy, coin, signal, confidence, timestamp FROM signals ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in rows]
    finally:
        await db.close()
