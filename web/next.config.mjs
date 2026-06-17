const RAW = process.env.API_URL || "http://127.0.0.1:8000";
const API_BASE = /^https?:\/\//.test(RAW) ? RAW : `https://${RAW}`;

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: API_BASE + "/:path*",
      },
    ];
  },
};
export default nextConfig;
