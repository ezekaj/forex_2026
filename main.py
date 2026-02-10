import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="ZeDigital Trading Bot API",
    description="Paper trading backend with real CoinGecko market data, strategy signals, and backtesting.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ezekaj.github.io", "http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


VALID_COINS = set(SUPPORTED_COINS.keys())
VALID_STRATEGIES = {"ma_crossover", "rsi", "macd", "bollinger_bands"}


class TradeRequest(BaseModel):
    coin_id: str = Field(..., description="Coin identifier")
    side: str = Field(..., pattern="^(buy|sell)$", description="Trade side: buy or sell")
    amount_usd: float = Field(..., gt=0, le=100000, description="Trade amount in USD (max $100,000)")

    @field_validator("coin_id")
    @classmethod
    def validate_coin_id(cls, v: str) -> str:
        if v not in VALID_COINS:
            raise ValueError(f"Unsupported coin. Available: {sorted(VALID_COINS)}")
        return v


class BacktestRequest(BaseModel):
    strategy: str = Field(..., description="Strategy identifier")
    coin_id: str = Field(default="bitcoin", description="Coin identifier")
    days: int = Field(default=90, ge=7, le=365, description="Backtest period in days")
    initial_capital: float = Field(default=10000.0, gt=0, le=1000000, description="Initial capital in USD")
    params: Optional[dict] = None

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v not in VALID_STRATEGIES:
            raise ValueError(f"Unknown strategy. Available: {sorted(VALID_STRATEGIES)}")
        return v

    @field_validator("coin_id")
    @classmethod
    def validate_coin_id(cls, v: str) -> str:
        if v not in VALID_COINS:
            raise ValueError(f"Unsupported coin. Available: {sorted(VALID_COINS)}")
        return v

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Optional[dict]) -> Optional[dict]:
        if v is None:
            return v
        for key, val in v.items():
            if not isinstance(val, (int, float)):
                raise ValueError(f"Strategy param '{key}' must be a number")
            if val <= 0:
                raise ValueError(f"Strategy param '{key}' must be positive")
            if val > 10000:
                raise ValueError(f"Strategy param '{key}' exceeds maximum value of 10000")
        return v


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "zedigital-trading-bot"}


@app.get("/api/prices")
@limiter.limit("60/minute")
async def get_prices(request: Request):
    prices = await fetch_prices()
    return {"prices": prices, "count": len(prices)}


@app.get("/api/prices/{coin_id}")
@limiter.limit("60/minute")
async def get_coin_price(request: Request, coin_id: str):
    if coin_id not in VALID_COINS:
        raise HTTPException(status_code=400, detail=f"Unsupported coin. Available: {sorted(VALID_COINS)}")
    detail = await fetch_coin_detail(coin_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Price data not available for '{coin_id}'")
    return detail


@app.get("/api/market")
@limiter.limit("60/minute")
async def get_market(request: Request):
    overview = await fetch_market_overview()
    return overview


@app.post("/api/trade")
@limiter.limit("10/minute")
async def post_trade(request: Request, req: TradeRequest):
    result = await execute_trade(req.coin_id, req.side, req.amount_usd)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/portfolio")
async def get_portfolio():
    summary = await get_portfolio_summary()
    return summary


@app.get("/api/strategies")
async def list_strategies():
    return {"strategies": STRATEGIES}


@app.post("/api/backtest")
@limiter.limit("5/minute")
async def run_backtest(request: Request, req: BacktestRequest):
    history = await fetch_history(req.coin_id, days=req.days)
    if not history or len(history) < 60:
        raise HTTPException(status_code=400, detail="Insufficient historical data for backtesting")

    result = backtest(
        strategy_id=req.strategy,
        prices=history,
        initial_capital=req.initial_capital,
        params=req.params,
    )
    return result


@app.get("/api/signals")
@limiter.limit("60/minute")
async def get_signals(
    request: Request,
    coin_id: str = Query(default="bitcoin"),
    days: int = Query(default=30, ge=7, le=365),
):
    if coin_id not in VALID_COINS:
        raise HTTPException(status_code=400, detail=f"Unsupported coin. Available: {sorted(VALID_COINS)}")

    history = await fetch_history(coin_id, days=days)
    if not history or len(history) < 20:
        raise HTTPException(status_code=400, detail="Insufficient data for signal generation")

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
