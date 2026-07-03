from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

from .indicators import ema, vwap
from .sessions import annotate_et
from .types import Direction, EntryAtom

DirectionMode = Literal['both', 'long', 'short']

# Fashionably-late gate: wait out the first 15 minutes after the open.
FASHIONABLY_LATE_MINUTES = 15
# Cross earliest allowed local-time-of-bar after the gate (default 09:45 ET).
FASHIONABLY_LATE_OPEN_AFTER = dt.time(9, 45)

TIMEFRAME_SECONDS = {
    '1m': 60,
    '2m': 2 * 60,
    '3m': 3 * 60,
    '5m': 5 * 60,
    '10m': 10 * 60,
    '15m': 15 * 60,
    '30m': 30 * 60,
    '1h': 60 * 60,
    '1hr': 60 * 60,
    '4h': 4 * 60 * 60,
    '4hr': 4 * 60 * 60,
    '1d': 24 * 60 * 60,
    '1w': 7 * 24 * 60 * 60,
}
TIMEFRAME_ALIASES = {
    '1hr': '1h',
    '4hr': '4h',
}
SUPPORTED_TIMEFRAMES = ('1m', '2m', '3m', '5m', '10m', '15m', '30m', '1h', '4h', '1d', '1w')


def normalize_timeframe(timeframe: str, default: str = '15m') -> str:
    timeframe = TIMEFRAME_ALIASES.get(str(timeframe), str(timeframe))
    return timeframe if timeframe in SUPPORTED_TIMEFRAMES else default


def timeframe_seconds(timeframe: str) -> int:
    return TIMEFRAME_SECONDS.get(normalize_timeframe(timeframe), 15 * 60)


@dataclass
class StreakReversalEntryAtom:
    """Entry after N same-color candles followed by opposite-color close."""

    price: float
    direction: Direction
    bar: dict
    close_ts: int
    timeframe: str
    streak_len: int
    setup_color: str
    trigger_color: str
    setup_bars: list[dict]

    @property
    def ts(self) -> int:
        return int(self.close_ts)

    @property
    def bar_ts(self) -> int:
        return int(self.bar['ts'])

    @property
    def anchor(self) -> str:
        return 'bar_close'

    def setup_times(self) -> list[str]:
        return [b['et'].strftime('%H:%M') for b in self.setup_bars]

    def display_time(self) -> str | None:
        close_dt = self.bar.get('close_dt')
        if close_dt is not None:
            return close_dt.strftime('%H:%M')
        return None

    def to_payload(self) -> dict:
        return {
            'ts': self.ts,
            'bar_ts': self.bar_ts,
            'time': self.display_time(),
            'price': round(self.price, 4),
            'direction': self.direction,
            'side': 'buy' if self.direction == 'long' else 'sell',
            'rule': f"first_{self.trigger_color}_{self.timeframe}_close_after_{self.streak_len}_{self.setup_color}_{self.timeframe}_candles",
            'streak_len': len(self.setup_bars),
            'setup_color': self.setup_color,
            'trigger_color': self.trigger_color,
            'setup_bar_times': self.setup_times(),
            'entry_bar_open': round(self.bar['open'], 4),
            'entry_bar_close': round(self.bar['close'], 4),
            'anchor': self.anchor,
        }


def aggregate_clock(bars: list[dict], timeframe: str) -> list[dict]:
    """Aggregate sorted bars into deterministic clock-aligned timeframe bars."""
    seconds = timeframe_seconds(timeframe)
    buckets: list[dict] = []
    current_key = None
    current = None

    for bar in bars:
        key = int(bar['ts']) // seconds * seconds
        if current_key != key:
            if current is not None:
                buckets.append(current)
            current_key = key
            current = {
                **bar,
                'ts': key,
                'time': key,
                'close_ts': key + seconds,
                'open': bar['open'],
                'high': bar['high'],
                'low': bar['low'],
                'close': bar['close'],
                'volume': bar.get('volume') or 0,
                'source_bars': [bar],
            }
            continue

        assert current is not None
        current['high'] = max(current['high'], bar['high'])
        current['low'] = min(current['low'], bar['low'])
        current['close'] = bar['close']
        current['close_ts'] = key + seconds
        current['volume'] += bar.get('volume') or 0
        current['source_bars'].append(bar)

    if current is not None:
        buckets.append(current)
    return buckets


