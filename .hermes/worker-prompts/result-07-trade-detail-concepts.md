# Result 07 — Trade Detail Layout Concepts

10 distinct visual concepts for the data panel that goes **below each ORB chart card** on `orb.html`. All use the same SPY trade data (long, 15m ORB breakout, EOD scratch at -0.21R). All match the olive `#1a2018` background, orange `#ff682c` accent, and cyan/red direction palette from `orb.html`.

## Files

All 10 files live in `/tmp/`:

| # | Filename | Size |
|---|----------|------|
| 01 | `/tmp/concept-01-bloomberg-dense.html` | 7.6 KB |
| 02 | `/tmp/concept-02-card-sections.html` | 9.2 KB |
| 03 | `/tmp/concept-03-r-multiple-hero.html` | 6.9 KB |
| 04 | `/tmp/concept-04-horizontal-timeline.html` | 9.7 KB |
| 05 | `/tmp/concept-05-trade-journal.html` | 8.8 KB |
| 06 | `/tmp/concept-06-quant-table.html` | 10.4 KB |
| 07 | `/tmp/concept-07-mini-tiles.html` | 9.1 KB |
| 08 | `/tmp/concept-08-sparklines.html` | 12.8 KB |
| 09 | `/tmp/concept-09-risk-reward-gauge.html` | 10.7 KB |
| 10 | `/tmp/concept-10-vertical-timeline.html` | 11.7 KB |

Verification:
- All 10 files exist on disk (`ls /tmp/concept-*.html | wc -l` → 10)
- All 10 parse cleanly with `html.parser.HTMLParser`
- Concepts 02, 03, 08, 09, 10 spot-checked in browser — render without console errors
- All contain olive bg, orange accent, cyan/red direction colors, and the SPY trade data inline

## Comparison table

| # | Name | Layout | Density | Hero element | Visual technique |
|---|------|--------|---------|--------------|------------------|
| 01 | **Bloomberg Terminal Dense** | Single panel, 4-col grid | Dense | Sub-header row of 6 key stats | Monospace (JetBrains Mono), sectioned grid, color-coded deltas, ticker tape footer |
| 02 | **Card Sections** | Header strip + 4 labeled cards in 2×2 grid | Medium | R-multiple + duration + excursion + R:R hero strip | Rounded 12px borders, dot-icon section heads, hero stat strip on top, callout box at bottom |
| 03 | **R-Multiple Hero** | Header + huge R + 6-stat grid + footer | Spacious | **148px gradient R-multiple number** | Massive gradient text fill, tiny stop/entry/target meter, all other fields subordinated |
| 04 | **Horizontal Timeline** | Header + time-axis + 4-col grid + footer | Medium | **Entry → peak → trough → exit pins on a time ruler** | SVG time ruler with colored dot pins + stop/target lollipops, intraday hour ticks |
| 05 | **Trade Journal** | Masthead + verdict banner + serif narrative | Spacious | Drop-cap journal entry | Serif body (IBM Plex Serif), inline data callouts, drop-cap first letter, "Lesson" footer with tag |
| 06 | **Quant Table** | Status bar + toolbar + strict 25-row table + drawer | Very dense | Numbered row index + sort/filter/export affordances | Monospace, sticky header, sectioned `<tbody>`, section dividers, "selected" row highlight |
| 07 | **Mini Stat Tiles** | Header + 4-col tile grid (4 sections of 4 tiles) + footer | Spacious | Color-coded icon tiles | Material-style 32px icon badges, left accent bars, wide tiles for paired metrics, meta-row dividers |
| 08 | **Sparklines** | Header + featured price path + 5 metric rows with mini SVGs + footer | Medium | **Full-width featured intraday price chart with E/X markers** | Inline SVG path/area/bar sparklines per row, JetBrains Mono numerics, peak/trough dots |
| 09 | **Risk/Reward Gauge** | Header + horizontal price ladder + 4-stat grid + 3-check checklist | Medium | **Stop → Entry → Actual → Target pins on a horizontal price ladder** | Gradient track, dashed zone bands, glowing pin markers, color-coded ✓/!/× checklist |
| 10 | **Vertical Timeline** | Two-column: left summary / right chronological stack | Medium | **6-step timeline: Prep → Entry → MFE → MAE → Exit → Review** | Glowing circular nodes on gradient rail, color-coded step cards, post-trade review step |

