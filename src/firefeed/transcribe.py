"""Speech-to-text for calls that come as audio. Calls with a .txt transcript skip this step."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from firefeed.budget import RequestBudget
from firefeed.cache import JsonCache, stable_hash
from firefeed.config import TranscribeConfig
from firefeed.models import CallInput, Usage

log = logging.getLogger("firefeed.transcribe")
NAMESPACE = "transcribe"


@dataclass
class TranscriptOutcome:
    text: str | None
    source: str  # "text" or "transcribed"
    cache_hit: bool = False
    usage: Usage = field(default_factory=Usage)
    needs_request: bool = False
    cache_key: str | None = None
    recorded_at: str | None = None


class Transcriber:
    def __init__(
        self,
        cfg: TranscribeConfig,
        cache: JsonCache,
        client: Callable[[], Any],
        budget: RequestBudget,
    ) -> None:
        self.cfg = cfg
        self.cache = cache
        self.client = client
        self.budget = budget

    def key(self, call: CallInput) -> str:
        assert call.audio_path is not None
        digest = hashlib.sha256(call.audio_path.read_bytes()).hexdigest()
        return stable_hash(
            {
                "audio_sha256": digest,
                "model": self.cfg.model,
                "language": self.cfg.language,
                "prompt": self.cfg.prompt,
            }
        )

    def transcribe(self, call: CallInput, *, dry_run: bool = False) -> TranscriptOutcome:
        if call.text_path is not None:
            text = call.text_path.read_text(encoding="utf-8").strip()
            return TranscriptOutcome(text=text, source="text")

        key = self.key(call)
        cached = self.cache.get(NAMESPACE, key)
        if cached is not None and isinstance(cached.get("text"), str):
            log.log(logging.DEBUG if dry_run else logging.INFO, "transcribe %s: cache hit", call.id)
            return TranscriptOutcome(
                text=cached["text"],
                source="transcribed",
                cache_hit=True,
                usage=Usage.from_dict(cached.get("usage")),
                cache_key=key,
                recorded_at=cached.get("created_at"),
            )
        if dry_run:
            estimate = Usage(requests=1, audio_seconds=call.duration_s or 0.0)
            return TranscriptOutcome(
                text=None, source="transcribed", usage=estimate, needs_request=True
            )

        self.budget.take()
        options: dict[str, Any] = {}
        if self.cfg.language:
            options["language"] = self.cfg.language
        if self.cfg.prompt:
            options["prompt"] = self.cfg.prompt
        assert call.audio_path is not None
        with call.audio_path.open("rb") as audio:
            response = self.client().audio.transcriptions.create(
                model=self.cfg.model, file=audio, **options
            )
        text = (getattr(response, "text", None) or "").strip()
        if call.duration_s is None:
            log.warning("transcribe %s: audio length unknown, its cost is not counted", call.id)
        usage = Usage(requests=1, audio_seconds=call.duration_s or 0.0)
        created = datetime.now(UTC).isoformat(timespec="seconds")
        self.cache.put(
            NAMESPACE,
            key,
            {
                "call_id": call.id,
                "created_at": created,
                "model": self.cfg.model,
                "text": text,
                "usage": usage.to_dict(),
            },
        )
        log.info(
            "transcribe %s: API request (model %s), %d characters",
            call.id,
            self.cfg.model,
            len(text),
        )
        return TranscriptOutcome(
            text=text, source="transcribed", usage=usage, cache_key=key, recorded_at=created
        )
