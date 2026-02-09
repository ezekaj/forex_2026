from database import (
    get_cash_balance,
    set_cash_balance,
    get_positions,
    update_position,
    record_trade,
    get_trade_history,
    record_snapshot,
    get_snapshots,
)
from market import get_price_for_coin, fetch_prices


async def get_portfolio_summary() -> dict:
    cash = await get_cash_balance()
    positions = await get_positions()
    prices = await fetch_prices()

    holdings = []
    total_holdings_value = 0.0

    for pos in positions:
        coin_id = pos["coin"]
        amount = pos["amount"]
        avg_entry = pos["avg_entry_price"]
        total_cost = pos["total_cost"]

        current_price = 0.0
        if coin_id in prices:
            current_price = prices[coin_id]["price_usd"]
        elif get_price_for_coin(coin_id):
            current_price = get_price_for_coin(coin_id)

        current_value = amount * current_price
        pnl = current_value - total_cost
        pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else 0

        holdings.append({
            "coin": coin_id,
            "symbol": prices.get(coin_id, {}).get("symbol", coin_id.upper()),
            "amount": round(amount, 8),
            "avg_entry_price": round(avg_entry, 6),
            "current_price": round(current_price, 6),
            "current_value": round(current_value, 2),
            "total_cost": round(total_cost, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })
        total_holdings_value += current_value

    total_value = cash + total_holdings_value
    initial_balance = 10000.0
    total_pnl = total_value - initial_balance
    total_pnl_pct = (total_pnl / initial_balance * 100) if initial_balance > 0 else 0

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
    win_rate = (win_count / len(sells) * 100) if sells else 0

    return {
        "cash": round(cash, 2),
        "holdings": holdings,
        "total_holdings_value": round(total_holdings_value, 2),
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "total_trades": len(trades),
        "win_rate": round(win_rate, 1),
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

    price = coin_data["price_usd"]
    if price <= 0:
        return {"success": False, "error": "Invalid price data"}

    qty = amount_usd / price

    if side == "buy":
        cash = await get_cash_balance()
        if amount_usd > cash:
            return {
                "success": False,
                "error": f"Insufficient cash. Available: ${cash:.2f}",
            }
        await set_cash_balance(cash - amount_usd)
        await update_position(coin_id, qty, amount_usd)
        await record_trade(coin_id, "buy", qty, price, amount_usd)

    else:
        positions = await get_positions()
        pos = next((p for p in positions if p["coin"] == coin_id), None)
        if not pos or pos["amount"] < qty:
            available = pos["amount"] if pos else 0
            return {
                "success": False,
                "error": f"Insufficient {coin_data['symbol']} holdings. Available: {available:.8f}",
            }
        avg_entry = pos["avg_entry_price"]
        cost_basis = qty * avg_entry
        await update_position(coin_id, -qty, -cost_basis)
        cash = await get_cash_balance()
        await set_cash_balance(cash + amount_usd)
        await record_trade(coin_id, "sell", qty, price, amount_usd)

    new_portfolio = await get_portfolio_summary()
    await record_snapshot(new_portfolio["total_value"])

    return {
        "success": True,
        "trade": {
            "coin": coin_id,
            "symbol": coin_data["symbol"],
            "side": side,
            "qty": round(qty, 8),
            "price": round(price, 6),
            "total_usd": round(amount_usd, 2),
        },
        "portfolio": new_portfolio,
    }
