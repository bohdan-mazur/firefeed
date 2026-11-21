import wave
from pathlib import Path

import pytest

from firefeed.ingest import IngestError, load_calls
from helpers import write_call


def test_loads_calls_sorted_by_time(tmp_path: Path) -> None:
    folder = tmp_path / "calls"
    write_call(folder, "b", "2026-10-17T13:05:00-05:00", text="Second call")
    write_call(folder, "a", "2026-10-17T13:04:00-05:00", "Fireground 2", text="First call")

    calls = load_calls(folder)

    assert [c.id for c in calls] == ["a", "b"]
    assert calls[0].channel == "Fireground 2"
    assert calls[0].text_path == folder / "a.txt"
    assert calls[0].audio_path is None
    assert calls[0].timestamp.utcoffset().total_seconds() == -5 * 3600


def test_reports_every_problem_at_once(tmp_path: Path) -> None:
    folder = tmp_path / "calls"
    folder.mkdir()
    (folder / "no_meta.txt").write_text("text", encoding="utf-8")
    (folder / "orphan.json").write_text(
        '{"timestamp": "2026-10-17T13:04:00-05:00", "channel": "Dispatch"}', encoding="utf-8"
    )
    write_call(folder, "naive", "2026-10-17T13:04:00", text="x")
    write_call(folder, "nochannel", "2026-10-17T13:04:00-05:00", "", text="x")
    write_call(folder, "renamed", "2026-10-17T13:04:00-05:00", text="x", id="other")
    write_call(folder, "extra", "2026-10-17T13:04:00-05:00", text="x", talkgroup=7)

    with pytest.raises(IngestError) as error:
        load_calls(folder)

    message = str(error.value)
    for expected in (
        "no_meta: metadata file no_meta.json is missing",
        "orphan.json: no transcript",
        "naive.json: timestamp '2026-10-17T13:04:00' needs a UTC offset",
        "nochannel.json: channel is required",
        "renamed.json: id 'other' does not match",
        "extra.json: unknown fields ['talkgroup']",
    ):
        assert expected in message


def test_missing_folder(tmp_path: Path) -> None:
    with pytest.raises(IngestError, match="not found"):
        load_calls(tmp_path / "nope")


def test_transcript_wins_over_audio(tmp_path: Path) -> None:
    folder = tmp_path / "calls"
    write_call(folder, "c1", "2026-10-17T13:04:00-05:00", text="Typed", audio=b"not audio")

    (call,) = load_calls(folder)

    assert call.text_path == folder / "c1.txt"
    assert call.audio_path == folder / "c1.wav"


def test_reads_wav_length(tmp_path: Path) -> None:
    folder = tmp_path / "calls"
    write_call(folder, "c1", "2026-10-17T13:04:00-05:00")
    with wave.open(str(folder / "c1.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 12000)

    (call,) = load_calls(folder)

    assert call.duration_s == pytest.approx(1.5)
