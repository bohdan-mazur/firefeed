import Link from "next/link";

import { SITE } from "@/lib/site";

import styles from "./Frame.module.css";

const NAV = [
  { href: "/", label: "Live feed" },
  { href: "/how-it-works/", label: "How it works" },
  { href: "/about/", label: "About" },
];

export function SyntheticBanner() {
  return (
    <p className={styles.banner} role="note">
      <strong>Demo on synthetic data.</strong> All calls, places and people are fictional.
    </p>
  );
}

export function SiteHeader() {
  return (
    <header className={styles.header}>
      <div className={`container ${styles.headerInner}`}>
        <Link href="/" className={styles.brand} aria-label="FireFeed, live feed">
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" className={styles.mark}>
            <path d="M5 19a9 9 0 0 1 0-14M8.5 15.5a4 4 0 0 1 0-7" />
            <circle cx="14" cy="12" r="2.2" />
            <path d="M19 5v14" />
          </svg>
          FireFeed
        </Link>
        <nav aria-label="Main" className={styles.nav}>
          {NAV.map((item) => (
            <Link key={item.href} href={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className={styles.actions}>
          <a className={styles.button} href={SITE.vulpes}>
            Vulpes Tech
          </a>
          <a className={styles.button} href={SITE.github}>
            GitHub
          </a>
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <div className={`container ${styles.footerInner}`}>
        <p>
          <strong>{SITE.notice}</strong> Larkmoor County does not exist; the transmissions were written for this demo.
        </p>
        <p>
          A portfolio project by {SITE.author}, <a href={SITE.vulpes}>Vulpes Tech</a>. Code on{" "}
          <a href={SITE.github}>GitHub</a>. The site sets no cookies and runs no analytics (
          <Link href="/about/#privacy">privacy</Link>).
        </p>
      </div>
    </footer>
  );
}
