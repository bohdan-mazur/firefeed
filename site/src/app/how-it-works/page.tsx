import type { Metadata } from "next";
import Link from "next/link";

import { Pipeline } from "@/components/Pipeline";
import { getEvaluation, getFeed } from "@/lib/data";
import { usd } from "@/lib/labels";
import { SITE } from "@/lib/site";
import type { Field } from "@/lib/types";

import styles from "../prose.module.css";

export const metadata: Metadata = {
  title: "How it works",
  description:
    "Ingest, speech-to-text, structured extraction with the OpenAI Responses API and a strict JSON schema, rule-based grouping and a cost-controlled cache, with numbers measured on 53 synthetic calls.",
  alternates: { canonical: "/how-it-works/" },
};

const FIELD_NAMES: Record<Field, string> = {
  is_fire: "Fire call or not",
  incident_type: "Incident type",
  street: "Street",
  units: "Units",
  status: "Status",
};

const SCHEMA_FIELDS = [
  ["is_fire", "boolean", "part of the response to a fire call, true even when the crew finds no fire"],
  ["incident_type", "enum of 12", "structure_fire, vehicle_fire, wildland_fire, mva_with_fire, … unknown, not_incident"],
  ["location_as_heard", "string | null", "the incident location as spoken, including a command name such as “Maple Command”"],
  ["units", "string[]", "every fire unit named, as type and number"],
  ["status", "enum of 8", "dispatched, en_route, on_scene, working, under_control, cleared, cancelled, none"],
  ["summary", "string", "one plain sentence"],
  ["confidence", "number", "0 to 1, checked locally"],
];

// Why the recorded run differs from the labels (data/README.md, "Where the model and the labels differ").
const WHY: Partial<Record<Field, React.ReactNode>> = {
  status: (
    <>
      arrival reports that already name the first action. Labeled <code>on_scene</code>, answered{" "}
      <code>working</code>; the labeling rules do not say which stage wins.
    </>
  ),
  incident_type: (
    <>
      the type follows from context but is never stated. Answered <code>unknown</code>.
    </>
  ),
  street: (
    <>
      “the hydrant at Bellwether and Tinsmith” was labeled as the incident street; the model returned no location. A
      hydrant is not the fire&apos;s address, so the label is arguable.
    </>
  ),
};

const n = (value: number) => value.toLocaleString("en-US");

