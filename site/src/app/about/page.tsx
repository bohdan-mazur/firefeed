import type { Metadata } from "next";
import Link from "next/link";

import { SITE } from "@/lib/site";

import styles from "../prose.module.css";

export const metadata: Metadata = {
  title: "About this demo",
  description:
    "What FireFeed is, what is fictional in it, what it is not, and what can be connected to it. A portfolio project by Bohdan Mazur, Vulpes Tech.",
  alternates: { canonical: "/about/" },
};

export default function AboutPage() {
  return (
    <div className={`container ${styles.page}`}>
      <header className={styles.head}>
        <h1>About this demo</h1>
        <p className={styles.lead}>
          FireFeed is a portfolio project by {SITE.author} (Vulpes Tech). It shows one AI integration end to end:
          ingest, speech-to-text, structured extraction with schema validation, grouping, cost control and a static
          front end.
        </p>
        <div className={styles.actions}>
          <a className={styles.action} href={SITE.github}>
            Code on GitHub
          </a>
          <a className={styles.action} href={SITE.vulpes}>
            AI integrations at Vulpes Tech
          </a>
        </div>
      </header>

      <section className={styles.section} aria-labelledby="fictional">
        <h2 id="fictional">What is fictional</h2>
        <p>
          Larkmoor County, its streets, units and people do not exist; the name was checked against real places before
          use. The 53 transmissions and their expected answers were written for this demo. No recordings or transcripts
          from real radio systems or scanner services were collected or used.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="scope">
        <h2 id="scope">Scope</h2>
        <p>
          FireFeed runs on the synthetic set only and listens to no real channel. Every number on this site was measured
          on that set; accuracy on real radio traffic has not been measured.
        </p>
      </section>

      <section className={styles.section} aria-labelledby="connect">
        <h2 id="connect">What can be connected</h2>
        <ul className={styles.list}>
          <li>
            Your own recordings or recorder output: one audio or text file per transmission and a JSON sidecar with the
            time and channel. <Link href="/how-it-works/">How it works</Link> describes the format.
          </li>
          <li>A street and unit list for your area, so misheard names map to the right street.</li>
          <li>Alerts for new fire incidents to Telegram or a webhook: implemented, switched off in the demo.</li>
          <li>A real channel, only with the written permission of the source&apos;s owner.</li>
        </ul>
      </section>

      <section className={styles.section} aria-labelledby="privacy-title" id="privacy">
        <h2 id="privacy-title">Privacy</h2>
        <p>
          This site sets no cookies, runs no analytics and has no forms, so it collects nothing about you. The hosting
          provider may keep standard server logs (IP address, time, requested page) to operate the service.
        </p>
      </section>
    </div>
  );
}
