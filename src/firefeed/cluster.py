"""Group related calls into incidents.

Rules, in order, for a call that is about an incident:
1. Only open incidents whose last call is at most ``max_gap_s`` old are candidates.
2. Two different known streets never join.
3. A new dispatch joins only an incident at the same street; otherwise it starts a new one.
4. Same street links strongest, then a shared unit, then (for a call with no street and no
   units) the same channel within ``window_s``.
5. A call that reports ``cleared`` or ``cancelled`` closes its incident. A closed incident still
   takes another closing call heard within ``window_s`` ("Medic 2 is back in service too").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from firefeed.config import ClusterConfig
from firefeed.models import CallResult

CLOSING_STATUSES = frozenset({"cleared", "cancelled"})
VAGUE_TYPES = frozenset({"unknown", "not_incident"})


@dataclass
class Incident:
    id: str = ""
    calls: list[CallResult] = field(default_factory=list)
    closed: bool = False

    @property
    def start(self) -> datetime:
        return self.calls[0].call.timestamp

    @property
    def end(self) -> datetime:
        return self.calls[-1].call.timestamp

    @property
    def street(self) -> str | None:
        return next((c.street for c in self.calls if c.street), None)

    @property
    def units(self) -> list[str]:
        seen: list[str] = []
        for c in self.calls:
            seen.extend(u for u in c.units if u not in seen)
        return seen

    @property
    def incident_type(self) -> str:
        for c in self.calls:
            assert c.analysis is not None
            if c.analysis["incident_type"] not in VAGUE_TYPES:
                return c.analysis["incident_type"]
        return "unknown"

    @property
    def is_fire(self) -> bool:
        return any(c.analysis is not None and c.analysis["is_fire"] for c in self.calls)

    @property
    def status(self) -> str:
        last = self.calls[-1].analysis
        assert last is not None
        return last["status"]

    def last_on_channel(self, channel: str) -> datetime | None:
        times = [c.call.timestamp for c in self.calls if c.call.channel == channel]
        return times[-1] if times else None


def link_score(result: CallResult, incident: Incident, cfg: ClusterConfig) -> int:
    """How strongly ``result`` belongs to ``incident``; 0 means it does not."""
    assert result.analysis is not None
    when = result.call.timestamp
    gap = (when - incident.end).total_seconds()
    if gap < 0 or gap > cfg.max_gap_s:
        return 0
    status = result.analysis["status"]
    if incident.closed and not (status in CLOSING_STATUSES and gap <= cfg.window_s):
        return 0
    if result.street and incident.street and result.street != incident.street:
        return 0
    same_street = result.street is not None and result.street == incident.street
    if status == "dispatched" and not same_street:
        return 0
    if same_street:
        return 3
    if set(result.units) & set(incident.units):
        return 2
    if not result.street and not result.units:
        last = incident.last_on_channel(result.call.channel)
        if last is not None and (when - last).total_seconds() <= cfg.window_s:
            return 1
    return 0


def cluster_calls(results: list[CallResult], cfg: ClusterConfig) -> list[Incident]:
    """Incidents in order of their first call. Sets ``incident_id`` on every grouped call."""
    incidents: list[Incident] = []
    for result in sorted(results, key=lambda r: (r.call.timestamp, r.call.id)):
        result.incident_id = None
        if not result.is_incident_traffic:
            continue
        best: Incident | None = None
        best_rank: tuple[int, datetime] | None = None
        for incident in incidents:
            score = link_score(result, incident, cfg)
            if score and (best_rank is None or (score, incident.end) > best_rank):
                best, best_rank = incident, (score, incident.end)
        if best is None:
            best = Incident()
            incidents.append(best)
        best.calls.append(result)
        assert result.analysis is not None
        if result.analysis["status"] in CLOSING_STATUSES:
            best.closed = True

    for number, incident in enumerate(incidents, start=1):
        incident.id = f"inc-{number:02d}"
        for c in incident.calls:
            c.incident_id = incident.id
    return incidents
