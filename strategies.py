import numpy as np
from typing import Optional


STRATEGIES = {
    "ma_crossover": {
        "name": "MA Crossover",
        "description": "Short/long moving average crossover strategy. Generates buy signal when short MA crosses above long MA, sell when it crosses below.",
        "params": {"short_period": 20, "long_period": 50},
    },
    "rsi": {
        "name": "RSI",
        "description": "Relative Strength Index strategy. Buy when RSI drops below oversold level, sell when it rises above overbought level.",
        "params": {"period": 14, "oversold": 30, "overbought": 70},
    },
    "macd": {
        "name": "MACD",
        "description": "Moving Average Convergence Divergence. Buy on bullish crossover, sell on bearish crossover.",
        "params": {"fast": 12, "slow": 26, "signal_period": 9},
    },
    "bollinger_bands": {
        "name": "Bollinger Bands",
        "description": "Mean reversion strategy using Bollinger Bands. Buy when price touches lower band, sell when it touches upper band.",
        "params": {"period": 20, "std_dev": 2.0},
    },
}


def _sma(data: np.ndarray, period: int) -> np.ndarray:
    if len(data) < period:
        return np.full(len(data), np.nan)
    result = np.full(len(data), np.nan)
    cumsum = np.cumsum(data)
    result[period - 1 :] = (cumsum[period - 1 :] - np.concatenate(([0], cumsum[:-period]))) / period
    return result


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    if len(data) < period:
        return np.full(len(data), np.nan)
    result = np.full(len(data), np.nan)
    multiplier = 2.0 / (period + 1)
    result[period - 1] = np.mean(data[:period])
    for i in range(period, len(data)):
        result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
    return result


def _rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
    if len(data) < period + 1:
        return np.full(len(data), np.nan)

    deltas = np.diff(data)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    result = np.full(len(data), np.nan)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    return result


def ma_crossover_signal(
    prices: list, short_period: int = 20, long_period: int = 50
) -> dict:
    if len(prices) < long_period + 2:
        return {"signal": "hold", "confidence": 0, "reason": "Insufficient data"}

    data = np.array([p[1] for p in prices])
    short_ma = _sma(data, short_period)
    long_ma = _sma(data, long_period)

    current_short = short_ma[-1]
    current_long = long_ma[-1]
    prev_short = short_ma[-2]
    prev_long = long_ma[-2]

    if np.isnan(current_short) or np.isnan(current_long):
        return {"signal": "hold", "confidence": 0, "reason": "Insufficient data for MAs"}

    spread = (current_short - current_long) / current_long * 100

    if prev_short <= prev_long and current_short > current_long:
        confidence = min(0.95, 0.6 + abs(spread) * 0.1)
        return {
            "signal": "buy",
            "confidence": round(confidence, 2),
            "reason": f"Bullish crossover: {short_period}MA crossed above {long_period}MA",
            "short_ma": round(current_short, 2),
            "long_ma": round(current_long, 2),
        }
    elif prev_short >= prev_long and current_short < current_long:
        confidence = min(0.95, 0.6 + abs(spread) * 0.1)
        return {
            "signal": "sell",
            "confidence": round(confidence, 2),
            "reason": f"Bearish crossover: {short_period}MA crossed below {long_period}MA",
            "short_ma": round(current_short, 2),
            "long_ma": round(current_long, 2),
        }
    else:
        trend = "bullish" if current_short > current_long else "bearish"
        return {
            "signal": "hold",
            "confidence": round(min(0.8, abs(spread) * 0.05), 2),
            "reason": f"No crossover. Trend is {trend} (spread: {spread:.2f}%)",
            "short_ma": round(current_short, 2),
            "long_ma": round(current_long, 2),
        }


