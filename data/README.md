# Synthetic dataset: Larkmoor County

> **Demo on synthetic data. All calls, places and people are fictional.**

This folder holds the invented radio traffic that the FireFeed demo runs on. Larkmoor County, its streets, units and people do not exist. No recordings or transcripts from real radio systems, scanner sites or other services were collected or used.

## Files

| Path | What it is |
|---|---|
| `spec.csv` | One row per radio call with the expected answer (ground truth). The pipeline never reads it; only `firefeed evaluate` does. |
| `gazetteer.json` | The fictional county: 20 streets, 8 units, 3 radio channels. |
| `demo/calls/` | Pipeline input: `<id>.txt` (transcript) and `<id>.json` (time and channel) for every call. |
| `demo/cache/` | Cached model answers from the one recorded run, so a fresh clone reproduces the results without API calls. |
| `demo/out/` | Pipeline output (`feed.json`) and the comparison with `spec.csv` (`evaluation.json`). |

## The day

Saturday, 2026-10-17, 12:58–17:45 local time (UTC−05:00), during a red flag warning. 53 calls on three channels: `Dispatch` (45), `Fireground 2` (4), `Fireground 3` (4).

| Scenario | Calls | Incidents |
|---|---:|---:|
| Structure fire (house fire, kitchen fire) | 14 | 2 |
| Vehicle fire | 4 | 1 |
| Grass fire | 5 | 1 |
| Fire alarm (burnt food) | 3 | 1 |
| False call (barbecue smoker, alarm test) | 4 | 2 |
| Crash with vehicle fire | 4 | 1 |
| Dumpster fire | 2 | 1 |
| Gas leak | 4 | 1 |
| Medical call | 2 | 2 |
| Public assist (smoke detector battery) | 1 | 1 |
| Radio check | 4 | — |
| Unit status and admin | 3 | — |
| Announcement | 3 | — |
| **Total** | **53** | **13** |

36 calls belong to fire calls (`is_fire = true`) and 17 do not (32 %). Ten incidents consist of 2–9 calls each.

Some calls are hard on purpose. The `note` column in `spec.csv` names the trap: a street heard the way speech-to-text might write it ("Bell weather", "Thimble Crick", "Lantern Field"), a street given only through a command name ("Bellwether Command"), 10-codes (10-97 arrived, 10-8 back in service), announcements that mention fire or burning, a public assist about a smoke detector, and a gas call described with fire phrases ("nothing showing").

## Labeling rules

Each call is labeled from its own transcript only. The pipeline analyzes calls one at a time, so the expected answer contains only what that transmission says. Incident context comes later, from grouping.

- **`is_fire`**: `true` when the transmission is part of the response to a fire call: a reported, suspected or confirmed fire, smoke or burning odor, or a fire alarm, including fireground work (search, water supply, ventilation, overhaul) and status updates. It stays `true` when the crew finds no fire. `false` for medical calls, gas leaks, crashes without fire, public assists, radio checks, announcements and unit status.
- **`incident_type`**: `structure_fire`, `vehicle_fire`, `wildland_fire`, `mva_with_fire`, `other_fire` (dumpster, rubbish), `fire_alarm`, `smoke_investigation`, `gas_leak`, `medical`, `other_incident`, `unknown` (incident traffic that does not say what kind), `not_incident`.
- **`street`**: the street where the incident is, from the gazetteer, when the transmission names it (also through a command name such as "Bellwether Command"). The first street of an intersection is the incident street. Empty when no street is spoken, and for traffic that is not about an incident.
- **`units`**: every fire unit named in the transmission, as in the gazetteer. Dispatch and "Command" are roles, not units.
- **`status`**:
  - `dispatched`: units are sent to a new call;
  - `en_route`: a unit reports it is responding;
  - `on_scene`: arrival and first report;
  - `working`: active operations or a request for more resources;
  - `under_control`: fire knocked down or contained;
  - `cleared`: units clear, back in service;
  - `cancelled`: the response is called off, or no emergency is found (false alarm, unfounded);
  - `none`: not about an incident.

`incident_id` in `spec.csv` groups calls that belong to one incident. Calls that are not about an incident have no `incident_id`.

## Recorded run

One run on 2026-11-21 with `gpt-6-luna` (reasoning effort `low`, prompt version `2026-11-21.1`). The numbers come from `demo/out/feed.json` and `demo/out/evaluation.json` and describe these 53 synthetic calls only. They say nothing about accuracy on real radio traffic.

| Field | Correct |
|---|---:|
| `is_fire` | 53 of 53 |
| `incident_type` | 50 of 53 |
| `street` | 52 of 53 |
| `units` | 53 of 53 |
| `status` | 50 of 53 |
| Incidents grouped exactly | 13 of 13 |

47 of the 53 calls match on every field.

Measured cost: 53 API requests, 55,454 input and 6,565 output tokens (2,498 of them reasoning), $0.0088 in total, or $0.00017 per call, at the Standard-tier prices in `firefeed.toml` (checked 2026-11-21). The dry run before the batch had estimated $0.0166.

### Where the model and the labels differ

The labels were fixed before the run and were not changed afterwards.

- Status, 3 calls (`c006`, `c020`, `c040`): arrival reports that already name the first action ("stretching a line"). Labeled `on_scene`; the model answered `working`. The rules above do not say which stage wins when one transmission reports both.
- Incident type, 3 calls (`c007`, `c009`, `c026`): the type follows from context ("primary search on the second floor", "investigating with the gas meter") but is not stated. The model answered `unknown`.
- Street, 1 call (`c007`): "the hydrant at Bellwether and Tinsmith" is labeled as the incident street; the model gave no location. A hydrant is a water source near the fire, not its address, so this label is arguable.

## Name check

Checked on 2026-11-21 with web search:

- "Cedar Falls County", the example name in the plan: no such county, but Cedar Falls, Iowa, is a real city with its own fire department and local fire news. Rejected, so the demo cannot be mistaken for a real event there.
- "Wexmoor County": no results; search maps it to Wexford County, Michigan. Rejected as too close to a real county.
- "Larkmoor County": no real county. "Larkmoor" alone matches only a village in a fantasy role-playing wiki, which is unrelated. "Larkmoor" with fire, street or road: no matches. Accepted.
- Street spot check ("Bellwether Avenue", "Copperwick Lane", "Tinsmith Street", "Lanternfield Drive", "Saltbox Road", "Thimble Creek Road"): no matches in the results.

Every address in the dataset is in Larkmoor County, so none of them exists. The street names were not checked one by one against every map in the world; a street with the same name elsewhere would still be in a different, real place.
