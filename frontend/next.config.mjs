/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*", // frontend /api/*
        destination: "https://data.capraeleadseekers.site/api/:path*", // backend
      },
    ];
  },
};

export default nextConfig;
