import { appendFile } from 'node:fs/promises';
import { setTimeout } from 'node:timers/promises';
import { pathToFileURL } from 'node:url';

export async function deployStaging(env, request = fetch, pause = setTimeout) {
  for (const key of ['VERCEL_TOKEN', 'VERCEL_ORG_ID', 'VERCEL_PROJECT_ID', 'VERCEL_AUTOMATION_BYPASS_SECRET', 'GITHUB_SHA', 'GITHUB_REF_NAME']) {
    if (!env[key]) throw new Error(`Missing deployment setting: ${key}`);
  }
  if (!/^[a-f0-9]{40}$/.test(env.GITHUB_SHA)) throw new Error('Invalid deployment revision');
  const api = async (path, body) => {
    const url = new URL(path, 'https://api.vercel.com');
    url.searchParams.set('teamId', env.VERCEL_ORG_ID);
    const response = await request(url, {
      method: body ? 'POST' : 'GET',
      headers: { Authorization: `Bearer ${env.VERCEL_TOKEN}`, 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(15000),
      redirect: 'error',
    });
    if (!response.ok) throw new Error(`Deployment API failed (${response.status}); inspect the restricted provider dashboard`);
    return response.json();
  };
  const project = await api(`/v9/projects/${encodeURIComponent(env.VERCEL_PROJECT_ID)}`);
  // APP_ENV is non-secret and must be stored as plain text so the target can be
  // checked without decrypting or copying any database credentials into CI.
  const appEnvironment = project.env?.filter((entry) => entry.key === 'APP_ENV' && entry.target?.includes('production'));
  if (project.id !== env.VERCEL_PROJECT_ID || appEnvironment?.length !== 1 || appEnvironment[0].type !== 'plain' || appEnvironment[0].value !== 'staging') {
    throw new Error('Target project is not explicitly configured for staging');
  }
  const deployment = await api('/v13/deployments', {
    name: project.name,
    project: project.id,
    target: 'production',
    gitSource: { type: 'github', org: 'lpb-ship', repo: 'master', ref: env.GITHUB_REF_NAME, sha: env.GITHUB_SHA },
  });
  if (typeof deployment.id !== 'string') throw new Error('Missing deployment ID');
  // Bound remote build polling to ten minutes. Never retry deployment creation:
  // an ambiguous network failure may already have created a deployment.
  const deadline = Date.now() + 10 * 60 * 1000;
  for (let attempt = 0; attempt < 60 && Date.now() < deadline; attempt++) {
    const result = await api(`/v13/deployments/${encodeURIComponent(deployment.id)}`);
    if (['ERROR', 'CANCELED'].includes(result.readyState)) throw new Error('Remote deployment failed; inspect the restricted provider dashboard');
    if (result.readyState === 'READY') {
      if (typeof result.url !== 'string' || !/^[a-z0-9-]+\.vercel\.app$/.test(result.url)) throw new Error('Unexpected deployment hostname');
      const url = `https://${result.url}`;
      for (let check = 0; check < 6; check++) {
        const response = await request(`${url}/api/ready`, {
          headers: { 'x-vercel-protection-bypass': env.VERCEL_AUTOMATION_BYPASS_SECRET },
          signal: AbortSignal.timeout(15000), redirect: 'error',
        });
        if (response.ok && (await response.json()).status === 'ready') return url;
        await pause(10000);
      }
      throw new Error('Staging readiness failed; deployment may already serve traffic, review rollback');
    }
    await pause(10000);
  }
  throw new Error('Deployment wait timed out; inspect its state before retrying');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const url = await deployStaging(process.env);
    console.log(`Staging ready: ${url}`);
    if (process.env.GITHUB_STEP_SUMMARY) await appendFile(process.env.GITHUB_STEP_SUMMARY, `Staging deployment: ${url}\n\nCommit: ${process.env.GITHUB_SHA}\n`);
  } catch {
    // Network/provider errors can contain credentials. Keep CI output generic.
    console.error('Staging deployment or readiness failed. Check environment settings and the restricted provider dashboard before retrying or rolling back.');
    process.exitCode = 1;
  }
}
