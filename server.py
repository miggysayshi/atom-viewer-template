#!/usr/bin/env python3
"""Local Yahoo Finance -> Lightweight Charts demo.

Runs a tiny stdlib HTTP server so the browser never talks to Yahoo directly
(Yahoo chart endpoint does not send permissive CORS headers).
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import mimetypes
import pathlib
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

ROOT = pathlib.Path(__file__).resolve().parent
ALLOWED_RANGES = {"1d", "5d", "7d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"}
INTERVAL_BASE = {
    "1m": ("1m", 1),
    "2m": ("2m", 1),
    "3m": ("1m", 3),
    "5m": ("5m", 1),
    "10m": ("5m", 2),
    "15m": ("15m", 1),
    "30m": ("30m", 1),
    "1h": ("1h", 1),
    "4h": ("1h", 4),
    "12h": ("1h", 12),
    "24h": ("1h", 24),
    "1d": ("1d", 1),
    "1wk": ("1wk", 1),
    "1mo": ("1mo", 1),
    "1y": ("1mo", 12),
}
INTERVAL_SECONDS = {
    "1m": 60,
    "2m": 120,
    "3m": 180,
    "5m": 300,
    "10m": 600,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "12h": 43200,
    "24h": 86400,
    "1d": 86400,
    "1wk": 7 * 86400,
    "1mo": 31 * 86400,
    "1y": 366 * 86400,
}


def normalize_time(ts: int, interval: str):
    if interval in {"1d", "1wk", "1mo", "1y"}:
        return time.strftime("%Y-%m-%d", time.gmtime(ts))
    return int(ts)


def parse_before(value: str, interval: str) -> int:
    if value.isdigit():
        return int(value)
    try:
        parsed = dt.datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
        return int(parsed.timestamp())
    except ValueError as exc:
        raise ValueError(f"Invalid before value for {interval}: {value}") from exc


def aggregate_bars(bars: list[dict], factor: int, interval: str) -> list[dict]:
    if factor <= 1:
        return bars

    def make_bar(chunk: list[dict]) -> dict:
        return {
            "time": chunk[0]["time"],
            "open": chunk[0]["open"],
            "high": round(max(b["high"] for b in chunk), 4),
            "low": round(min(b["low"] for b in chunk), 4),
            "close": chunk[-1]["close"],
            "volume": int(sum(b.get("volume") or 0 for b in chunk)),
            "adjClose": chunk[-1].get("adjClose"),
        }

    # Intraday timestamps are sparse across nights/weekends. Chunking by raw
    # array index drifts buckets across sessions; group inside each UTC trading
    # date so 4h bars start at the first bar of that session.
    if bars and isinstance(bars[0]["time"], int):
        out: list[dict] = []
        day_chunk: list[dict] = []
        current_day = None
        for bar in bars:
            day = time.strftime("%Y-%m-%d", time.gmtime(bar["time"]))
            if day != current_day:
                for start in range(0, len(day_chunk), factor):
                    out.append(make_bar(day_chunk[start:start + factor]))
                day_chunk = []
                current_day = day
            day_chunk.append(bar)
        for start in range(0, len(day_chunk), factor):
            out.append(make_bar(day_chunk[start:start + factor]))
        return out

    # Coarser string-date bars can stay sequential; for 1y from 1mo this gives
    # year-ish bars without inventing dates.
    out = []
    for start in range(0, len(bars), factor):
        chunk = bars[start:start + factor]
        if chunk:
            out.append(make_bar(chunk))
    return out


def validate_symbol_interval(symbol: str, interval: str) -> tuple[str, str, int]:
    symbol = symbol.strip().upper()
    if not symbol or len(symbol) > 18 or not all(ch.isalnum() or ch in ".-^=" for ch in symbol):
        raise ValueError("Ticker must be 1-18 chars: letters, numbers, '.', '-', '^', '='")
    if interval not in INTERVAL_BASE:
        raise ValueError(f"Unsupported interval: {interval}")
    base_interval, aggregate_factor = INTERVAL_BASE[interval]
    return symbol, base_interval, aggregate_factor


def yahoo_request(symbol: str, interval: str, params: dict, chart_range: str | None = None) -> dict:
    symbol, base_interval, aggregate_factor = validate_symbol_interval(symbol, interval)
    params = {
        **params,
        "interval": base_interval,
        "events": "history",
        "includeAdjustedClose": "true",
    }
    query = urllib.parse.urlencode(params)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 lightweight-yahoo-chart/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    result = payload.get("chart", {}).get("result") or []
    error = payload.get("chart", {}).get("error")
    if error:
        raise ValueError(error.get("description") or str(error))
    if not result:
        raise ValueError(f"No Yahoo data returned for {symbol} ({chart_range or 'window'}, {interval})")

    node = result[0]
    timestamps = node.get("timestamp") or []
    quote = (node.get("indicators", {}).get("quote") or [{}])[0]
    adjclose = (node.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose") or []
    bars = []
    for idx, ts in enumerate(timestamps):
        try:
            open_, high, low, close, volume = (
                quote["open"][idx], quote["high"][idx], quote["low"][idx], quote["close"][idx], quote["volume"][idx]
            )
        except (KeyError, IndexError):
            continue
        if None in (open_, high, low, close):
            continue
        bars.append({
            "time": normalize_time(ts, interval),
            "open": round(float(open_), 4),
            "high": round(float(high), 4),
            "low": round(float(low), 4),
            "close": round(float(close), 4),
            "volume": int(volume or 0),
            "adjClose": round(float(adjclose[idx]), 4) if idx < len(adjclose) and adjclose[idx] is not None else None,
        })

    bars = aggregate_bars(bars, aggregate_factor, interval)
    meta = node.get("meta", {})
    return {
        "symbol": meta.get("symbol", symbol),
        "name": meta.get("longName") or meta.get("shortName") or symbol,
        "currency": meta.get("currency", "USD"),
        "exchange": meta.get("fullExchangeName") or meta.get("exchangeName") or "Yahoo Finance",
        "range": chart_range,
        "interval": interval,
        "baseInterval": base_interval,
        "bars": bars,
        "source": "Yahoo Finance chart API v8",
    }


def yahoo_bars(symbol: str, chart_range: str, interval: str) -> dict:
    if chart_range not in ALLOWED_RANGES:
        raise ValueError(f"Unsupported range: {chart_range}")
    return yahoo_request(symbol, interval, {"range": chart_range}, chart_range=chart_range)


# ── Opening Range Breakout ────────────────────────────────────────────────

def fetch_raw_intraday(symbol: str, interval: str, days: int) -> list[dict]:
    """Fetch raw intraday bars (with premarket) from Yahoo. interval: 1m/2m/5m/15m/30m/1h."""
    params = {
        "interval": interval,
        "range": "max" if days > 30 else "1mo",
        "includePrePost": "true",
    }
    # For >30 days of intraday, Yahoo doesn't support long ranges well.
    # Use period1/period2 windows.
    now_ts = int(time.time())
    seconds_per_day = 86400
    # Request 2x buffer for weekends/holidays
    buffer_days = max(days * 2, days + 10)
    params = {
        "interval": interval,
        "period1": str(now_ts - buffer_days * seconds_per_day),
        "period2": str(now_ts),
        "includePrePost": "true",
    }
    symbol_clean = symbol.strip().upper()
    query = urllib.parse.urlencode(params)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol_clean)}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 lightweight-yahoo-chart/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    result = payload.get("chart", {}).get("result") or []
    error = payload.get("chart", {}).get("error")
    if error:
        raise ValueError(error.get("description") or str(error))
    if not result:
        raise ValueError(f"No Yahoo data for {symbol}")

    node = result[0]
    timestamps = node.get("timestamp") or []
    quote = (node.get("indicators", {}).get("quote") or [{}])[0]
    bars = []
    for idx, ts in enumerate(timestamps):
        try:
            o = quote["open"][idx]; h = quote["high"][idx]; l = quote["low"][idx]; c = quote["close"][idx]; v = quote["volume"][idx]
        except (KeyError, IndexError):
            continue
        if None in (o, h, l, c):
            continue
        bars.append({
            "ts": int(ts),
            "time": int(ts),
            "open": round(float(o), 4),
            "high": round(float(h), 4),
            "low": round(float(l), 4),
            "close": round(float(c), 4),
            "volume": int(v or 0),
        })
    return bars


def group_by_et_day(bars: list[dict]) -> dict[str, list[dict]]:
    """Group bars by America/New_York calendar date."""
    days: dict[str, list[dict]] = defaultdict(list)
    for bar in bars:
        et_dt = dt.datetime.fromtimestamp(bar["ts"], tz=ET)
        day_key = et_dt.strftime("%Y-%m-%d")
        days[day_key].append(bar)
    # sort bars within each day by timestamp
    for day_key in days:
        days[day_key].sort(key=lambda b: b["ts"])
    return dict(days)


MARKET_OPEN = dt.time(9, 30)
MARKET_CLOSE = dt.time(16, 0)
PRE_START = dt.time(4, 0)


def run_orb_for_day(day_bars: list[dict], or_minutes: int) -> dict | None:
    """
    Run ORB on a single day's bars (already sorted by ts).
    Returns trade result dict or None if no valid setup.
    """
    if not day_bars:
        return None

    # Convert all bars to ET datetime
    annotated = []
    for b in day_bars:
        et_dt = dt.datetime.fromtimestamp(b["ts"], tz=ET)
        annotated.append({**b, "et": et_dt})

    # Separate premarket, OR window, and RTHS
    or_end_time = (dt.datetime.combine(dt.date.today(), MARKET_OPEN) + dt.timedelta(minutes=or_minutes)).time()

    premarket = [b for b in annotated if b["et"].time() < MARKET_OPEN]
    or_window = [b for b in annotated if MARKET_OPEN <= b["et"].time() < or_end_time]
    rest_of_day = [b for b in annotated if b["et"].time() >= or_end_time]
    rth_bars_all = [b for b in annotated if MARKET_OPEN <= b["et"].time() < MARKET_CLOSE]
    post_bars = [b for b in annotated if b["et"].time() >= MARKET_CLOSE]

    # ── Data cleanup: clamp bad wicks on RTH + premarket + after-hours ────
    # Premarket and after-hours have a heavier tail of bad wicks than RTH
    # (premarket max 1.55% / post max 7.50% vs RTH 0.93%, all vs median
    # ~0.05–0.11%), so they get a TIGHTER threshold (3×median) than RTH
    # (5×median). The median for each group is computed independently from
    # that group's bars so an outlier-heavy premarket/post can't drag the
    # RTH baseline around.
    # Premarket/post cleanup does NOT affect OR-window detection because
    # the OR window only considers bars where et.time() >= MARKET_OPEN.
    def clamp_bad_wicks(bars, threshold):
        if not bars:
            return 0
        ranges = [b["high"] - b["low"] for b in bars]
        sorted_ranges = sorted(ranges)
        n = len(sorted_ranges)
        median_range = (
            sorted_ranges[n // 2]
            if n % 2
            else (sorted_ranges[n // 2 - 1] + sorted_ranges[n // 2]) / 2
        )
        if median_range <= 0:
            return 0
        cutoff = threshold * median_range
        cleaned = 0
        for b in bars:
            if b["high"] - b["low"] > cutoff:
                body_high = max(b["open"], b["close"])
                body_low = min(b["open"], b["close"])
                new_high = body_high + median_range
                new_low = body_low - median_range
                # Only reduce, never expand. (Pathological bars where the body
                # is pinned to one extreme — e.g. body_low == bar.low — may not
                # shrink here because new_low ends up below the existing low;
                # accepted as a known limitation. See result-05 file.)
                b["high"] = min(b["high"], round(new_high, 4))
                b["low"] = max(b["low"], round(new_low, 4))
                cleaned += 1
        return cleaned

    cleaned_rth = clamp_bad_wicks(rth_bars_all, threshold=5.0)
    cleaned_pre = clamp_bad_wicks(premarket, threshold=3.0)
    cleaned_post = clamp_bad_wicks(post_bars, threshold=3.0)
    if cleaned_rth or cleaned_pre or cleaned_post:
        day_key_log = annotated[0]["et"].strftime("%Y-%m-%d")
        print(
            f"  [{day_key_log}] cleaned {cleaned_rth} RTH + {cleaned_pre} premarket + {cleaned_post} post bars"
        )

    if not or_window:
        return None

    or_high = round(max(b["high"] for b in or_window), 4)
    or_low = round(min(b["low"] for b in or_window), 4)

    # Detect breakout in rest_of_day (first bar to breach OR high/low)
    entry = None
    direction = None
    entry_bar = None
    for b in rest_of_day:
        if b["high"] > or_high and entry is None:
            entry = or_high
            direction = "long"
            entry_bar = b
            break
        elif b["low"] < or_low and entry is None:
            entry = or_low
            direction = "short"
            entry_bar = b
            break

    if entry is None or entry_bar is None:
        return None

    # ── Stop & target (3N from entry) ──
    if direction == "long":
        stop_price = or_low
        risk = entry - stop_price
        target_price = entry + 3 * risk
    else:
        stop_price = or_high
        risk = stop_price - entry
        target_price = entry - 3 * risk

    # ── Scan forward through RTH bars for target / stop / eod exit ──
    rth_bars = [b for b in rth_bars_all if b["ts"] >= entry_bar["ts"]]
    if not rth_bars:
        return None

    exit_price = None
    exit_bar = None
    exit_reason = "eod"
    for b in rth_bars:
        if direction == "long":
            hit_target = b["high"] >= target_price
            hit_stop = b["low"] <= stop_price
        else:
            hit_target = b["low"] <= target_price
            hit_stop = b["high"] >= stop_price
        if hit_target and hit_stop:
            # Both in same bar — conservative: assume stop (worst case fill)
            exit_price = stop_price
            exit_bar = b
            exit_reason = "stop"
            break
        if hit_target:
            exit_price = target_price
            exit_bar = b
            exit_reason = "target"
            break
        if hit_stop:
            exit_price = stop_price
            exit_bar = b
            exit_reason = "stop"
            break

    if exit_price is None:
        # Neither target nor stop hit — exit at EOD close
        eod_bar = rth_bars_all[-1]
        exit_price = eod_bar["close"]
        exit_bar = eod_bar
        exit_reason = "eod"

    if direction == "long":
        pnl_pct = round((exit_price - entry) / entry * 100, 2)
        pnl = round(exit_price - entry, 2)
    else:
        pnl_pct = round((entry - exit_price) / entry * 100, 2)
        pnl = round(entry - exit_price, 2)

    # MFE / MAE — restrict to bars from entry up to (and including) the exit bar
    if exit_bar is not None:
        post_entry = [b for b in rth_bars if b["ts"] <= exit_bar["ts"]]
    else:
        post_entry = rth_bars
    if direction == "long":
        mfe = round(max(b["high"] for b in post_entry) - entry, 2) if post_entry else 0
        mae = round(entry - min(b["low"] for b in post_entry), 2) if post_entry else 0
    else:
        mfe = round(entry - min(b["low"] for b in post_entry), 2) if post_entry else 0
        mae = round(max(b["high"] for b in post_entry) - entry, 2) if post_entry else 0

    exit_ts = exit_bar["ts"] if exit_bar is not None else rth_bars_all[-1]["ts"]
    exit_et = exit_bar["et"] if exit_bar is not None else rth_bars_all[-1]["et"]

    # Build all bars for charting (premarket + RTH)
    all_bars = []
    for b in annotated:
        all_bars.append({
            "time": b["ts"],
            "open": b["open"],
            "high": b["high"],
            "low": b["low"],
            "close": b["close"],
            "volume": b["volume"],
            "et": b["et"].strftime("%H:%M"),
            "session": "pre" if b["et"].time() < MARKET_OPEN else ("rth" if b["et"].time() < MARKET_CLOSE else "post"),
        })

    day_key = annotated[0]["et"].strftime("%a %b %d, %Y")

    return {
        "day": day_key,
        "date": annotated[0]["et"].strftime("%Y-%m-%d"),
        "or_high": or_high,
        "or_low": or_low,
        "or_minutes": or_minutes,
        "entry": round(entry, 4),
        "exit": round(exit_price, 4),
        "direction": direction,
        "entry_time": entry_bar["et"].strftime("%H:%M"),
        "entry_ts": entry_bar["ts"],
        "exit_time": exit_et.strftime("%H:%M"),
        "exit_ts": exit_ts,
        "stop_price": round(stop_price, 4),
        "target_price": round(target_price, 4),
        "exit_reason": exit_reason,
        "pnl_pct": pnl_pct,
        "pnl": pnl,
        "mfe": mfe,
        "mae": mae,
        "bars": all_bars,
    }


def _clamp_wicks_for_session(bars: list[dict], session: str) -> int:
    """Mirror of the inline clamp_bad_wicks thresholds in run_orb_for_day().
    Returns number of bars cleaned. RTH=5x median, premarket/post=3x median.
    Used on the 1m parallel-fetch path so client-side aggregation starts from
    clean data without re-running the per-trade pipeline.
    """
    if not bars:
        return 0
    threshold = 5.0 if session == "rth" else 3.0
    ranges = [b["high"] - b["low"] for b in bars]
    sorted_ranges = sorted(ranges)
    n = len(sorted_ranges)
    if n == 0:
        return 0
    median_range = (
        sorted_ranges[n // 2]
        if n % 2
        else (sorted_ranges[n // 2 - 1] + sorted_ranges[n // 2]) / 2
    )
    if median_range <= 0:
        return 0
    cutoff = threshold * median_range
    cleaned = 0
    for b in bars:
        if b["high"] - b["low"] > cutoff:
            body_high = max(b["open"], b["close"])
            body_low = min(b["open"], b["close"])
            new_high = body_high + median_range
            new_low = body_low - median_range
            b["high"] = min(b["high"], round(new_high, 4))
            b["low"] = max(b["low"], round(new_low, 4))
            cleaned += 1
    return cleaned


def _fetch_1m_bars_safe(symbol: str, days: int) -> list[dict]:
    """Best-effort fetch of 1m bars for the most recent N days. Yahoo 422s on
    ranges beyond ~7 days for 1m intervals — wrap the call so the main
    backtest response is never blocked. Returns [] on any failure.
    """
    try:
        # Yahoo 1m limit is ~7 calendar days of history. We always cap at 7
        # to avoid 422s — fetch_raw_intraday's own buffer logic goes much
        # further back, which trips Yahoo's 1m window check. Pin period1
        # to exactly 7 days before now.
        import time as _t
        now_ts = int(_t.time())
        period1 = now_ts - 7 * 86400
        period2 = now_ts
        params = {
            "interval": "1m",
            "period1": str(period1),
            "period2": str(period2),
            "includePrePost": "true",
        }
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{urllib.parse.quote(symbol.strip().upper())}?"
            f"{urllib.parse.urlencode(params)}"
        )
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 lightweight-yahoo-chart/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        result = (payload.get("chart", {}) or {}).get("result") or []
        if not result:
            return []
        node = result[0]
        timestamps = node.get("timestamp") or []
        quote = (node.get("indicators", {}).get("quote") or [{}])[0]
        bars = []
        for idx, ts in enumerate(timestamps):
            try:
                o = quote["open"][idx]
                h = quote["high"][idx]
                l = quote["low"][idx]
                c = quote["close"][idx]
                v = quote["volume"][idx]
            except (KeyError, IndexError):
                continue
            if None in (o, h, c, l):
                continue
            bars.append({
                "ts": int(ts),
                "open": round(float(o), 4),
                "high": round(float(h), 4),
                "low": round(float(l), 4),
                "close": round(float(c), 4),
                "volume": int(v or 0),
            })
        return bars
    except Exception as exc:
        print(f"  [1m] fetch failed for {symbol}: {exc!r}")
        return []


def compute_orb(symbol: str, or_minutes: int, days: int, interval: str = "5m") -> dict:
    """Full ORB run across N trading days."""
    raw = fetch_raw_intraday(symbol, interval, days)

    # ── Parallel 1m fetch (best-effort) ─────────────────────────────────
    # Yahoo returns 422 for 1m queries spanning >~7 days. Try anyway with a
    # capped window so the client has full-resolution bars to aggregate from.
    # If the call fails for any reason (422, network, parse), the main
    # response proceeds unchanged and `bars_1m` is simply omitted from each
    # trade — the client falls back to the requested interval.
    raw_1m = _fetch_1m_bars_safe(symbol, days)
    bars_1m_by_day: dict[str, list[dict]] = {}
    if raw_1m:
        # Apply per-session clamp to the 1m bars (same thresholds as the
        # 5m path) before attaching them. Group by ET day for direct lookup.
        for bar in raw_1m:
            et_dt = dt.datetime.fromtimestamp(bar["ts"], tz=ET)
            session = (
                "pre" if et_dt.time() < MARKET_OPEN
                else ("rth" if et_dt.time() < MARKET_CLOSE else "post")
            )
            bar["_session"] = session
        grouped_1m = group_by_et_day(raw_1m)
        for day_key, day_bars in grouped_1m.items():
            pre = [b for b in day_bars if b["_session"] == "pre"]
            rth = [b for b in day_bars if b["_session"] == "rth"]
            post = [b for b in day_bars if b["_session"] == "post"]
            _clamp_wicks_for_session(pre, "pre")
            _clamp_wicks_for_session(rth, "rth")
            _clamp_wicks_for_session(post, "post")
            # Strip the _session marker before serialization (purely internal)
            for b in day_bars:
                b.pop("_session", None)
            bars_1m_by_day[day_key] = [
                {
                    "time": b["ts"],
                    "open": b["open"],
                    "high": b["high"],
                    "low": b["low"],
                    "close": b["close"],
                    "volume": b["volume"],
                    "et": dt.datetime.fromtimestamp(b["ts"], tz=ET).strftime("%H:%M"),
                    "session": (
                        "pre" if dt.datetime.fromtimestamp(b["ts"], tz=ET).time() < MARKET_OPEN
                        else ("rth" if dt.datetime.fromtimestamp(b["ts"], tz=ET).time() < MARKET_CLOSE else "post")
                    ),
                }
                for b in day_bars
            ]

    grouped = group_by_et_day(raw)

    # Filter: only days that have RTH bars (skip weekends/holidays with no data)
    valid_days = []
    for day_key, day_bars in sorted(grouped.items(), reverse=True):
        et_dts = [dt.datetime.fromtimestamp(b["ts"], tz=ET) for b in day_bars]
        has_rth = any(MARKET_OPEN <= d.time() < MARKET_CLOSE for d in et_dts)
        if not has_rth:
            continue
        valid_days.append((day_key, day_bars))

    # Limit to requested number of days
    valid_days = valid_days[:days]

    trades = []
    skipped = 0
    for day_key, day_bars in valid_days:
        result = run_orb_for_day(day_bars, or_minutes)
        if result:
            trades.append(result)
        else:
            skipped += 1

    # Attach bars_1m (per trade day) if the parallel fetch produced any data.
    # Look up by the trade's date string ("YYYY-MM-DD") — that matches the
    # ET-day key the parallel fetch grouped by.
    bars_1m_trade_count = 0
    if bars_1m_by_day:
        for trade in trades:
            day_bars_1m = bars_1m_by_day.get(trade["date"])
            if day_bars_1m:
                trade["bars_1m"] = day_bars_1m
                bars_1m_trade_count += 1
        if bars_1m_trade_count:
            print(
                f"  [1m] attached bars_1m to {bars_1m_trade_count}/{len(trades)} trades"
            )

    # Summary stats
    total_pnl = sum(t["pnl"] for t in trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    longs = [t for t in trades if t["direction"] == "long"]
    shorts = [t for t in trades if t["direction"] == "short"]
    target_exits = sum(1 for t in trades if t.get("exit_reason") == "target")
    stop_exits = sum(1 for t in trades if t.get("exit_reason") == "stop")
    eod_exits = sum(1 for t in trades if t.get("exit_reason") == "eod")

    summary = {
        "symbol": symbol,
        "or_minutes": or_minutes,
        "interval": interval,
        "bars_1m_available": bars_1m_trade_count > 0,
        "bars_1m_trade_count": bars_1m_trade_count,
        "total_days": len(valid_days),
        "trade_days": len(trades),
        "skipped_days": skipped,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(total_pnl / len(trades), 2) if trades else 0,
        "avg_win": round(sum(t["pnl"] for t in wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0,
        "long_count": len(longs),
        "short_count": len(shorts),
        "target_exits": target_exits,
        "stop_exits": stop_exits,
        "eod_exits": eod_exits,
        "best_trade": max((t["pnl"] for t in trades), default=0),
        "worst_trade": min((t["pnl"] for t in trades), default=0),
    }

    return {"summary": summary, "trades": trades}


def yahoo_bars_before(symbol: str, before: str, interval: str, count: int) -> dict:
    symbol, base_interval, aggregate_factor = validate_symbol_interval(symbol, interval)
    count = max(20, min(int(count or 200), 2000))
    period2 = parse_before(before, interval)
    # Ask for a wider calendar window than count because markets have nights,
    # weekends, holidays, and intraday sessions are sparse.
    seconds = INTERVAL_SECONDS.get(interval, 86400)
    widen = 4 if interval in {"1d", "1wk", "1mo", "1y"} else 8
    period1 = max(0, period2 - (seconds * count * widen))
    payload = yahoo_request(symbol, interval, {"period1": period1, "period2": period2}, chart_range=None)
    bars = payload["bars"]
    # `period2` is exclusive-ish, but protect against duplicate first bar.
    if bars:
        if isinstance(bars[0]["time"], str):
            bars = [b for b in bars if b["time"] < before]
        else:
            bars = [b for b in bars if int(b["time"]) < period2]
    payload["bars"] = bars[-count:]
    payload["before"] = before
    payload["requestedCount"] = count
    payload["range"] = "page"
    return payload


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib override name
        print(f"{self.address_string()} - {format % args}")

    def send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/screenshot":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            data_url = body.get("dataUrl", "")
            if not data_url.startswith("data:image/png;base64,"):
                raise ValueError("Expected PNG data URL")
            raw = base64.b64decode(data_url.split(",", 1)[1])
            out_dir = ROOT / "screenshots"
            out_dir.mkdir(exist_ok=True)
            filename = f"lightweight-yahoo-chart-{int(time.time())}.png"
            out_path = out_dir / filename
            out_path.write_bytes(raw)
            self.send_json(200, {"path": str(out_path), "bytes": len(raw)})
        except Exception as exc:
            self.send_json(400, {"error": str(exc)})

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/bars":
            query = urllib.parse.parse_qs(parsed.query)
            symbol = query.get("symbol", ["AAPL"])[0]
            chart_range = query.get("range", ["1y"])[0]
            interval = query.get("interval", ["1d"])[0]
            before = query.get("before", [None])[0]
            count = int(query.get("count", ["200"])[0])
            try:
                if before:
                    self.send_json(200, yahoo_bars_before(symbol, before, interval, count))
                else:
                    self.send_json(200, yahoo_bars(symbol, chart_range, interval))
            except Exception as exc:  # small demo: keep message useful in UI
                self.send_json(400, {"error": str(exc)})
            return

        if parsed.path == "/api/orb":
            query = urllib.parse.parse_qs(parsed.query)
            symbol = query.get("symbol", ["SPY"])[0]
            or_minutes = int(query.get("or", ["15"])[0])
            days = int(query.get("days", ["20"])[0])
            interval = query.get("interval", ["5m"])[0]
            try:
                result = compute_orb(symbol, or_minutes, days, interval)
                self.send_json(200, result)
            except Exception as exc:
                self.send_json(400, {"error": str(exc)})
            return

        rel = "index.html" if parsed.path in ("/", "") else parsed.path.lstrip("/")
        path = (ROOT / rel).resolve()
        if ROOT not in path.parents and path != ROOT:
            self.send_error(403)
            return
        if not path.exists() or path.is_dir():
            self.send_error(404)
            return
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "8765"))
    host = os.environ.get("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Lightweight Yahoo chart: http://{host}:{port}")
    server.serve_forever()
