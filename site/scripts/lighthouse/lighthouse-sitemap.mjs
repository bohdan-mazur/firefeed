#!/usr/bin/env node
// Lighthouse over every URL of the sitemap (WDH 50.02): mobile profile, URLs one after another, the
// median of N runs by performance per URL, a JSON and a Markdown report. Measure a production build
// (next start / standalone), never the dev server; raw reports stay outside the repository.
//
//   npm --prefix scripts/lighthouse install                       once
//   npm run lighthouse -- http://localhost:3110 [runs=1] [--desktop] [--out=<dir>]
//
// Local numbers are for comparing pages with each other; the final word is PageSpeed Insights on the
// live site. One run varies by about ±10 points: use 5 runs for the home page and key templates.

import fs from "node:fs";
import path from "node:path";

import { launch } from "chrome-launcher";
import lighthouse from "lighthouse";

const args = process.argv.slice(2);
const base = (args.find((a) => /^https?:\/\//.test(a)) ?? "").replace(/\/$/, "");
const runs = Number(args.find((a) => /^\d+$/.test(a)) ?? 1);
const desktop = args.includes("--desktop");
const outDir = path.resolve(args.find((a) => a.startsWith("--out="))?.slice(6) ?? ".");
if (!base) {
    console.error("usage: npm run lighthouse -- <base URL> [runs] [--desktop] [--out=<dir>]");
    process.exit(2);
}

// FireFeed: --paths=/,/about/ measures only those paths instead of the whole sitemap.
const only = args.find((a) => a.startsWith("--paths="))?.slice(8).split(",").filter(Boolean);
const xml = only ? "" : await (await fetch(`${base}/sitemap.xml`)).text();
// The sitemap names the public origin; measure the same paths on the given base
const paths = only ?? [...xml.matchAll(/<loc>(.*?)<\/loc>/g)].map((m) => new URL(m[1]).pathname);

const chrome = await launch({ chromePath: process.env.CHROME_PATH || undefined, chromeFlags: ["--headless=new", "--no-first-run"] });
const config = desktop ? { extends: "lighthouse:default", settings: { formFactor: "desktop", screenEmulation: { mobile: false, width: 1350, height: 940, deviceScaleFactor: 1, disabled: false }, throttlingMethod: "simulate" } } : undefined;
const rows = [];

try {
    for (const p of paths) {
        const results = [];
        for (let i = 0; i < runs; i++) {
            const { lhr } = await lighthouse(base + p, { port: chrome.port, output: "json", logLevel: "error" }, config);
            const c = lhr.categories;
            results.push({
                perf: Math.round(c.performance.score * 100),
                a11y: Math.round(c.accessibility.score * 100),
                bp: Math.round(c["best-practices"].score * 100),
                seo: Math.round(c.seo.score * 100),
                lcp: Math.round(lhr.audits["largest-contentful-paint"].numericValue),
                tbt: Math.round(lhr.audits["total-blocking-time"].numericValue),
                cls: Number(lhr.audits["cumulative-layout-shift"].numericValue.toFixed(3)),
                lcpElement: lhr.audits["largest-contentful-paint-element"]?.details?.items?.[0]?.items?.[0]?.node?.snippet ?? "",
                failed: Object.values(lhr.audits).filter((a) => a.score === 0 && a.scoreDisplayMode === "binary").map((a) => a.id),
            });
        }
        results.sort((a, b) => a.perf - b.perf);
        const median = results[Math.floor(results.length / 2)];
        rows.push({ path: p, runs, ...median });
        console.log(`${p.padEnd(40)} perf ${median.perf}  a11y ${median.a11y}  bp ${median.bp}  seo ${median.seo}  LCP ${median.lcp} ms  TBT ${median.tbt} ms`);
    }
} finally {
    // FireFeed: on Windows chrome-launcher can fail to delete its temp profile (EPERM); keep the report.
    try {
        await chrome.kill();
    } catch (err) {
        console.warn(`chrome cleanup: ${err.code ?? err.message}`);
    }
}

const stamp = new Date().toISOString().slice(0, 10);
const stats = (key) => {
    const values = rows.map((r) => r[key]).sort((a, b) => a - b);
    return `${values[0]} | ${values[Math.floor(values.length / 2)]} | ${values.at(-1)}`;
};
const md = [
    `# Lighthouse ${desktop ? "desktop" : "mobile"}, ${base}, ${stamp}`,
    "",
    `${rows.length} URLs, ${runs} run(s) each, median by performance.`,
    "",
    "| Category | Min | Median | Max |",
    "|---|---|---|---|",
    `| Performance | ${stats("perf")} |`,
    `| Accessibility | ${stats("a11y")} |`,
    `| Best practices | ${stats("bp")} |`,
    `| SEO | ${stats("seo")} |`,
    "",
    "| Path | Perf | A11y | BP | SEO | LCP ms | TBT ms | Failed audits |",
    "|---|---|---|---|---|---|---|---|",
    ...rows.map((r) => `| ${r.path} | ${r.perf} | ${r.a11y} | ${r.bp} | ${r.seo} | ${r.lcp} | ${r.tbt} | ${r.failed.join(", ")} |`),
    "",
].join("\n");

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, `lighthouse-report-${stamp}.json`), JSON.stringify(rows, null, 2));
fs.writeFileSync(path.join(outDir, `lighthouse-report-${stamp}.md`), md);
console.log(`\nreport → ${path.join(outDir, `lighthouse-report-${stamp}.md`)}`);
