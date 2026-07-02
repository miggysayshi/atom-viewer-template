# Issue 05 — After-Hours Bad-Wick Cleanup

## Summary

After-hours bars had the same problem premarket had: bad wicks stretching the chart's y-axis. The RTH clamping from Issue 04 (5× median) and premarket clamping (3× median) did not extend to after-hours. Added a third call to the existing `clamp_bad_wicks` helper, with `threshold=3.0` (matching premarket, since both are extended-hours sessions with sparse liquidity).

- **5-day POST max**: **7.4478% → 0.3767%** (19.8× reduction, well under the 0.5% target; close to the ~0.3% goal)
- **5-day POST median**: **0.0564% → 0.0564%** (preserved — only the tail was touched, not the body)
- **5-day POST p99**: **6.6942% → 0.3747%** (18× reduction)
- **20-day POST max**: **7.4970% → 1.6840%** (4.5× reduction; see "Residual" below for why the 20-day number is higher than the 5-day number)
- **RTH untouched**: identical values before/after (independent median computation verified)
- **Premarket untouched**: identical values before/after (the new post-bars list is separate from `premarket`)
- **OR-window detection unaffected**: 5/5 trade count + 1t/2s/2e exit breakdown unchanged in 5-day window; 20/20 trades + identical summary in 20-day window

## Files modified

| File | Change |
|---|---|
| `/Users/cynthia/backtesting-software/lightweight-yahoo-chart/server.py` | Added `post_bars` partition alongside `premarket` and `rth_bars_all`. Added `cleaned_post = clamp_bad_wicks(post_bars, threshold=3.0)` after the premarket call. Updated the log condition and format string to include the new count. Updated the section comment. **+9 lines net** (1 partition + 1 call + log condition + comment expansion). |

Untouched (as instructed): `orb.html`, `index.html`, `das-overlay.js`, `bg-sketches.html`.

## Verification

### 1. `python3 -m py_compile server.py` — must pass

```text
$ python3 -m py_compile /Users/cynthia/backtesting-software/lightweight-yahoo-chart/server.py
$ echo $?
0
```

Exit code: **0**.

### 2. Server restart on :8765

```bash
kill $(lsof -t -iTCP:8765 -sTCP:LISTEN) 2>/dev/null; sleep 1
PYTHONUNBUFFERED=1 python3 -u server.py > /tmp/lightweight-yahoo-chart.log 2>&1 &
sleep 3
lsof -iTCP:8765 -sTCP:LISTEN
```

Live lsof output (post-restart with patched code, PID 14496):

```text
COMMAND   PID    USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
Python  14496 cynthia    4u  IPv4 0x1496464586f95e83      0t0  TCP *:ultraseek-http (LISTEN)
```

HTTP 200 health check: `curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8765/` → `HTTP 200`.

### 3. POST max BEFORE vs AFTER (the proof)

Baseline fetches were taken with the post-Issue-04 (pre-Issue-05) code running on the same port, then the patched code was re-run for the AFTER fetch. All fetches used `http://100.120.135.5:8765/api/orb?symbol=SPY&or=15&days=N&interval=5m`.

#### 5-day window (matches the brief's "5 days" framing)

| Metric | BEFORE (post-Issue-04) | AFTER (post-Issue-05) | Change |
|---|---|---|---|
| POST n | 192 | 192 | (same bars, just clamped) |
| POST min | 0.0068% | 0.0068% | unchanged |
| POST **median** | 0.0564% | 0.0564% | **unchanged (only tail touched)** |
| POST p90 | 0.5076% | 0.1278% | -75% |
| POST p95 | 1.1684% | 0.1703% | -85% |
| POST p99 | 6.6942% | 0.3747% | **-94%** |
| POST **max** | **7.4478%** | **0.3767%** | **-95% (19.8× reduction)** |
| PRE max | 0.3746% | 0.3746% | unchanged |
| RTH max | 0.7540% | 0.7540% | unchanged |
| trades returned | 5 | 5 | identical |
| exit breakdown | 1t/2s/2e | 1t/2s/2e | identical |

The brief's target was "<0.5% (target ~0.3%)". Achieved **0.3767%** on the 5-day window — under target.

#### 20-day window (broader, used to compute trade-count regression check)

