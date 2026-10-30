import assert from 'node:assert/strict';
import { rootCertificates } from 'node:tls';
import test from 'node:test';
import { readConfig } from '../src/server/config.mjs';

const project = 'abcdefghijklmnopqrst';
const local = {
  APP_ENV: 'local', APP_ORIGIN: 'http://127.0.0.1:3000',
  DATABASE_URL: 'postgresql://postgres:local-only@127.0.0.1:54322/postgres',
};
const staging = {
  APP_ENV: 'staging', APP_ORIGIN: 'https://staging.example.com',
  SUPABASE_PROJECT_REF: project, DATABASE_CA_CERT: rootCertificates[0],
  DATABASE_URL: `postgresql://app_runtime.${project}:secret@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=verify-full`,
};

test('local configuration permits only loopback connections', () => {
  assert.equal(readConfig(local).database.ssl, false);
  for (const url of ['https://staging.example.com', 'http://192.168.1.1:3000']) {
    assert.throws(() => readConfig({ ...local, APP_ORIGIN: url }), /APP_ORIGIN/);
  }
  assert.throws(() => readConfig({ ...local, DATABASE_URL: staging.DATABASE_URL }), /DATABASE_URL/);
});

test('remote connections preserve CA and certificate validation outside the URL', () => {
  const { database } = readConfig(staging);
  assert.deepEqual(database.ssl, { ca: rootCertificates[0], rejectUnauthorized: true });
  assert.equal(new URL(database.connectionString).search, '');
  assert.equal(database.max, 2);
  assert.ok(database.connectionTimeoutMillis > 0);
  assert.equal(readConfig({ ...staging, APP_ENV: 'production' }).appEnv, 'production');
  assert.equal(readConfig({ ...staging, DATABASE_URL: `postgresql://app_runtime:secret@db.${project}.supabase.co:5432/postgres?sslmode=verify-full` }).database.ssl.rejectUnauthorized, true);
});

test('missing configuration and TLS downgrade attempts fail closed', () => {
  for (const field of ['APP_ENV', 'APP_ORIGIN', 'DATABASE_URL', 'DATABASE_CA_CERT', 'SUPABASE_PROJECT_REF']) {
    assert.throws(() => readConfig({ ...staging, [field]: '' }), new RegExp(field));
  }
  for (const mode of ['', '?sslmode=require', '?sslmode=disable', '?sslmode=verify-full&sslmode=disable', '?sslmode=verify-full&sslcert=x', '?sslmode=verify-full&ssl=false']) {
    assert.throws(() => readConfig({ ...staging, DATABASE_URL: staging.DATABASE_URL.split('?')[0] + mode }), /DATABASE_URL/);
  }
  assert.throws(() => readConfig({ ...staging, DATABASE_CA_CERT: 'not-a-certificate' }), /DATABASE_CA_CERT/);
  assert.throws(() => readConfig({ ...staging, NODE_TLS_REJECT_UNAUTHORIZED: '0' }), /NODE_TLS_REJECT_UNAUTHORIZED/);
});

test('environment mismatches, public variables, insecure origins and privileged users fail', () => {
  for (const change of [
    { APP_ENV: 'test' }, { VERCEL_ENV: 'preview', APP_ENV: 'production' },
    { NEXT_PUBLIC_DATABASE_URL: 'secret' }, { APP_ORIGIN: 'http://staging.example.com' },
    { APP_ORIGIN: 'https://user:secret@staging.example.com' },
    { APP_ORIGIN: 'https://staging.example.com/callback' },
    { SUPABASE_PROJECT_REF: 'zyxwvutsrqponmlkjihg' },
    { DATABASE_URL: staging.DATABASE_URL.replace('app_runtime.', 'postgres.') },
    { DATABASE_URL: staging.DATABASE_URL.replace('pooler.supabase.com', 'attacker.example.com') },
  ]) assert.throws(() => readConfig({ ...staging, ...change }), /Invalid or missing configuration/);
  assert.throws(() => readConfig({ ...local, VERCEL: '1' }), /APP_ENV/);
});

test('validation errors do not expose supplied secrets', () => {
  for (const DATABASE_URL of ['secret-password', 'https://user:secret-password@bad-host/', 'postgresql://user:secret-password@bad-host/postgres']) {
    assert.throws(() => readConfig({ ...staging, DATABASE_URL }), (error) => {
      assert.equal(error.message, 'Invalid or missing configuration: DATABASE_URL');
      return true;
    });
  }
});
