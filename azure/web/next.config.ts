import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker: bundle only the files needed at runtime, so the runner image
  // carries a trimmed node_modules instead of the full dependency tree.
  output: "standalone",

  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains",
          },
          {
            // 'unsafe-inline' for scripts is required by Next's hydration
            // payload — a known relaxation, not a strict CSP.
            key: "Content-Security-Policy",
            value:
              "default-src 'self'; script-src 'self' 'unsafe-inline'; " +
              "style-src 'self' 'unsafe-inline'; img-src 'self' data:; " +
              "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
