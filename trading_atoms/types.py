from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal['long', 'short']
ExitReason = Literal['target', 'stop', 'eod', 'market_close']


@dataclass
class OpeningRangeAtom:
    high: float
    low: float
    minutes: int
    bars: list[dict]
    rest_of_day: list[dict]
    rth_bars: list[dict]

    def to_payload(self) -> dict:
        return {
            'high': self.high,
            'low': self.low,
            'minutes': self.minutes,
        }


@dataclass
class EntryAtom:
    price: float
    direction: Direction
    bar: dict
    rule: str
    rule_ref: float

    @property
    def ts(self) -> int:
        return int(self.bar['ts'])

    def to_payload(self) -> dict:
        return {
            'ts': self.ts,
            'time': self.bar['et'].strftime('%H:%M') if self.bar.get('et') else None,
            'price': round(self.price, 4),
            'direction': self.direction,
            'side': 'buy' if self.direction == 'long' else 'sell',
            'rule': self.rule,
            'rule_ref': round(self.rule_ref, 4),
        }


@dataclass
class StopAtom:
    price: float
    risk: float
    rule: str
    rule_ref: float

    def to_payload(self, ts: int | None = None) -> dict:
        return {
            'ts': ts,
            'price': round(self.price, 4),
            'risk_per_share': round(self.risk, 4),
            'rule': self.rule,
            'rule_ref': round(self.rule_ref, 4),
        }


@dataclass
class TargetAtom:
    price: float
    multiple: float
    rule: str
    rule_ref: float

    def to_payload(self) -> dict:
        return {
            'ts': None,
            'price': round(self.price, 4),
            'multiple': self.multiple,
            'rule': self.rule,
            'rule_ref': self.rule_ref,
        }


@dataclass
class ExitAtom:
    price: float
    bar: dict
    reason: ExitReason
    same_bar_collision: bool = False

    @property
    def ts(self) -> int:
        return int(self.bar['ts'])

    def to_payload(self, direction: Direction) -> dict:
        return {
            'ts': self.ts,
            'time': self.bar['et'].strftime('%H:%M') if self.bar.get('et') else None,
            'price': round(self.price, 4),
            'side': 'sell' if direction == 'long' else 'buy',
            'rule': self.reason,
            'same_bar_collision': self.same_bar_collision,
        }


@dataclass
class MetricsAtom:
    pnl: float
    pnl_pct: float
    mfe: float
    mae: float
    r_multiple: float

    def to_payload(self) -> dict:
        return {
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'mfe': self.mfe,
            'mae': self.mae,
            'r_multiple': self.r_multiple,
        }
