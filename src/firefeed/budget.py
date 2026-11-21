"""A per-run cap on API requests, shared by transcription and analysis."""

from __future__ import annotations


class RequestLimitReached(RuntimeError):
    """The run already made as many API requests as the limit allows."""


class RequestBudget:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0

    def take(self) -> None:
        if self.used >= self.limit:
            raise RequestLimitReached(f"API request limit reached ({self.limit} per run)")
        self.used += 1
