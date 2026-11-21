import styles from "./Pipeline.module.css";

const STAGES = [
  {
    name: "Radio call",
    what: "audio or a transcript",
    packet: "c004.txt",
    icon: "M-7 -12h14v24h-14z M-3 -12v-8 M-4 4h8 M-4 8h8 M-4 -6h8v4h-8z",
  },
  {
    name: "Transcribe",
    what: "skipped when text exists",
    packet: "text",
    icon: "M-14 0h3l2 -7l3 13l3 -10l2 6l2 -2h13 M2 -8h11 M2 8h11",
  },
  {
    name: "Analyze",
    what: "strict JSON schema",
    packet: "{ is_fire: true }",
    icon: "M-6 -13c-5 0 -5 3 -5 7s-3 6 -5 6c2 0 5 2 5 6s0 7 5 7 M6 -13c5 0 5 3 5 7s3 6 5 6c-2 0 -5 2 -5 6s0 7 -5 7 M-3 -4h6 M-3 4h6",
  },
  {
    name: "Group",
    what: "calls into incidents",
    packet: "inc-01",
    icon: "M-12 -8h18v12h-18z M-8 -12h18v12 M-4 -16h18v12",
  },
  {
    name: "Feed",
    what: "this site",
    packet: "feed.json",
    icon: "M-12 -13h24v26h-24z M-8 -7h16 M-8 -1h16 M-8 5h10",
  },
];

/** The pipeline as five stations with a pulse running through them. CSS only, no JavaScript. */
export function Pipeline() {
  return (
    <figure className={styles.figure}>
      <ol className={styles.pipe}>
        {STAGES.map((s, i) => (
          <li key={s.name} className={styles.stage} style={{ "--i": i } as React.CSSProperties}>
            <span className={styles.node} aria-hidden="true">
              <svg viewBox="-20 -20 40 40" width="40" height="40">
                <path d={s.icon} />
              </svg>
            </span>
            <code className={styles.packet} aria-hidden="true">
              {s.packet}
            </code>
            <b className={styles.name}>{s.name}</b>
            <span className={styles.what}>{s.what}</span>
          </li>
        ))}
      </ol>
      <figcaption className={styles.caption}>
        A sixth step, alerts to Telegram or a webhook for new fire incidents, is implemented and switched off in the
        demo.
      </figcaption>
    </figure>
  );
}
