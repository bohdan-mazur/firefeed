import type { MapData } from "./types";

type Pt = [number, number];

/** A smooth path through the points (Catmull-Rom as cubic Béziers). */
export function smoothPath(pts: Pt[]): string {
  if (pts.length < 3) return "M" + pts.map((p) => `${p[0]} ${p[1]}`).join("L");
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] ?? p2;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += `C${c1[0].toFixed(1)} ${c1[1].toFixed(1)} ${c2[0].toFixed(1)} ${c2[1].toFixed(1)} ${p2[0]} ${p2[1]}`;
  }
  return d;
}

/** Point and upright text angle at fraction t of the polyline's length. */
export function along(pts: Pt[], t: number): { x: number; y: number; angle: number } {
  const lengths = pts.slice(1).map((p, i) => Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]));
  let goal = t * lengths.reduce((a, b) => a + b, 0);
  for (let i = 0; i < lengths.length; i++) {
    if (goal <= lengths[i] || i === lengths.length - 1) {
      const k = lengths[i] ? goal / lengths[i] : 0;
      const a = pts[i];
      const b = pts[i + 1];
      let angle = (Math.atan2(b[1] - a[1], b[0] - a[0]) * 180) / Math.PI;
      if (angle > 90) angle -= 180;
      if (angle <= -90) angle += 180;
      return { x: a[0] + (b[0] - a[0]) * k, y: a[1] + (b[1] - a[1]) * k, angle };
    }
    goal -= lengths[i];
  }
  return { x: pts[0][0], y: pts[0][1], angle: 0 };
}

export type MapGeometry = {
  width: number;
  height: number;
  town: { name: string; x: number; y: number };
  water: { name: string; d: string; label: { x: number; y: number; angle: number } }[];
  streets: { name: string; rank: number; d: string; label: { x: number; y: number; angle: number } }[];
  spots: Record<string, [number, number]>;
};

/** Everything the map draws, computed once at build time. */
export function buildMapGeometry(map: MapData): MapGeometry {
  const label = (pts: Pt[], t: number, offset: number) => {
    const a = along(pts, t);
    const r = (a.angle * Math.PI) / 180;
    return {
      x: +(a.x + Math.sin(r) * offset).toFixed(1),
      y: +(a.y - Math.cos(r) * offset).toFixed(1),
      angle: +a.angle.toFixed(1),
    };
  };
  return {
    width: map.size[0],
    height: map.size[1],
    town: { name: map.town.name, x: map.town.label[0], y: map.town.label[1] },
    water: map.water.map((w) => ({ name: w.name, d: smoothPath(w.path), label: label(w.path, w.labelAt, -12) })),
    streets: map.streets
      .slice()
      .sort((a, b) => b.rank - a.rank)
      .map((s) => ({ name: s.name, rank: s.rank, d: smoothPath(s.path), label: label(s.path, s.labelAt, 6) })),
    spots: Object.fromEntries(map.streets.filter((s) => s.spot).map((s) => [s.name, s.spot as Pt])),
  };
}
