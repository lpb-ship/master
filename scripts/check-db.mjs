import pg from 'pg';
import { readConfig } from '../src/server/config.mjs';

let pool;
try {
  const config = readConfig(process.env);
  pool = new pg.Pool(config.database);
  const { rows } = await pool.query(`
    SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()
  `);
  if (config.appEnv !== 'local' && rows[0]?.ssl !== true) throw new Error();
  console.log(`Database connection verified for ${config.appEnv}.`);
} catch {
  console.error('Database verification failed. Check configuration, credentials, TLS trust, and network access.');
  process.exitCode = 1;
} finally {
  await pool?.end();
}
