export const SITE = {
  name: "FireFeed",
  url: "https://fire-feeds.online",
  title: "FireFeed: fire radio traffic to structured incidents",
  description:
    "A demo pipeline that turns fire dispatch radio traffic into typed, grouped incidents with an LLM and a strict JSON schema. Runs on 53 synthetic calls from a fictional county.",
  notice: "Demo on synthetic data. All calls, places and people are fictional.",
  // Public repository: final name is set in M6 (see PLAN.md).
  github: "https://github.com/bohdan-mazur/firefeed",
  vulpes: "https://vulpes-tech.net/ai-integrations",
  author: "Bohdan Mazur",
} as const;
