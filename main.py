import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db
from market import fetch_prices, fetch_coin_detail, fetch_market_overview, fetch_history, SUPPORTED_COINS
from portfolio import get_portfolio_summary, execute_trade
from strategies import STRATEGIES, get_signal, backtest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized.")
    logger.info("Pre-fetching prices...")
    try:
        await fetch_prices()
        logger.info("Prices loaded.")
    except Exception as e:
        logger.warning(f"Initial price fetch failed: {e}")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="ZeDigital Trading Bot API",
    description="Paper trading backend with real CoinGecko market data, strategy signals, and backtesting.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ezekaj.github.io", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TradeRequest(BaseModel):
    coin_id: str
    side: str
    amount_usd: float


class BacktestRequest(BaseModel):
    strategy: str
    coin_id: str = "bitcoin"
    days: int = 90
    initial_capital: float = 10000.0
    params: Optional[dict] = None


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "zedigital-trading-bot"}


@app.get("/api/prices")
async def get_prices():
    prices = await fetch_prices()
    return {"prices": prices, "count": len(prices)}


@app.get("/api/prices/{coin_id}")
async def get_coin_price(coin_id: str):
    detail = await fetch_coin_detail(coin_id)
    if not detail:
        return {"error": f"Coin '{coin_id}' not supported. Supported: {list(SUPPORTED_COINS.keys())}"}
    return detail


@app.get("/api/market")
async def get_market():
    overview = await fetch_market_overview()
    return overview


@app.post("/api/trade")
async def post_trade(req: TradeRequest):
    result = await execute_trade(req.coin_id, req.side, req.amount_usd)
    if not result["success"]:
        return {"error": result["error"]}, 400
    return result


@app.get("/api/portfolio")
async def get_portfolio():
    summary = await get_portfolio_summary()
    return summary


@app.get("/api/strategies")
async def list_strategies():
    return {"strategies": STRATEGIES}


@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    if req.strategy not in STRATEGIES:
        return {"error": f"Unknown strategy. Available: {list(STRATEGIES.keys())}"}

    if req.coin_id not in SUPPORTED_COINS:
        return {"error": f"Unsupported coin. Available: {list(SUPPORTED_COINS.keys())}"}

    days = max(7, min(365, req.days))
    history = await fetch_history(req.coin_id, days=days)
    if not history or len(history) < 60:
        return {"error": "Insufficient historical data for backtesting"}

    result = backtest(
        strategy_id=req.strategy,
        prices=history,
        initial_capital=req.initial_capital,
        params=req.params,
    )
    return result


@app.get("/api/signals")
async def get_signals(
    coin_id: str = Query(default="bitcoin"),
    days: int = Query(default=30, ge=7, le=365),
):
    if coin_id not in SUPPORTED_COINS:
        return {"error": f"Unsupported coin. Available: {list(SUPPORTED_COINS.keys())}"}

    history = await fetch_history(coin_id, days=days)
    if not history or len(history) < 20:
        return {"error": "Insufficient data for signal generation"}

    signals = {}
    for strategy_id in STRATEGIES:
        sig = get_signal(strategy_id, history)
        sig["strategy"] = strategy_id
        sig["strategy_name"] = STRATEGIES[strategy_id]["name"]
        signals[strategy_id] = sig

    buy_count = sum(1 for s in signals.values() if s["signal"] == "buy")
    sell_count = sum(1 for s in signals.values() if s["signal"] == "sell")
    if buy_count > sell_count:
        consensus = "buy"
    elif sell_count > buy_count:
        consensus = "sell"
    else:
        consensus = "hold"

    avg_confidence = sum(s["confidence"] for s in signals.values()) / len(signals) if signals else 0

    return {
        "coin_id": coin_id,
        "coin_symbol": SUPPORTED_COINS[coin_id]["symbol"],
        "signals": signals,
        "consensus": consensus,
        "avg_confidence": round(avg_confidence, 2),
    }


connected_clients: set = set()


@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"WebSocket client connected. Total: {len(connected_clients)}")

    try:
        while True:
            try:
                prices = await fetch_prices()
                await websocket.send_json({
                    "type": "prices",
                    "data": prices,
                })
            except Exception as e:
                logger.warning(f"Price fetch error in WS loop: {e}")

            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(connected_clients)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
