"""Build feed.json, the file the demo site reads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from firefeed import SYNTHETIC_NOTICE, __version__
from firefeed.cluster import Incident
from firefeed.config import Config
from firefeed.costs import total_cost
from firefeed.gazetteer import Gazetteer
from firefeed.models import CallResult, Usage
from firefeed.prompt import PROMPT_VERSION

FEED_FORMAT = 1


def _call(result: CallResult) -> dict[str, Any]:
    call = result.call
    return {
        "id": call.id,
        "timestamp": call.timestamp.isoformat(),
        "channel": call.channel,
        "duration_s": call.duration_s,
        "audio": call.audio_path.name if call.audio_path else None,
        "transcript": result.transcript,
        "transcript_source": result.transcript_source,
        "analysis": result.analysis,
        "error": result.error,
        "street": result.street,
        "units": result.units,
        "unknown_units": result.unknown_units,
        "incident_id": result.incident_id,
    }


def _incident(incident: Incident) -> dict[str, Any]:
    first = incident.calls[0].analysis or {}
    return {
        "id": incident.id,
        "call_ids": [c.call.id for c in incident.calls],
        "start": incident.start.isoformat(),
        "end": incident.end.isoformat(),
        "channels": sorted({c.call.channel for c in incident.calls}),
        "incident_type": incident.incident_type,
        "is_fire": incident.is_fire,
        "street": incident.street,
        "units": incident.units,
        "status": incident.status,
        "summary": first.get("summary"),
    }


def recorded_usage(results: list[CallResult]) -> Usage:
    """Usage recorded when the answers were produced, each cache entry counted once."""
    total = Usage()
    seen: set[str] = set()
    for r in results:
        if r.cache_keys and set(r.cache_keys) <= seen:
            continue
        seen.update(r.cache_keys)
        total += r.usage
    return total


def build_feed(
    results: list[CallResult],
    incidents: list[Incident],
    *,
    cfg: Config,
    gazetteer: Gazetteer,
) -> dict[str, Any]:
    usage = recorded_usage(results)
    analyzed = sum(1 for r in results if r.analysis is not None)
    prices = cfg.analysis.price_per_million
    cost = total_cost(usage, prices, cfg.transcribe.price_per_minute)
    recorded = sorted(r.recorded_at for r in results if r.recorded_at)
    channels = [ch for ch in gazetteer.channels if any(r.call.channel == ch for r in results)]
    channels += sorted({r.call.channel for r in results} - set(channels))
    return {
        "format": FEED_FORMAT,
        "notice": SYNTHETIC_NOTICE if cfg.synthetic else None,
        "dataset": {
            "name": cfg.dataset_name,
            "synthetic": cfg.synthetic,
            "calls": len(results),
            "analyzed": analyzed,
            "incidents": len(incidents),
        },
        "pipeline": {
            "version": __version__,
            "analysis_model": cfg.analysis.model,
            "reasoning_effort": cfg.analysis.reasoning_effort,
            "prompt_version": PROMPT_VERSION,
            "transcription_model": (
                cfg.transcribe.model
                if any(r.transcript_source == "transcribed" for r in results)
                else None
            ),
        },
        "usage": {
            "api_requests": usage.requests,
            "input_tokens": usage.input_tokens,
            "cached_input_tokens": usage.cached_input_tokens,
            "output_tokens": usage.output_tokens,
            "reasoning_tokens": usage.reasoning_tokens,
            "audio_seconds": round(usage.audio_seconds, 1),
            "cost_usd": round(cost, 6),
            "cost_per_call_usd": round(cost / analyzed, 7) if analyzed and usage.requests else None,
            "recorded_from": recorded[0] if recorded else None,
            "recorded_to": recorded[-1] if recorded else None,
            "prices": {
                "input_per_million": prices.input,
                "cached_input_per_million": prices.cached_input,
                "output_per_million": prices.output,
                "transcription_per_minute": cfg.transcribe.price_per_minute,
                "source": cfg.price_source,
                "checked": cfg.prices_checked,
            },
        },
        "channels": channels,
        "calls": [_call(r) for r in results],
        "incidents": [_incident(i) for i in incidents],
    }


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path
