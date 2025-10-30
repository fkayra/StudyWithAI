/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.BACKEND_BASE + '/:path*',
      },
    ]
  },
}

module.exports = nextConfig
