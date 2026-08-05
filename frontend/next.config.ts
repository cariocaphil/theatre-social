import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produces a minimal, self-contained server bundle (node_modules pruned
  // to only what's needed at runtime) - ideal for small container images.
  output: "standalone",
};

export default nextConfig;
