import { STATUS_LABEL, TYPE_LABEL } from "@/lib/labels";
import type { Answer, EvalRow, Field } from "@/lib/types";

import styles from "./MatchTable.module.css";

const ROWS: { field: Field; label: string }[] = [
  { field: "is_fire", label: "Fire call" },
  { field: "incident_type", label: "Incident type" },
  { field: "street", label: "Street" },
  { field: "units", label: "Units" },
  { field: "status", label: "Status" },
];

function show(answer: Answer | null, field: Field): string {
  if (!answer) return "no answer";
  const value = answer[field];
  if (field === "is_fire") return value ? "Yes" : "No";
  if (field === "incident_type") return TYPE_LABEL[value as Answer["incident_type"]];
  if (field === "status") return STATUS_LABEL[value as Answer["status"]];
  if (Array.isArray(value)) return value.length ? value.join(", ") : "none named";
  return (value as string | null) ?? "none spoken";
}

/** Pipeline output next to the expected answer from spec.csv, field by field. */
export function MatchTable({ row }: { row: EvalRow }) {
  return (
    <table className={styles.table}>
      <caption className="sr-only">Pipeline output compared with the expected answer</caption>
      <thead>
        <tr>
          <th scope="col">Field</th>
          <th scope="col">Pipeline</th>
          <th scope="col">Expected</th>
          <th scope="col">
            <span className="sr-only">Result</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {ROWS.map(({ field, label }) => {
          const ok = row.match[field];
          return (
            <tr key={field} className={ok ? "" : styles.miss}>
              <th scope="row">{label}</th>
              <td>
                {show(row.model, field)}
                {field === "street" && row.location_as_heard && (
                  <span className={styles.heard}>heard as “{row.location_as_heard}”</span>
                )}
              </td>
              <td>{show(row.expected, field)}</td>
              <td className={styles.mark}>{ok ? "✓ match" : "✗ differs"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
