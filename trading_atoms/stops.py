from __future__ import annotations

from .types import Direction, OpeningRangeAtom, StopAtom, TargetAtom


def opposite_side_stop(entry: float, or_range: OpeningRangeAtom, direction: Direction) -> StopAtom:
    if direction == 'long':
        stop_price = or_range.low
        risk = entry - stop_price
        rule_ref = or_range.low
    else:
        stop_price = or_range.high
        risk = stop_price - entry
        rule_ref = or_range.high
    return StopAtom(price=stop_price, risk=risk, rule='or_opposite', rule_ref=rule_ref)


def r_multiple_target(entry: float, stop: StopAtom, direction: Direction, multiple: float = 3.0) -> TargetAtom:
    if direction == 'long':
        price = entry + multiple * stop.risk
    else:
        price = entry - multiple * stop.risk
    return TargetAtom(price=price, multiple=multiple, rule='r_multiple', rule_ref=multiple)
