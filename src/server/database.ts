import 'server-only';
import { Pool } from 'pg';
import { readConfig } from './config.mjs';

const globalDatabase = globalThis as typeof globalThis & { databasePool?: Pool };

export function databasePool(): Pool {
  if (!globalDatabase.databasePool) {
    const pool = new Pool(readConfig(process.env).database);
    // An idle connection can fail outside a request. Never log the raw error.
    pool.on('error', () => console.error('database_idle_connection_failed'));
    globalDatabase.databasePool = pool;
  }
  return globalDatabase.databasePool;
}
