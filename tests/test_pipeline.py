import dataclasses
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from firefeed.cli import main
from firefeed.config import Config, LimitsConfig
from firefeed.pipeline import ConfirmationRequired, TooManyRequests, run
from helpers import FakeClient, answer, no_client, not_incident, reply_by_transcript, write_call

TABLE = {
    "structure fire": answer(
        location_as_heard="1420 Bell weather Avenue", units=["Engine One", "Ladder 1"]
    ),
    "primary search": answer(
        status="working",
        location_as_heard=None,
        units=["Ladder 1"],
        summary="Primary search is clear.",
    ),
    "radio check": not_incident(units=["Engine 3"]),
}


def setup_calls(cfg: Config) -> None:
    write_call(
        cfg.input_dir,
        "c1",
        "2026-10-17T13:04:12-05:00",
        text="Larkmoor to Engine 1, Ladder 1, structure fire, 1420 Bellwether Avenue.",
    )
    write_call(
        cfg.input_dir,
        "c2",
        "2026-10-17T13:13:58-05:00",
        "Fireground 2",
        text="Ladder 1 to Command, primary search complete, all clear.",
    )
    write_call(cfg.input_dir, "c3", "2026-10-17T13:20:00-05:00", text="Engine 3, radio check.")


def read_feed(cfg: Config) -> dict:
    return json.loads((cfg.output_dir / "feed.json").read_text(encoding="utf-8"))


def test_run_then_rerun_from_cache(make_config: Callable[..., Config]) -> None:
    cfg = make_config()
    setup_calls(cfg)
    client = FakeClient(reply_by_transcript(TABLE))

    summary = run(cfg, client_factory=lambda: client, env={})

    assert summary.api_requests == 3
    assert summary.errors == {}
    feed = read_feed(cfg)
    assert feed["notice"] == "Demo on synthetic data. All calls, places and people are fictional."
    assert [c["street"] for c in feed["calls"]] == ["Bellwether Avenue", None, None]
    assert feed["calls"][0]["units"] == ["Engine 1", "Ladder 1"]
    assert [c["incident_id"] for c in feed["calls"]] == ["inc-01", "inc-01", None]
    (incident,) = feed["incidents"]
    assert incident["call_ids"] == ["c1", "c2"]
    assert incident["channels"] == ["Dispatch", "Fireground 2"]
    assert feed["usage"]["api_requests"] == 3
    assert feed["usage"]["cost_usd"] > 0
    assert feed["usage"]["cost_per_call_usd"] == pytest.approx(
        feed["usage"]["cost_usd"] / 3, abs=1e-6
    )

    again = run(cfg, client_factory=no_client, env={})

    assert again.api_requests == 0
    assert again.cache_hits == 3
    assert again.cost_this_run_usd == 0
    assert read_feed(cfg) == feed


def test_dry_run_estimates_and_writes_nothing(make_config: Callable[..., Config]) -> None:
    cfg = make_config()
    setup_calls(cfg)

    summary = run(cfg, dry_run=True, client_factory=no_client, env={})

    assert summary.requests_needed == 3
    assert summary.estimated_cost_usd > 0
    assert not (cfg.output_dir / "feed.json").exists()


def test_request_limit_and_confirmation(make_config: Callable[..., Config]) -> None:
    cfg = make_config(limits=LimitsConfig(max_api_requests_per_run=2))
    setup_calls(cfg)
    with pytest.raises(TooManyRequests, match="3 API requests needed, the limit is 2"):
        run(cfg, client_factory=no_client, env={})

    cfg = dataclasses.replace(cfg, limits=LimitsConfig(confirm_above_usd=0.0))
    with pytest.raises(ConfirmationRequired, match="--yes"):
        run(cfg, client_factory=no_client, env={})

    client = FakeClient(reply_by_transcript(TABLE))
    assert run(cfg, assume_yes=True, client_factory=lambda: client, env={}).api_requests == 3


def test_cli_dry_run_needs_no_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    write_call(tmp_path / "calls", "c1", "2026-10-17T13:04:12-05:00", text="Engine 3, radio check.")
    (tmp_path / "firefeed.toml").write_text('[dataset]\ninput_dir = "calls"\n', encoding="utf-8")

    assert main(["run", "--dry-run"]) == 0


def test_cli_reports_a_missing_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    write_call(tmp_path / "calls", "c1", "2026-10-17T13:04:12-05:00", text="Engine 3, radio check.")
    (tmp_path / "firefeed.toml").write_text('[dataset]\ninput_dir = "calls"\n', encoding="utf-8")

    assert main(["run"]) == 1
    assert "OPENAI_API_KEY is not set" in capsys.readouterr().err


def test_cli_never_prints_key_fragments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import httpx2
    import openai

    import firefeed.pipeline

    def rejecting_client() -> object:
        response = httpx2.Response(
            401, request=httpx2.Request("POST", "https://api.openai.com/v1/responses")
        )
        message = "Incorrect API key provided: sk-proj-****************CsgA."

        def create(**kwargs: object) -> object:
            raise openai.AuthenticationError(message, response=response, body=None)

        return FakeClient(lambda request: create())

    monkeypatch.setattr(firefeed.pipeline, "default_client", rejecting_client)
    monkeypatch.chdir(tmp_path)
    write_call(tmp_path / "calls", "c1", "2026-10-17T13:04:12-05:00", text="Engine 3, radio check.")
    (tmp_path / "firefeed.toml").write_text('[dataset]\ninput_dir = "calls"\n', encoding="utf-8")

    assert main(["run"]) == 1
    err = capsys.readouterr().err
    assert "the API rejected the key (401)" in err
    assert "sk-" not in err and "CsgA" not in err
