// Submits fire-feeds.online addresses to IndexNow: Bing and the other engines of the protocol get them
// in one request, with no daily quota. Run it on purpose after a deploy that adds or changes pages,
// because it sends the addresses to an outside service.
//   npm run indexnow -- --dry-run              check the key and list what would be sent, send nothing
//   npm run indexnow                           every address in the live sitemap
//   npm run indexnow -- /about/ /calls/c004/   only these paths or full addresses, each must be in the sitemap
// The key is public/<key>.txt: 32 hex characters as the file name and as its only content. It is public
// by design (engines fetch it to confirm the site), so it is kept in git and the script reads it from there.
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const HOST = "fire-feeds.online";
const ENDPOINT = "https://api.indexnow.org/IndexNow";
const PUBLIC = fileURLToPath(new URL("../public/", import.meta.url));

class Stop extends Error {}

function readKey() {
  const files = readdirSync(PUBLIC).filter((f) => /^[0-9a-f]{32}\.txt$/.test(f));
  if (files.length !== 1) throw new Stop(`expected one <key>.txt in public/, found ${files.length}`);
  const key = files[0].slice(0, -".txt".length);
  if (readFileSync(PUBLIC + files[0], "utf8").trim() !== key) throw new Stop(`public/${files[0]} must contain its own name`);
  return key;
}

// Bodies are always read: an unread body keeps its socket busy, and exiting then crashes Node on Windows
async function get(url) {
  const res = await fetch(url);
  return { status: res.status, ok: res.ok, text: await res.text() };
}

// Paths or full addresses: a full address glued to the host gives 422 (WDH 70.01)
const toUrl = (p) => (/^https?:\/\//.test(p) ? p : `https://${HOST}${p.startsWith("/") ? "" : "/"}${p}`);

async function main(args) {
  const dryRun = args.includes("--dry-run");
  const paths = args.filter((a) => a !== "--dry-run");

  const key = readKey();
  const keyLocation = `https://${HOST}/${key}.txt`;
  // Without the live key file the engines answer 403, so check it before sending anything
  const live = await get(keyLocation);
  if (!live.ok || live.text.trim() !== key) {
    throw new Stop(`${keyLocation} returned ${live.status}${live.ok ? " with other content" : ""}: deploy the site with this key first`);
  }

  const sitemap = await get(`https://${HOST}/sitemap.xml`);
  if (!sitemap.ok) throw new Stop(`sitemap.xml returned ${sitemap.status}`);
  const inSitemap = [...sitemap.text.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  const urlList = paths.length ? paths.map(toUrl) : inSitemap;
  // Typos and paths a shell rewrote (Git Bash turns /about/ into C:/.../about/) would send dead addresses
  const unknown = urlList.filter((u) => !inSitemap.includes(u));
  if (unknown.length) throw new Stop(`not in the live sitemap of ${HOST}: ${unknown.join(", ")}`);
  if (!urlList.length) throw new Stop("nothing to send");

  console.log(`${urlList.length} address(es), key file ${keyLocation} is live:`);
  for (const u of urlList) console.log(`  ${u}`);
  if (dryRun) {
    console.log("dry run: nothing was sent");
    return;
  }

  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({ host: HOST, key, keyLocation, urlList }),
  });
  const text = await res.text().catch(() => "");
  if (res.status !== 200 && res.status !== 202) {
    // A new key can get 403 for a few hours even when the key file is live: retry later with the same key
    const hint = res.status === 403 ? " (a new key may need a few hours: retry later, keep the key)" : "";
    throw new Stop(`IndexNow answered ${res.status}${hint}: ${text || res.statusText}`);
  }
  console.log(`IndexNow answered ${res.status}: accepted`);
}

// No process.exit(): the exit code is set and Node ends once open sockets close
main(process.argv.slice(2)).catch((error) => {
  console.error(error instanceof Stop ? error.message : error);
  process.exitCode = 1;
});
