import type { Metadata, Viewport } from "next";

import { SiteFooter, SiteHeader, SyntheticBanner } from "@/components/Frame";
import { SITE } from "@/lib/site";

import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE.url),
  title: { default: SITE.title, template: "%s · FireFeed" },
  description: SITE.description,
  applicationName: SITE.name,
  authors: [{ name: SITE.author }],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: SITE.name,
    title: SITE.title,
    description: SITE.description,
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "FireFeed. Demo on synthetic data." }],
  },
  twitter: { card: "summary_large_image" },
  formatDetection: { telephone: false, address: false },
};

export const viewport: Viewport = {
  themeColor: "#faf8f4",
  colorScheme: "light",
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  "@id": `${SITE.url}/#website`,
  name: SITE.name,
  url: `${SITE.url}/`,
  description: SITE.description,
  inLanguage: "en",
  author: { "@type": "Person", name: SITE.author },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <SyntheticBanner />
        <SiteHeader />
        <main id="main">{children}</main>
        <SiteFooter />
        {/* Built from constants above, not from input; "<" is escaped so the JSON cannot close the tag. */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }}
        />
      </body>
    </html>
  );
}
