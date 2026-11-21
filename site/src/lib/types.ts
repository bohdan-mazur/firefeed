// Shapes of the pipeline output (data/demo/out/*.json) and the map (data/map.json).

export type IncidentType =
  | "structure_fire"
  | "vehicle_fire"
  | "wildland_fire"
  | "mva_with_fire"
  | "other_fire"
  | "fire_alarm"
  | "smoke_investigation"
  | "gas_leak"
  | "medical"
  | "other_incident"
  | "unknown"
  | "not_incident";

export type Status =
  | "dispatched"
  | "en_route"
  | "on_scene"
  | "working"
  | "under_control"
  | "cleared"
  | "cancelled"
  | "none";

export type Analysis = {
  is_fire: boolean;
  incident_type: IncidentType;
  location_as_heard: string | null;
  units: string[];
  status: Status;
  summary: string;
  confidence: number;
};

export type Call = {
  id: string;
  timestamp: string;
  channel: string;
  duration_s: number | null;
  audio: string | null;
  transcript: string;
  transcript_source: string;
  analysis: Analysis | null;
  error: string | null;
  street: string | null;
  units: string[];
  unknown_units: string[];
  incident_id: string | null;
};

export type Incident = {
  id: string;
  call_ids: string[];
  start: string;
  end: string;
  channels: string[];
  incident_type: IncidentType;
  is_fire: boolean;
  street: string | null;
  units: string[];
  status: Status;
  summary: string | null;
};

export type Usage = {
  api_requests: number;
  input_tokens: number;
  cached_input_tokens: number;
  output_tokens: number;
  reasoning_tokens: number;
  audio_seconds: number;
  cost_usd: number;
  cost_per_call_usd: number | null;
  recorded_from: string | null;
  recorded_to: string | null;
  prices: {
    input_per_million: number;
    cached_input_per_million: number;
    output_per_million: number;
    transcription_per_minute: number;
    source: string | null;
    checked: string | null;
  };
};

export type Feed = {
  format: number;
  notice: string | null;
  dataset: { name: string; synthetic: boolean; calls: number; analyzed: number; incidents: number };
  pipeline: {
    version: string;
    analysis_model: string;
    reasoning_effort: string | null;
    prompt_version: string;
    transcription_model: string | null;
  };
  usage: Usage;
  channels: string[];
  calls: Call[];
  incidents: Incident[];
};

export type Field = "is_fire" | "incident_type" | "street" | "units" | "status";

export type Answer = {
  is_fire: boolean;
  incident_type: IncidentType;
  street: string | null;
  units: string[];
  status: Status;
};

export type EvalRow = {
  id: string;
  expected: Answer;
  model: Answer | null;
  match: Record<Field, boolean>;
  all_match: boolean;
  location_as_heard: string | null;
  expected_incident: string | null;
  predicted_incident: string | null;
};

export type Evaluation = {
  calls_compared: number;
  calls_fully_correct: number;
  fields: Record<Field, { correct: number; total: number; accuracy: number | null }>;
  is_fire: { tp: number; fp: number; fn: number; tn: number; precision: number | null; recall: number | null };
  grouping: {
    incidents_expected: number;
    incidents_predicted: number;
    incidents_exact: number;
    pair_precision: number | null;
    pair_recall: number | null;
  };
  calls: EvalRow[];
};

export type MapStreet = {
  name: string;
  rank: 1 | 2 | 3;
  path: [number, number][];
  spot?: [number, number];
  labelAt: number;
};

export type MapData = {
  name: string;
  size: [number, number];
  town: { name: string; label: [number, number] };
  water: { name: string; path: [number, number][]; labelAt: number }[];
  streets: MapStreet[];
};
