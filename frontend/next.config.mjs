/** @type {import('next').NextConfig} */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Proxy API calls to the backend in dev to avoid CORS.
    return [
      { source: "/api/:path*", destination: `${API_BASE}/api/:path*` },
    ];
  },
};

export default nextConfig;
