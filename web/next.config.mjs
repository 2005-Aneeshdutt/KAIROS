/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Proxy API calls to the FastAPI backend so the dashboard uses same-origin /api.
    return [
      {
        source: "/api/:path*",
        destination: (process.env.API_URL || "http://127.0.0.1:8000") + "/:path*",
      },
    ];
  },
};
export default nextConfig;
