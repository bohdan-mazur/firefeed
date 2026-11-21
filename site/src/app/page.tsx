import Link from "next/link";

import { LiveView } from "@/components/LiveView";
import { getEvaluation, getFeed, getMap } from "@/lib/data";
import { buildMapGeometry } from "@/lib/geometry";
import { dayLabel, usd } from "@/lib/labels";
import { mapPins, toRow } from "@/lib/rows";

import styles from "./page.module.css";

export default function HomePage() {
  const feed = getFeed();
  const evaluation = getEvaluation();
  const day = dayLabel(feed.calls[0].timestamp);
  const recorded = feed.usage.recorded_to?.slice(0, 10);
  return (
    <div className="container">
      <header className={styles.intro}>
        <p className={styles.kicker}>Larkmoor County · {day} · fictional</p>
        <h1 className={styles.title}>Fire radio traffic, read by a model and filed as incidents</h1>
        <p className={styles.lead}>
          One afternoon of invented dispatch traffic: {feed.dataset.calls} transmissions on {feed.channels.length}{" "}
          channels. Each went through <code>{feed.pipeline.analysis_model}</code> once, into a record that follows a
          strict JSON schema, and the records were grouped into {feed.dataset.incidents} incidents. The replay reads the
          stored answers and makes no API calls.
        </p>
      </header>

      <LiveView calls={feed.calls.map(toRow)} pins={mapPins()} geo={buildMapGeometry(getMap())} channels={feed.channels} />

      <section className={styles.numbers} aria-labelledby="numbers">
        <h2 id="numbers">Measured on {evaluation.calls_compared} synthetic calls</h2>
        <dl>
          <div>
            <dt>Calls correct on every field</dt>
            <dd>
              {evaluation.calls_fully_correct} of {evaluation.calls_compared}
            </dd>
          </div>
          <div>
            <dt>Fire call or not</dt>
            <dd>
              {evaluation.fields.is_fire.correct} of {evaluation.fields.is_fire.total}
            </dd>
          </div>
          <div>
            <dt>Incidents grouped as expected</dt>
            <dd>
              {evaluation.grouping.incidents_exact} of {evaluation.grouping.incidents_expected}
            </dd>
          </div>
          <div>
            <dt>API cost per call</dt>
            <dd>{feed.usage.cost_per_call_usd !== null ? usd(feed.usage.cost_per_call_usd, 5) : "n/a"}</dd>
          </div>
        </dl>
        <p className={styles.small}>
          One run on {recorded}, compared with hand-written expected answers. These numbers describe this synthetic set
          only, not real radio traffic. <Link href="/how-it-works/">How it works and where the model differs</Link>.
        </p>
      </section>
    </div>
  );
}