def green(bar: dict) -> bool:
    return bar['close'] > bar['open']


def red(bar: dict) -> bool:
    return bar['close'] < bar['open']


def _direction_allowed(direction: Direction, mode: str) -> bool:
    return mode == 'both' or mode == direction


def _candidate_from_streak(bar: dict, streak_bars: list[dict], direction_mode: str) -> dict | None:
    if len(streak_bars) < 3:
        return None

    streak_is_green = all(green(b) for b in streak_bars)
    streak_is_red = all(red(b) for b in streak_bars)

    if streak_is_green and red(bar) and _direction_allowed('short', direction_mode):
        return {'direction': 'short', 'setup_color': 'green', 'trigger_color': 'red'}
    if streak_is_red and green(bar) and _direction_allowed('long', direction_mode):
        return {'direction': 'long', 'setup_color': 'red', 'trigger_color': 'green'}
    return None


def find_streak_reversal_close_entry(
    rth_bars: list[dict],
    *,
    timeframe: str = '15m',
    direction_mode: DirectionMode | str = 'both',
    streak_len: int = 3,
) -> StreakReversalEntryAtom | None:
    """Find the first streak-reversal close entry in RTH bars.

    Entry atom:
    - >= streak_len green candles then first red close => short
    - >= streak_len red candles then first green close => long
    - execution price = trigger candle close
    - execution time = trigger candle close edge
    """
    direction_mode = direction_mode if direction_mode in {'both', 'long', 'short'} else 'both'
    timeframe = normalize_timeframe(timeframe, default='15m')
    strategy_bars = aggregate_clock(rth_bars, timeframe)
    streak_bars: list[dict] = []
    streak_color = None

    for bar in strategy_bars:
        color = 'green' if green(bar) else ('red' if red(bar) else 'doji')
        candidate = _candidate_from_streak(bar, streak_bars, direction_mode)
        if candidate is not None:
            return StreakReversalEntryAtom(
                price=bar['close'],
                direction=candidate['direction'],
                bar=bar,
                close_ts=int(bar.get('close_ts') or bar['ts']),
                timeframe=timeframe,
                streak_len=streak_len,
                setup_color=candidate['setup_color'],
                trigger_color=candidate['trigger_color'],
                setup_bars=list(streak_bars),
            )

        if color == 'doji':
            streak_bars = []
            streak_color = None
            continue
        if color != streak_color:
            streak_bars = [bar]
            streak_color = color
        else:
            streak_bars.append(bar)

        if len(streak_bars) > streak_len:
            streak_bars = streak_bars[-streak_len:]

    return None


@dataclass
class ThreeBarPivotReversalEntryAtom:
    """Larry Williams-style 3-candle pivot reversal entry.

    Short pattern: high, higher high, lower high -> short on next candle open.
    Long pattern: low, lower low, higher low -> long on next candle open.
    """

    price: float
    direction: Direction
    bar: dict
    entry_ts: int
    timeframe: str
    pattern_bars: list[dict]
    pivot_ref: float

    @property
    def ts(self) -> int:
        return int(self.entry_ts)

    @property
    def bar_ts(self) -> int:
        return int(self.bar['ts'])

    @property
    def anchor(self) -> str:
        return 'bar_open'

    def pattern_times(self) -> list[str]:
        return [b['et'].strftime('%H:%M') for b in self.pattern_bars]

    def display_time(self) -> str | None:
        close_dt = self.bar.get('close_dt')
        if close_dt is not None:
            return close_dt.strftime('%H:%M')
        return None

    def to_payload(self) -> dict:
        highs = [round(b['high'], 4) for b in self.pattern_bars]
        lows = [round(b['low'], 4) for b in self.pattern_bars]
        return {
            'ts': self.ts,
            'bar_ts': self.bar_ts,
            'time': self.display_time(),
            'price': round(self.price, 4),
            'direction': self.direction,
            'side': 'buy' if self.direction == 'long' else 'sell',
            'rule': 'three_bar_pivot_high_reversal' if self.direction == 'short' else 'three_bar_pivot_low_reversal',
            'rule_ref': round(self.pivot_ref, 4),
            'timeframe': self.timeframe,
            'pattern_bar_times': self.pattern_times(),
            'pattern_highs': highs,
            'pattern_lows': lows,
            'entry_bar_open': round(self.bar['open'], 4),
            'entry_bar_close': round(self.bar['close'], 4),
            'execution': 'next_candle_open',
            'anchor': self.anchor,
        }


