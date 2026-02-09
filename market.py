import time
import httpx
from typing import Optional

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

SUPPORTED_COINS = {
    "bitcoin": {"symbol": "BTC", "name": "Bitcoin"},
    "ethereum": {"symbol": "ETH", "name": "Ethereum"},
    "solana": {"symbol": "SOL", "name": "Solana"},
    "binancecoin": {"symbol": "BNB", "name": "BNB"},
    "cardano": {"symbol": "ADA", "name": "Cardano"},
    "polkadot": {"symbol": "DOT", "name": "Polkadot"},
    "avalanche-2": {"symbol": "AVAX", "name": "Avalanche"},
    "matic-network": {"symbol": "MATIC", "name": "Polygon"},
}

COIN_IDS = list(SUPPORTED_COINS.keys())

_price_cache: dict = {}
_price_cache_ts: float = 0
PRICE_CACHE_TTL = 30

_market_cache: dict = {}
_market_cache_ts: float = 0

_history_cache: dict = {}
HISTORY_CACHE_TTL = 300


def _get_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=15.0,
        headers={"Accept": "application/json"},
        follow_redirects=True,
    )


async def fetch_prices() -> dict:
    global _price_cache, _price_cache_ts

    now = time.time()
    if _price_cache and (now - _price_cache_ts) < PRICE_CACHE_TTL:
        return _price_cache

    ids_str = ",".join(COIN_IDS)
    url = (
        f"{COINGECKO_BASE}/simple/price"
        f"?ids={ids_str}"
        f"&vs_currencies=usd"
        f"&include_24hr_change=true"
        f"&include_24hr_vol=true"
        f"&include_market_cap=true"
    )

    async with _get_client() as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 429:
                if _price_cache:
                    return _price_cache
                raise Exception("Rate limited by CoinGecko")
            resp.raise_for_status()
            data = resp.json()

            result = {}
            for coin_id, info in data.items():
                meta = SUPPORTED_COINS.get(coin_id, {})
                result[coin_id] = {
                    "id": coin_id,
                    "symbol": meta.get("symbol", coin_id.upper()),
                    "name": meta.get("name", coin_id.title()),
                    "price_usd": info.get("usd", 0),
                    "change_24h": info.get("usd_24h_change", 0),
                    "volume_24h": info.get("usd_24h_vol", 0),
                    "market_cap": info.get("usd_market_cap", 0),
                }

            _price_cache = result
            _price_cache_ts = now
            return result
        except httpx.HTTPStatusError:
            if _price_cache:
                return _price_cache
            raise


async def fetch_coin_detail(coin_id: str) -> Optional[dict]:
    if coin_id not in SUPPORTED_COINS:
        return None

    prices = await fetch_prices()
    coin_data = prices.get(coin_id)
    if not coin_data:
        return None

    history = await fetch_history(coin_id, days=1)

    return {
        **coin_data,
        "history_24h": history,
    }


async def fetch_history(coin_id: str, days: int = 7) -> list:
    cache_key = f"{coin_id}_{days}"
    now = time.time()

    if cache_key in _history_cache:
        cached = _history_cache[cache_key]
        if (now - cached["ts"]) < HISTORY_CACHE_TTL:
            return cached["data"]

    url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"

    async with _get_client() as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 429:
                if cache_key in _history_cache:
                    return _history_cache[cache_key]["data"]
                return []
            resp.raise_for_status()
            data = resp.json()
            prices = data.get("prices", [])

            _history_cache[cache_key] = {"data": prices, "ts": now}
            return prices
        except httpx.HTTPStatusError:
            if cache_key in _history_cache:
                return _history_cache[cache_key]["data"]
            return []


async def fetch_market_overview() -> dict:
    global _market_cache, _market_cache_ts

    now = time.time()
    if _market_cache and (now - _market_cache_ts) < PRICE_CACHE_TTL:
        return _market_cache

    url = f"{COINGECKO_BASE}/global"

    async with _get_client() as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 429:
                if _market_cache:
                    return _market_cache
                return {}
            resp.raise_for_status()
            data = resp.json().get("data", {})

            result = {
                "total_market_cap_usd": data.get("total_market_cap", {}).get("usd", 0),
                "total_volume_24h_usd": data.get("total_volume", {}).get("usd", 0),
                "btc_dominance": data.get("market_cap_percentage", {}).get("btc", 0),
                "eth_dominance": data.get("market_cap_percentage", {}).get("eth", 0),
                "active_cryptocurrencies": data.get("active_cryptocurrencies", 0),
                "market_cap_change_24h": data.get("market_cap_change_percentage_24h_usd", 0),
            }

            _market_cache = result
            _market_cache_ts = now
            return result
        except httpx.HTTPStatusError:
            if _market_cache:
                return _market_cache
            return {}


def get_price_for_coin(coin_id: str) -> Optional[float]:
    if coin_id in _price_cache:
        return _price_cache[coin_id].get("price_usd")
    return None
