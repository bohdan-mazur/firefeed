import "server-only";

import type { RowCall } from "@/components/CallRow";
import type { MapPin } from "@/components/CountyMap";

import { getEvalRow, getFeed, getIncident } from "./data";
import { clockShort, TYPE_LABEL } from "./labels";
import type { Call, Field, Incident } from "./types";

export function incidentTitle(incident: Incident): string {
  return `${TYPE_LABEL[incident.incident_type]}${incident.street ? ` on ${incident.street}` : ""}`;
}

export function differingFields(callId: string): Field[] {
  const row = getEvalRow(callId);
  if (!row) return [];
  return (Object.entries(row.match) as [Field, boolean][]).filter(([, ok]) => !ok).map(([f]) => f);
}

export function toRow(call: Call): RowCall {
  const a = call.analysis;
  const incident = call.incident_id ? getIncident(call.incident_id) : undefined;
  return {
    id: call.id,
    timestamp: call.timestamp,
    channel: call.channel,
    transcript: call.transcript,
    fire: a?.is_fire ?? null,
    type: a?.incident_type ?? null,
    street: call.street,
    units: call.units,
    status: a?.status ?? null,
    incident: call.incident_id,
    incidentLabel: incident ? `Incident: ${incidentTitle(incident)}` : null,
    differs: differingFields(call.id),
  };
}

export function mapPins(): MapPin[] {
  return getFeed()
    .incidents.filter((i) => i.street)
    .map((i) => ({
      id: i.id,
      street: i.street as string,
      fire: i.is_fire,
      label: `${clockShort(i.start)} · ${incidentTitle(i)} (${i.call_ids.length} ${i.call_ids.length === 1 ? "call" : "calls"})`,
    }));
}
