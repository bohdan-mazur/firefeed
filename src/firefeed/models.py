"""Plain records passed between pipeline steps."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class CallInput:
    """One radio call found in the input folder."""

    id: str
    timestamp: datetime
    channel: str
    text_path: Path | None = None
    audio_path: Path | None = None
    duration_s: float | None = None


@dataclass
class Usage:
    """API usage: measured from responses, or estimated in a dry run."""

    requests: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    audio_seconds: float = 0.0

    def __iadd__(self, other: Usage) -> Usage:
        for f in fields(self):
            setattr(self, f.name, getattr(self, f.name) + getattr(other, f.name))
        return self

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> Usage:
        data = data or {}
        return cls(**{f.name: data.get(f.name, 0) for f in fields(cls)})


@dataclass
class CallResult:
    """A call after transcription and analysis."""

    call: CallInput
    transcript: str
    transcript_source: str  # "text" or "transcribed"
    analysis: dict | None = None
    error: str | None = None
    street: str | None = None
    units: list[str] = field(default_factory=list)
    unknown_units: list[str] = field(default_factory=list)
    incident_id: str | None = None
    cache_hit: bool = False
    # Usage recorded when the answers were produced (read back from the cache on later runs).
    usage: Usage = field(default_factory=Usage)
    cache_keys: tuple[str, ...] = ()
    recorded_at: str | None = None

    @property
    def is_incident_traffic(self) -> bool:
        a = self.analysis
        return a is not None and a["incident_type"] != "not_incident" and a["status"] != "none"
