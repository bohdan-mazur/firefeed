"""Run the steps: ingest, transcribe, analyze, cluster, export, and notify when enabled.

Before any request the run counts the cache misses and estimates their cost. It refuses to start
when the count is above the per-run limit, and asks for confirmation above the cost threshold.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from firefeed.analyze import AnalysisOutcome, Analyzer
from firefeed.budget import RequestBudget
from firefeed.cache import JsonCache
from firefeed.cluster import cluster_calls
from firefeed.config import Config
from firefeed.costs import total_cost
from firefeed.export import build_feed, write_json
from firefeed.gazetteer import Gazetteer
from firefeed.ingest import load_calls
from firefeed.models import CallResult, Usage
from firefeed.notify import Notifier
from firefeed.transcribe import Transcriber

log = logging.getLogger("firefeed.pipeline")

# Placeholder length for the analysis estimate of an audio call that is not transcribed yet.
ASSUMED_TRANSCRIPT = "x" * 600


class MissingApiKey(RuntimeError):
    pass


class TooManyRequests(RuntimeError):
    pass


class ConfirmationRequired(RuntimeError):
    pass


def default_client() -> Any:
    from openai import OpenAI

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise MissingApiKey(
            "OPENAI_API_KEY is not set. Put it in .env (see .env.example) or the environment."
        )
    return OpenAI(api_key=key, max_retries=3, timeout=60.0)


class LazyClient:
    """Creates the API client on first use, so cached and dry runs need no key."""

    def __init__(self, factory: Callable[[], Any]) -> None:
        self.factory = factory
        self.instance: Any = None

    def __call__(self) -> Any:
        if self.instance is None:
            self.instance = self.factory()
        return self.instance


@dataclass
class RunSummary:
    calls: int = 0
    cache_hits: int = 0
    requests_needed: int = 0
    estimate: Usage = field(default_factory=Usage)
    estimated_cost_usd: float = 0.0
    api_requests: int = 0
    cost_this_run_usd: float = 0.0
    errors: dict[str, str] = field(default_factory=dict)
    incidents: int = 0
    feed_path: Path | None = None
    dry_run: bool = False


def run(
    cfg: Config,
    *,
    dry_run: bool = False,
    assume_yes: bool = False,
    client_factory: Callable[[], Any] | None = None,
    env: Mapping[str, str] | None = None,
) -> RunSummary:
    env = os.environ if env is None else env
    calls = load_calls(cfg.input_dir)
    log.info("ingest: %d calls from %s", len(calls), cfg.input_dir)
    gazetteer = Gazetteer.load(cfg.gazetteer) if cfg.gazetteer else Gazetteer()
    cache = JsonCache(cfg.cache_dir)
    budget = RequestBudget(cfg.limits.max_api_requests_per_run)
    client = LazyClient(client_factory or default_client)
    transcriber = Transcriber(cfg.transcribe, cache, client, budget)
    analyzer = Analyzer(cfg.analysis, cache, client, budget, gazetteer.hints())
    summary = RunSummary(calls=len(calls), dry_run=dry_run)

    # Pass 1: what is cached, what would need the API, and what would it cost.
    for call in calls:
        transcript = transcriber.transcribe(call, dry_run=True)
        if transcript.needs_request:
            summary.requests_needed += 1
            summary.estimate += transcript.usage
        outcome = analyzer.analyze(call, transcript.text or ASSUMED_TRANSCRIPT, dry_run=True)
        if outcome.needs_request:
            summary.requests_needed += 1
            assert outcome.estimate is not None
            summary.estimate += outcome.estimate
        else:
            summary.cache_hits += 1
    summary.estimated_cost_usd = total_cost(
        summary.estimate, cfg.analysis.price_per_million, cfg.transcribe.price_per_minute
    )
    log.info(
        "plan: %d calls, %d cached, %d API request(s) needed, estimated %d input + %d output "
        "tokens, about $%.4f (estimate)",
        len(calls),
        summary.cache_hits,
        summary.requests_needed,
        summary.estimate.input_tokens,
        summary.estimate.output_tokens,
        summary.estimated_cost_usd,
    )
    if dry_run:
        log.info("dry run: no API requests made")
        return summary
    limit = cfg.limits.max_api_requests_per_run
    if summary.requests_needed > limit:
        raise TooManyRequests(
            f"{summary.requests_needed} API requests needed, the limit is {limit} per run "
            "([limits] max_api_requests_per_run, or --max-requests)"
        )
    if summary.estimated_cost_usd > cfg.limits.confirm_above_usd and not assume_yes:
        raise ConfirmationRequired(
            f"estimated cost ${summary.estimated_cost_usd:.4f} is above "
            f"${cfg.limits.confirm_above_usd:.2f}; run again with --yes to go ahead"
        )

    # Pass 2: the real run.
    this_run = Usage()
    results: list[CallResult] = []
    for call in calls:
        transcript = transcriber.transcribe(call)
        if transcript.text:
            outcome = analyzer.analyze(call, transcript.text)
        else:
            outcome = AnalysisOutcome(analysis=None, error="empty transcript")
        result = CallResult(
            call=call,
            transcript=transcript.text or "",
            transcript_source=transcript.source,
            analysis=outcome.analysis,
            error=outcome.error,
            cache_hit=outcome.cache_hit,
        )
        result.usage += transcript.usage
        result.usage += outcome.usage
        result.cache_keys = tuple(k for k in (transcript.cache_key, outcome.cache_key) if k)
        result.recorded_at = outcome.recorded_at or transcript.recorded_at
        if not transcript.cache_hit:
            this_run += transcript.usage
        if not outcome.cache_hit:
            this_run += outcome.usage
        if result.analysis is not None:
            result.units, result.unknown_units = gazetteer.normalize_units(result.analysis["units"])
            if result.is_incident_traffic:
                result.street = gazetteer.match_street(result.analysis["location_as_heard"])
            if result.unknown_units:
                log.warning(
                    "analyze %s: units not in the gazetteer: %s",
                    call.id,
                    ", ".join(result.unknown_units),
                )
        else:
            summary.errors[call.id] = result.error or "no analysis"
        results.append(result)

    incidents = cluster_calls(results, cfg.cluster)
    summary.incidents = len(incidents)
    feed = build_feed(results, incidents, cfg=cfg, gazetteer=gazetteer)
    summary.feed_path = write_json(cfg.output_dir / "feed.json", feed)
    Notifier(cfg.notify, env, cfg.cache_dir / "notified.json").send_new(feed["incidents"])

    summary.api_requests = this_run.requests
    summary.cost_this_run_usd = total_cost(
        this_run, cfg.analysis.price_per_million, cfg.transcribe.price_per_minute
    )
    log.info(
        "done: %d calls, %d incidents, %d API request(s) this run, cost this run $%.6f, "
        "%d error(s); wrote %s",
        len(results),
        len(incidents),
        this_run.requests,
        summary.cost_this_run_usd,
        len(summary.errors),
        summary.feed_path,
    )
    return summary
