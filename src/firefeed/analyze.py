"""Structured analysis of one transcript with the OpenAI Responses API.

Every answer is checked against the JSON schema before it is used or cached. A cache hit
costs nothing; the cache key covers the model, settings, instructions, schema and input.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import openai

from firefeed.budget import RequestBudget
from firefeed.cache import JsonCache, stable_hash
from firefeed.config import AnalysisConfig
from firefeed.costs import estimate_tokens
from firefeed.models import CallInput, Usage
from firefeed.prompt import PROMPT_VERSION, build_input, build_instructions
from firefeed.schema import ANALYSIS_SCHEMA, SCHEMA_NAME, validate_analysis

log = logging.getLogger("firefeed.analyze")
NAMESPACE = "analyze"
CACHE_FORMAT = 1
# One more try when an answer fails validation.
MAX_ATTEMPTS = 2
# Errors worth recording and moving on from; anything else (bad key, unknown model) stops the run.
TRANSIENT_ERRORS = (openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError)
# A 429 that means "no money left" rather than "too fast": waiting does not help.
QUOTA_CODES = frozenset(
    {"insufficient_quota", "credit_balance_exhausted", "billing_hard_limit_reached"}
)


class QuotaExhausted(RuntimeError):
    """The API account has no credits or quota left."""

    def __init__(self) -> None:
        super().__init__(
            "the API account has no credits left (insufficient_quota). Add credits in the "
            "OpenAI billing settings, then run again; answers so far stay cached."
        )


def is_quota_error(exc: BaseException) -> bool:
    body = getattr(exc, "body", None)
    error = body.get("error", body) if isinstance(body, dict) else None
    codes = {getattr(exc, "code", None), getattr(exc, "type", None)}
    if isinstance(error, dict):
        codes |= {error.get("code"), error.get("type")}
    return bool(codes & QUOTA_CODES)


@dataclass
class AnalysisOutcome:
    analysis: dict | None
    cache_hit: bool = False
    usage: Usage = field(default_factory=Usage)
    error: str | None = None
    needs_request: bool = False
    estimate: Usage | None = None
    cache_key: str | None = None
    recorded_at: str | None = None


def usage_from_response(response: Any) -> Usage:
    usage = getattr(response, "usage", None)
    if usage is None:
        return Usage(requests=1)
    in_details = getattr(usage, "input_tokens_details", None)
    out_details = getattr(usage, "output_tokens_details", None)
    return Usage(
        requests=1,
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        cached_input_tokens=getattr(in_details, "cached_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        reasoning_tokens=getattr(out_details, "reasoning_tokens", 0) or 0,
    )


def parse_response(response: Any) -> tuple[dict | None, str | None]:
    """The validated answer, or an error message."""
    status = getattr(response, "status", None)
    if status not in (None, "completed"):
        details = getattr(response, "incomplete_details", None)
        reason = getattr(details, "reason", None)
        return None, f"response status {status}" + (f" ({reason})" if reason else "")
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", None) or []:
            if getattr(content, "type", None) == "refusal":
                return None, f"model refused: {getattr(content, 'refusal', '')}"
    text = getattr(response, "output_text", "") or ""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"answer is not JSON ({exc})"
    problems = validate_analysis(data)
    if problems:
        return None, "answer does not match the schema: " + "; ".join(problems)
    return data, None


class Analyzer:
    def __init__(
        self,
        cfg: AnalysisConfig,
        cache: JsonCache,
        client: Callable[[], Any],
        budget: RequestBudget,
        local_knowledge: str | None = None,
    ) -> None:
        self.cfg = cfg
        self.cache = cache
        self.client = client
        self.budget = budget
        self.instructions = build_instructions(local_knowledge if cfg.use_gazetteer_hints else None)

    def request(self, call: CallInput, transcript: str) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self.cfg.model,
            "instructions": self.instructions,
            "input": build_input(call.channel, transcript),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": SCHEMA_NAME,
                    "schema": ANALYSIS_SCHEMA,
                    "strict": True,
                }
            },
            "max_output_tokens": self.cfg.max_output_tokens,
            "store": False,
        }
        if self.cfg.reasoning_effort:
            request["reasoning"] = {"effort": self.cfg.reasoning_effort}
        return request

    @staticmethod
    def key(request: dict[str, Any]) -> str:
        return stable_hash({"cache_format": CACHE_FORMAT, "request": request})

    def estimate(self, request: dict[str, Any]) -> Usage:
        prompt = request["instructions"] + request["input"] + json.dumps(ANALYSIS_SCHEMA)
        return Usage(
            requests=1,
            input_tokens=estimate_tokens(prompt),
            output_tokens=self.cfg.estimated_output_tokens,
        )

    def analyze(
        self, call: CallInput, transcript: str, *, dry_run: bool = False
    ) -> AnalysisOutcome:
        request = self.request(call, transcript)
        key = self.key(request)
        cached = self.cache.get(NAMESPACE, key)
        if cached is not None:
            problems = validate_analysis(cached.get("output"))
            if not problems:
                log.log(
                    logging.DEBUG if dry_run else logging.INFO, "analyze %s: cache hit", call.id
                )
                return AnalysisOutcome(
                    analysis=cached["output"],
                    cache_hit=True,
                    usage=Usage.from_dict(cached.get("usage")),
                    cache_key=key,
                    recorded_at=cached.get("created_at"),
                )
            log.warning(
                "analyze %s: cached answer is invalid, asking again (%s)",
                call.id,
                "; ".join(problems),
            )
        if dry_run:
            return AnalysisOutcome(
                analysis=None, needs_request=True, estimate=self.estimate(request)
            )

        usage = Usage()
        error = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self.budget.take()
            try:
                response = self.client().responses.create(**request)
            except TRANSIENT_ERRORS as exc:
                if is_quota_error(exc):
                    raise QuotaExhausted() from None
                code = getattr(exc, "code", None)
                error = f"API error: {type(exc).__name__}" + (f" ({code})" if code else "")
                log.warning("analyze %s: %s", call.id, error)
                return AnalysisOutcome(analysis=None, usage=usage, error=error)
            step = usage_from_response(response)
            usage += step
            log.info(
                "analyze %s: API request %d (model %s) input=%d cached=%d output=%d reasoning=%d",
                call.id,
                attempt,
                getattr(response, "model", self.cfg.model),
                step.input_tokens,
                step.cached_input_tokens,
                step.output_tokens,
                step.reasoning_tokens,
            )
            data, error = parse_response(response)
            if data is not None:
                created = datetime.now(UTC).isoformat(timespec="seconds")
                self.cache.put(
                    NAMESPACE,
                    key,
                    {
                        "cache_format": CACHE_FORMAT,
                        "call_id": call.id,
                        "created_at": created,
                        "model": getattr(response, "model", self.cfg.model),
                        "response_id": getattr(response, "id", None),
                        "prompt_version": PROMPT_VERSION,
                        "output": data,
                        "usage": usage.to_dict(),
                    },
                )
                return AnalysisOutcome(
                    analysis=data, usage=usage, cache_key=key, recorded_at=created
                )
            log.warning("analyze %s: attempt %d rejected: %s", call.id, attempt, error)
        return AnalysisOutcome(analysis=None, usage=usage, error=error)
