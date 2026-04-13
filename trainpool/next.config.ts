import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    // Enables Server Actions in forms, used by the trip create form
    serverActions: {
      bodySizeLimit: "1mb",
    },
  },
};

export default nextConfig;