def _three_bar_pivot_candidate(bars: list[dict], direction_mode: str) -> dict | None:
    first, middle, third = bars
    if (
        first['high'] < middle['high']
        and third['high'] < middle['high']
        and _direction_allowed('short', direction_mode)
    ):
        return {'direction': 'short', 'pivot_ref': middle['high']}
    if (
        first['low'] > middle['low']
        and third['low'] > middle['low']
        and _direction_allowed('long', direction_mode)
    ):
        return {'direction': 'long', 'pivot_ref': middle['low']}
    return None


def find_three_bar_pivot_reversal_entry(
    rth_bars: list[dict],
    *,
    timeframe: str = '15m',
    direction_mode: DirectionMode | str = 'both',
) -> ThreeBarPivotReversalEntryAtom | None:
    """Find first 3-bar pivot reversal entry in RTH bars.

    - Short: bar1 high < bar2 high and bar3 high < bar2 high.
    - Long: bar1 low > bar2 low and bar3 low > bar2 low.
    - Entry price/time = next candle open / next candle start after the 3-bar pattern completes.
    """
    direction_mode = direction_mode if direction_mode in {'both', 'long', 'short'} else 'both'
    timeframe = normalize_timeframe(timeframe, default='15m')
    strategy_bars = aggregate_clock(rth_bars, timeframe)

    for i in range(2, len(strategy_bars) - 1):
        pattern = strategy_bars[i - 2:i + 1]
        candidate = _three_bar_pivot_candidate(pattern, direction_mode)
        if candidate is None:
            continue
        entry_bar = strategy_bars[i + 1]
        return ThreeBarPivotReversalEntryAtom(
            price=entry_bar['open'],
            direction=candidate['direction'],
            bar=entry_bar,
            entry_ts=int(entry_bar['ts']),
            timeframe=timeframe,
            pattern_bars=pattern,
            pivot_ref=candidate['pivot_ref'],
        )
    return None


@dataclass
class EmaVwapCrossEntryAtom:
    """Fashionably-late EMA9 × VWAP cross entry.

    Composition reuse: stores an :class:`EntryAtom` so the rest of the
    package (stop / exit / strategy adapters) can treat this entry the same
    way it treats any other entry.
    """

    price: float
    direction: Direction
    bar: dict
    close_ts: int
    timeframe: str
    ema_period: int
    ema_at_entry: float
    vwap_at_entry: float
    eligible_after: dt.time
    anchor: str = 'bar_close'

    @property
    def ts(self) -> int:
        return int(self.close_ts)

    @property
    def bar_ts(self) -> int:
        return int(self.bar['ts'])

    def to_payload(self) -> dict:
        return {
            'ts': self.ts,
            'bar_ts': self.bar_ts,
            'time': self.bar.get('et').strftime('%H:%M') if self.bar.get('et') else None,
            'price': round(self.price, 4),
            'direction': self.direction,
            'side': 'buy' if self.direction == 'long' else 'sell',
            'rule': f'ema{self.ema_period}_vwap_cross_after_{(self.eligible_after or dt.time(9, 45)).strftime("%H%M")}',
            'rule_ref': round(self.vwap_at_entry, 4),
            'ema_at_entry': round(self.ema_at_entry, 4),
            'vwap_at_entry': round(self.vwap_at_entry, 4),
            'anchor': self.anchor,
        }

    def as_entry_atom(self) -> EntryAtom:
        return EntryAtom(
            price=self.price,
            direction=self.direction,
            bar=self.bar,
            rule=f'ema{self.ema_period}_vwap_cross',
            rule_ref=self.vwap_at_entry,
        )