def rsi_signal(
    prices: list, period: int = 14, oversold: int = 30, overbought: int = 70
) -> dict:
    if len(prices) < period + 2:
        return {"signal": "hold", "confidence": 0, "reason": "Insufficient data"}

    data = np.array([p[1] for p in prices])
    rsi_values = _rsi(data, period)
    current_rsi = rsi_values[-1]

    if np.isnan(current_rsi):
        return {"signal": "hold", "confidence": 0, "reason": "RSI not computed"}

    if current_rsi <= oversold:
        distance = oversold - current_rsi
        confidence = min(0.95, 0.55 + distance * 0.02)
        return {
            "signal": "buy",
            "confidence": round(confidence, 2),
            "reason": f"RSI oversold at {current_rsi:.1f} (below {oversold})",
            "rsi": round(current_rsi, 2),
        }
    elif current_rsi >= overbought:
        distance = current_rsi - overbought
        confidence = min(0.95, 0.55 + distance * 0.02)
        return {
            "signal": "sell",
            "confidence": round(confidence, 2),
            "reason": f"RSI overbought at {current_rsi:.1f} (above {overbought})",
            "rsi": round(current_rsi, 2),
        }
    else:
        return {
            "signal": "hold",
            "confidence": 0.3,
            "reason": f"RSI neutral at {current_rsi:.1f}",
            "rsi": round(current_rsi, 2),
        }


def macd_signal(
    prices: list, fast: int = 12, slow: int = 26, signal_period: int = 9
) -> dict:
    if len(prices) < slow + signal_period + 2:
        return {"signal": "hold", "confidence": 0, "reason": "Insufficient data"}

    data = np.array([p[1] for p in prices])
    fast_ema = _ema(data, fast)
    slow_ema = _ema(data, slow)

    macd_line = fast_ema - slow_ema
    valid_macd = macd_line[~np.isnan(macd_line)]
    if len(valid_macd) < signal_period + 2:
        return {"signal": "hold", "confidence": 0, "reason": "Insufficient MACD data"}

    signal_line = _ema(valid_macd, signal_period)

    current_macd = valid_macd[-1]
    current_signal = signal_line[-1]
    prev_macd = valid_macd[-2]
    prev_signal = signal_line[-2]

    if np.isnan(current_signal) or np.isnan(prev_signal):
        return {"signal": "hold", "confidence": 0, "reason": "MACD signal not ready"}

    histogram = current_macd - current_signal

    if prev_macd <= prev_signal and current_macd > current_signal:
        confidence = min(0.9, 0.55 + abs(histogram) / data[-1] * 100)
        return {
            "signal": "buy",
            "confidence": round(confidence, 2),
            "reason": "MACD bullish crossover",
            "macd": round(current_macd, 4),
            "signal_line": round(current_signal, 4),
            "histogram": round(histogram, 4),
        }
    elif prev_macd >= prev_signal and current_macd < current_signal:
        confidence = min(0.9, 0.55 + abs(histogram) / data[-1] * 100)
        return {
            "signal": "sell",
            "confidence": round(confidence, 2),
            "reason": "MACD bearish crossover",
            "macd": round(current_macd, 4),
            "signal_line": round(current_signal, 4),
            "histogram": round(histogram, 4),
        }
    else:
        trend = "bullish" if histogram > 0 else "bearish"
        return {
            "signal": "hold",
            "confidence": 0.3,
            "reason": f"MACD {trend}, no crossover",
            "macd": round(current_macd, 4),
            "signal_line": round(current_signal, 4),
            "histogram": round(histogram, 4),
        }


def bollinger_bands_signal(prices: list, period: int = 20, std_dev: float = 2.0) -> dict:
    if len(prices) < period + 2:
        return {"signal": "hold", "confidence": 0, "reason": "Insufficient data"}

    data = np.array([p[1] for p in prices])
    middle = _sma(data, period)

    if np.isnan(middle[-1]):
        return {"signal": "hold", "confidence": 0, "reason": "BB not computed"}

    rolling_std = np.full(len(data), np.nan)
    for i in range(period - 1, len(data)):
        rolling_std[i] = np.std(data[i - period + 1 : i + 1])

    upper = middle + std_dev * rolling_std
    lower = middle - std_dev * rolling_std

    current_price = data[-1]
    current_upper = upper[-1]
    current_lower = lower[-1]
    current_middle = middle[-1]
    band_width = current_upper - current_lower

    if current_price <= current_lower:
        pct_below = (current_lower - current_price) / band_width * 100 if band_width > 0 else 0
        confidence = min(0.9, 0.5 + pct_below * 0.05)
        return {
            "signal": "buy",
            "confidence": round(confidence, 2),
            "reason": f"Price at lower Bollinger Band (mean reversion expected)",
            "price": round(current_price, 2),
            "upper": round(current_upper, 2),
            "middle": round(current_middle, 2),
            "lower": round(current_lower, 2),
        }
    elif current_price >= current_upper:
        pct_above = (current_price - current_upper) / band_width * 100 if band_width > 0 else 0
        confidence = min(0.9, 0.5 + pct_above * 0.05)
        return {
            "signal": "sell",
            "confidence": round(confidence, 2),
            "reason": f"Price at upper Bollinger Band (reversal expected)",
            "price": round(current_price, 2),
            "upper": round(current_upper, 2),
            "middle": round(current_middle, 2),
            "lower": round(current_lower, 2),
        }
    else:
        position = (current_price - current_lower) / band_width if band_width > 0 else 0.5
        return {
            "signal": "hold",
            "confidence": 0.3,
            "reason": f"Price within bands ({position:.0%} from lower to upper)",
            "price": round(current_price, 2),
            "upper": round(current_upper, 2),
            "middle": round(current_middle, 2),
            "lower": round(current_lower, 2),
        }


