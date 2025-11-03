/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Only use rewrites if BACKEND_BASE is defined and valid (local development)
    // In production, API calls go directly to the backend URL via absolute URLs
    const backendBase = process.env.BACKEND_BASE;
    
    if (backendBase && backendBase !== 'undefined' && backendBase.trim() !== '') {
      return [
        {
          source: '/api/:path*',
          destination: `${backendBase}/:path*`,
        },
      ]
    }
    
    // Return empty array if no backend base is configured
    // Frontend will use absolute URLs for API calls
    return []
  },
}

module.exports = nextConfig