def find_ema_vwap_cross_entry(
    rth_bars: list[dict],
    *,
    timeframe: str = '5m',
    ema_period: int = 9,
    eligible_after: dt.time = FASHIONABLY_LATE_OPEN_AFTER,
    market_open: dt.time = dt.time(9, 30),
    direction_mode: DirectionMode | str = 'both',
) -> EmaVwapCrossEntryAtom | None:
    """Find first EMA × VWAP cross after the fashionably-late gate.

    - Aggregates RTH bars into clock-aligned timeframe candles (defaults to
      ``5m`` so we have 3 candles worth of history after the 09:45 gate).
    - Computes the EMA on aggregated *closes* and session VWAP on aggregated
      typicals (high+low+close)/3. VWAP is cumulative so it includes only
      bars known through the trigger candle close — no hindsight.
    - Bullish cross: previous bar ``EMA < VWAP`` and current bar ``EMA > VWAP``
      with an eligible bar-open time strictly after ``eligible_after``.
    - Bearish cross: previous bar ``EMA > VWAP`` and current bar ``EMA < VWAP``
      with an eligible bar-open time strictly after ``eligible_after``.
    - Entry price = trigger candle close. Entry time = trigger candle close
      edge (consistent with existing streak-reversal entry atom).
    - Crosses before the gate are ignored (they exist in the EMA series but
      are not eligible to trigger an entry).
    """
    direction_mode = direction_mode if direction_mode in {'both', 'long', 'short'} else 'both'
    timeframe = normalize_timeframe(timeframe, default='5m')

    bars = aggregate_clock(annotate_et(rth_bars), timeframe)
    closes = [b['close'] for b in bars]
    ema_series = ema(closes, period=ema_period)
    vwap_series = vwap(bars)

    for i in range(1, len(bars)):
        prev_ema = ema_series[i - 1]
        cur_ema = ema_series[i]
        cur_vwap = vwap_series[i]
        if prev_ema is None or cur_ema is None or cur_vwap is None:
            continue

        # Gate: trigger bar-open time must be strictly after the eligible cutoff.
        bar_et = bars[i].get('et')
        if bar_et is None:
            continue
        gate_dt = bar_et.replace(
            hour=eligible_after.hour,
            minute=eligible_after.minute,
            second=0,
            microsecond=0,
        )
        if bar_et < gate_dt:
            continue

        bullish_cross = prev_ema <= cur_vwap and cur_ema > cur_vwap
        bearish_cross = prev_ema >= cur_vwap and cur_ema < cur_vwap

        if bullish_cross and direction_mode in {'both', 'long'}:
            return EmaVwapCrossEntryAtom(
                price=bars[i]['close'],
                direction='long',
                bar=bars[i],
                close_ts=int(bars[i].get('close_ts') or bars[i]['ts']),
                timeframe=timeframe,
                ema_period=ema_period,
                ema_at_entry=cur_ema,
                vwap_at_entry=cur_vwap,
                eligible_after=eligible_after,
            )
        if bearish_cross and direction_mode in {'both', 'short'}:
            return EmaVwapCrossEntryAtom(
                price=bars[i]['close'],
                direction='short',
                bar=bars[i],
                close_ts=int(bars[i].get('close_ts') or bars[i]['ts']),
                timeframe=timeframe,
                ema_period=ema_period,
                ema_at_entry=cur_ema,
                vwap_at_entry=cur_vwap,
                eligible_after=eligible_after,
            )

    return None


