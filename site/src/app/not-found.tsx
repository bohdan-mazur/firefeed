import type { Metadata } from "next";
import Link from "next/link";

import styles from "./prose.module.css";

export const metadata: Metadata = {
  title: "Page not found",
  robots: { index: false, follow: true },
};

export default function NotFound() {
  return (
    <div className={`container ${styles.page}`}>
      <header className={styles.head}>
        <p className={styles.note}>404</p>
        <h1>No such page</h1>
        <p className={styles.lead}>
          The address may be mistyped, or the call or incident is not part of this demo.
        </p>
        <div className={styles.actions}>
          <Link className={styles.action} href="/">
            Back to the live feed
          </Link>
          <Link className={styles.action} href="/how-it-works/">
            How it works
          </Link>
        </div>
      </header>
    </div>
  );
}
