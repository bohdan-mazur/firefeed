import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { FireChip, StatusChip, TypeChip } from "@/components/Chips";
import { MatchTable } from "@/components/MatchTable";
import { callsOf, getCall, getEvalRow, getFeed, getIncident } from "@/lib/data";
import { clock, dayLabel } from "@/lib/labels";
import { incidentTitle } from "@/lib/rows";

import styles from "../../detail.module.css";

export const dynamicParams = false;

export function generateStaticParams() {
  return getFeed().calls.map((c) => ({ id: c.id }));
}

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const call = getCall(id);
  if (!call) return {};
  return {
    title: `Call ${id}, ${clock(call.timestamp)} on ${call.channel}`,
    description: `${call.analysis?.summary ?? call.transcript} Synthetic radio call from the FireFeed demo, with the pipeline's reading next to the expected answer.`,
    alternates: { canonical: `/calls/${id}/` },
  };
}

export default async function CallPage({ params }: Props) {
  const { id } = await params;
  const call = getCall(id);
  const row = getEvalRow(id);
  if (!call || !row) notFound();
  const calls = getFeed().calls;
  const index = calls.findIndex((c) => c.id === id);
  const prev = calls[index - 1];
  const next = calls[index + 1];
  const incident = call.incident_id ? getIncident(call.incident_id) : undefined;
  const a = call.analysis;

  return (
    <div className="container">
      <nav aria-label="Breadcrumb" className={styles.crumbs}>
        <Link href="/">Live feed</Link> / <span aria-current="page">Call {id}</span>
      </nav>

      <header className={styles.head}>
        <p className={styles.kicker}>
          {dayLabel(call.timestamp)} · <time dateTime={call.timestamp}>{clock(call.timestamp)}</time> · {call.channel}
        </p>
        <h1>Call {id}</h1>
        {a && (
          <div className={styles.chips}>
            <FireChip fire={a.is_fire} />
            <TypeChip type={a.incident_type} />
            {a.status !== "none" && <StatusChip status={a.status} />}
          </div>
        )}
      </header>

      <div className={styles.columns}>
        <div className={styles.main}>
          <section aria-labelledby="transcript">
            <h2 id="transcript" className={styles.h2}>
              Transcript
            </h2>
            <blockquote className={styles.quote}>{call.transcript}</blockquote>
            <p className={styles.note}>
              The input was a text file, so the transcription step was skipped. With an audio file the pipeline runs
              speech-to-text first; this demo has no audio.
            </p>
          </section>

          <section aria-labelledby="reading">
            <h2 id="reading" className={styles.h2}>
              The pipeline&apos;s reading next to the expected answer
            </h2>
            <MatchTable row={row} />
            {a && (
              <p className={styles.note}>
                Model summary: “{a.summary}” Confidence {a.confidence.toFixed(2)}. Expected answers are hand-written in{" "}
                <code>data/spec.csv</code> from this transcript alone.
              </p>
            )}
          </section>
        </div>

        <aside className={styles.side} aria-labelledby="incident">
          <h2 id="incident" className={styles.h2}>
            Incident
          </h2>
          {incident ? (
            <>
              <p>
                <Link href={`/incidents/${incident.id}/`}>{incidentTitle(incident)}</Link>
              </p>
              <p className={styles.note}>
                {incident.call_ids.length} {incident.call_ids.length === 1 ? "call" : "calls"},{" "}
                {clock(incident.start)} to {clock(incident.end)}
              </p>
              <ol className={styles.related}>
                {callsOf(incident).map((c) => (
                  <li key={c.id} aria-current={c.id === id ? "true" : undefined}>
                    <Link href={`/calls/${c.id}/`}>
                      <time dateTime={c.timestamp}>{clock(c.timestamp)}</time> {c.channel}
                    </Link>
                    <span>{c.analysis?.summary}</span>
                  </li>
                ))}
              </ol>
            </>
          ) : (
            <p className={styles.note}>
              Not grouped: the pipeline read this transmission as traffic that is not about an incident.
            </p>
          )}
        </aside>
      </div>

      <nav aria-label="Other calls" className={styles.pager}>
        {prev ? <Link href={`/calls/${prev.id}/`}>← Call {prev.id}</Link> : <span />}
        {next ? <Link href={`/calls/${next.id}/`}>Call {next.id} →</Link> : <span />}
      </nav>
    </div>
  );
}
