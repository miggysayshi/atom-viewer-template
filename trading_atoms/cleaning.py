from __future__ import annotations


def clamp_bad_wicks(bars: list[dict], threshold: float) -> int:
    """Clamp pathological high/low wicks in-place, preserving current behavior.

    Uses median range for the provided session slice. Only reduces extremes;
    never expands a bar. Returns count of cleaned bars.
    """
    if not bars:
        return 0
    ranges = [b['high'] - b['low'] for b in bars]
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
        if b['high'] - b['low'] > cutoff:
            body_high = max(b['open'], b['close'])
            body_low = min(b['open'], b['close'])
            new_high = body_high + median_range
            new_low = body_low - median_range
            b['high'] = min(b['high'], round(new_high, 4))
            b['low'] = max(b['low'], round(new_low, 4))
            cleaned += 1
    return cleaned


def clamp_bars_by_session(pre: list[dict], rth: list[dict], post: list[dict]) -> dict[str, int]:
    return {
        'pre': clamp_bad_wicks(pre, threshold=3.0),
        'rth': clamp_bad_wicks(rth, threshold=5.0),
        'post': clamp_bad_wicks(post, threshold=3.0),
    }
