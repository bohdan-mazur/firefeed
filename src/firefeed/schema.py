"""The JSON schema the model answers with, plus checks the schema cannot express."""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

INCIDENT_TYPES = (
    "structure_fire",
    "vehicle_fire",
    "wildland_fire",
    "mva_with_fire",
    "other_fire",
    "fire_alarm",
    "smoke_investigation",
    "gas_leak",
    "medical",
    "other_incident",
    "unknown",
    "not_incident",
)
STATUSES = (
    "dispatched",
    "en_route",
    "on_scene",
    "working",
    "under_control",
    "cleared",
    "cancelled",
    "none",
)

SCHEMA_NAME = "radio_call_analysis"

# Strict Structured Outputs: every property required, no extra keys, null only where allowed.
ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "is_fire": {
            "type": "boolean",
            "description": "True when the transmission is part of the response to a fire call.",
        },
        "incident_type": {"type": "string", "enum": list(INCIDENT_TYPES)},
        "location_as_heard": {
            "type": ["string", "null"],
            "description": "Incident location as spoken, or null when none is spoken.",
        },
        "units": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Fire units named in the transmission, such as Engine 1.",
        },
        "status": {"type": "string", "enum": list(STATUSES)},
        "summary": {"type": "string", "description": "One plain sentence."},
        "confidence": {"type": "number", "description": "From 0 to 1."},
    },
    "required": [
        "is_fire",
        "incident_type",
        "location_as_heard",
        "units",
        "status",
        "summary",
        "confidence",
    ],
    "additionalProperties": False,
}

_validator = Draft202012Validator(ANALYSIS_SCHEMA)


def validate_analysis(data: Any) -> list[str]:
    """Problems with an answer; an empty list means it can be used."""
    errors = sorted(
        f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
        for e in _validator.iter_errors(data)
    )
    if errors:
        return errors
    problems = []
    if not 0 <= data["confidence"] <= 1:
        problems.append("confidence: must be between 0 and 1")
    if (data["incident_type"] == "not_incident") != (data["status"] == "none"):
        problems.append("status: 'none' goes with incident_type 'not_incident', and only with it")
    if not data["summary"].strip():
        problems.append("summary: empty")
    if any(not unit.strip() for unit in data["units"]):
        problems.append("units: empty unit name")
    return problems
