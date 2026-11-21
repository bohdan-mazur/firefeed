from datetime import datetime

from firefeed.cluster import cluster_calls
from firefeed.config import ClusterConfig
from firefeed.models import CallInput, CallResult
from helpers import answer, not_incident

CFG = ClusterConfig(window_s=120, max_gap_s=3600)


def result(
    call_id: str,
    time: str,
    *,
    status: str,
    street: str | None = None,
    units: tuple[str, ...] = (),
    channel: str = "Dispatch",
    incident_type: str = "structure_fire",
) -> CallResult:
    call = CallInput(
        id=call_id,
        timestamp=datetime.fromisoformat(f"2026-10-17T{time}-05:00"),
        channel=channel,
    )
    if incident_type == "not_incident":
        analysis = not_incident(units=list(units))
    else:
        analysis = answer(
            status=status, incident_type=incident_type, location_as_heard=street, units=list(units)
        )
    return CallResult(
        call=call,
        transcript="",
        transcript_source="text",
        analysis=analysis,
        street=street,
        units=list(units),
    )


def groups(results: list[CallResult]) -> list[list[str]]:
    return [[c.call.id for c in i.calls] for i in cluster_calls(results, CFG)]


def test_incident_from_dispatch_to_clear_then_a_new_one() -> None:
    results = [
        result(
            "a",
            "13:04:00",
            status="dispatched",
            street="Bellwether Avenue",
            units=("Engine 1", "Ladder 1"),
        ),
        result("b", "13:08:00", status="on_scene", street="Bellwether Avenue", units=("Engine 1",)),
        result("c", "13:09:00", status="working", units=("Ladder 1",), channel="Fireground 2"),
        result(
            "d",
            "13:50:00",
            status="cleared",
            street="Bellwether Avenue",
            units=("Engine 1", "Ladder 1"),
        ),
        result(
            "e",
            "14:00:00",
            status="dispatched",
            street="Gristmill Way",
            units=("Engine 1",),
            incident_type="vehicle_fire",
        ),
        result("f", "14:05:00", status="on_scene", units=("Engine 1",), incident_type="unknown"),
    ]

    incidents = cluster_calls(results, CFG)

    assert [[c.call.id for c in i.calls] for i in incidents] == [["a", "b", "c", "d"], ["e", "f"]]
    assert [i.id for i in incidents] == ["inc-01", "inc-02"]
    assert incidents[0].closed and incidents[0].status == "cleared"
    assert incidents[0].street == "Bellwether Avenue"
    assert incidents[0].units == ["Engine 1", "Ladder 1"]
    assert incidents[1].incident_type == "vehicle_fire"
    assert [r.incident_id for r in results] == ["inc-01"] * 4 + ["inc-02"] * 2


def test_new_dispatch_elsewhere_is_a_new_incident_despite_a_shared_unit() -> None:
    results = [
        result("a", "13:00:00", status="dispatched", street="Tinsmith Street", units=("Engine 3",)),
        result("b", "13:20:00", status="dispatched", street="Gristmill Way", units=("Engine 3",)),
    ]

    assert groups(results) == [["a"], ["b"]]


def test_different_streets_never_join() -> None:
    results = [
        result("a", "13:00:00", status="dispatched", street="Tinsmith Street", units=("Engine 3",)),
        result("b", "13:05:00", status="on_scene", street="Gristmill Way", units=("Engine 3",)),
    ]

    assert groups(results) == [["a"], ["b"]]


def test_traffic_that_is_not_about_an_incident_stays_out() -> None:
    results = [
        result("a", "13:00:00", status="dispatched", street="Tinsmith Street", units=("Engine 3",)),
        result("b", "13:01:00", status="none", units=("Engine 3",), incident_type="not_incident"),
        result("c", "13:05:00", status="on_scene", units=("Engine 3",)),
    ]

    assert groups(results) == [["a", "c"]]
    assert results[1].incident_id is None


def test_window_links_a_call_with_no_street_and_no_units() -> None:
    results = [
        result("a", "13:00:00", status="dispatched", street="Tinsmith Street", units=("Engine 3",)),
        result("b", "13:01:30", status="working"),
        result("c", "13:10:00", status="working"),
    ]

    assert groups(results) == [["a", "b"], ["c"]]


def test_window_is_per_channel() -> None:
    results = [
        result("a", "13:00:00", status="dispatched", street="Tinsmith Street", units=("Engine 3",)),
        result("b", "13:00:30", status="working", channel="Fireground 2"),
    ]

    assert groups(results) == [["a"], ["b"]]


def test_max_gap() -> None:
    results = [
        result("a", "13:00:00", status="dispatched", street="Tinsmith Street", units=("Engine 1",)),
        result("b", "14:30:00", status="on_scene", street="Tinsmith Street", units=("Engine 1",)),
    ]

    assert groups(results) == [["a"], ["b"]]


def test_closed_incident_takes_one_more_closing_call_within_the_window() -> None:
    results = [
        result(
            "a",
            "13:00:00",
            status="dispatched",
            street="Tinsmith Street",
            units=("Engine 1", "Medic 2"),
        ),
        result("b", "13:30:00", status="cleared", units=("Engine 1",)),
        result("c", "13:31:00", status="cleared", units=("Medic 2",)),
        result("d", "13:40:00", status="on_scene", units=("Medic 2",)),
    ]

    assert groups(results) == [["a", "b", "c"], ["d"]]


def test_incident_type_from_the_first_specific_call() -> None:
    results = [
        result("a", "13:00:00", status="working", units=("Engine 1",), incident_type="unknown"),
        result(
            "b", "13:01:00", status="working", units=("Engine 1",), incident_type="wildland_fire"
        ),
    ]

    (incident,) = cluster_calls(results, CFG)

    assert incident.incident_type == "wildland_fire"
    assert incident.is_fire