def get_signal(strategy_id: str, prices: list, params: Optional[dict] = None) -> dict:
    if params is None:
        params = {}

    strategy_map = {
        "ma_crossover": ma_crossover_signal,
        "rsi": rsi_signal,
        "macd": macd_signal,
        "bollinger_bands": bollinger_bands_signal,
    }

    func = strategy_map.get(strategy_id)
    if not func:
        return {"signal": "hold", "confidence": 0, "reason": f"Unknown strategy: {strategy_id}"}

    default_params = STRATEGIES[strategy_id]["params"].copy()
    default_params.update(params)

    return func(prices, **default_params)


def backtest(
    strategy_id: str,
    prices: list,
    initial_capital: float = 10000.0,
    params: Optional[dict] = None,
) -> dict:
    if len(prices) < 60:
        return {"error": "Need at least 60 data points for backtesting"}

    if params is None:
        params = {}

    default_params = STRATEGIES.get(strategy_id, {}).get("params", {}).copy()
    default_params.update(params)

    data = np.array([p[1] for p in prices])
    timestamps = [p[0] for p in prices]

    capital = initial_capital
    position = 0.0
    entry_price = 0.0
    equity_curve = []
    trades = []
    wins = 0
    losses = 0
    total_profit = 0.0
    total_loss = 0.0

    min_lookback = 55
    for i in range(min_lookback, len(prices)):
        window = prices[max(0, i - 200) : i + 1]
        sig = get_signal(strategy_id, window, default_params)

        current_price = data[i]
        portfolio_value = capital + position * current_price

        if sig["signal"] == "buy" and sig["confidence"] > 0.4 and position == 0:
            risk_fraction = 0.1 + sig["confidence"] * 0.15
            invest = capital * risk_fraction
            position = invest / current_price
            capital -= invest
            entry_price = current_price
            trades.append({
                "type": "buy",
                "price": round(current_price, 2),
                "amount": round(position, 6),
                "timestamp": timestamps[i],
                "confidence": sig["confidence"],
            })
        elif sig["signal"] == "sell" and position > 0:
            proceeds = position * current_price
            capital += proceeds
            pnl = (current_price - entry_price) * position
            if pnl > 0:
                wins += 1
                total_profit += pnl
            else:
                losses += 1
                total_loss += abs(pnl)
            trades.append({
                "type": "sell",
                "price": round(current_price, 2),
                "amount": round(position, 6),
                "timestamp": timestamps[i],
                "pnl": round(pnl, 2),
            })
            position = 0.0
            entry_price = 0.0

        equity_curve.append(round(portfolio_value, 2))

    final_value = capital + position * data[-1]
    total_return = (final_value - initial_capital) / initial_capital * 100

    peak = initial_capital
    max_drawdown = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        if dd > max_drawdown:
            max_drawdown = dd

    daily_returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i - 1] > 0:
            daily_returns.append(
                (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            )

    if daily_returns:
        mean_r = np.mean(daily_returns)
        std_r = np.std(daily_returns)
        sharpe = float(mean_r / std_r * np.sqrt(252)) if std_r > 0 else 0
    else:
        sharpe = 0

    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    profit_factor = (total_profit / total_loss) if total_loss > 0 else (999 if total_profit > 0 else 0)

    step = max(1, len(equity_curve) // 200)
    sampled_curve = equity_curve[::step]
    if equity_curve and sampled_curve[-1] != equity_curve[-1]:
        sampled_curve.append(equity_curve[-1])

    return {
        "strategy": strategy_id,
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_return": round(total_return, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "equity_curve": sampled_curve,
        "trades": trades[-20:],
    }
