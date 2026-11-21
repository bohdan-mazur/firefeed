import { STATUS_LABEL, STATUS_TONE, TYPE_LABEL } from "@/lib/labels";
import type { IncidentType, Status } from "@/lib/types";

import styles from "./Chips.module.css";

export function FireChip({ fire }: { fire: boolean }) {
  return <span className={`${styles.chip} ${fire ? styles.fire : ""}`}>{fire ? "Fire call" : "Not a fire"}</span>;
}

export function TypeChip({ type }: { type: IncidentType }) {
  return <span className={styles.chip}>{TYPE_LABEL[type]}</span>;
}

export function StatusChip({ status }: { status: Status }) {
  return <span className={`${styles.chip} ${styles[STATUS_TONE[status]]}`}>{STATUS_LABEL[status]}</span>;
}

export function Chip({ children, mono = false }: { children: React.ReactNode; mono?: boolean }) {
  return <span className={`${styles.chip} ${mono ? styles.mono : ""}`}>{children}</span>;
}
