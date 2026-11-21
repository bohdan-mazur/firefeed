"""Instructions for the analysis model.

The cache key includes the full instructions, so any wording change makes the next run ask the
model again. Bump PROMPT_VERSION with every change so exported results say which prompt they used.
"""

from __future__ import annotations

PROMPT_VERSION = "2026-11-21.1"

INSTRUCTIONS = """\
You analyze one transmission of fire department radio traffic and answer with JSON that matches \
the schema.

The transcript comes from speech-to-text or a radio log. It can contain misheard or split words \
("Oak wood" for "Oakwood"), 10-codes and call signs. The dispatcher and "Command" (the incident \
commander) are roles, not units.

Judge this transmission on its own and do not add facts it does not state.

Fields:
- is_fire: true when the transmission is part of the response to a fire call: a reported, \
suspected or confirmed fire, smoke or burning odor, or a fire alarm. This includes fireground \
work (search, water supply, ventilation, overhaul) and status updates, and it stays true when \
the crew finds no fire. false for medical calls, gas leaks, crashes without fire, public \
assists, radio checks, announcements, training notices and unit status.
- incident_type, one of:
  structure_fire: fire in or on a building;
  vehicle_fire: fire in a car or truck, without a crash;
  wildland_fire: grass, brush or forest fire;
  mva_with_fire: vehicle crash with fire;
  other_fire: dumpster, rubbish or other outdoor fire;
  fire_alarm: automatic fire alarm activation;
  smoke_investigation: reported smoke or burning odor with an unknown source;
  gas_leak: gas odor or leak;
  medical: medical emergency;
  other_incident: any other incident, such as a crash without fire or a public assist;
  unknown: incident traffic that does not say what kind of incident it is;
  not_incident: radio checks, announcements, training and unit status not tied to an incident.
- location_as_heard: the incident location as spoken: address, street, intersection, or a \
command name such as "Maple Command", which is named after the street. Join obvious \
speech-to-text splits. null when no location is spoken and for not_incident traffic. A place \
units go to or come from (a hospital, a station, a fuel stop) is not the incident location.
- units: every fire unit named, as type and number ("Engine 1", "Ladder 1", "Battalion 1"). \
Empty list when none is named.
- status, the stage this transmission reports:
  dispatched: units are sent to a new call;
  en_route: a unit reports it is responding;
  on_scene: arrival and first report;
  working: active operations, or a request for more resources;
  under_control: fire knocked down or contained;
  cleared: units clear, back in service;
  cancelled: the response is called off, or no emergency is found (false alarm, unfounded);
  none: not about an incident.
- summary: one plain sentence of at most 25 words about this transmission.
- confidence: from 0 to 1, how sure you are about is_fire and incident_type.
"""


def build_instructions(local_knowledge: str | None) -> str:
    if not local_knowledge:
        return INSTRUCTIONS
    return f"{INSTRUCTIONS}\nLocal knowledge:\n{local_knowledge}\n"


def build_input(channel: str, transcript: str) -> str:
    return f"Channel: {channel}\nTranscript:\n{transcript.strip()}"