@dataclass
class EngulfingCloseEntryAtom:
    """Miguel's engulfing candle definition: close through previous extreme.

    Short: current candle closes below the previous candle's low.
    Long:  current candle closes above the previous candle's high.

    Preferred opposite-color filter (default on):
        short preferred: previous candle green, current candle red.
        long preferred:  previous candle red,  current candle green.

    - Entry price = trigger candle close.
    - Entry time  = trigger candle close edge.
    - Entry anchor = ``bar_close``.
    """

    price: float
    direction: Direction
    bar: dict
    previous_bar: dict
    close_ts: int
    timeframe: str
    require_opposite_color: bool
    previous_high: float
    previous_low: float
    previous_color: str
    trigger_color: str

    @property
    def ts(self) -> int:
        return int(self.close_ts)

    @property
    def bar_ts(self) -> int:
        return int(self.bar['ts'])

    @property
    def anchor(self) -> str:
        return 'bar_close'

    def display_time(self) -> str | None:
        close_dt = self.bar.get('close_dt')
        if close_dt is not None:
            return close_dt.strftime('%H:%M')
        bar_et = self.bar.get('et')
        if bar_et is not None:
            return bar_et.strftime('%H:%M')
        return None

    def previous_display_time(self) -> str | None:
        prev_et = self.previous_bar.get('et')
        if prev_et is not None:
            return prev_et.strftime('%H:%M')
        return None

    def rule(self) -> str:
        if self.direction == 'short':
            return 'engulfing_close_below_previous_low'
        return 'engulfing_close_above_previous_high'

    def rule_ref(self) -> float:
        return self.previous_low if self.direction == 'short' else self.previous_high

    def to_payload(self) -> dict:
        return {
            'ts': self.ts,
            'bar_ts': self.bar_ts,
            'time': self.display_time(),
            'price': round(self.price, 4),
            'direction': self.direction,
            'side': 'buy' if self.direction == 'long' else 'sell',
            'rule': self.rule(),
            'rule_ref': round(self.rule_ref(), 4),
            'timeframe': self.timeframe,
            'previous_bar_time': self.previous_display_time(),
            'previous_high': round(self.previous_high, 4),
            'previous_low': round(self.previous_low, 4),
            'previous_color': self.previous_color,
            'trigger_color': self.trigger_color,
            'entry_bar_open': round(self.bar['open'], 4),
            'entry_bar_close': round(self.bar['close'], 4),
            'require_opposite_color': bool(self.require_opposite_color),
            'anchor': self.anchor,
        }


def _bar_color(bar: dict) -> str:
    """Return canonical candle color label: 'green', 'red', or 'doji'."""
    if green(bar):
        return 'green'
    if red(bar):
        return 'red'
    return 'doji'


