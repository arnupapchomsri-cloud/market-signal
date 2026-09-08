#!/usr/bin/env python3
"""
Daily SET100 (Thai stocks) signal fetcher.

Same mechanical methodology as scripts/fetch_signals.py, applied to a
list of ~99 SET100-index Thai stocks (Yahoo Finance tickers, .BK suffix).
Writes everything to data/set100_signals.json (kept separate from the
global ETF/Index/crypto file so the two watchlists never collide).

Trend status is fully mechanical (no discretionary calls):
  - price > EMA20 and price > EMA50            -> UPTREND
  - price < EMA20 and price < EMA50            -> DOWNTREND
  - anything else (mixed)                       -> SIDEWAYS / MIXED

NOTE on the ticker list: this was assembled from public sources (not
downloaded directly from set.or.th), so it may not match the official
SET100 rebalance 100% at all times (occasional inclusion/exclusion drift
every 6-month SET50/SET100 review). Update the TICKERS dict below if a
name needs to be added, removed, or renamed.
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

# key -> (yahoo_ticker, label)
TICKERS = {
    "ADVANC": ("ADVANC.BK", "Advanced Info Service"),
    "AEONTS": ("AEONTS.BK", "Aeon Thana Sinsap"),
    "AOT":    ("AOT.BK",    "Airports of Thailand"),
    "AMATA":  ("AMATA.BK",  "Amata Corp"),
    "AP":     ("AP.BK",     "AP (Thailand)"),
    "AAV":    ("AAV.BK",    "Asia Aviation"),
    "BCP":    ("BCP.BK",    "Bangchak Corp"),
    "BBL":    ("BBL.BK",    "Bangkok Bank"),
    "BCH":    ("BCH.BK",    "Bangkok Chain Hospital"),
    "BLA":    ("BLA.BK",    "Bangkok Life Assurance"),
    "BJC":    ("BJC.BK",    "Berli Jucker"),
    "BDMS":   ("BDMS.BK",   "Bangkok Dusit Medical Services"),
    "BTS":    ("BTS.BK",    "BTS Group"),
    "BH":     ("BH.BK",     "Bumrungrad Hospital"),
    "CCET":   ("CCET.BK",   "Cal-Comp Electronics"),
    "CPN":    ("CPN.BK",    "Central Pattana"),
    "CENTEL": ("CENTEL.BK", "Central Plaza Hotel"),
    "CK":     ("CK.BK",     "CH. Karnchang"),
    "CPF":    ("CPF.BK",    "Charoen Pokphand Foods"),
    "CHG":    ("CHG.BK",    "Chularat Hospital"),
    "CPALL":  ("CPALL.BK",  "CP All"),
    "DELTA":  ("DELTA.BK",  "Delta Electronics (Thailand)"),
    "EGCO":   ("EGCO.BK",   "Electricity Generating"),
    "ERW":    ("ERW.BK",    "Erawan Group"),
    "GFPT":   ("GFPT.BK",   "GFPT"),
    "GUNKUL": ("GUNKUL.BK", "Gunkul Engineering"),
    "HANA":   ("HANA.BK",   "Hana Microelectronics"),
    "HMPRO":  ("HMPRO.BK",  "Home Product Center"),
    "ICHI":   ("ICHI.BK",   "Ichitan Group"),
    "IVL":    ("IVL.BK",    "Indorama Ventures"),
    "IRPC":   ("IRPC.BK",   "IRPC"),
    "JMART":  ("JMART.BK",  "Jay Mart"),
    "JMT":    ("JMT.BK",    "JMT Network Services"),
    "KBANK":  ("KBANK.BK",  "Kasikornbank"),
    "KCE":    ("KCE.BK",    "KCE Electronics"),
    "KKP":    ("KKP.BK",    "Kiatnakin Phatra Bank"),
    "KTB":    ("KTB.BK",    "Krung Thai Bank"),
    "KTC":    ("KTC.BK",    "Krungthai Card"),
    "LH":     ("LH.BK",     "Land and Houses"),
    "MEGA":   ("MEGA.BK",   "Mega Lifesciences"),
    "MINT":   ("MINT.BK",   "Minor International"),
    "M":      ("M.BK",      "MK Restaurant Group"),
    "PTG":    ("PTG.BK",    "PTG Energy"),
    "PTT":    ("PTT.BK",    "PTT"),
    "PTTEP":  ("PTTEP.BK",  "PTT Exploration and Production"),
    "PTTGC":  ("PTTGC.BK",  "PTT Global Chemical"),
    "QH":     ("QH.BK",     "Quality Houses"),
    "RATCH":  ("RATCH.BK",  "Ratch Group"),
    "RCL":    ("RCL.BK",    "Regional Container Lines"),
    "SIRI":   ("SIRI.BK",   "Sansiri"),
    "SCC":    ("SCC.BK",    "Siam Cement Group"),
    "GLOBAL": ("GLOBAL.BK", "Siam Global House"),
    "STA":    ("STA.BK",    "Sri Trang Agro-Industry"),
    "SAWAD":  ("SAWAD.BK",  "Srisawad Corp"),
    "SPALI":  ("SPALI.BK",  "Supalai"),
    "THAI":   ("THAI.BK",   "Thai Airways International"),
    "TOP":    ("TOP.BK",    "Thai Oil"),
    "THCOM":  ("THCOM.BK",  "Thaicom"),
    "TCAP":   ("TCAP.BK",   "Thanachart Capital"),
    "TASCO":  ("TASCO.BK",  "Tipco Asphalt"),
    "TISCO":  ("TISCO.BK",  "Tisco Financial Group"),
    "TTB":    ("TTB.BK",    "TMBThanachart Bank"),
    "TRUE":   ("TRUE.BK",   "True Corporation"),
    "VGI":    ("VGI.BK",    "VGI"),
    "WHA":    ("WHA.BK",    "WHA Corp"),
    "EA":     ("EA.BK",     "Energy Absolute"),
    "BA":     ("BA.BK",     "Bangkok Airways"),
    "CBG":    ("CBG.BK",    "Carabao Group"),
    "PLANB":  ("PLANB.BK",  "Plan B Media"),
    "BEM":    ("BEM.BK",    "Bangkok Expressway and Metro"),
    "COM7":   ("COM7.BK",   "COM7"),
    "GPSC":   ("GPSC.BK",   "Global Power Synergy"),
    "SPRC":   ("SPRC.BK",   "Star Petroleum Refining"),
    "TFG":    ("TFG.BK",    "Thai Foods Group"),
    "TU":     ("TU.BK",     "Thai Union Group"),
    "BCPG":   ("BCPG.BK",   "BCPG"),
    "WHAUP":  ("WHAUP.BK",  "WHA Utilities and Power"),
    "BGRIM":  ("BGRIM.BK",  "B.Grimm Power"),
    "PRM":    ("PRM.BK",    "Prima Marine"),
    "TOA":    ("TOA.BK",    "TOA Paint (Thailand)"),
    "MTC":    ("MTC.BK",    "Muangthai Capital"),
    "PR9":    ("PR9.BK",    "Praram 9 Hospital"),
    "OSP":    ("OSP.BK",    "Osotspa"),
    "DOHOME": ("DOHOME.BK", "Dohome"),
    "BAM":    ("BAM.BK",    "Bangkok Commercial Asset Management"),
    "AWC":    ("AWC.BK",    "Asset World Corp"),
    "CRC":    ("CRC.BK",    "Central Retail Corporation"),
    "STGT":   ("STGT.BK",   "Sri Trang Gloves (Thailand)"),
    "SCGP":   ("SCGP.BK",   "SCG Packaging"),
    "OR":     ("OR.BK",     "PTT Oil and Retail Business"),
    "SCB":    ("SCB.BK",    "SCB X"),
    "TLI":    ("TLI.BK",    "Thai Life Insurance"),
    "BTG":    ("BTG.BK",    "Betagro"),
    "AURA":   ("AURA.BK",   "Aurora Design"),
    "MOSHI":  ("MOSHI.BK",  "Moshi Moshi Retail Corporation"),
    "STECON": ("STECON.BK", "Stecon Group"),
    "GULF":   ("GULF.BK",   "Gulf Development"),
    "TIDLOR": ("TIDLOR.BK", "Ngern Tid Lor"),
    "MRDIY":  ("MRDIY.BK",  "MR DIY (Thailand)"),
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
            "SET100 watchlist (~99 Thai stocks, .BK Yahoo Finance tickers). "
            "EMA20/EMA50 = % price is above/below the 20- and 50-day exponential "
            "moving average. TP/SL reference = 52-week high/low of daily closes. "
            "R:R = remaining upside % to 52w high divided by remaining downside % "
            "to 52w low. Status is mechanical: UPTREND if price is above both EMAs, "
            "DOWNTREND if below both, otherwise SIDEWAYS / MIXED. Ticker list "
            "compiled from public sources and may not match the official SET100 "
            "rebalance 100% at all times. Educational use only, not investment advice."
        ),
        "signals": results,
    }

    with open("data/set100_signals.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote data/set100_signals.json with {len(results)} tickers")


if __name__ == "__main__":
    main()
