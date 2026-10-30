import assert from 'node:assert/strict';
import test from 'node:test';
import { deployStaging } from '../scripts/deploy-staging.mjs';

const env = {
  VERCEL_TOKEN: 'private-token', VERCEL_ORG_ID: 'team_test', VERCEL_PROJECT_ID: 'prj_test',
  VERCEL_AUTOMATION_BYPASS_SECRET: 'private-bypass', GITHUB_SHA: 'a'.repeat(40), GITHUB_REF_NAME: 'release',
};
const project = { id: 'prj_test', name: 'staging', env: [{ key: 'APP_ENV', target: ['production'], type: 'plain', value: 'staging' }] };
const json = (body, status = 200) => new Response(JSON.stringify(body), { status });
const noWait = async () => {};

test('deploys the exact revision and sends each secret only to its intended service', async () => {
  const calls = [];
  const responses = [project, { id: 'dpl_test' }, { readyState: 'BUILDING' }, { readyState: 'READY', url: 'staging-123.vercel.app' }, { status: 'ready' }];
  const url = await deployStaging(env, async (url, options) => {
    calls.push({ url: String(url), ...options });
    return json(responses.shift());
  }, noWait);
  assert.equal(url, 'https://staging-123.vercel.app');
  assert.equal(JSON.parse(calls[1].body).gitSource.sha, env.GITHUB_SHA);
  assert.equal(calls[0].headers.Authorization, 'Bearer private-token');
  assert.equal(calls.at(-1).headers.Authorization, undefined);
  assert.equal(calls.at(-1).headers['x-vercel-protection-bypass'], 'private-bypass');
  assert.ok(calls.every((call) => call.redirect === 'error'));
});

test('refuses a production or unclassified project before creating a deployment', async () => {
  for (const value of ['production', undefined]) {
    let calls = 0;
    await assert.rejects(deployStaging(env, async () => {
      calls++;
      return json({ ...project, env: [{ ...project.env[0], value }] });
    }, noWait), /not explicitly configured/);
    assert.equal(calls, 1);
  }
});

test('does not follow a malicious readiness hostname or leak API error bodies', async () => {
  const responses = [project, { id: 'dpl_test' }, { readyState: 'READY', url: 'attacker.example' }];
  await assert.rejects(deployStaging(env, async () => json(responses.shift()), noWait), /Unexpected deployment hostname/);
  await assert.rejects(deployStaging(env, async () => json({ error: 'private-token' }, 403), noWait), (error) => !error.message.includes('private-token'));
});

test('reports remote build failure and bounds readiness retries', async () => {
  for (const state of ['ERROR', 'CANCELED']) {
    const responses = [project, { id: 'dpl_test' }, { readyState: state }];
    await assert.rejects(deployStaging(env, async () => json(responses.shift()), noWait), /Remote deployment failed/);
  }
  const responses = [project, { id: 'dpl_test' }, { readyState: 'READY', url: 'staging-123.vercel.app' }];
  let requests = 0;
  await assert.rejects(deployStaging(env, async () => {
    requests++;
    return json(responses.shift() ?? { status: 'unavailable' });
  }, noWait), /readiness failed/);
  assert.equal(requests, 9);
});
