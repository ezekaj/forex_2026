import threading
from decimal import Decimal, ROUND_HALF_UP

from database import (
    get_cash_balance,
    set_cash_balance,
    get_positions,
    update_position,
    record_trade,
    get_trade_history,
    record_snapshot,
    get_snapshots,
    execute_trade_atomic,
)
from market import get_price_for_coin, fetch_prices

_portfolio_lock = threading.Lock()


def _to_decimal(value) -> Decimal:
    return Decimal(str(value))


def _round_usd(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _round_qty(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP))


def _round_price(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


async def get_portfolio_summary() -> dict:
    cash = _to_decimal(await get_cash_balance())
    positions = await get_positions()
    prices = await fetch_prices()

    holdings = []
    total_holdings_value = Decimal("0")

    for pos in positions:
        coin_id = pos["coin"]
        amount = _to_decimal(pos["amount"])
        avg_entry = _to_decimal(pos["avg_entry_price"])
        total_cost = _to_decimal(pos["total_cost"])

        current_price = Decimal("0")
        if coin_id in prices:
            current_price = _to_decimal(prices[coin_id]["price_usd"])
        elif get_price_for_coin(coin_id):
            current_price = _to_decimal(get_price_for_coin(coin_id))

        current_value = amount * current_price
        pnl = current_value - total_cost
        pnl_pct = (pnl / total_cost * Decimal("100")) if total_cost > 0 else Decimal("0")

        holdings.append({
            "coin": coin_id,
            "symbol": prices.get(coin_id, {}).get("symbol", coin_id.upper()),
            "amount": _round_qty(amount),
            "avg_entry_price": _round_price(avg_entry),
            "current_price": _round_price(current_price),
            "current_value": _round_usd(current_value),
            "total_cost": _round_usd(total_cost),
            "pnl": _round_usd(pnl),
            "pnl_pct": _round_usd(pnl_pct),
        })
        total_holdings_value += current_value

    total_value = cash + total_holdings_value
    initial_balance = Decimal("10000")
    total_pnl = total_value - initial_balance
    total_pnl_pct = (total_pnl / initial_balance * Decimal("100")) if initial_balance > 0 else Decimal("0")

    trades = await get_trade_history(limit=100)
    snapshots = await get_snapshots(limit=500)

    sells = [t for t in trades if t["side"] == "sell"]
    win_count = 0
    for sell_trade in sells:
        matching_buys = [
            t
            for t in trades
            if t["coin"] == sell_trade["coin"]
            and t["side"] == "buy"
            and t["timestamp"] < sell_trade["timestamp"]
        ]
        if matching_buys and sell_trade["price"] > matching_buys[-1]["price"]:
            win_count += 1
    win_rate = (_to_decimal(win_count) / _to_decimal(len(sells)) * Decimal("100")) if sells else Decimal("0")

    return {
        "cash": _round_usd(cash),
        "holdings": holdings,
        "total_holdings_value": _round_usd(total_holdings_value),
        "total_value": _round_usd(total_value),
        "total_pnl": _round_usd(total_pnl),
        "total_pnl_pct": _round_usd(total_pnl_pct),
        "total_trades": len(trades),
        "win_rate": float(_to_decimal(win_rate).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
        "trade_history": trades[:50],
        "portfolio_snapshots": snapshots,
    }


async def execute_trade(coin_id: str, side: str, amount_usd: float) -> dict:
    if side not in ("buy", "sell"):
        return {"success": False, "error": "Side must be 'buy' or 'sell'"}

    if amount_usd <= 0:
        return {"success": False, "error": "Amount must be positive"}

    prices = await fetch_prices()
    coin_data = prices.get(coin_id)
    if not coin_data:
        return {"success": False, "error": f"Price data not available for {coin_id}"}

    price_d = _to_decimal(coin_data["price_usd"])
    amount_d = _to_decimal(amount_usd)

    if price_d <= 0:
        return {"success": False, "error": "Invalid price data"}

    qty_d = amount_d / price_d
    qty = float(qty_d)
    price = float(price_d)

    with _portfolio_lock:
        result = await execute_trade_atomic(coin_id, side, qty, price, amount_usd)

    if not result["success"]:
        return result

    new_portfolio = await get_portfolio_summary()
    await record_snapshot(new_portfolio["total_value"])

    return {
        "success": True,
        "trade": {
            "coin": coin_id,
            "symbol": coin_data["symbol"],
            "side": side,
            "qty": _round_qty(qty_d),
            "price": _round_price(price_d),
            "total_usd": _round_usd(amount_d),
        },
        "portfolio": new_portfolio,
    }
