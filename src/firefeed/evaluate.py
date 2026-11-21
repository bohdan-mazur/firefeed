"""Compare pipeline output (feed.json) with the expected answers (spec.csv)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

FIELDS = ("is_fire", "incident_type", "street", "units", "status")
SPEC_COLUMNS = frozenset(
    {"call_id", "incident_id", "is_fire", "incident_type", "street", "units", "status"}
)


@dataclass(frozen=True)
class Expected:
    call_id: str
    incident_id: str | None
    is_fire: bool
    incident_type: str
    street: str | None
    units: tuple[str, ...]
    status: str

    def answer(self) -> dict[str, Any]:
        return {
            "is_fire": self.is_fire,
            "incident_type": self.incident_type,
            "street": self.street,
            "units": sorted(self.units),
            "status": self.status,
        }


def load_spec(path: Path) -> dict[str, Expected]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = SPEC_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name} lacks columns: {', '.join(sorted(missing))}")
        spec: dict[str, Expected] = {}
        for line, row in enumerate(reader, start=2):
            flag = row["is_fire"].strip().lower()
            if flag not in ("true", "false"):
                raise ValueError(f"{path.name}:{line}: is_fire must be true or false")
            call_id = row["call_id"].strip()
            if call_id in spec:
                raise ValueError(f"{path.name}:{line}: duplicate call_id {call_id}")
            spec[call_id] = Expected(
                call_id=call_id,
                incident_id=row["incident_id"].strip() or None,
                is_fire=flag == "true",
                incident_type=row["incident_type"].strip(),
                street=row["street"].strip() or None,
                units=tuple(u.strip() for u in row["units"].split(";") if u.strip()),
                status=row["status"].strip(),
            )
    return spec


def _ratio(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def _pairs(groups: dict[str, set[str]]) -> set[frozenset[str]]:
    return {frozenset(p) for g in groups.values() for p in combinations(sorted(g), 2)}


def evaluate_grouping(calls: list[dict[str, Any]], spec: dict[str, Expected]) -> dict[str, Any]:
    expected: dict[str, set[str]] = {}
    for e in spec.values():
        if e.incident_id:
            expected.setdefault(e.incident_id, set()).add(e.call_id)
    predicted: dict[str, set[str]] = {}
    for c in calls:
        if c.get("incident_id"):
            predicted.setdefault(c["incident_id"], set()).add(c["id"])

    predicted_sets = list(predicted.values())
    mismatches = []
    exact = 0
    for incident_id, members in sorted(expected.items()):
        if members in predicted_sets:
            exact += 1
            continue
        mismatches.append(
            {
                "expected_incident": incident_id,
                "expected_calls": sorted(members),
                "predicted_groups": sorted(sorted(g) for g in predicted_sets if g & members),
            }
        )
    true_pairs, pred_pairs = _pairs(expected), _pairs(predicted)
    both = true_pairs & pred_pairs
    return {
        "incidents_expected": len(expected),
        "incidents_predicted": len(predicted),
        "incidents_exact": exact,
        "pair_precision": _ratio(len(both), len(pred_pairs)),
        "pair_recall": _ratio(len(both), len(true_pairs)),
        "mismatches": mismatches,
    }


def evaluate(feed: dict[str, Any], spec: dict[str, Expected]) -> dict[str, Any]:
    calls = {c["id"]: c for c in feed["calls"]}
    rows = []
    totals = {f: [0, 0] for f in FIELDS}
    confusion = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    not_analyzed = []
    for call_id in sorted(set(spec) & set(calls)):
        exp = spec[call_id]
        call = calls[call_id]
        analysis = call.get("analysis")
        expected = exp.answer()
        model = None
        if analysis is not None:
            model = {
                "is_fire": analysis["is_fire"],
                "incident_type": analysis["incident_type"],
                "street": call.get("street"),
                "units": sorted(call.get("units") or []),
                "status": analysis["status"],
            }
            key = ("t" if model["is_fire"] == exp.is_fire else "f") + (
                "p" if model["is_fire"] else "n"
            )
            confusion[key] += 1
        else:
            not_analyzed.append(call_id)
        match = {f: model is not None and model[f] == expected[f] for f in FIELDS}
        for f in FIELDS:
            totals[f][0] += match[f]
            totals[f][1] += 1
        rows.append(
            {
                "id": call_id,
                "expected": expected,
                "model": model,
                "match": match,
                "all_match": all(match.values()),
                "location_as_heard": analysis.get("location_as_heard") if analysis else None,
                "expected_incident": exp.incident_id,
                "predicted_incident": call.get("incident_id"),
            }
        )

    tp, fp, fn = confusion["tp"], confusion["fp"], confusion["fn"]
    return {
        "format": 1,
        "notice": feed.get("notice"),
        "analysis_model": feed.get("pipeline", {}).get("analysis_model"),
        "prompt_version": feed.get("pipeline", {}).get("prompt_version"),
        "recorded_from": feed.get("usage", {}).get("recorded_from"),
        "calls_compared": len(rows),
        "calls_fully_correct": sum(1 for r in rows if r["all_match"]),
        "not_analyzed": not_analyzed,
        "missing_in_feed": sorted(set(spec) - set(calls)),
        "missing_in_spec": sorted(set(calls) - set(spec)),
        "fields": {
            f: {"correct": c, "total": t, "accuracy": _ratio(c, t)} for f, (c, t) in totals.items()
        },
        "is_fire": {**confusion, "precision": _ratio(tp, tp + fp), "recall": _ratio(tp, tp + fn)},
        "grouping": evaluate_grouping(list(calls.values()), spec),
        "calls": rows,
    }