| Metric | BEFORE (post-Issue-04) | AFTER (post-Issue-05) | Change |
|---|---|---|---|
| POST n | 912 | 912 | (same bars, just clamped) |
| POST **median** | 0.0519% | 0.0517% | **unchanged (only tail touched)** |
| POST p99 | 5.7936% | 0.2662% | **-95%** |
| POST **max** | **7.4970%** | **1.6840%** | **-78% (4.5× reduction)** |
| PRE max | 0.5142% | 0.5142% | unchanged |
| RTH max | 0.9285% | 0.9285% | unchanged |
| trades returned | 20 | 20 | identical |
| exit breakdown | 2t/11s/7e | 2t/11s/7e | identical |
| summary | identical | identical | (wins/losses/PnL/avg/best/worst all match) |

### 4. POST max BEFORE vs AFTER (the headline number the brief asked for)

```text
POST max BEFORE (post-Issue-04, pre-Issue-05): 7.4970%
POST max AFTER  (post-Issue-05):              1.6840%
Reduction: 5.8129%  (77.5% decrease)
```

The brief mentioned `1.583%` as the BEFORE value with `n=18` POST bars, suggesting a probe was taken on a narrower window (perhaps 1 day or only the most recent 5 days using a different interval). On every window I can reproduce (5d, 20d), the BEFORE POST max is dominated by 5–7% outliers on 2026-06-09/10/11/16/24 — well above 1.5%. The AFTER value (1.6840% on 20d, 0.3767% on 5d) is dramatically lower regardless of which BEFORE figure is used.

### 5. Trade count + exit breakdown unchanged (5-day)

The brief specifies `1t/2s/2e` (1 target, 2 stop, 2 eod) as the expected outcome. Verified on the 5-day window:

| | BEFORE | AFTER |
|---|---|---|
| trade count | 5 | 5 |
| exit reasons | 1t / 2s / 2e | 1t / 2s / 2e |
| per-day detail | 06-30 target, 06-29 stop, 06-26 eod, 06-25 eod, 06-24 stop | identical |

OR-window detection is computed from `or_window = [b for b in annotated if MARKET_OPEN <= b["et"].time() < or_end_time]`, which never includes after-hours. The clamp modifies the same `annotated` dicts in place (like premarket and RTH), but only affects `bars` rendered in the `session == "post"` bucket of the chart. Entry/exit decisions are unchanged.

### 6. Diff `/tmp/orb_now.json` vs `/tmp/orb_20d_before.json` — only POST bars differ

```text
PRE:  1260 unchanged, 0 changed
RTH:  1540 unchanged, 1 changed    ← single live-tick artifact (see note)
POST: 782 unchanged, 130 changed   ← 130 POST bars clamped, all others untouched
```

The 1 RTH bar that differs is `2026-06-30 14:18` (high/low changed from 746.7600 → 746.8100) — this is a still-forming live 5-minute bar whose OHLC updated between the two fetches (~48 seconds apart). It is not a clamp-induced change: the RTH clamp logic was not modified, and the per-day RTH cleanup log line is identical between the two runs (`0 RTH + N premarket + K post bars` → RTH count is `0` for 06-30, matching).

### 7. Cleanup log line format (new)

Sample from `/tmp/lightweight-yahoo-chart.log`:

```text
[2026-06-30] cleaned 0 RTH + 2 premarket + 0 post bars
[2026-06-29] cleaned 1 RTH + 5 premarket + 8 post bars
[2026-06-26] cleaned 1 RTH + 6 premarket + 10 post bars
[2026-06-25] cleaned 0 RTH + 5 premarket + 5 post bars
[2026-06-24] cleaned 0 RTH + 3 premarket + 11 post bars
[2026-06-23] cleaned 0 RTH + 5 premarket + 7 post bars
[2026-06-22] cleaned 0 RTH + 6 premarket + 5 post bars
[2026-06-18] cleaned 0 RTH + 4 premarket + 8 post bars
[2026-06-17] cleaned 1 RTH + 2 premarket + 11 post bars
[2026-06-16] cleaned 0 RTH + 2 premarket + 7 post bars
[2026-06-15] cleaned 0 RTH + 4 premarket + 7 post bars
[2026-06-12] cleaned 0 RTH + 4 premarket + 7 post bars
[2026-06-11] cleaned 0 RTH + 8 premarket + 9 post bars
[2026-06-10] cleaned 0 RTH + 5 premarket + 4 post bars
[2026-06-09] cleaned 0 RTH + 5 premarket + 5 post bars
[2026-06-08] cleaned 0 RTH + 8 premarket + 2 post bars
[2026-06-05] cleaned 0 RTH + 9 premarket + 10 post bars
[2026-06-04] cleaned 0 RTH + 4 premarket + 4 post bars
[2026-06-03] cleaned 0 RTH + 5 premarket + 12 post bars
[2026-06-02] cleaned 0 RTH + 6 premarket + 1 post bars
```

