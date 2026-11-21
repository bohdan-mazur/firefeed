// Renders public/og.png (1200 x 630) from an SVG with the site's colours. Run once and commit the PNG:
// the result depends on the fonts of the machine that renders it.
import { writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const out = fileURLToPath(new URL("../public/og.png", import.meta.url));
const serif = "Georgia, 'Iowan Old Style', 'Times New Roman', serif";
const sans = "'Segoe UI', Arial, sans-serif";
const mono = "Consolas, 'Courier New', monospace";

const rows = [
  ["13:04:12", "Dispatch", "Structure fire, Bellwether Avenue", "Dispatched"],
  ["13:21:40", "Fireground 2", "Fire knocked down, check the attic", "Under control"],
  ["14:58:20", "Dispatch", "Odor of natural gas, Ferrier Street", "Not a fire"],
];

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#faf8f4"/>
  <rect width="1200" height="56" fill="#1b1b1f"/>
  <text x="64" y="36" font-family="${sans}" font-size="22" fill="#ffffff"><tspan font-weight="700">Demo on synthetic data.</tspan> All calls, places and people are fictional.</text>
  <g transform="translate(64 120)" fill="none" stroke="#c2410c" stroke-width="3.2" stroke-linecap="round">
    <path d="M8 34a17 17 0 0 1 0-26"/><path d="M15 27a8 8 0 0 1 0-12"/><path d="M36 6v30"/>
  </g>
  <circle cx="91" cy="141" r="4.5" fill="#c2410c"/>
  <text x="118" y="152" font-family="${serif}" font-size="34" font-weight="700" fill="#1b1b1f">FireFeed</text>
  <text x="64" y="248" font-family="${serif}" font-size="62" font-weight="600" fill="#1b1b1f">Fire radio traffic, read by a model</text>
  <text x="64" y="322" font-family="${serif}" font-size="62" font-weight="600" fill="#1b1b1f">and filed as incidents</text>
  ${rows
    .map(
      ([t, ch, text, status], i) => `
  <g transform="translate(64 ${388 + i * 66})">
    <line x1="0" y1="0" x2="1072" y2="0" stroke="#e4e0d8"/>
    <text x="0" y="40" font-family="${mono}" font-size="22" fill="#1b1b1f">${t}</text>
    <text x="130" y="40" font-family="${mono}" font-size="18" fill="#5b5b66">${ch}</text>
    <text x="300" y="40" font-family="${serif}" font-size="26" fill="#1b1b1f">${text}</text>
    <text x="1072" y="40" text-anchor="end" font-family="${sans}" font-size="20" font-weight="700" fill="${status === "Not a fire" ? "#3b5b7a" : status === "Under control" ? "#8a5a00" : "#a9380a"}">${status}</text>
  </g>`,
    )
    .join("")}
</svg>`;

const png = await sharp(Buffer.from(svg)).png({ compressionLevel: 9 }).toBuffer();
await writeFile(out, png);
console.log(`wrote ${out} (${Math.round(png.length / 1024)} KB)`);
