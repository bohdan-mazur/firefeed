"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { MapGeometry } from "@/lib/geometry";
import { clock, TYPE_LABEL } from "@/lib/labels";
import type { IncidentType } from "@/lib/types";

import { CallRow, type RowCall } from "./CallRow";
import { CountyMap, type MapPin } from "./CountyMap";
import styles from "./LiveView.module.css";

type Mode = "full" | "playing" | "paused" | "ended";
type Speed = 1 | 10;

// At 1x the text is typed at about the pace of speech; quiet stretches longer than GAP_CAP are skipped.
const CHARS_PER_SECOND = 15;
const GAP_CAP_S = 3;

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const update = () => setReduced(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return reduced;
}

/** Types `text` into a span without re-rendering React on every frame. */
function TypingText({
  text,
  speed,
  paused,
  instant,
  onDone,
}: {
  text: string;
  speed: Speed;
  paused: boolean;
  instant: boolean;
  onDone: () => void;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const progress = useRef(0);
  const speedRef = useRef(speed);
  const doneRef = useRef(onDone);
  speedRef.current = speed;
  doneRef.current = onDone;

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (instant) {
      node.textContent = text;
      const t = window.setTimeout(() => doneRef.current(), 250);
      return () => window.clearTimeout(t);
    }
    if (paused) return;
    let frame = 0;
    let last = performance.now();
    const tick = (now: number) => {
      progress.current += ((now - last) / 1000) * CHARS_PER_SECOND * speedRef.current;
      last = now;
      const shown = Math.min(text.length, Math.floor(progress.current));
      node.textContent = text.slice(0, shown);
      if (shown >= text.length) {
        doneRef.current();
        return;
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [text, paused, instant]);

  return (
    <>
      <span ref={ref} aria-hidden="true" />
      <span className={styles.caret} aria-hidden="true" />
      <span className="sr-only">{text}</span>
    </>
  );
}

export function LiveView({
  calls,
  pins,
  geo,
  channels,
}: {
  calls: RowCall[];
  pins: MapPin[];
  geo: MapGeometry;
  channels: string[];
}) {
  const [mode, setMode] = useState<Mode>("full");
  const [speed, setSpeed] = useState<Speed>(1);
  const [shown, setShown] = useState(calls.length);
  const [typingId, setTypingId] = useState<string | null>(null);
  const [channel, setChannel] = useState("all");
  const [kind, setKind] = useState("all");
  const [focus, setFocus] = useState<string | null>(null);
  const reduced = useReducedMotion();

  const types = useMemo(() => {
    const present = new Set(calls.map((c) => c.type).filter((t): t is IncidentType => Boolean(t)));
    return (Object.keys(TYPE_LABEL) as IncidentType[]).filter((t) => present.has(t));
  }, [calls]);

  // Schedules the next call once the current one has finished typing.
  useEffect(() => {
    if (mode !== "playing" || typingId) return;
    if (shown >= calls.length) {
      setMode("ended");
      return;
    }
    const next = calls[shown];
    const prev = calls[shown - 1];
    const gapS = prev ? (Date.parse(next.timestamp) - Date.parse(prev.timestamp)) / 1000 : 0.5;
    const waitMs = (Math.min(gapS, GAP_CAP_S) / speed) * 1000;
    const timer = window.setTimeout(() => {
      setShown((n) => n + 1);
      setTypingId(next.id);
    }, waitMs);
    return () => window.clearTimeout(timer);
  }, [mode, typingId, shown, speed, calls]);

  const play = () => {
    if (mode === "paused") {
      setMode("playing");
      return;
    }
    setShown(0);
    setTypingId(null);
    setMode("playing");
  };
  const showAll = () => {
    setMode("full");
    setShown(calls.length);
    setTypingId(null);
  };

  const revealed = calls.slice(0, shown);
  const latest = revealed[revealed.length - 1];
  const live = mode !== "full";
  const seen = useMemo(
    () => (live ? new Set(revealed.map((c) => c.incident).filter((x): x is string => Boolean(x))) : null),
    [live, revealed],
  );
  const activeIncident = focus ?? (live && latest ? latest.incident : null);
  const activePin = pins.find((p) => p.id === activeIncident);

  const matches = (c: RowCall) =>
    (channel === "all" || c.channel === channel) &&
    (kind === "all" ||
      (kind === "fire" && c.fire === true) ||
      (kind === "nofire" && c.fire === false) ||
      c.type === kind);
  const rows = revealed.slice().reverse().filter(matches);

  // A call hidden by the filters cannot finish typing on screen; count it as typed so the replay goes on.
  const typingHidden = typingId !== null && !rows.some((r) => r.id === typingId);
  useEffect(() => {
    if (typingHidden) setTypingId(null);
  }, [typingHidden]);

  const status =
    mode === "full"
      ? `Showing all ${calls.length} calls, newest first.`
      : mode === "ended"
        ? `Replay finished: ${calls.length} calls.`
        : `Replay ${mode === "paused" ? "paused" : "at " + speed + "×"}${latest ? `, ${clock(latest.timestamp)}` : ""}, call ${shown} of ${calls.length}.`;

  return (
    <div className={styles.live}>
      <div className={styles.controls}>
        <div className={styles.buttons}>
          {mode === "playing" ? (
            <button type="button" className={styles.primary} onClick={() => setMode("paused")}>
              Pause
            </button>
          ) : (
            <button type="button" className={styles.primary} onClick={play}>
              {mode === "paused" ? "Resume" : "Replay the afternoon"}
            </button>
          )}
          <div className={styles.speed} role="group" aria-label="Replay speed">
            {([1, 10] as Speed[]).map((s) => (
              <button key={s} type="button" aria-pressed={speed === s} onClick={() => setSpeed(s)}>
                {s}×
              </button>
            ))}
          </div>
          {live && (
            <button type="button" className={styles.quiet} onClick={showAll}>
              Show all
            </button>
          )}
        </div>
        <div className={styles.filters}>
          <label>
            <span>Channel</span>
            <select value={channel} onChange={(e) => setChannel(e.target.value)}>
              <option value="all">All channels</option>
              {channels.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Type</span>
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="all">All calls</option>
              <option value="fire">Fire calls</option>
              <option value="nofire">Not a fire</option>
              {types.map((t) => (
                <option key={t} value={t}>
                  {TYPE_LABEL[t]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className={styles.status} aria-live="polite">
          {status}
        </p>
      </div>

      <div className={styles.grid}>
        <section className={styles.mapCol} aria-label="Map">
          <div className={styles.sticky}>
            <CountyMap geo={geo} pins={pins} active={activeIncident} seen={seen} />
            <p className={styles.caption}>
              {activePin ? (
                <>
                  <b>{activePin.label}</b>
                </>
              ) : (
                <>Larkmoor County is fictional. Pins mark incidents; select one to open it.</>
              )}
            </p>
          </div>
        </section>

        <section className={styles.feedCol} aria-label="Calls">
          {rows.length === 0 ? (
            <p className={styles.empty}>{shown === 0 ? "Waiting for the first call" : "No calls match these filters yet."}</p>
          ) : (
            <ol className={styles.list}>
              {rows.map((c) => {
                const typing = c.id === typingId;
                const fresh = live && latest?.id === c.id && !typing;
                return (
                  <CallRow
                    key={c.id}
                    call={c}
                    state={typing ? "typing" : fresh ? "fresh" : "done"}
                    highlight={!typing && focus !== null && c.incident === focus}
                    onFocusIncident={setFocus}
                    text={
                      typing ? (
                        <TypingText
                          text={c.transcript}
                          speed={speed}
                          paused={mode === "paused"}
                          instant={reduced}
                          onDone={() => setTypingId(null)}
                        />
                      ) : undefined
                    }
                  />
                );
              })}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}
