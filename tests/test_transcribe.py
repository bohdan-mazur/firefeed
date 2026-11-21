from pathlib import Path

from firefeed.budget import RequestBudget
from firefeed.cache import JsonCache
from firefeed.config import TranscribeConfig
from firefeed.ingest import load_calls
from firefeed.transcribe import Transcriber
from helpers import FakeClient, answer, fake_response, no_client, write_call


def test_calls_with_a_transcript_skip_transcription(tmp_path: Path) -> None:
    write_call(
        tmp_path / "calls", "c1", "2026-10-17T13:04:00-05:00", text="  Engine 3, radio check. \n"
    )
    (call,) = load_calls(tmp_path / "calls")

    outcome = Transcriber(
        TranscribeConfig(), JsonCache(tmp_path), no_client, RequestBudget(0)
    ).transcribe(call)

    assert outcome.text == "Engine 3, radio check."
    assert outcome.source == "text"
    assert outcome.usage.requests == 0


def test_audio_is_transcribed_once(tmp_path: Path) -> None:
    write_call(
        tmp_path / "calls", "c1", "2026-10-17T13:04:00-05:00", audio=b"fake wav", duration_s=12.0
    )
    (call,) = load_calls(tmp_path / "calls")
    client = FakeClient(lambda request: fake_response(answer()), transcript="Engine 2 on scene.")
    cache = JsonCache(tmp_path / "cache")

    first = Transcriber(TranscribeConfig(), cache, lambda: client, RequestBudget(1)).transcribe(
        call
    )
    second = Transcriber(TranscribeConfig(), cache, no_client, RequestBudget(0)).transcribe(call)

    assert first.text == second.text == "Engine 2 on scene."
    assert first.source == "transcribed"
    assert first.usage.audio_seconds == 12.0
    assert second.cache_hit
    assert client.audio.transcriptions.requests == [{"model": "gpt-transcribe", "language": "en"}]


def test_dry_run_counts_the_audio_without_a_request(tmp_path: Path) -> None:
    write_call(
        tmp_path / "calls", "c1", "2026-10-17T13:04:00-05:00", audio=b"fake wav", duration_s=30.0
    )
    (call,) = load_calls(tmp_path / "calls")

    outcome = Transcriber(
        TranscribeConfig(), JsonCache(tmp_path), no_client, RequestBudget(0)
    ).transcribe(call, dry_run=True)

    assert outcome.needs_request
    assert outcome.text is None
    assert outcome.usage.audio_seconds == 30.0
