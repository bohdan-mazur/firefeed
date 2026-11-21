import Link from "next/link";

import { clock, TYPE_LABEL } from "@/lib/labels";
import type { IncidentType, Status } from "@/lib/types";

import { Chip, FireChip, StatusChip, TypeChip } from "./Chips";
import styles from "./CallRow.module.css";

/** A call as the feed shows it: model output plus how it compares with the expected answer. */
export type RowCall = {
  id: string;
  timestamp: string;
  channel: string;
  transcript: string;
  fire: boolean | null;
  type: IncidentType | null;
  street: string | null;
  units: string[];
  status: Status | null;
  incident: string | null;
  incidentLabel: string | null;
  differs: string[];
};

const FIELD_LABEL: Record<string, string> = {
  is_fire: "fire call",
  incident_type: "type",
  street: "street",
  units: "units",
  status: "status",
};

export function CallRow({
  call,
  text,
  state = "done",
  highlight = false,
  onFocusIncident,
}: {
  call: RowCall;
  text?: React.ReactNode;
  state?: "typing" | "fresh" | "done";
  highlight?: boolean;
  onFocusIncident?: (id: string | null) => void;
}) {
  const enter = onFocusIncident && call.incident ? () => onFocusIncident(call.incident) : undefined;
  const leave = onFocusIncident ? () => onFocusIncident(null) : undefined;
  return (
    <li
      className={`${styles.row} ${styles[state]} ${highlight ? styles.highlight : ""}`}
      onPointerEnter={enter}
      onPointerLeave={leave}
      onFocus={enter}
      onBlur={leave}
    >
      <div className={styles.meta}>
        <time dateTime={call.timestamp}>{clock(call.timestamp)}</time>
        <span className={styles.channel}>{call.channel}</span>
      </div>
      <div className={styles.body}>
        <p className={styles.text}>{text ?? call.transcript}</p>
        <div className={styles.chips} aria-hidden={state === "typing" ? true : undefined}>
          {call.fire !== null && <FireChip fire={call.fire} />}
          {call.type && call.type !== "not_incident" && <TypeChip type={call.type} />}
          {call.street && <Chip>{call.street}</Chip>}
          {call.units.length > 0 && <Chip mono>{call.units.join(" · ")}</Chip>}
          {call.status && call.status !== "none" && <StatusChip status={call.status} />}
          {call.type === "not_incident" && <Chip>{TYPE_LABEL.not_incident}</Chip>}
        </div>
        <p className={styles.links}>
          <Link href={`/calls/${call.id}/`}>Call card {call.id}</Link>
          {call.incident && (
            <>
              {" · "}
              <Link href={`/incidents/${call.incident}/`}>{call.incidentLabel ?? call.incident}</Link>
            </>
          )}
          {" · "}
          {call.differs.length === 0 ? (
            <span className={styles.ok}>matches the expected answer</span>
          ) : (
            <span className={styles.diff}>differs on {call.differs.map((f) => FIELD_LABEL[f] ?? f).join(", ")}</span>
          )}
        </p>
      </div>
    </li>
  );
}
