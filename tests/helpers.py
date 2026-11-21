"""Test helpers: a fake OpenAI client, canned answers and an input-folder builder."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

GAZETTEER = {
    "name": "Test County",
    "streets": [
        {"name": "Bellwether Avenue"},
        {"name": "Tinsmith Street"},
        {"name": "Gristmill Way"},
        {"name": "Thimble Creek Road"},
        {"name": "Fallowmere Road"},
        {"name": "Kestrel Ridge Road"},
        {"name": "County Road 12", "aliases": ["CR 12"]},
        {"name": "Main Street"},
    ],
    "units": [
        {"name": "Engine 1"},
        {"name": "Engine 2"},
        {"name": "Engine 3"},
        {"name": "Ladder 1", "aliases": ["Truck 1"]},
        {"name": "Battalion 1", "aliases": ["Battalion Chief 1"]},
        {"name": "Medic 2"},
    ],
    "channels": ["Dispatch", "Fireground 2"],
    "dispatcher": "Larkmoor",
    "radio_codes": {"10-8": "back in service", "10-97": "arrived on scene"},
}


def answer(**overrides: Any) -> dict[str, Any]:
    """A valid analysis answer, changed by ``overrides``."""
    base: dict[str, Any] = {
        "is_fire": True,
        "incident_type": "structure_fire",
        "location_as_heard": "1420 Bellwether Avenue",
        "units": ["Engine 1"],
        "status": "dispatched",
        "summary": "Structure fire dispatch.",
        "confidence": 0.9,
    }
    base.update(overrides)
    return base


def not_incident(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "is_fire": False,
        "incident_type": "not_incident",
        "location_as_heard": None,
        "status": "none",
        "summary": "Radio check.",
    }
    base.update(overrides)
    return answer(**base)


def fake_response(
    payload: dict[str, Any] | str,
    *,
    input_tokens: int = 600,
    cached: int = 0,
    output_tokens: int = 150,
    reasoning: int = 40,
    status: str = "completed",
    refusal: str | None = None,
) -> SimpleNamespace:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    if refusal:
        content = [SimpleNamespace(type="refusal", refusal=refusal)]
        text = ""
    else:
        content = [SimpleNamespace(type="output_text", text=text)]
    return SimpleNamespace(
        id="resp_test",
        model="test-model",
        status=status,
        incomplete_details=SimpleNamespace(reason="max_output_tokens")
        if status != "completed"
        else None,
        output=[SimpleNamespace(type="message", content=content)],
        output_text=text,
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            input_tokens_details=SimpleNamespace(cached_tokens=cached),
            output_tokens=output_tokens,
            output_tokens_details=SimpleNamespace(reasoning_tokens=reasoning),
        ),
    )


class FakeResponses:
    def __init__(self, reply: Callable[[dict[str, Any]], Any]) -> None:
        self.reply = reply
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        return self.reply(kwargs)


class FakeTranscriptions:
    def __init__(self, text: str) -> None:
        self.text = text
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.requests.append({k: v for k, v in kwargs.items() if k != "file"})
        return SimpleNamespace(text=self.text)


class FakeClient:
    def __init__(
        self,
        reply: Callable[[dict[str, Any]], Any],
        transcript: str = "Engine 2 on scene at Gristmill Way, the vehicle fire is knocked down.",
    ) -> None:
        self.responses = FakeResponses(reply)
        self.audio = SimpleNamespace(transcriptions=FakeTranscriptions(transcript))


def reply_by_transcript(table: dict[str, dict[str, Any]]) -> Callable[[dict[str, Any]], Any]:
    """Answer with the first entry whose key appears in the request input."""

    def reply(request: dict[str, Any]) -> Any:
        for needle, payload in table.items():
            if needle in request["input"]:
                return fake_response(payload)
        raise AssertionError(f"no fake answer for input: {request['input']!r}")

    return reply


def no_client() -> Any:
    raise AssertionError("this run must not create an API client")


def write_call(
    folder: Path,
    call_id: str,
    timestamp: str,
    channel: str = "Dispatch",
    *,
    text: str | None = None,
    audio: bytes | None = None,
    **meta: Any,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    if text is not None:
        (folder / f"{call_id}.txt").write_text(text, encoding="utf-8")
    if audio is not None:
        (folder / f"{call_id}.wav").write_bytes(audio)
    payload = {"timestamp": timestamp, "channel": channel, **meta}
    (folder / f"{call_id}.json").write_text(json.dumps(payload), encoding="utf-8")
