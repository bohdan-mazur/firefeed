from datetime import datetime
from pathlib import Path

import pytest

from firefeed.analyze import Analyzer
from firefeed.budget import RequestBudget, RequestLimitReached
from firefeed.cache import JsonCache
from firefeed.config import AnalysisConfig
from firefeed.models import CallInput
from helpers import FakeClient, answer, fake_response, no_client

CALL = CallInput(
    id="c1", timestamp=datetime.fromisoformat("2026-10-17T13:04:00-05:00"), channel="Dispatch"
)
TEXT = "Larkmoor to Engine 1, structure fire, 1420 Bellwether Avenue."


def make(
    tmp_path: Path, client: object, *, limit: int = 10, effort: str | None = "low"
) -> Analyzer:
    return Analyzer(
        AnalysisConfig(reasoning_effort=effort),
        JsonCache(tmp_path / "cache"),
        lambda: client,
        RequestBudget(limit),
        "Known streets: Bellwether Avenue.",
    )


def cached_files(tmp_path: Path) -> list[Path]:
    return sorted((tmp_path / "cache").rglob("*.json"))


def test_request_shape(tmp_path: Path) -> None:
    client = FakeClient(lambda request: fake_response(answer()))

    outcome = make(tmp_path, client).analyze(CALL, TEXT)

    (request,) = client.responses.requests
    assert request["model"] == "gpt-6-luna"
    assert request["text"]["format"]["type"] == "json_schema"
    assert request["text"]["format"]["strict"] is True
    assert request["store"] is False
    assert request["reasoning"] == {"effort": "low"}
    assert "Known streets: Bellwether Avenue." in request["instructions"]
    assert request["input"] == f"Channel: Dispatch\nTranscript:\n{TEXT}"
    assert outcome.analysis == answer()
    assert outcome.usage.requests == 1
    assert outcome.usage.input_tokens == 600
    assert outcome.usage.reasoning_tokens == 40


def test_no_reasoning_option_when_effort_is_empty(tmp_path: Path) -> None:
    client = FakeClient(lambda request: fake_response(answer()))

    make(tmp_path, client, effort=None).analyze(CALL, TEXT)

    assert "reasoning" not in client.responses.requests[0]


def test_second_run_is_served_from_the_cache(tmp_path: Path) -> None:
    first = make(tmp_path, FakeClient(lambda request: fake_response(answer()))).analyze(CALL, TEXT)

    second = Analyzer(
        AnalysisConfig(),
        JsonCache(tmp_path / "cache"),
        no_client,
        RequestBudget(0),
        "Known streets: Bellwether Avenue.",
    ).analyze(CALL, TEXT)

    assert second.cache_hit
    assert second.analysis == first.analysis
    # The usage recorded with the answer comes back with it, so exports can report it.
    assert second.usage == first.usage
    assert len(cached_files(tmp_path)) == 1


def test_changed_input_or_settings_miss_the_cache(tmp_path: Path) -> None:
    client = FakeClient(lambda request: fake_response(answer()))

    make(tmp_path, client).analyze(CALL, TEXT)
    make(tmp_path, client).analyze(CALL, TEXT + " Time out 13:04.")
    make(tmp_path, client, effort="none").analyze(CALL, TEXT)
    make(tmp_path, client).analyze(CALL, TEXT)

    assert len(client.responses.requests) == 3


def test_invalid_answer_is_retried_then_reported(tmp_path: Path) -> None:
    client = FakeClient(lambda request: fake_response("this is not JSON"))

    outcome = make(tmp_path, client).analyze(CALL, TEXT)

    assert outcome.analysis is None
    assert "not JSON" in (outcome.error or "")
    assert len(client.responses.requests) == 2
    assert outcome.usage.requests == 2
    assert cached_files(tmp_path) == []


def test_answer_that_breaks_the_schema_gets_a_second_try(tmp_path: Path) -> None:
    replies = iter([fake_response({"is_fire": True}), fake_response(answer())])
    client = FakeClient(lambda request: next(replies))

    outcome = make(tmp_path, client).analyze(CALL, TEXT)

    assert outcome.analysis == answer()
    assert outcome.usage.requests == 2


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (fake_response(answer(), refusal="I can't help with that."), "model refused"),
        (fake_response(answer(), status="incomplete"), "incomplete (max_output_tokens)"),
    ],
)
def test_refusal_and_incomplete_answers(tmp_path: Path, response: object, error: str) -> None:
    outcome = make(tmp_path, FakeClient(lambda request: response)).analyze(CALL, TEXT)

    assert outcome.analysis is None
    assert error in (outcome.error or "")


def test_request_limit(tmp_path: Path) -> None:
    analyzer = make(tmp_path, FakeClient(lambda request: fake_response(answer())), limit=1)
    analyzer.analyze(CALL, TEXT)

    with pytest.raises(RequestLimitReached):
        analyzer.analyze(CALL, "Another transmission.")


def test_dry_run_creates_no_client(tmp_path: Path) -> None:
    analyzer = Analyzer(
        AnalysisConfig(), JsonCache(tmp_path / "cache"), no_client, RequestBudget(0)
    )

    outcome = analyzer.analyze(CALL, TEXT, dry_run=True)

    assert outcome.needs_request
    assert outcome.estimate is not None
    assert outcome.estimate.input_tokens > 100
    assert outcome.estimate.output_tokens == 400


def rate_limit(error_type: str, code: str) -> Exception:
    import httpx2
    import openai

    response = httpx2.Response(
        429, request=httpx2.Request("POST", "https://api.openai.com/v1/responses")
    )
    body = {"type": error_type, "code": code, "message": "429"}
    return openai.RateLimitError("429", response=response, body=body)


def test_no_credits_stops_the_run(tmp_path: Path) -> None:
    from firefeed.analyze import QuotaExhausted

    def reply(request: object) -> object:
        raise rate_limit("insufficient_quota", "credit_balance_exhausted")

    with pytest.raises(QuotaExhausted, match="no credits left"):
        make(tmp_path, FakeClient(reply)).analyze(CALL, TEXT)


def test_plain_rate_limit_is_recorded_and_the_run_goes_on(tmp_path: Path) -> None:
    def reply(request: object) -> object:
        raise rate_limit("requests", "rate_limit_exceeded")

    outcome = make(tmp_path, FakeClient(reply)).analyze(CALL, TEXT)

    assert outcome.analysis is None
    assert outcome.error == "API error: RateLimitError (rate_limit_exceeded)"