## Axes varied across the 10

- **Layout**: single-panel grid (01, 06), header+cards (02, 07), hero+stats (03), timeline+stats (04, 09, 10), narrative (05), sparkline rows (08)
- **Density**: dense (01, 06) ↔ medium (02, 04, 07, 08, 09, 10) ↔ spacious (03, 05)
- **Hero emphasis**: P&L (07), R-multiple (03), execution (02, 04), time-in-trade (04, 10), price action (08, 09), reflection (05), raw data (01, 06)
- **Visualization**: pure numbers (01, 06), cards (02, 07), typography (03, 05), SVG sparklines (08, 04), price ladder (09), chronological stack (10)
- **Tone**: institutional (01, 06, 08), retail-friendly (02, 07), quant-research (08, 09), trader-journal (05, 10), hero-product (03), execution-focused (04)
- **Typography**: monospace only (01, 06), sans (02, 04, 07, 09, 10), serif narrative (05), mixed serif+sans (05), mixed sans+mono (08)

## Screenshot

The brief mentioned `http://100.120.135.5:8765/api/screenshot` — that endpoint does not exist on the local dev server (404 on all variations tried). Per the brief's "if it exists, otherwise skip" instruction, screenshots are skipped. Render verification was done via headless browser (selenium-like navigation + DOM queries confirming elements render) on concepts 02, 03, 08, 09, 10.

## Recommendation

**Prototype these 3 against the real chart in `orb.html`:**

### 1. **Concept 02 (Card Sections)** — primary candidate
- Most universally readable. Pairs naturally with the existing `orb.html` card structure (the `card-details` div on line 226 is already a 4-col grid — concept 02 is the obvious enrichment of that pattern).
- The "Execution / Risk / Result / Opening Range" framing maps 1:1 to how a trader thinks about a trade. Easy to scan.
- Header strip + 2×2 card grid is the most "shippable" layout for a v1.
- All numerics are tabular and color-coded; nothing requires explanation.

### 2. **Concept 09 (Risk/Reward Gauge)** — the differentiator
- Adds the most *new* information per pixel: the relationship between stop, entry, actual exit, and target is instantly readable as a horizontal ladder.
- The "achieved portion" of the bar visually encodes the trade outcome (orange band between actual and target) in a way no other concept does.
- For a trading tool, this is genuinely useful — most retail platforms just dump numbers; the gauge turns them into a picture.
- Works well as the *secondary* panel below the card (concept 02 on top, concept 09 below, or vice versa).

### 3. **Concept 04 (Horizontal Timeline)** — for the power-user view
- The "entry → peak → trough → exit" pins on a real time axis is the most Bloomberg/TradingView-like option in the set.
- Pairs well with the actual chart card above it — the timeline conceptually mirrors the chart's x-axis but reads at a glance.
- Slightly more complex to build (requires knowing the times of MFE/MAE — already in the data though), but the payoff is high: a trader can correlate the chart's price action with the trade's lifecycle in one glance.

### Why not the others
- **01, 06** (Bloomberg/quant) — too dense for a single card; better suited to a separate analytics page
- **03** (R-hero) — striking but wastes vertical space; better as a single stat callout, not a full panel
- **05** (journal) — high effort to maintain (narrative copy is hard to templatize from raw trade data); more of a "review mode" affordance
- **07** (mini tiles) — pretty but lacks the "stop vs target vs actual" spatial relationship that the gauge captures
- **08** (sparklines) — beautiful but overlaps with the chart card directly above it; redundant
- **10** (vertical timeline) — strongest narrative but the most vertical real estate; not ideal in a card grid where many trades stack

**Ship plan suggestion:** concept 02 as the default panel for every chart card, with concept 09 as a collapsible "show risk/reward" expander inside it, and concept 04 as the "expanded" view when the user clicks a card.
