# Issue 05 — After-Hours Bad-Wick Cleanup

## Problem

After-hours wicks are also blowing up the chart scale. The y-axis gets stretched by 1-3% outliers in after-hours bars, making the RTH bars look flat.

Same probe (fresh `/api/orb` fetch):
- POST max: 1.583% (likely culprit — 1 of the 5 days)
- POST median: 0.04%
- POST n: 18 bars

RTH (unchanged): max 0.920%, median 0.11% — fine.
PRE (post-Issue 04): max 0.514% — fine.

OR-detection is unaffected: OR is computed from bars where `MARKET_OPEN <= et.time() < OR_END`, which never includes after-hours.

## What to do

Apply the **same post-Issue 04 premarket cleanup logic** to after-hours bars in `server.py`:

1. Find the existing `clamp_bad_wicks(bars, threshold)` helper (added in Issue 04 — handles RTH + premarket).
2. Add a third call: `after_hours_cleaned, ah_cleaned = clamp_bad_wicks(post_bars, threshold=3)` (or whatever the helper returns).
3. Premarket threshold: 3× median (separate from RTH's 5×).
4. After-hours threshold: **3× median** (separate from RTH's 5× AND premarket's 3× — same as premarket since both are extended-hours segments with sparse liquidity).

Wait — re-read helper signature. It probably returns `(cleaned_bars, count_cleaned)`. Match whatever the Issue 04 worker shipped.

5. Update log line to: `cleaned N RTH + M premarket + K post bars`
6. Build final bar list: `rth_cleaned + pre_cleaned + post_cleaned` (sorted by timestamp, deduplicated).
7. Update the probe endpoint (`/api/probe` if it exists, or however you'd query) so after-hours bars show in stats with the new cleanup applied.

## Files

- `server.py` — extend cleanup pass
- ONLY `server.py` — no UI changes (premarket overlay doesn't need an after-hours overlay; the BG toggle stays 4 colors).

## Restart

After server.py changes:
```bash
kill $(lsof -t -iTCP:8765 -sTCP:LISTEN) 2>/dev/null
PYTHONUNBUFFERED=1 nohup python3 -u server.py > /tmp/lightweight-yahoo-chart.log 2>&1 &
sleep 3
lsof -iTCP:8765 -sTCP:LISTEN   # confirm rebound
```

## Verification

1. `python3 -m py_compile server.py` — must pass
2. `curl -s 'http://100.120.135.5:8765/api/orb?...' -o /tmp/orb_now.json` — note timestamp on file
3. Probe the JSON: POST max should be **< 0.5%** (target ~0.3%), POST median unchanged
4. Verify trade count = 5 (no regression)
5. Verify exit breakdown (1t/2s/2e) unchanged
6. `diff /tmp/orb_now.json /tmp/orb_pm.json` — only the after-hours bars should differ from the post-Issue-04 fetch
7. Screenshot `curl -s 'http://100.120.135.5:8765/api/screenshot?...'` — actually no, screenshot may not be set up. Just do a browser verify: open `/orb.html?debug=1` and confirm charts render with visible y-axis room around RTH bars (not stretched to after-hours extremes).
8. Write result file to `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/.hermes/worker-prompts/result-05-afterhours-cleanup.md` with before/after numbers and diff evidence.

## Constraints

- MiniMax-M3 workers cap at 600s. This is a small slice — should be 60-120s.
- Don't touch `orb.html`, `index.html`, `das-overlay.js`, `bg-sketches.html`.
- Don't change RTH threshold or premarket threshold.

## DO NOT fabricate success.

Real numbers from the probe must appear in the result file with path to fresh JSON.
