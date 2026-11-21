import type { IncidentType, Status } from "./types";

export const TYPE_LABEL: Record<IncidentType, string> = {
  structure_fire: "Structure fire",
  vehicle_fire: "Vehicle fire",
  wildland_fire: "Wildland fire",
  mva_with_fire: "Crash with fire",
  other_fire: "Outdoor fire",
  fire_alarm: "Fire alarm",
  smoke_investigation: "Smoke report",
  gas_leak: "Gas leak",
  medical: "Medical",
  other_incident: "Other incident",
  unknown: "Type not stated",
  not_incident: "Not an incident",
};

export const STATUS_LABEL: Record<Status, string> = {
  dispatched: "Dispatched",
  en_route: "En route",
  on_scene: "On scene",
  working: "Working",
  under_control: "Under control",
  cleared: "Cleared",
  cancelled: "Cancelled",
  none: "No incident",
};

export type Tone = "alert" | "control" | "cleared" | "cancelled" | "none";

export const STATUS_TONE: Record<Status, Tone> = {
  dispatched: "alert",
  en_route: "alert",
  on_scene: "alert",
  working: "alert",
  under_control: "control",
  cleared: "cleared",
  cancelled: "cancelled",
  none: "none",
};

/** "13:04:12" from "2026-10-17T13:04:12-05:00": the clock time as recorded. */
export const clock = (iso: string): string => iso.slice(11, 19);
export const clockShort = (iso: string): string => iso.slice(11, 16);

export function dayLabel(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

export const usd = (value: number, digits = 4): string => `$${value.toFixed(digits)}`;