Format string: `cleaned {rth} RTH + {pre} premarket + {post} post bars` — exactly matches the brief's "cleaned N RTH + M premarket + K post bars" spec.

### 8. Fresh `/api/orb` output (proof artifact)

```text
$ stat -f "Modified: %Sm  Size: %z bytes  Path: %N" /tmp/orb_now.json
Modified: Jun 30 11:21:49 2026  Size: 510095 bytes  Path: /tmp/orb_now.json
```

Absolute path: **`/tmp/orb_now.json`** (510,095 bytes, fetched 2026-06-30 11:21:49 ET against `http://100.120.135.5:8765/api/orb?symbol=SPY&or=15&days=20&interval=5m`).

Pre-Issue-05 baseline fetches (preserved for diff):
- `/tmp/orb_5d_before.json` (5-day, post-Issue-04, pre-Issue-05 baseline)
- `/tmp/orb_20d_before.json` (20-day, post-Issue-04, pre-Issue-05 baseline)

Post-Issue-05 fetches:
- `/tmp/orb_5d_now.json` (5-day, post-Issue-05)
- `/tmp/orb_now.json` (20-day, post-Issue-05) ← **proof artifact**

## Residual: why the 20-day POST max is 1.68% (not <0.5%)

On the 20-day view the worst residual is a single bar: `2026-06-11 16:40` with `open=737.67, high=737.7088, low=725.4914, close=725.4914`. The body_low equals the bar's low (close == low == 725.49). The clamp formula computes:

```
new_low = body_low - median = 725.4914 - 0.3685 = 725.1229
new_high = body_high + median = 737.67 + 0.3685 = 738.0385
```

The "only reduce, never expand" guard then does:

```
b["high"] = min(737.7088, 738.0385) = 737.7088  (no change, high already < new_high)
b["low"]  = max(725.4914, 725.1229) = 725.4914  (no change, low already > new_low)
```

The clamp cannot compress a bar whose body extends to the same low as the bar's low — the algorithm has nothing left to pull in from below. This is a fundamental limitation of the "min/max" clamp, not a regression. The 5-day window doesn't include 2026-06-11, so the 5-day max reaches 0.3767% (well under target).

If we ever want to push the 20-day POST max below 1%, the next step would be a "body-aware" clamp that recognizes `open==low` and `close==low` patterns as likely bad ticks even when the body is already pinned at the bar extremes. That's out of scope for Issue 05 — the brief's target was <0.5% on the 5-day window, which is met.

## Implementation notes

### server.py — diff (the actual change)

```diff
@@ -291,14 +291,17 @@
     or_window = [b for b in annotated if MARKET_OPEN <= b["et"].time() < or_end_time]
     rest_of_day = [b for b in annotated if b["et"].time() >= or_end_time]
     rth_bars_all = [b for b in annotated if MARKET_OPEN <= b["et"].time() < MARKET_CLOSE]
-    
-    # ── Data cleanup: clamp bad wicks on RTH + premarket bars ─────────────
-    # Premarket has a heavier tail of bad wicks (max 1.55% vs median 0.05%),
-    # so it gets a TIGHTER threshold (3×median) than RTH (5×median). The
-    # median for each group is computed independently from that group's bars
-    # so an outlier-heavy premarket can't drag the RTH baseline around.
-    # Premarket cleanup does NOT affect OR-window detection because the OR
-    # window only considers bars where et.time() >= MARKET_OPEN.
+    post_bars = [b for b in annotated if b["et"].time() >= MARKET_CLOSE]
+
+    # ── Data cleanup: clamp bad wicks on RTH + premarket + after-hours ────
+    # Premarket and after-hours have a heavier tail of bad wicks than RTH
+    # (premarket max 1.55% / post max 7.50% vs RTH 0.93%, all vs median
+    # ~0.05–0.11%), so they get a TIGHTER threshold (3×median) than RTH
+    # (5×median). The median for each group is computed independently from
+    # that group's bars so an outlier-heavy premarket/post can't drag the
+    # RTH baseline around.
+    # Premarket/post cleanup does NOT affect OR-window detection because
+    # the OR window only considers bars where et.time() >= MARKET_OPEN.
     def clamp_bad_wicks(bars, threshold):
@@ -331,10 +334,11 @@
 
     cleaned_rth = clamp_bad_wicks(rth_bars_all, threshold=5.0)
     cleaned_pre = clamp_bad_wicks(premarket, threshold=3.0)
-    if cleaned_rth or cleaned_pre:
+    cleaned_post = clamp_bad_wicks(post_bars, threshold=3.0)
+    if cleaned_rth or cleaned_pre or cleaned_post:
         day_key_log = annotated[0]["et"].strftime("%Y-%m-%d")
         print(
-            f"  [{day_key_log}] cleaned {cleaned_rth} RTH + {cleaned_pre} premarket bad-wick bars"
+            f"  [{day_key_log}] cleaned {cleaned_rth} RTH + {cleaned_pre} premarket + {cleaned_post} post bars"
         )
```

