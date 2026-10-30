import { readConfig } from './src/server/config.mjs';

readConfig(process.env);

export default {
  poweredByHeader: false,
  async headers() {
    return [{ source: '/api/:path*', headers: [
      { key: 'Cache-Control', value: 'no-store' },
      { key: 'X-Content-Type-Options', value: 'nosniff' },
    ] }];
  },
};
