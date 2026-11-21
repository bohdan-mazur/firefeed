import "server-only";

import fs from "node:fs";
import path from "node:path";

import type { Call, EvalRow, Evaluation, Feed, Incident, MapData } from "./types";

// The site is built from the committed pipeline output; nothing here calls an API.
const DATA_DIR = path.join(process.cwd(), "..", "data");

function readJson<T>(relative: string): T {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, relative), "utf8")) as T;
}

type Store = {
  feed: Feed;
  evaluation: Evaluation;
  map: MapData;
  calls: Map<string, Call>;
  incidents: Map<string, Incident>;
  rows: Map<string, EvalRow>;
};

let store: Store | null = null;

function load(): Store {
  if (store) return store;
  const feed = readJson<Feed>("demo/out/feed.json");
  const evaluation = readJson<Evaluation>("demo/out/evaluation.json");
  const map = readJson<MapData>("map.json");
  store = {
    feed,
    evaluation,
    map,
    calls: new Map(feed.calls.map((c) => [c.id, c])),
    incidents: new Map(feed.incidents.map((i) => [i.id, i])),
    rows: new Map(evaluation.calls.map((r) => [r.id, r])),
  };
  return store;
}

export const getFeed = (): Feed => load().feed;
export const getEvaluation = (): Evaluation => load().evaluation;
export const getMap = (): MapData => load().map;
export const getCall = (id: string): Call | undefined => load().calls.get(id);
export const getIncident = (id: string): Incident | undefined => load().incidents.get(id);
export const getEvalRow = (id: string): EvalRow | undefined => load().rows.get(id);

export function callsOf(incident: Incident): Call[] {
  return incident.call_ids.map((id) => load().calls.get(id)).filter((c): c is Call => Boolean(c));
}
