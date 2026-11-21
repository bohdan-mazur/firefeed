import type { MapGeometry } from "@/lib/geometry";

import styles from "./CountyMap.module.css";

export type MapPin = { id: string; street: string; fire: boolean; label: string };

/**
 * Schematic map of the fictional county. Pins link to incident pages.
 * `seen` = null shows every pin; otherwise only the listed ones.
 */
export function CountyMap({
  geo,
  pins,
  active = null,
  seen = null,
  title = "Schematic map of the fictional Larkmoor County with incident locations",
}: {
  geo: MapGeometry;
  pins: MapPin[];
  active?: string | null;
  seen?: Set<string> | null;
  title?: string;
}) {
  return (
    <svg className={styles.map} viewBox={`0 0 ${geo.width} ${geo.height}`} role="group" aria-label={title}>
      <rect x="1" y="1" width={geo.width - 2} height={geo.height - 2} rx="5" className={styles.frame} />
      <g aria-hidden="true">
        {geo.water.map((w) => (
          <g key={w.name}>
            <path d={w.d} className={styles.water} />
            <path d={w.d} className={styles.waterEdge} />
            <text
              x={w.label.x}
              y={w.label.y}
              transform={`rotate(${w.label.angle} ${w.label.x} ${w.label.y})`}
              className={styles.waterLabel}
            >
              {w.name}
            </text>
          </g>
        ))}
        {geo.streets.map((s) => (
          <path key={s.name} d={s.d} className={`${styles.street} ${styles[`r${s.rank}`]}`} />
        ))}
        {geo.streets.map((s) => (
          <text
            key={`${s.name}-label`}
            x={s.label.x}
            y={s.label.y}
            transform={`rotate(${s.label.angle} ${s.label.x} ${s.label.y})`}
            className={`${styles.label} ${s.rank === 3 ? styles.minor : ""}`}
          >
            {s.name.toUpperCase()}
          </text>
        ))}
        <text x={geo.town.x} y={geo.town.y} className={styles.town}>
          {geo.town.name.toUpperCase()}
        </text>
      </g>
      {pins.map((pin) => {
        const spot = geo.spots[pin.street];
        if (!spot) return null;
        const visible = seen === null || seen.has(pin.id);
        const on = active === pin.id;
        const cls = [styles.pin, pin.fire ? styles.fire : styles.other, visible ? styles.seen : styles.hidden, on ? styles.on : ""];
        return (
          <a key={pin.id} href={`/incidents/${pin.id}/`} className={cls.join(" ")} tabIndex={visible ? 0 : -1} aria-hidden={visible ? undefined : true}>
            <title>{pin.label}</title>
            <circle cx={spot[0]} cy={spot[1]} r="7" className={styles.ring} />
            <circle cx={spot[0]} cy={spot[1]} r="5" className={styles.core} />
          </a>
        );
      })}
    </svg>
  );
}
