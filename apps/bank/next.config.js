/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      {
        source: '/share/:token',
        destination: '/wish/:token',
        permanent: true,
      },
    ];
  },
};

module.exports = nextConfig;
