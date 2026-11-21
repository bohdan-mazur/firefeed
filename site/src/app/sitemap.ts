import type { MetadataRoute } from "next";

import { getFeed } from "@/lib/data";
import { SITE } from "@/lib/site";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const feed = getFeed();
  // The content changes only with a new recorded run, so its date is the page date.
  const updated = new Date(feed.usage.recorded_to ?? "2026-11-21");
  const pages = ["/", "/how-it-works/", "/about/"];
  return [
    ...pages.map((path) => ({ url: `${SITE.url}${path}`, lastModified: updated })),
    ...feed.incidents.map((i) => ({ url: `${SITE.url}/incidents/${i.id}/`, lastModified: updated })),
    ...feed.calls.map((c) => ({ url: `${SITE.url}/calls/${c.id}/`, lastModified: updated })),
  ];
}
