/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { isServer }) => {
    // Handle canvas dependency for PDF rendering
    if (isServer) {
      config.externals = config.externals || [];
      config.externals.push('canvas');
    } else {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        canvas: false,
      };
    }
    
    return config;
  },
  experimental: {
    esmExternals: 'loose'
  }
};

module.exports = nextConfig;

