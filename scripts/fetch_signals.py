#!/usr/bin/env python3
"""
Daily market signal fetcher.
"""

import json
import sys
from datetime import datetime, timezone

try:
    import pandas as pd
    import yfinance as yf
except ImportError:
    print("Missing dependency: pip install yfinance pandas", file=sys.stderr)
    raise

TICKERS = {
    "XLE":    ("XLE",       "Energy Select Sector SPDR"),
    "XLF":    ("XLF",       "Financial Select Sector SPDR"),
    "XLK":    ("XLK",       "Technology Select Sector SPDR"),
    "XLU":    ("XLU",       "Utilities Select Sector SPDR"),
    "XLV":    ("XLV",       "Health Care Select Sector SPDR"),
    "XLY":    ("XLY",       "Consumer Discretionary Select SPDR"),
    "XLP":    ("XLP",       "Consumer Staples Select SPDR"),
    "SOXX":   ("SOXX",      "iShares Semiconductor ETF"),
    "SPX":    ("^GSPC",     "S&P 500"),
    "IXIC":   ("^IXIC",     "Nasdaq Composite"),
    "NIKKEI": ("^N225",     "Nikkei 225 (Japan)"),
    "SXXP":   ("^STOXX",    "STOXX Europe 600"),
    "SENSEX": ("^BSESN",    "S&P BSE Sensex (India)"),
    "KOSPI":  ("^KS11",     "KOSPI Composite (Korea)"),
    "HSI":    ("^HSI",      "Hang Seng Index (Hong Kong)"),
    "CSI300": ("000300.SS", "CSI 300 Index (China)"),
    "GOLD":   ("GLD",       "SPDR Gold Shares ETF"),
    "BTCUSD": ("BTC-USD",   "Bitcoin / USD"),
    "ETHUSD": ("ETH-USD",   "Ethereum / USD"),
    "ESPO":   ("ESPO",      "VanEck Video Gaming & eSports ETF"),
    "PSEI":   ("PSEI.PS",   "Philippine Stock Exchange Index"),
    "JILL":   ("JILL",      "J.Jill Inc (tentative - confirm mapping)"),
}


def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def get_close_series(hist):
    """yfinance sometimes returns a MultiIndex-column DataFrame even for a
    single ticker (depending on version/args). Normalize to a plain 1-D
    Series of closes no matter what shape came back."""
    close = hist["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.dropna()


def compute_signal(yahoo_ticker, label):
    hist = yf.download(yahoo_ticker, period="1y", interval="1d",
                        progress=False, auto_adjust=False)
    if hist.empty:
        return {"ticker": yahoo_ticker, "label": label, "error": "no_data"}

    close = get_close_series(hist)
    if len(close) < 55:
        return {"ticker": yahoo_ticker, "label": label, "error": "insufficient_data"}

    price = float(close.iloc[-1])

    ema20 = float(ema(close, 20).iloc[-1])
    ema50 = float(ema(close, 50).iloc[-1])
    ema20_pct = (price - ema20) / ema20 * 100
    ema50_pct = (price - ema50) / ema50 * 100

    high_52w = float(close.max())
    low_52w = float(close.min())

    up_pct = (high_52w - price) / price * 100
    down_pct = (price - low_52w) / price * 100
    rr = round(up_pct / down_pct, 2) if down_pct > 0 else None

    if price > ema20 and price > ema50:
        status = "UPTREND"
    elif price < ema20 and price < ema50:
        status = "DOWNTREND"
    else:
        status = "SIDEWAYS / MIXED"

    prev_close = float(close.iloc[-2]) if len(close) > 1 else price
    chg_1d_pct = (price - prev_close) / prev_close * 100 if prev_close else 0.0

    return {
        "ticker": yahoo_ticker,
        "label": label,
        "price": round(price, 4),
        "chg1d_pct": round(chg_1d_pct, 2),
        "ema20_pct": round(ema20_pct, 2),
        "ema50_pct": round(ema50_pct, 2),
        "high_52w": round(high_52w, 4),
        "low_52w": round(low_52w, 4),
        "up_pct_to_high": round(up_pct, 1),
        "down_pct_to_low": round(down_pct, 1),
        "rr": rr,
        "status": status,
    }


def main():
    results = {}
    for key, (yahoo_ticker, label) in TICKERS.items():
        try:
            results[key] = compute_signal(yahoo_ticker, label)
        except Exception as exc:
            results[key] = {"ticker": yahoo_ticker, "label": label, "error": str(exc)}

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "methodology": (
            "EMA20/EMA50 = % price is above/below the 20- and 50-day exponential "
            "moving average. TP/SL reference = 52-week high/low of daily closes. "
            "R:R = remaining upside % to 52w high divided by remaining downside % "
            "to 52w low. Status is mechanical: UPTREND if price is above both EMAs, "
            "DOWNTREND if below both, otherwise SIDEWAYS / MIXED. Educational use "
            "only, not investment advice."
        ),
        "signals": results,
    }

    with open("data/signals.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote data/signals.json with {len(results)} tickers")


if __name__ == "__main__":
    main()