def find_engulfing_close_entry(
    rth_bars: list[dict],
    *,
    timeframe: str = '15m',
    direction_mode: DirectionMode | str = 'both',
    require_opposite_color: bool = True,
) -> EngulfingCloseEntryAtom | None:
    """Find the first engulfing close-entry atom in RTH bars.

    Detection:
        - Aggregate RTH bars into clock-aligned ``timeframe`` candles first.
        - Walk adjacent pairs (previous, current); current qualifies when its
          close pierces the previous bar's opposite extreme.
        - Short: ``current.close < previous.low``.
        - Long : ``current.close > previous.high``.
        - When ``require_opposite_color=True``, the preferred
          opposite-color filter is also enforced:
            - short : previous green, current red.
            - long  : previous red,   current green.
          Doji candles never satisfy the opposite-color filter (neither
          ``green()`` nor ``red()`` returns True for a doji).
        - When ``require_opposite_color=False``, only the close-through-extreme
          rule is required.
        - Same-bar dual qualifying (e.g. synthetic range cases) prefers short
          to keep behavior consistent with existing dual-qualifying precedence.

    Entry:
        - price = current candle close.
        - ts    = current candle close edge.
        - bar_ts = current candle start.
        - anchor = ``bar_close``.

    Anti-hindsight: only the previous and current bars are consulted; no
    future bars are scanned at decision time.
    """
    direction_mode = direction_mode if direction_mode in {'both', 'long', 'short'} else 'both'
    timeframe = normalize_timeframe(timeframe, default='15m')
    strategy_bars = aggregate_clock(rth_bars, timeframe)

    for previous_bar, current_bar in zip(strategy_bars, strategy_bars[1:]):
        prev_color = _bar_color(previous_bar)
        cur_color = _bar_color(current_bar)

        # Short candidate: current closes below previous low.
        short_extreme = current_bar['close'] < previous_bar['low']
        long_extreme = current_bar['close'] > previous_bar['high']

        if require_opposite_color:
            short_color_ok = prev_color == 'green' and cur_color == 'red'
            long_color_ok = prev_color == 'red' and cur_color == 'green'
        else:
            short_color_ok = True
            long_color_ok = True

        # Prefer short on dual-qualifying bars (consistent with existing precedence).
        if (
            short_extreme
            and short_color_ok
            and _direction_allowed('short', direction_mode)
        ):
            return EngulfingCloseEntryAtom(
                price=current_bar['close'],
                direction='short',
                bar=current_bar,
                previous_bar=previous_bar,
                close_ts=int(current_bar.get('close_ts') or current_bar['ts']),
                timeframe=timeframe,
                require_opposite_color=require_opposite_color,
                previous_high=previous_bar['high'],
                previous_low=previous_bar['low'],
                previous_color=prev_color,
                trigger_color=cur_color,
            )

        if (
            long_extreme
            and long_color_ok
            and _direction_allowed('long', direction_mode)
        ):
            return EngulfingCloseEntryAtom(
                price=current_bar['close'],
                direction='long',
                bar=current_bar,
                previous_bar=previous_bar,
                close_ts=int(current_bar.get('close_ts') or current_bar['ts']),
                timeframe=timeframe,
                require_opposite_color=require_opposite_color,
                previous_high=previous_bar['high'],
                previous_low=previous_bar['low'],
                previous_color=prev_color,
                trigger_color=cur_color,
            )

    return None


