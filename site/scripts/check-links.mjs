// Checks the static export in out/: every internal link resolves to a file, every page carries the
// synthetic-data notice. With --external, also requests each external link once (GET, no body kept).
import { readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const OUT = fileURLToPath(new URL("../out/", import.meta.url));
const NOTICE = "Demo on synthetic data.";
// Canonical and OG addresses on the production domain mirror internal pages; they are checked as internal.
const SELF = "https://fire-feeds.online";
const external = process.argv.includes("--external");

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = await Promise.all(
    entries.map((e) => (e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)])),
  );
  return files.flat();
}

async function exists(file) {
  try {
    return (await stat(file)).isFile();
  } catch {
    return false;
  }
}

function target(href) {
  const clean = decodeURI(href.split("#")[0].split("?")[0]);
  if (clean === "" || clean.endsWith("/")) return path.join(OUT, clean, "index.html");
  return path.join(OUT, clean);
}

const pages = (await walk(OUT)).filter((f) => f.endsWith(".html"));
const problems = [];
const outside = new Map();
let checked = 0;

for (const page of pages) {
  const html = await readFile(page, "utf8");
  const name = path.relative(OUT, page).replaceAll("\\", "/");
  if (!html.includes(NOTICE)) problems.push(`${name}: no synthetic-data notice`);
  for (let [, href] of html.matchAll(/\s(?:href|src|content)="([^"]+)"/g)) {
    if (href.startsWith(SELF)) href = href.slice(SELF.length) || "/";
    if (href.startsWith("http://") || href.startsWith("https://")) {
      if (!outside.has(href)) outside.set(href, name);
      continue;
    }
    if (!href.startsWith("/") || href.startsWith("//")) continue;
    checked += 1;
    if (!(await exists(target(href)))) problems.push(`${name}: broken link ${href}`);
  }
}

console.log(`${pages.length} pages, ${checked} internal links checked, ${outside.size} external links`);
if (external) {
  for (const [href, from] of outside) {
    let status;
    try {
      const res = await fetch(href, { redirect: "follow", signal: AbortSignal.timeout(15000) });
      status = res.status;
      await res.body?.cancel();
    } catch (err) {
      status = `error: ${err.cause?.code ?? err.name}`;
    }
    console.log(`  ${status}  ${href}  (first seen on ${from})`);
  }
}
if (problems.length) {
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log("ok: no broken internal links, notice on every page");
