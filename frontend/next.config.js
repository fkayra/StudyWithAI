/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Only use rewrites if BACKEND_BASE is defined (local development)
    // In production, API calls go directly to the backend URL
    if (process.env.BACKEND_BASE) {
      return [
        {
          source: '/api/:path*',
          destination: process.env.BACKEND_BASE + '/:path*',
        },
      ]
    }
    return []
  },
}

module.exports = nextConfig
