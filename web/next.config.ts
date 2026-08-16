import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker: bundle only the files needed at runtime, so the runner image
  // carries a trimmed node_modules instead of the full dependency tree.
  // Harmless outside Docker — `npm run dev` ignores it.
  output: "standalone",
};

export default nextConfig;
