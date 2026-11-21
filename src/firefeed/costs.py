"""Token and cost arithmetic.

Dry runs estimate tokens from text length. Real runs record the usage the API reports, and the
published cost per call comes only from those recorded numbers.
"""

from __future__ import annotations

import math

from firefeed.config import Prices
from firefeed.models import Usage

# Rough rule for English text, used only for dry-run estimates.
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))


def token_cost(usage: Usage, prices: Prices) -> float:
    """USD for text tokens. Output tokens already include reasoning tokens."""
    uncached = max(0, usage.input_tokens - usage.cached_input_tokens)
    return (
        uncached * prices.input
        + usage.cached_input_tokens * prices.cached_input
        + usage.output_tokens * prices.output
    ) / 1_000_000


def audio_cost(seconds: float, price_per_minute: float) -> float:
    return seconds / 60 * price_per_minute


def total_cost(usage: Usage, prices: Prices, price_per_minute: float) -> float:
    return token_cost(usage, prices) + audio_cost(usage.audio_seconds, price_per_minute)
