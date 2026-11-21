from firefeed.schema import ANALYSIS_SCHEMA, validate_analysis
from helpers import answer, not_incident


def test_valid_answers_pass() -> None:
    assert validate_analysis(answer()) == []
    assert validate_analysis(not_incident(units=["Engine 3"])) == []


def test_schema_is_strict() -> None:
    assert ANALYSIS_SCHEMA["additionalProperties"] is False
    assert set(ANALYSIS_SCHEMA["required"]) == set(ANALYSIS_SCHEMA["properties"])


def test_missing_and_extra_fields() -> None:
    data = answer(extra=1)
    del data["status"]

    problems = validate_analysis(data)

    assert any("'status' is a required property" in p for p in problems)
    assert any("'extra'" in p for p in problems)


def test_wrong_values() -> None:
    assert validate_analysis(answer(incident_type="volcano"))
    assert validate_analysis(answer(units="Engine 1"))
    assert validate_analysis(answer(is_fire="yes"))
    assert validate_analysis("not an object")


def test_rules_beyond_the_schema() -> None:
    assert validate_analysis(answer(confidence=1.5)) == ["confidence: must be between 0 and 1"]
    assert validate_analysis(answer(status="none"))
    assert validate_analysis(not_incident(status="working"))
    assert validate_analysis(answer(summary="  "))
    assert validate_analysis(answer(units=["Engine 1", " "]))
