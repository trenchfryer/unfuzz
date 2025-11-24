/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['localhost', 'unfuzz.vercel.app'],
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/uploads/**',
      },
    ],
  },
  // PWA configuration will be added via next-pwa when needed
  // For now, we can manually add service worker support
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      };
    }
    return config;
  },
};

module.exports = nextConfig;
