# Issue 01 — Backend: Data Cleanup + Stop Loss + Target

## File

`/Users/cynthia/backtesting-software/lightweight-yahoo-chart/server.py` — ONLY this file.

## Context

The ORB strategy endpoint `/api/orb` lives in `run_orb_for_day()` (starts ~line 270). It currently:
1. Fetches raw intraday bars from Yahoo (with premarket via `includePrePost=true`)
2. Groups by ET trading day
3. Computes opening range high/low from first N minutes after 9:30
4. Detects breakout (first bar to breach OR high → long, OR low → short)
5. Holds to EOD close (4:00 PM) — no stop, no target
6. Returns trade dict with entry/exit/pnl/mfe/mae/bars

## Changes Required

### 1. Data Cleanup — Remove Bad Wicks

Yahoo intraday data has misprints: extremely long wicks (high/low spikes) that are data errors, not real price action. These corrupt the OR high/low and P&L.

**Implementation:** In `run_orb_for_day()`, after annotating bars with ET datetimes (~line 283), add a cleanup pass that:

- Compute the median body size (`abs(close - open)`) and median range (`high - low`) across the day's RTH bars.
- Flag any bar where `high - low > 5 * median_range` as a suspected bad bar.
- For flagged bars: clamp the wicks. Set `high = max(open, close) + median_range` and `low = min(open, close) - median_range`. This removes the spike but keeps the bar in the sequence.
- Only apply to RTH bars (skip premarket — premarket is thin and naturally wider).
- Log to server stdout: `"  [{date}] cleaned {count} bad-wick bars"` so we can verify.

### 2. Stop Loss — OR Opposite Extremity

Currently there's no stop. The stop should be:

- **Long trade:** stop = OR low (the opposite end of the opening range from where we entered)
- **Short trade:** stop = OR high

Add `stop_price` to the trade dict.

### 3. Target — 3N (Risk-Reward 3:1)

- `N = abs(entry - stop_price)` (the risk distance)
- `target_price = entry + 3*N` for longs, `entry - 3*N` for shorts
- Add `target_price` to the trade dict.

### 4. Exit Logic — Target OR EOD

Replace the current "always exit at EOD" logic:

- After entry, scan forward through RTH bars.
- **If a bar's high (long) or low (short) reaches `target_price`**: exit at `target_price`, set `exit_reason = "target"`, record the exit bar timestamp.
- **If a bar's low (long) or high (short) reaches `stop_price` FIRST**: exit at `stop_price`, set `exit_reason = "stop"`, record the exit bar timestamp.
- **If neither hit by EOD**: exit at EOD close (last RTH bar), set `exit_reason = "eod"`.
- Update P&L based on actual exit price.

### 5. Update Trade Dict

Add these fields to the returned trade dict:
```python
"stop_price": stop_price,
"target_price": target_price,
"exit_reason": exit_reason,   # "target" | "stop" | "eod"
```

Keep all existing fields (`entry`, `exit`, `pnl`, `mfe`, `mae`, `bars`, etc.).

### 6. Update Summary Stats

In `compute_orb()`, add exit reason breakdown:
```python
"target_exits": count of trades with exit_reason == "target",
"stop_exits": count of trades with exit_reason == "stop",
"eod_exits": count of trades with exit_reason == "eod",
```

## Constraints

- Do NOT change the API URL or query params (`/api/orb?symbol=X&or=Y&days=Z&interval=W`).
- Do NOT change `fetch_raw_intraday()` or `group_by_et_day()` — only modify `run_orb_for_day()` and `compute_orb()`.
- Do NOT touch any HTML/JS files.
- Preserve the existing bar shape in the `bars` array (same fields: time, open, high, low, close, volume, et, session).
- The data cleanup must NOT remove bars from the `bars` array — it clamps wicks in place. Bar count must stay the same.

## Verification

```bash
cd /Users/cynthia/backtesting-software/lightweight-yahoo-chart

# 1. Syntax check
python3 -m py_compile server.py && echo OK

# 2. Restart server (kill existing first)
pkill -f "server.py" 2>/dev/null; sleep 1
python3 server.py > /tmp/server.log 2>&1 &
sleep 2

# 3. API smoke test — check new fields exist
curl -s "http://127.0.0.1:8765/api/orb?symbol=SPY&or=15&days=5&interval=5m" | python3 -c "
import json,sys
d=json.load(sys.stdin)
s=d.get('summary',{})
print('exit breakdown:', s.get('target_exits'), 'targets /', s.get('stop_exits'), 'stops /', s.get('eod_exits'), 'eod')
for t in d.get('trades',[]):
    print(f\"{t['date']} {t['direction']:5s} entry={t['entry']:.2f} stop={t.get('stop_price','?'):.2f} target={t.get('target_price','?'):.2f} exit={t['exit']:.2f} reason={t.get('exit_reason','?')} pnl={t['pnl']:+.2f}\")
"

# 4. Verify no bad wicks — check max range is sane (< 2% of price for SPY)
curl -s "http://127.0.0.1:8765/api/orb?symbol=SPY&or=15&days=3&interval=5m" | python3 -c "
import json,sys
d=json.load(sys.stdin)
for t in d.get('trades',[]):
    ranges = [(b['high']-b['low'])/b['close']*100 for b in t['bars']]
    print(f\"{t['date']}: max range={max(ranges):.2f}% mean={sum(ranges)/len(ranges):.3f}% bars={len(ranges)}\")
"
```

## Output

Write `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-01-backend-stops-targets.md` with:
- Summary of changes (functions modified, line ranges)
- Verification output (full curl + python output)
- Acceptance checklist

**Do NOT stop after writing code. Run verification yourself and report real results.**