@dataclass
class FairValueGapRetraceEntryAtom:
    """Miguel's 3-candle fair-value-gap 50% retrace entry atom.

    Bearish (short) FVG:
        ``candle1.low > candle3.high``  (strict gap)
        zone       = ``[candle3.high, candle1.low]``
        midpoint   = zone_low + 0.5 * (zone_high - zone_low)
        short when a future bar's ``high >= midpoint``
        suggested stop = ``candle2.high`` (the displacement / FVG candle)

    Bullish (long) FVG:
        ``candle1.high < candle3.low``  (strict gap)
        zone       = ``[candle1.high, candle3.low]``
        midpoint   = zone_low + 0.5 * (zone_high - zone_low)
        long when a future bar's ``low <= midpoint``
        suggested stop = ``candle2.low``

    Entry semantics:
        - ``price``           = FVG midpoint.
        - ``ts`` / ``bar_ts`` = start of the *retrace* bar that touched the
          midpoint (intrabar-approximated; tick-level data would be required
          to know the precise touch instant).
        - ``anchor``          = ``'bar_open'``.
        - ``execution``       = ``'fvg_midpoint_retrace_touch'``.

    The 3-bar FVG pattern is detected on aggregated timeframe candles. Once
    a valid gap is identified, every bar strictly after ``candle3`` is
    scanned until one trades through the midpoint; that bar is the retrace
    trigger. First gap whose future retrace reaches 50% wins; short takes
    precedence over long when a synthetic/dual pattern qualifies both.
    """

    price: float
    direction: Direction
    bar: dict
    entry_ts: int
    timeframe: str
    retrace_fraction: float
    candle1: dict
    candle2: dict
    candle3: dict
    gap_start: float
    gap_end: float
    gap_midpoint: float
    suggested_stop_price: float

    @property
    def ts(self) -> int:
        return int(self.entry_ts)

    @property
    def bar_ts(self) -> int:
        return int(self.bar['ts'])

    @property
    def anchor(self) -> str:
        return 'bar_open'

    def rule(self) -> str:
        if self.direction == 'short':
            return 'bearish_fvg_50pct_retrace_short'
        return 'bullish_fvg_50pct_retrace_long'

    def rule_ref(self) -> float:
        return round(self.gap_midpoint, 4)

    def suggested_stop_rule(self) -> str:
        if self.direction == 'short':
            return 'bearish_fvg_candle_high'
        return 'bullish_fvg_candle_low'

    def display_time(self) -> str | None:
        bar_et = self.bar.get('et')
        if bar_et is not None:
            return bar_et.strftime('%H:%M')
        return None

    def fvg_candle_time(self) -> str | None:
        """Time label for candle2 — the displacement / FVG candle."""
        candle2_et = self.candle2.get('et')
        if candle2_et is not None:
            return candle2_et.strftime('%H:%M')
        return None

    def to_payload(self) -> dict:
        return {
            'ts': self.ts,
            'bar_ts': self.bar_ts,
            'time': self.display_time(),
            'price': round(self.price, 4),
            'direction': self.direction,
            'side': 'buy' if self.direction == 'long' else 'sell',
            'rule': self.rule(),
            'rule_ref': self.rule_ref(),
            'timeframe': self.timeframe,
            'fvg_candle_time': self.fvg_candle_time(),
            'gap_start': round(self.gap_start, 4),
            'gap_end': round(self.gap_end, 4),
            'gap_midpoint': round(self.gap_midpoint, 4),
            'retrace_fraction': round(self.retrace_fraction, 4),
            'suggested_stop_price': round(self.suggested_stop_price, 4),
            'suggested_stop_rule': self.suggested_stop_rule(),
            'entry_bar_open': round(self.bar['open'], 4),
            'entry_bar_close': round(self.bar['close'], 4),
            'execution': 'fvg_midpoint_retrace_touch',
            'anchor': self.anchor,
        }


def _fvg_zone_and_midpoint(candle1: dict, candle3: dict, direction: Direction):
    """Return ``(gap_start, gap_end, midpoint)`` for a valid FVG.

    For a bearish (short) FVG: ``candle1.low > candle3.high`` (strict).
        zone     = ``[candle3.high, candle1.low]``
        midpoint = ``zone_low + 0.5 * (zone_high - zone_low)``

    For a bullish (long) FVG: ``candle1.high < candle3.low`` (strict).
        zone     = ``[candle1.high, candle3.low]``
        midpoint = ``zone_low + 0.5 * (zone_high - zone_low)``
    """
    if direction == 'short':
        gap_start = float(candle3['high'])
        gap_end = float(candle1['low'])
    else:
        gap_start = float(candle1['high'])
        gap_end = float(candle3['low'])
    zone_low = min(gap_start, gap_end)
    zone_high = max(gap_start, gap_end)
    midpoint = zone_low + 0.5 * (zone_high - zone_low)
    return gap_start, gap_end, midpoint


