import type { NextConfig } from "next";

const BACKEND = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8420";

const nextConfig: NextConfig = {
  // Browser code calls same-origin /api/*; Next proxies it to the FastAPI
  // backend. This is what makes a tunnel (ngrok) work: a remote visitor's
  // browser never needs to reach localhost:8420 itself.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
  },
  // Dev server blocks cross-origin dev assets by default; allow ngrok tunnels.
  // The resume audit (/api/audit) waits on a local LLM for up to a few minutes;
  // the rewrite proxy's default 30 s timeout would cut it off.
  experimental: { proxyTimeout: 300_000 },
  allowedDevOrigins: ["*.ngrok-free.app", "*.ngrok-free.dev", "*.ngrok.app", "*.ngrok.dev", "*.ngrok.io"],
};

export default nextConfig;
