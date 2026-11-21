import pytest

from firefeed.config import Prices
from firefeed.costs import audio_cost, estimate_tokens, token_cost, total_cost
from firefeed.models import Usage

PRICES = Prices(input=0.10, cached_input=0.01, output=0.50)


def test_cached_input_is_charged_at_the_cached_price() -> None:
    usage = Usage(input_tokens=1_000_000, cached_input_tokens=400_000, output_tokens=100_000)

    assert token_cost(usage, PRICES) == pytest.approx(0.6 * 0.10 + 0.4 * 0.01 + 0.1 * 0.50)


def test_audio_and_total() -> None:
    assert audio_cost(90, 0.0045) == pytest.approx(0.00675)
    usage = Usage(output_tokens=1_000_000, audio_seconds=60)
    assert total_cost(usage, PRICES, 0.0045) == pytest.approx(0.5045)


def test_estimate_tokens() -> None:
    assert estimate_tokens("abcd" * 10) == 10
    assert estimate_tokens("") == 1


def test_usage_adds_up() -> None:
    total = Usage(requests=1, input_tokens=10)
    total += Usage(requests=2, input_tokens=5, audio_seconds=1.5)

    assert total == Usage(requests=3, input_tokens=15, audio_seconds=1.5)
    assert Usage.from_dict(total.to_dict()) == total
    assert Usage.from_dict(None) == Usage()