def find_fair_value_gap_retrace_entry(
    rth_bars: list[dict],
    *,
    timeframe: str = '15m',
    direction_mode: DirectionMode | str = 'both',
    retrace_fraction: float = 0.5,
) -> FairValueGapRetraceEntryAtom | None:
    """Find the first fair-value-gap 50% retrace entry in RTH bars.

    Detection:
        - Aggregate RTH bars into clock-aligned ``timeframe`` candles first.
        - For every consecutive 3-candle window ``(candle1, candle2, candle3)``,
          detect a strict 3-bar FVG:
              * Bearish (short): ``candle1.low > candle3.high``.
              * Bullish (long) : ``candle1.high < candle3.low``.
        - For each detected gap, walk future bars strictly after ``candle3``
          until one trades through the retrace level
          (``retrace_fraction`` of the gap, default 0.5 = midpoint):
              * Short: ``future_bar.high >= midpoint`` → enter short at midpoint.
              * Long : ``future_bar.low  <= midpoint`` → enter long at midpoint.
        - First gap whose future retrace reaches the level wins. Short takes
          precedence over long when a synthetic/dual pattern qualifies both,
          consistent with existing dual-qualifying precedence in this module.

    Entry:
        - ``price``  = gap retrace level (default = gap midpoint).
        - ``ts`` / ``bar_ts`` = start of the retrace bar that touched the level.
        - ``anchor`` = ``'bar_open'`` (intrabar-approximated until tick data is
          available; ``execution='fvg_midpoint_retrace_touch'`` signals this).

    Suggested stop (exposed in payload only — no separate stop atom here):
        - Short: ``candle2.high`` (Miguel: FVG candle high).
        - Long : ``candle2.low``.

    Anti-hindsight: only candle1/candle2/candle3 of the gap and the future
    retrace bar at the moment of touch are consulted; the stop-ref candle2
    is part of the gap pattern itself, so it's known at decision time.
    """
    direction_mode = direction_mode if direction_mode in {'both', 'long', 'short'} else 'both'
    timeframe = normalize_timeframe(timeframe, default='15m')

    if not 0.0 <= retrace_fraction <= 1.0:
        # Clamp defensively; the spec is 0.5 but we don't want a silent garbage value.
        retrace_fraction = max(0.0, min(1.0, retrace_fraction))

    strategy_bars = aggregate_clock(rth_bars, timeframe)

    for i in range(len(strategy_bars) - 2):
        candle1 = strategy_bars[i]
        candle2 = strategy_bars[i + 1]
        candle3 = strategy_bars[i + 2]

        # Bearish (short) FVG: candle1.low strictly above candle3.high.
        bearish_gap = candle1['low'] > candle3['high']
        # Bullish (long) FVG: candle1.high strictly below candle3.low.
        bullish_gap = candle1['high'] < candle3['low']

        # Short takes precedence when both qualify on the same triple.
        candidate_directions: list[Direction] = []
        if bearish_gap and _direction_allowed('short', direction_mode):
            candidate_directions.append('short')
        if bullish_gap and _direction_allowed('long', direction_mode):
            candidate_directions.append('long')

        if not candidate_directions:
            continue

        # Scan future bars strictly after candle3 for the retrace touch.
        for j in range(i + 3, len(strategy_bars)):
            future_bar = strategy_bars[j]
            for direction in candidate_directions:
                gap_start, gap_end, midpoint = _fvg_zone_and_midpoint(
                    candle1, candle3, direction
                )
                retrace_level = gap_start + retrace_fraction * (gap_end - gap_start)

                if direction == 'short':
                    if future_bar['high'] >= retrace_level:
                        return FairValueGapRetraceEntryAtom(
                            price=retrace_level,
                            direction='short',
                            bar=future_bar,
                            entry_ts=int(future_bar['ts']),
                            timeframe=timeframe,
                            retrace_fraction=retrace_fraction,
                            candle1=candle1,
                            candle2=candle2,
                            candle3=candle3,
                            gap_start=gap_start,
                            gap_end=gap_end,
                            gap_midpoint=midpoint,
                            suggested_stop_price=float(candle2['high']),
                        )
                else:  # long
                    if future_bar['low'] <= retrace_level:
                        return FairValueGapRetraceEntryAtom(
                            price=retrace_level,
                            direction='long',
                            bar=future_bar,
                            entry_ts=int(future_bar['ts']),
                            timeframe=timeframe,
                            retrace_fraction=retrace_fraction,
                            candle1=candle1,
                            candle2=candle2,
                            candle3=candle3,
                            gap_start=gap_start,
                            gap_end=gap_end,
                            gap_midpoint=midpoint,
                            suggested_stop_price=float(candle2['low']),
                        )

    return None