export default function HowItWorksPage() {
  const feed = getFeed();
  const evaluation = getEvaluation();
  const u = feed.usage;
  const calls = feed.dataset.analyzed;
  const recorded = u.recorded_to?.slice(0, 10) ?? "";
  const repo = `${SITE.github}/blob/main/data/README.md`;
  const misses = (f: Field) => evaluation.calls.filter((r) => !r.match[f]).map((r) => r.id);

  return (
    <div className={`container ${styles.page}`}>
      <header className={styles.head}>
        <h1>How FireFeed reads the radio</h1>
        <p className={styles.lead}>
          Five steps from a transmission to an incident. The demo enters at the second step with text; the rest runs as
          it would on your own recordings.
        </p>
      </header>

      <Pipeline />

      <section className={styles.section} aria-labelledby="input">
        <h2 id="input">Input</h2>
        <p>
          One file per transmission: a transcript (<code>.txt</code>) or audio (<code>.wav</code>, <code>.mp3</code>,{" "}
          <code>.m4a</code>, <code>.ogg</code>, <code>.flac</code>, <code>.webm</code>), plus a JSON sidecar with an ISO
          8601 timestamp that carries a UTC offset, and the channel name. Ingest checks every file before the first
          request and reports all problems at once.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="stt">
        <h2 id="stt">Transcription</h2>
        <p>
          Audio goes to OpenAI speech-to-text (<code>gpt-transcribe</code> in <code>firefeed.toml</code>), cached by the
          SHA-256 of the audio bytes, model, language and prompt. A transmission that already has a transcript skips
          this step. This demo is text-only, so no transcription ran and the site has no audio player.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="extract">
        <h2 id="extract">Structured extraction</h2>
        <p>
          Each transcript goes alone to the Responses API (<code>{feed.pipeline.analysis_model}</code>, reasoning effort{" "}
          <code>{feed.pipeline.reasoning_effort}</code>, <code>store: false</code>) with Structured Outputs: a strict
          JSON schema, seven required fields, no extra keys. The answer is then validated locally against the same
          schema and against rules the schema cannot express, such as <code>not_incident</code> if and only if the status
          is <code>none</code>. A failed check gets one retry; after a second failure the call is marked as failed.
        </p>
        <table className={styles.table}>
          <caption className="sr-only">Fields of the analysis schema</caption>
          <thead>
            <tr>
              <th scope="col">Field</th>
              <th scope="col">Type</th>
              <th scope="col">Meaning</th>
            </tr>
          </thead>
          <tbody>
            {SCHEMA_FIELDS.map(([field, type, meaning]) => (
              <tr key={field}>
                <th scope="row">
                  <code>{field}</code>
                </th>
                <td>
                  <code>{type}</code>
                </td>
                <td>{meaning}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className={styles.section} aria-labelledby="local">
        <h2 id="local">Local knowledge</h2>
        <p>
          The instructions carry the county gazetteer: 20 street names, 8 unit names, the dispatcher&apos;s call sign and
          local 10-codes (10-97 arrived on scene, 10-8 back in service). After extraction, <code>location_as_heard</code>{" "}
          is matched to a street: exact words first, then a fuzzy comparison over joined words, with digits required to
          match. “Bell weather” becomes Bellwether Avenue and “Thimble Crick Road” becomes Thimble Creek Road, while
          “County Road 21” would not match County Road 12.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="group">
        <h2 id="group">Grouping</h2>
        <p>
          Calls about an incident are grouped by rules, applied in order. Two different known streets never join. A new
          dispatch joins only an incident at the same street. The same street links strongest, then a shared unit; a
          call with neither joins the incident heard on the same channel within 120 seconds. A <code>cleared</code> or{" "}
          <code>cancelled</code> call closes its incident, and an incident silent for 60 minutes takes no new calls.
          Every threshold lives in <code>firefeed.toml</code>.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="cost">
        <h2 id="cost">Cost control and measured cost</h2>
        <p>
          Every answer is cached under a SHA-256 of the model, settings, instructions, schema and input, so a repeat run
          makes no requests; the committed cache lets anyone reproduce this run without a key. Before a batch, a dry run
          counts cache misses and estimates tokens and cost. The run refuses to start above a request cap and asks for
          confirmation above a cost threshold.
        </p>
        <table className={styles.table}>
          <caption>
            The recorded run, {recorded}, {calls} synthetic calls
          </caption>
          <tbody>
            <tr>
              <th scope="row">API requests</th>
              <td>{n(u.api_requests)}</td>
            </tr>
            <tr>
              <th scope="row">Input tokens</th>
              <td>
                {n(u.input_tokens)} ({n(Math.round(u.input_tokens / calls))} per call)
              </td>
            </tr>
            <tr>
              <th scope="row">Output tokens</th>
              <td>
                {n(u.output_tokens)}, of them {n(u.reasoning_tokens)} reasoning ({n(Math.round(u.output_tokens / calls))}{" "}
                per call)
              </td>
            </tr>
            <tr>
              <th scope="row">Cost</th>
              <td>
                {usd(u.cost_usd)} in total, {u.cost_per_call_usd !== null ? usd(u.cost_per_call_usd, 5) : "n/a"} per call
              </td>
            </tr>
          </tbody>
        </table>
        <p className={styles.note}>
          Prices: ${u.prices.input_per_million.toFixed(2)} per million input tokens, $
          {u.prices.cached_input_per_million.toFixed(2)} cached, ${u.prices.output_per_million.toFixed(2)} output,
          Standard tier, from the{" "}
          <a href={u.prices.source ?? "https://developers.openai.com/api/docs/pricing"}>OpenAI pricing page</a>, checked{" "}
          {u.prices.checked}. Output tokens include reasoning tokens.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="accuracy">
        <h2 id="accuracy">Accuracy on {evaluation.calls_compared} synthetic calls</h2>
        <p>
          The expected answers were written by hand from each transcript alone, before the run, and were not changed
          after it. {evaluation.calls_fully_correct} of {evaluation.calls_compared} calls match on every field.
        </p>
        <table className={styles.table}>
          <caption className="sr-only">Correct answers per field</caption>
          <thead>
            <tr>
              <th scope="col">Field</th>
              <th scope="col">Correct</th>
            </tr>
          </thead>
          <tbody>
            {(Object.keys(FIELD_NAMES) as Field[]).map((f) => (
              <tr key={f}>
                <th scope="row">{FIELD_NAMES[f]}</th>
                <td>
                  {evaluation.fields[f].correct} of {evaluation.fields[f].total}
                </td>
              </tr>
            ))}
            <tr>
              <th scope="row">Incidents grouped exactly</th>
              <td>
                {evaluation.grouping.incidents_exact} of {evaluation.grouping.incidents_expected}
              </td>
            </tr>
          </tbody>
        </table>
        <p>Every difference goes the same way: the model is more cautious than the labels.</p>
        <ul className={styles.list}>
          {(Object.keys(WHY) as Field[])
            .filter((f) => misses(f).length > 0)
            .map((f) => (
              <li key={f}>
                {FIELD_NAMES[f]}, {misses(f).length} {misses(f).length === 1 ? "call" : "calls"} (
                {misses(f).map((id, k) => (
                  <span key={id}>
                    {k > 0 && ", "}
                    <Link href={`/calls/${id}/`}>{id}</Link>
                  </span>
                ))}
                ): {WHY[f]}
              </li>
            ))}
        </ul>
        <p className={styles.note}>
          Labeling rules and the full comparison: <a href={repo}>data/README.md</a> in the repository.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="limits">
        <h2 id="limits">Limits</h2>
        <p>
          The transmissions are synthetic and cleaner than real radio, which has crosstalk and clipped words. Accuracy
          on real traffic has not been measured. A real channel can be connected only
          with the written permission of the source&apos;s owner.
        </p>
        <p>
          Stack: a Python 3.12 pipeline (<code>openai</code>, <code>jsonschema</code>) covered by pytest and ruff; this
          site is a static Next.js export with no backend and no API keys.
        </p>
      </section>
    </div>
  );
}
