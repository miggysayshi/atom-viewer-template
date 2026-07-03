from __future__ import annotations

import datetime as dt

from .sessions import MARKET_CLOSE, MARKET_OPEN, session_name
from .types import EntryAtom


class PremarketRangeAtom:
    """Premarket high/low range atom for the same ET day.

    Additive to `OpeningRangeAtom`. Source bars are premarket-session bars
    (ET time < MARKET_OPEN). PMH/PML are deterministic, no-hindsight
    references for the first-RTH-bar breakout entry atom.
    """

    def __init__(
        self,
        high: float,
        low: float,
        bars: list[dict],
        date: dt.date | None = None,
    ) -> None:
        self.high = round(high, 4)
        self.low = round(low, 4)
        self.bars = bars
        self.date = date

    def to_payload(self) -> dict:
        return {
            'high': self.high,
            'low': self.low,
            'source': 'premarket_session',
            'bar_count': len(self.bars),
            'date': self.date.isoformat() if self.date else None,
        }


def premarket_range(
    annotated_bars: list[dict],
    *,
    date: dt.date | None = None,
) -> PremarketRangeAtom | None:
    """Compute premarket high/low from same-day premarket bars.

    Premarket session = ET time < 09:30 (per `sessions.session_name`).
    Post-market bars are ignored even if present in the input list. If the
    caller knows the trading date, pass `date` for a more informative
    payload; otherwise the first premarket bar's ET date is used.
    """
    pre_bars = [b for b in annotated_bars if session_name(b['et'].time()) == 'pre']
    if not pre_bars:
        return None

    resolved_date = date or pre_bars[0]['et'].date()
    return PremarketRangeAtom(
        high=max(b['high'] for b in pre_bars),
        low=min(b['low'] for b in pre_bars),
        bars=pre_bars,
        date=resolved_date,
    )


def _rth_bars(annotated_bars: list[dict]) -> list[dict]:
    return [
        b for b in annotated_bars
        if MARKET_OPEN <= b['et'].time() < MARKET_CLOSE
    ]


def find_premarket_breakout_entry(
    pm_range: PremarketRangeAtom,
    annotated_bars: list[dict],
    *,
    direction_mode: str = 'both',
) -> EntryAtom | None:
    """First RTH bar that closes beyond premarket high/low.

    Price rule (close-confirmed breakout):
    - long  trigger: bar.close > pm_range.high
    - short trigger: bar.close < pm_range.low

    Anti-hindsight:
    - PMH/PML come from `pm_range` (premarket-session only).
    - Only RTH bars at/after MARKET_OPEN are scanned.

    Same-first-bar convention: if both directions trigger on the same bar,
    long wins (matches `detect_breakout`). The atom payload records
    `price_rule='bar_close'` so consumers can audit the convention.
    """
    if direction_mode not in {'both', 'long', 'short'}:
        direction_mode = 'both'

    rth = _rth_bars(annotated_bars)
    for bar in rth:
        long_hit = (
            direction_mode in {'both', 'long'}
            and bar['close'] > pm_range.high
        )
        short_hit = (
            direction_mode in {'both', 'short'}
            and bar['close'] < pm_range.low
        )
        if long_hit and short_hit:
            return EntryAtom(
                price=bar['close'],
                direction='long',
                bar=bar,
                rule='premarket_high_breakout_close',
                rule_ref=pm_range.high,
            )
        if long_hit:
            return EntryAtom(
                price=bar['close'],
                direction='long',
                bar=bar,
                rule='premarket_high_breakout_close',
                rule_ref=pm_range.high,
            )
        if short_hit:
            return EntryAtom(
                price=bar['close'],
                direction='short',
                bar=bar,
                rule='premarket_low_breakdown_close',
                rule_ref=pm_range.low,
            )
    return None


def _close_inside_pm_range(bar: dict, pm_range: PremarketRangeAtom) -> bool:
    """A close is "inside the premarket range" when PML <= close <= PMH.

    Inclusive boundaries are intentional: Miguel's "comes back into the range"
    allows the close to land exactly on PMH/PML as a valid re-entry tick.
    """
    c = bar['close']
    return pm_range.low <= c <= pm_range.high


def find_premarket_reentry_entry(
    pm_range: PremarketRangeAtom,
    annotated_bars: list[dict],
    *,
    direction_mode: str = 'both',
) -> EntryAtom | None:
    """Find the first premarket-range re-entry entry in RTH bars.

    Strategy:
      - Short side (failed PMH breakout): first bar to *close back inside* the
        premarket range **after** some earlier bar traded above PMH
        (``high > PMH``). Entry price = trigger bar close.
      - Long side (failed PML breakdown): first bar to close back inside the
        premarket range **after** some earlier bar traded below PML
        (``low < PML``). Entry price = trigger bar close.

    The excursion and re-entry may coincide on a single bar (bar spikes above
    PMH *and* closes back inside). The atom only inspects state available at
    the trigger bar -- no future bars are used to decide the entry.

    ``direction_mode`` accepts ``'both'``, ``'long'``, or ``'short'``. Short is
    checked first to mirror ORB precedence when the same first bar qualifies
    for both directions (e.g., wide doji relative to a narrow PM range).
    """
    if direction_mode not in {'both', 'long', 'short'}:
        direction_mode = 'both'

    rth = _rth_bars(annotated_bars)

    saw_above_pmh = False
    saw_below_pml = False

    allow_short = direction_mode in {'both', 'short'}
    allow_long = direction_mode in {'both', 'long'}

    for bar in rth:
        # Update excursion state using the current bar's range (high/low).
        if bar['high'] > pm_range.high:
            saw_above_pmh = True
        if bar['low'] < pm_range.low:
            saw_below_pml = True

        if not _close_inside_pm_range(bar, pm_range):
            continue

        if allow_short and saw_above_pmh:
            return EntryAtom(
                price=bar['close'],
                direction='short',
                bar=bar,
                rule='pmh_failed_breakout_reentry',
                rule_ref=pm_range.high,
            )
        if allow_long and saw_below_pml:
            return EntryAtom(
                price=bar['close'],
                direction='long',
                bar=bar,
                rule='pml_failed_breakdown_reentry',
                rule_ref=pm_range.low,
            )

    return None