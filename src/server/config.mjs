import { X509Certificate } from 'node:crypto';

// Pure validation: never include values or provider errors in diagnostics.
export function readConfig(env) {
  const fail = (name) => { throw new Error(`Invalid or missing configuration: ${name}`); };
  const required = (name) => {
    const value = env[name];
    if (typeof value !== 'string' || !value.trim()) fail(name);
    return value;
  };
  const parseUrl = (name) => {
    try { return new URL(required(name)); } catch { return fail(name); }
  };
  const appEnv = required('APP_ENV');
  if (!['local', 'staging', 'production'].includes(appEnv)) fail('APP_ENV');
  const local = appEnv === 'local';
  if (env.VERCEL === '1' && local) fail('APP_ENV');
  if (env.VERCEL_ENV === 'preview' && appEnv !== 'staging') fail('APP_ENV');
  if (env.NODE_TLS_REJECT_UNAUTHORIZED === '0') fail('NODE_TLS_REJECT_UNAUTHORIZED');
  // This baseline has no public configuration. Add explicit public fields only
  // when a feature needs them, never a generic environment export.
  if (Object.keys(env).some((key) => key.startsWith('NEXT_PUBLIC_'))) fail('NEXT_PUBLIC_*');
  const loopback = (host) => ['localhost', '127.0.0.1', '[::1]'].includes(host);
  const origin = parseUrl('APP_ORIGIN');
  if (origin.username || origin.password || origin.search || origin.hash || origin.pathname !== '/') fail('APP_ORIGIN');
  if (local ? origin.protocol !== 'http:' || !loopback(origin.hostname) : origin.protocol !== 'https:' || loopback(origin.hostname)) fail('APP_ORIGIN');
  const database = parseUrl('DATABASE_URL');
  if (!['postgres:', 'postgresql:'].includes(database.protocol) || !database.username || !database.password || database.pathname !== '/postgres' || database.hash) fail('DATABASE_URL');
  // Never let connection-string SSL options override the explicit TLS policy.
  if ([...database.searchParams.keys()].some((key) => key !== 'sslmode')) fail('DATABASE_URL');
  if (database.searchParams.getAll('sslmode').length > 1) fail('DATABASE_URL');
  let ssl = false;
  if (local) {
    if (!loopback(database.hostname) || database.search) fail('DATABASE_URL');
  } else {
    const project = required('SUPABASE_PROJECT_REF');
    if (!/^[a-z]{20}$/.test(project)) fail('SUPABASE_PROJECT_REF');
    const direct = database.hostname === `db.${project}.supabase.co` && database.port === '5432';
    const pooled = /^[a-z0-9-]+\.pooler\.supabase\.com$/.test(database.hostname) && database.port === '6543';
    let username;
    try { username = decodeURIComponent(database.username); } catch { fail('DATABASE_URL'); }
    if (!direct && !pooled) fail('DATABASE_URL');
    if (pooled && !username.endsWith(`.${project}`)) fail('DATABASE_URL');
    const role = pooled ? username.slice(0, -(project.length + 1)) : username;
    if (!/^[a-z_][a-z0-9_]*$/.test(role) || ['postgres', 'supabase_admin', 'service_role', 'authenticator', 'anon', 'authenticated'].includes(role)) fail('DATABASE_URL');
    if (database.searchParams.get('sslmode') !== 'verify-full') fail('DATABASE_URL');
    const ca = required('DATABASE_CA_CERT').replaceAll('\\n', '\n');
    try { new X509Certificate(ca); } catch { fail('DATABASE_CA_CERT'); }
    ssl = { rejectUnauthorized: true, ca };
  }
  database.search = '';
  return {
    appEnv,
    origin: origin.origin,
    database: {
      connectionString: database.toString(),
      ssl,
      max: 2,
      connectionTimeoutMillis: 5000,
      idleTimeoutMillis: 10000,
      statement_timeout: 5000,
      query_timeout: 6000,
    },
  };
}
