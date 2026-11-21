import pytest

from firefeed.gazetteer import Gazetteer, normalize


def test_normalize() -> None:
    assert normalize("1420 Bellwether Ave.") == "1420 bellwether avenue"
    assert normalize("Engine One, E-1") == "engine 1 e 1"


@pytest.mark.parametrize(
    ("text", "street"),
    [
        ("1420 Bellwether Avenue", "Bellwether Avenue"),
        ("1420 Bellwether Ave.", "Bellwether Avenue"),
        ("1420 Bell weather", "Bellwether Avenue"),
        ("Bellwether Command", "Bellwether Avenue"),
        ("Thimble Crick Road", "Thimble Creek Road"),
        ("Thimble Creek Road at Fallowmere Road", "Thimble Creek Road"),
        ("Fallowmere Road and Thimble Creek Road", "Fallowmere Road"),
        ("County Road 12 at Kestrel Ridge Road", "County Road 12"),
        ("CR 12 near the bridge", "County Road 12"),
        ("parking lot, 300 Grist mill Way", "Gristmill Way"),
        ("100 Main St", "Main Street"),
    ],
)
def test_matches_streets(gazetteer: Gazetteer, text: str, street: str) -> None:
    assert gazetteer.match_street(text) == street


@pytest.mark.parametrize(
    "text",
    [None, "", "Larkmoor General", "County Road 21", "the main body of the fire", "the road"],
)
def test_no_street(gazetteer: Gazetteer, text: str | None) -> None:
    assert gazetteer.match_street(text) is None


def test_units(gazetteer: Gazetteer) -> None:
    units, unknown = gazetteer.normalize_units(
        ["Engine One", "engine 1", "Battalion Chief 1", "Truck 1", "Engine 9", ""]
    )

    assert units == ["Engine 1", "Battalion 1", "Ladder 1", "Engine 9"]
    assert unknown == ["Engine 9"]


def test_without_gazetteer_units_are_tidied_not_flagged() -> None:
    assert Gazetteer().normalize_units(["engine 3"]) == (["Engine 3"], [])
    assert Gazetteer().match_street("1420 Bellwether Avenue") is None


def test_hints(gazetteer: Gazetteer) -> None:
    hints = gazetteer.hints()

    assert hints is not None
    assert "Known streets: Bellwether Avenue; Tinsmith Street" in hints
    assert "Known units: Engine 1;" in hints
    assert '"Larkmoor" is the call sign of the dispatcher.' in hints
    assert "10-97 = arrived on scene" in hints
    assert Gazetteer().hints() is None
