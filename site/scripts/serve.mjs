// Serves out/ like a static host would: gzip, long cache for hashed assets, 404.html for misses.
// For local checks (Lighthouse, link checks) only.  node scripts/serve.mjs [port]
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createGzip } from "node:zlib";

const OUT = fileURLToPath(new URL("../out/", import.meta.url));
const PORT = Number(process.argv[2] ?? 4330);
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};
const COMPRESSIBLE = new Set([".html", ".js", ".css", ".json", ".txt", ".xml", ".svg"]);

async function resolve(urlPath) {
  const clean = decodeURIComponent(urlPath.split("?")[0]);
  const file = path.join(OUT, clean.endsWith("/") ? path.join(clean, "index.html") : clean);
  if (!file.startsWith(OUT)) return null;
  try {
    const info = await stat(file);
    if (info.isFile()) return file;
    if (info.isDirectory()) return resolve(`${clean}/`);
  } catch {}
  return null;
}

createServer(async (req, res) => {
  let file = await resolve(req.url ?? "/");
  let status = 200;
  if (!file) {
    file = path.join(OUT, "404.html");
    status = 404;
  }
  const ext = path.extname(file);
  const headers = {
    "Content-Type": TYPES[ext] ?? "application/octet-stream",
    "Cache-Control": req.url?.startsWith("/_next/static/") ? "public, max-age=31536000, immutable" : "public, max-age=0, must-revalidate",
    "X-Content-Type-Options": "nosniff",
  };
  const gzip = COMPRESSIBLE.has(ext) && /\bgzip\b/.test(req.headers["accept-encoding"] ?? "");
  if (gzip) headers["Content-Encoding"] = "gzip";
  res.writeHead(status, headers);
  const stream = createReadStream(file);
  (gzip ? stream.pipe(createGzip()) : stream).pipe(res);
}).listen(PORT, "127.0.0.1", () => console.log(`serving ${OUT} on http://127.0.0.1:${PORT}`));
