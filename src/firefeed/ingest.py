"""Read the input folder: one transcript or audio file per call, plus a JSON sidecar.

calls/
  c001.txt    transcript (wins over audio when both exist)
  c001.wav    audio, transcribed when there is no .txt
  c001.json   {"timestamp": "2026-10-17T13:04:12-05:00", "channel": "Dispatch"}
"""

from __future__ import annotations

import json
import wave
from datetime import datetime
from pathlib import Path

from firefeed.models import CallInput

TEXT_SUFFIXES = frozenset({".txt"})
AUDIO_SUFFIXES = frozenset({".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"})
METADATA_FIELDS = frozenset({"id", "timestamp", "channel", "duration_s"})


class IngestError(ValueError):
    """The input folder has missing or broken files. The message lists every problem."""


def _wav_seconds(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except (wave.Error, EOFError, OSError):
        return None


def _parse_metadata(stem: str, path: Path, problems: list[str]) -> dict | None:
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        problems.append(f"{path.name}: cannot read JSON ({exc})")
        return None
    if not isinstance(meta, dict):
        problems.append(f"{path.name}: must be a JSON object")
        return None
    unknown = sorted(set(meta) - METADATA_FIELDS)
    if unknown:
        problems.append(f"{path.name}: unknown fields {unknown}")
    if "id" in meta and meta["id"] != stem:
        problems.append(f"{path.name}: id {meta['id']!r} does not match the file name {stem!r}")

    timestamp = None
    raw = meta.get("timestamp")
    if not isinstance(raw, str):
        problems.append(f"{path.name}: timestamp is required (ISO 8601 with a UTC offset)")
    else:
        try:
            timestamp = datetime.fromisoformat(raw)
        except ValueError:
            problems.append(f"{path.name}: timestamp {raw!r} is not ISO 8601")
        else:
            if timestamp.tzinfo is None:
                problems.append(f"{path.name}: timestamp {raw!r} needs a UTC offset")
                timestamp = None

    channel = meta.get("channel")
    if not isinstance(channel, str) or not channel.strip():
        problems.append(f"{path.name}: channel is required")
        channel = None

    duration = meta.get("duration_s")
    if duration is not None and (
        isinstance(duration, bool) or not isinstance(duration, int | float) or duration < 0
    ):
        problems.append(f"{path.name}: duration_s must be a non-negative number")
        duration = None

    if timestamp is None or channel is None:
        return None
    return {"timestamp": timestamp, "channel": channel.strip(), "duration_s": duration}


def load_calls(input_dir: Path) -> list[CallInput]:
    """All calls in ``input_dir``, sorted by time. Raises IngestError listing every problem."""
    if not input_dir.is_dir():
        raise IngestError(f"input folder not found: {input_dir}")

    groups: dict[str, dict[str, list[Path]]] = {}
    for path in sorted(input_dir.iterdir()):
        suffix = path.suffix.lower()
        if not path.is_file():
            continue
        if suffix in TEXT_SUFFIXES:
            kind = "text"
        elif suffix in AUDIO_SUFFIXES:
            kind = "audio"
        elif suffix == ".json":
            kind = "meta"
        else:
            continue
        groups.setdefault(path.stem, {}).setdefault(kind, []).append(path)

    problems: list[str] = []
    calls: list[CallInput] = []
    for stem, files in sorted(groups.items()):
        text = files.get("text", [])
        audio = files.get("audio", [])
        meta = files.get("meta", [])
        if len(audio) > 1:
            problems.append(
                f"{stem}: more than one audio file ({', '.join(p.name for p in audio)})"
            )
            continue
        if not text and not audio:
            problems.append(f"{stem}.json: no transcript (.txt) or audio file with the same name")
            continue
        if not meta:
            problems.append(f"{stem}: metadata file {stem}.json is missing")
            continue
        parsed = _parse_metadata(stem, meta[0], problems)
        if parsed is None:
            continue
        audio_path = audio[0] if audio else None
        duration = parsed["duration_s"]
        if duration is None and audio_path is not None and audio_path.suffix.lower() == ".wav":
            duration = _wav_seconds(audio_path)
        calls.append(
            CallInput(
                id=stem,
                timestamp=parsed["timestamp"],
                channel=parsed["channel"],
                text_path=text[0] if text else None,
                audio_path=audio_path,
                duration_s=duration,
            )
        )

    if problems:
        raise IngestError("input has problems:\n  " + "\n  ".join(problems))
    calls.sort(key=lambda c: (c.timestamp, c.id))
    return calls
