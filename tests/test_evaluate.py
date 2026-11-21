from pathlib import Path

import pytest

from firefeed.evaluate import evaluate, load_spec
from helpers import answer, not_incident

SPEC = """\
call_id,timestamp,channel,incident_id,scenario,is_fire,incident_type,street,units,status,summary,note
c1,t,Dispatch,i1,structure_fire,true,structure_fire,Bellwether Avenue,Engine 1;Ladder 1,dispatched,,
c2,t,Dispatch,i1,structure_fire,true,structure_fire,,Ladder 1,working,,
c3,t,Dispatch,,radio_check,false,not_incident,,Engine 3,none,,
"""


def write_spec(tmp_path: Path, text: str = SPEC) -> Path:
    path = tmp_path / "spec.csv"
    path.write_text(text, encoding="utf-8")
    return path


def feed(c2_status: str = "on_scene", c2_incident: str = "inc-01") -> dict:
    return {
        "notice": "Demo on synthetic data. All calls, places and people are fictional.",
        "pipeline": {"analysis_model": "test-model", "prompt_version": "p1"},
        "usage": {"recorded_from": "2026-11-21T10:00:00+00:00"},
        "calls": [
            {
                "id": "c1",
                "analysis": answer(units=["Ladder 1", "Engine 1"]),
                "street": "Bellwether Avenue",
                "units": ["Ladder 1", "Engine 1"],
                "incident_id": "inc-01",
            },
            {
                "id": "c2",
                "analysis": answer(status=c2_status, location_as_heard=None, units=["Ladder 1"]),
                "street": None,
                "units": ["Ladder 1"],
                "incident_id": c2_incident,
            },
            {
                "id": "c3",
                "analysis": not_incident(units=["Engine 3"]),
                "street": None,
                "units": ["Engine 3"],
                "incident_id": None,
            },
        ],
    }


def test_scores_fields_and_grouping(tmp_path: Path) -> None:
    report = evaluate(feed(), load_spec(write_spec(tmp_path)))

    assert report["calls_compared"] == 3
    assert report["calls_fully_correct"] == 2
    assert report["fields"]["status"] == {"correct": 2, "total": 3, "accuracy": 0.6667}
    assert report["fields"]["units"]["correct"] == 3
    assert report["fields"]["street"]["correct"] == 3
    assert report["is_fire"] == {
        "tp": 2,
        "fp": 0,
        "fn": 0,
        "tn": 1,
        "precision": 1.0,
        "recall": 1.0,
    }
    grouping = report["grouping"]
    assert grouping["incidents_exact"] == 1
    assert grouping["pair_precision"] == 1.0
    assert grouping["pair_recall"] == 1.0
    assert report["calls"][1]["match"]["status"] is False


def test_split_incident_is_reported(tmp_path: Path) -> None:
    report = evaluate(
        feed(c2_status="working", c2_incident="inc-02"), load_spec(write_spec(tmp_path))
    )

    grouping = report["grouping"]
    assert grouping["incidents_exact"] == 0
    assert grouping["pair_recall"] == 0.0
    assert grouping["pair_precision"] is None
    assert grouping["mismatches"] == [
        {
            "expected_incident": "i1",
            "expected_calls": ["c1", "c2"],
            "predicted_groups": [["c1"], ["c2"]],
        }
    ]


def test_missing_analysis_counts_as_wrong(tmp_path: Path) -> None:
    data = feed()
    data["calls"][0]["analysis"] = None

    report = evaluate(data, load_spec(write_spec(tmp_path)))

    assert report["not_analyzed"] == ["c1"]
    assert report["fields"]["is_fire"]["correct"] == 2


def test_bad_spec(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="is_fire must be true or false"):
        load_spec(
            write_spec(tmp_path, SPEC.replace(",true,structure_fire,B", ",yes,structure_fire,B"))
        )
    with pytest.raises(ValueError, match="lacks columns: status"):
        load_spec(write_spec(tmp_path, "call_id,incident_id,is_fire,incident_type,street,units\n"))