### Design decisions

1. **Threshold of 3× median for post_bars** — matches premarket. The brief notes both are extended-hours segments with sparse liquidity, so they get the tighter clamp.
2. **Independent median per group** — `clamp_bad_wicks` always computes the median of its own input bars. RTH (5×) baseline is not contaminated by post outliers, premarket (3×) is not contaminated by post outliers, and post (3×) is not contaminated by premarket outliers.
3. **In-place mutation of the same `annotated` dicts** — consistent with the existing RTH and premarket code. The chart builder (line 433-445) reads `b["high"]/b["low"]` from these same dicts, so the cleanup propagates to the rendered bars without a separate "cleaned" array.
4. **No new endpoint** — `/api/probe` was mentioned in the brief but doesn't exist in the codebase; the verification was done by direct probe of the JSON response, which is what the brief actually requires (POST max BEFORE/AFTER + path to fresh JSON).
5. **Comment updated** — section header is now "RTH + premarket + after-hours", and the rationale block now explains the dual extended-hours treatment.

### Untouched invariants (verified by diff)

- `rth_bars_all` partition (line 293): unchanged
- `clamp_bad_wicks` helper (lines 305-330): unchanged
- `cleaned_rth = clamp_bad_wicks(rth_bars_all, threshold=5.0)`: unchanged
- `cleaned_pre = clamp_bad_wicks(premarket, threshold=3.0)`: unchanged
- All OR-window / entry / stop / target logic: unchanged
- `orb.html` / `index.html` / `das-overlay.js` / `bg-sketches.html`: not modified

## Acceptance checklist

- [x] server.py compiles (`python3 -m py_compile` exit 0)
- [x] Server restarted and responds with HTTP 200
- [x] POST max reduced dramatically: 5d 7.4478% → 0.3767% (target <0.5%, achieved 0.3767%)
- [x] POST p99 reduced: 5d 6.6942% → 0.3747% (-94%)
- [x] POST median preserved: 5d 0.0564% → 0.0564% (only tail touched)
- [x] RTH stats unchanged (independent median computation verified)
- [x] Premarket stats unchanged (post_bars partition is independent of premarket)
- [x] All 5 (and 20) trades still produced (OR-window detection unaffected)
- [x] Cleanup log format matches spec: `cleaned N RTH + M premarket + K post bars`
- [x] Exit breakdown 1t/2s/2e unchanged on 5-day window
- [x] Diff confirms only POST bars changed (RTH delta is a single live-tick artifact)
- [x] Fresh `/api/orb` JSON at `/tmp/orb_now.json` (510,095 bytes, 11:21:49)
- [x] Did NOT touch orb.html, das-overlay.js, index.html, bg-sketches.html

## Issues encountered

**None blocking.** Two notes:

1. **Brief's stated BEFORE POST max of 1.583% with n=18 bars** didn't match any natural probe I could reproduce. My fetches show BEFORE POST max as 7.45% (5d) / 7.50% (20d) with n=192 / n=912 respectively. The AFTER numbers (5d 0.38%, 20d 1.68%) are dramatically lower than every plausible BEFORE figure, so the cleanup demonstrably works regardless of which BEFORE value the brief was anchored to. Reported the real numbers from the actual data instead of trying to back-fit to the brief's number.

2. **1.6840% residual on 20-day view** (one bar on 2026-06-11 16:40) is a clamp-algorithm limitation (body pinned to bar's low). The 5-day view (which is the window the brief anchored to) achieves 0.3767%, well under the 0.5% target. Noted in the "Residual" section above.
