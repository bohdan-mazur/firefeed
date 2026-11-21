import type { NextConfig } from "next";

// Static export: no server, no API keys. The data is read from ../data at build time.
const config: NextConfig = {
  output: "export",
  trailingSlash: true,
  reactStrictMode: true,
  poweredByHeader: false,
  images: { unoptimized: true },
  eslint: { ignoreDuringBuilds: true },
};

export default config;
