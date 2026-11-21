import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CallRow } from "@/components/CallRow";
import { FireChip, StatusChip, TypeChip } from "@/components/Chips";
import { CountyMap } from "@/components/CountyMap";
import { callsOf, getEvaluation, getFeed, getIncident, getMap } from "@/lib/data";
import { buildMapGeometry } from "@/lib/geometry";
import { clock, dayLabel } from "@/lib/labels";
import { incidentTitle, mapPins, toRow } from "@/lib/rows";

import styles from "../../detail.module.css";

export const dynamicParams = false;

export function generateStaticParams() {
  return getFeed().incidents.map((i) => ({ id: i.id }));
}

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const incident = getIncident(id);
  if (!incident) return {};
  return {
    title: `${incidentTitle(incident)}, ${clock(incident.start)}`,
    description: `${incident.call_ids.length} synthetic radio calls grouped by the FireFeed pipeline into one incident: ${incident.summary ?? incidentTitle(incident)}`,
    alternates: { canonical: `/incidents/${id}/` },
  };
}

export default async function IncidentPage({ params }: Props) {
  const { id } = await params;
  const incident = getIncident(id);
  if (!incident) notFound();
  const calls = callsOf(incident);
  const evaluation = getEvaluation();
  const expectedIds = new Set(calls.map((c) => evaluation.calls.find((r) => r.id === c.id)?.expected_incident));
  const expected = [...expectedIds][0] ?? null;
  const expectedCalls = evaluation.calls.filter((r) => expected && r.expected_incident === expected).map((r) => r.id);
  const exact =
    expectedIds.size === 1 &&
    expected !== null &&
    expectedCalls.length === calls.length &&
    expectedCalls.every((cid) => incident.call_ids.includes(cid));
  const pins = mapPins();

  return (
    <div className="container">
      <nav aria-label="Breadcrumb" className={styles.crumbs}>
        <Link href="/">Live feed</Link> / <span aria-current="page">Incident {incident.id}</span>
      </nav>

      <header className={styles.head}>
        <p className={styles.kicker}>
          {dayLabel(incident.start)} · {clock(incident.start)} to {clock(incident.end)} · {incident.channels.join(", ")}
        </p>
        <h1>{incidentTitle(incident)}</h1>
        <div className={styles.chips}>
          <FireChip fire={incident.is_fire} />
          <TypeChip type={incident.incident_type} />
          <StatusChip status={incident.status} />
        </div>
      </header>

      <div className={styles.columns}>
        <div className={styles.main}>
          <section aria-labelledby="timeline">
            <h2 id="timeline" className={styles.h2}>
              {calls.length} {calls.length === 1 ? "call" : "calls"} in order
            </h2>
            <ol className={styles.timeline}>
              {calls.map((c) => (
                <CallRow key={c.id} call={toRow(c)} />
              ))}
            </ol>
          </section>
        </div>

        <aside className={styles.side} aria-labelledby="where">
          <h2 id="where" className={styles.h2}>
            Where
          </h2>
          <CountyMap
            geo={buildMapGeometry(getMap())}
            pins={pins}
            active={incident.id}
            title={`Schematic map of the fictional county with ${incident.street ?? "this incident"} marked`}
          />
          <dl className={styles.facts}>
            <div>
              <dt>Street</dt>
              <dd>{incident.street ?? "not spoken"}</dd>
            </div>
            <div>
              <dt>Units</dt>
              <dd>{incident.units.length ? incident.units.join(", ") : "none named"}</dd>
            </div>
            <div>
              <dt>Grouping check</dt>
              <dd>
                {exact
                  ? `Matches the expected incident in spec.csv (${expected}).`
                  : "Differs from the expected grouping in spec.csv; see the call cards."}
              </dd>
            </div>
          </dl>
        </aside>
      </div>
    </div>
  );
}
