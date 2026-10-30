# Development and secure deployment

Status: implemented local infrastructure; **cloud provisioning and repeated staging
verification pending**. Updated 2026-10-30. Source: [SUR-7](https://linear.app/lb-sandbox/issue/SUR-7).

This follows the selected direction in the [SUR-4 architecture draft](https://github.com/lpb-ship/master/blob/9e166fdd0f7340d1495f42eac0e5d9b698874ef4/docs/architecture/0001-foundation.md).
That draft still gates provider finalization on SUR-5/SUR-6. This change supplies a
reviewable runtime and workflow without purchasing services, choosing a region,
implementing authentication, or owning database schemas.

## Environment inventory and ownership

Logan Barragan, the assigned foundation coordinator, owns completing this inventory
and naming the deployment operator, backup operator, and release reviewer. These
are pending assignments, not evidence of operational sign-off.

| Environment | Resources and data boundary | Owner / current state |
| --- | --- | --- |
| Local | Per-developer loopback PostgreSQL; synthetic data; `.env.local`; no cloud credentials | Developer running it; runnable from README |
| Staging | Dedicated Vercel project and dedicated Supabase project; synthetic data only; protected deployment access | Logan to provision after SUR-4/SUR-6 decisions |
| PR previews | Disabled initially; CI uses only local dummy configuration. Future trusted previews require isolated synthetic data and reviewed callback rules | Logan; no secrets for fork/untrusted builds |
| Production | Separate Vercel and Supabase projects, credentials, keys, origins, and access grants | Logan to name operator/reviewer; not provisioned or enabled by this workflow |

Before enabling staging, record the exact Vercel team/project IDs, Supabase project
reference and region, function region, canonical HTTPS origin, operator/reviewer,
secret-store locations (names only), approved spend, and backup policy in this
inventory via a reviewed change. Never reuse production IDs or credentials in the
GitHub `staging` environment. Residency covers logs, email, support, and processors
as well as database placement; SUR-6 resolves it before personal data is admitted.

## Reproducible local setup

Follow [README](../README.md). Node is pinned in `mise.toml`, npm in `package.json`,
packages in `package-lock.json`, and the disposable PostgreSQL image by digest in
`compose.yaml`. Use `npm ci`; dependency/runtime updates must update the pins and
lockfile together, rerun checks, and review advisories. The local database tests
connectivity only; it is not an emulation of Supabase Auth, RLS, or migrations.

`npm run check:config` validates without connecting. `npm run check:db` connects with
a bounded timeout and checks TLS on remote connections. `/api/health` is liveness;
`/api/ready` executes `SELECT 1`, returns 503 on failure, and discloses no connection
or error details. Readiness is not an authorization or schema-compatibility test.
Both responses are uncached. The pool is bounded to two connections per process;
there is no named prepared statement or session-scoped actor state.

## Configuration and secrets

Next.js loads `.env.local` locally. The standalone check commands load that same
file; inherited variables take precedence. Hosted environments inject variables
from their own Vercel project. Validation runs at build and server initialization;
invalid configuration fails closed with variable names only. Build validation does
not connect to the database. No configuration is exported through Next's `env`
setting, and the database module is protected by `server-only`.

| Name | Scope and validation |
| --- | --- |
| `APP_ENV` | Required: `local`, `staging`, or `production`. Hosted local mode and production credentials declared as preview mode are rejected. The staging workflow verifies this target before deploying. |
| `APP_ORIGIN` | Required exact origin, no credentials/path/query/fragment. Local HTTP is loopback only; remote requires HTTPS. It reserves the canonical origin for future auth/CSRF integration; it does not implement those features. |
| `DATABASE_URL` | Server secret. Local loopback PostgreSQL only. Remote Supabase direct endpoint on 5432 or transaction pooler on 6543; project ref must match the host or pooler username. Requires `sslmode=verify-full`; other connection-string options are rejected. Use a non-admin runtime role supplied by SUR-8. |
| `SUPABASE_PROJECT_REF` | Required remotely; exact 20-letter project reference from the matching environment. No default or fallback to another environment. |
| `DATABASE_CA_CERT` | Required remotely; PEM root certificate downloaded from that Supabase project's database settings. Literal newlines or escaped `\n` are accepted. Node verifies chain and hostname; never disable certificate verification. The certificate itself is public trust material, but manage it with the matching environment configuration. |

Remote URL shape (replace every placeholder; URL-encode username/password):

```text
postgresql://<runtime-role>.<project-ref>:<password>@<provider-pooler-host>:6543/postgres?sslmode=verify-full
```

The pooler host comes from the project's Connect panel, not a guessed region.
Direct connections use `db.<project-ref>.supabase.co:5432` and the bare runtime role.
The validator rejects common admin usernames, but actual grants must also be
verified in SUR-8: a non-owner, non-superuser, no BYPASSRLS, no role/database creation,
and only required grants. A name alone does not establish least privilege.

All `NEXT_PUBLIC_*` variables are rejected in this baseline. Add a reviewed public
allowlist only when a feature needs it. Do not add Supabase admin/service-role keys,
SMTP passwords, provider tokens, or migration URLs to the app environment. Future
Auth configuration belongs in the server adapter; Resend SMTP credentials belong
in Supabase's configuration. Migration credentials belong only in the separately
controlled SUR-8 migration job, never function startup or this build.

`.gitignore` and `.vercelignore` exclude env files and private keys; ignore rules
are not a secret scanner. Review staged changes, scan built client assets for test
secret markers, and use repository secret scanning/push protection where available.
Do not print env dumps, raw database errors, connection strings, auth URLs, or
provider responses. Build logs and provider dashboards also need restricted access.
Require MFA for provider admins; restrict deployment tokens to the staging team
and shortest practical expiry, and restrict who can edit environment secrets.

For rotation: create a replacement environment-specific credential, update its
secret store, redeploy and verify readiness, then revoke the old credential and
confirm it fails. For suspected exposure, revoke immediately before recovery,
assess logs/artifacts/history and affected accounts, and rotate related secrets;
removing a file or rolling back the app does not revoke a secret. Coordinate
session-encryption key rotation with the auth owner before that feature exists.

## Staging deployment workflow

One-time setup, after provider/environment decisions:

1. Create the isolated staging Supabase project in the approved region. Enable
   database SSL enforcement and configure network restrictions compatible with
   the selected runner/function egress. Obtain its CA and the SUR-8 runtime role.
   SUR-8 owns applying migrations and grants using separate credentials.
2. Create a **dedicated staging Vercel project**, framework Next.js, Node 24.x,
   `npm ci` install and `npm run build` build command, and approved function region.
   Connect `lpb-ship/master` and disable automatic Git deployments so this workflow is the sole staging writer.
   Put the staging variables above in that project's **Production** variable scope.
   Store non-secret `APP_ENV=staging` with type Plain Text; the workflow checks it
   via the project API without decrypting database credentials.
   Vercel's API `target: production` means the stable target of this staging-only project; it does
   not mean the application's production environment. Do not link this workflow
   to a production project. Production deployment is intentionally unconfigured.
3. Require HTTPS, verify HTTP redirects to HTTPS and certificate validity on the
   stable origin, and enable deployment protection for staging and preview URLs.
   Create an automation bypass secret for readiness checks; do not publish it.
4. Create GitHub environment `staging` with required reviewer and allowed deployment
   branches restricted to the reviewed release branch. Set variables
   `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID`; set secrets `VERCEL_TOKEN` and
   `VERCEL_AUTOMATION_BYPASS_SECRET`. Only trusted reviewed code may use them.
   If the repository plan cannot enforce environment protection, do not enable the
   workflow until an equivalent access/review control is configured.
5. Run **Deploy staging** manually from the reviewed commit's branch. It installs
   locked dependencies, tests, builds, and typechecks without cloud secrets; then requests a remote build of the exact Git commit via the Vercel API with
   staging configuration. Local files and credentials are never uploaded. GitHub concurrency serializes deployments
   without canceling an in-flight deploy. No migrations run implicitly.
6. The workflow waits up to ten minutes for the remote build and checks the immutable deployment's `/api/ready` over HTTPS and records
   its URL and commit in the job summary. A failed post-deployment check fails the
   job but does not roll back the alias automatically; follow the rollback procedure.
   Also verify readiness on the stable origin and run `check:db` from a trusted
   operator session with staging variables injected securely. Never pass database
   credentials on command lines or commit a pulled environment file.
7. Repeat the deployment of the same revision, then a compatible new revision.
   Record both run/deployment IDs, commits, environment config revision (no values),
   migration version, TLS result, and smoke-test results. Confirm data survives
   redeployment and no production project was touched. These live checks are pending.

The manual workflow must exist on the repository's default branch before GitHub
shows its dispatch button. PR CI has read-only permissions and no cloud secrets.
Future migrations must share a release lock with deployment or be completed in a
controlled maintenance window; the deployment lock alone cannot serialize an
independent migration workflow.

## Database coordination and recovery

[SUR-8](https://linear.app/lb-sandbox/issue/SUR-8) owns schema, migration commands,
least-privilege grants, backup configuration, and database recovery. Before a release,
record migration versions compatible with both new and last-known-good app builds.
Apply additive migrations first with the migration role, deploy, then backfill;
defer destructive changes until the rollback window ends. Never run migrations
on function startup or against shared staging from concurrent preview builds.

For an application regression, stop new releases, record the failing deployment and
migration version, and select the last-known-good deployment in the **staging**
Vercel project's Deployments dashboard. Confirm schema/config compatibility and
promote/roll back to that deployment using the provider's rollback action. If it
is unavailable, dispatch the reviewed prior revision after confirming the current
environment variables remain compatible. Check stable-origin health/readiness and
feature smoke tests, then record the recovery result and owner. Old artifacts may
carry old configuration; fix compromised credentials before reusing one.

A hosting rollback does not revert schema, data, credentials, or emails. If database
changes are incompatible, hold writes/traffic and involve the SUR-8 owner; prefer
a reviewed forward fix. For data loss, restore a verified backup into an isolated
project, validate migrations/grants and identity mapping, reapply the deletion
ledger, invalidate restored sessions, configure new credentials/CA, and test before
switching traffic. Never restore over a live environment as an automatic rollback.
Capture recovery-point time, actual loss, and elapsed recovery time against approved
SUR-6 objectives. Full integrated rollback/restore rehearsal belongs to
[SUR-14](https://linear.app/lb-sandbox/issue/SUR-14); no successful rehearsal is claimed here.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Node/npm engine mismatch | Run `mise install`, then `mise exec -- npm ci`; do not regenerate the lockfile with an unrelated runtime. |
| Local DB won't start / readiness 503 | Check Docker readiness and port 54322, `docker compose ps` and local container logs; confirm `.env.local` matches the local-only password. Reset only disposable local volumes. |
| Build says invalid configuration | Check the named variable in the correct environment; no local defaults are used remotely. Changes require a rebuild/redeploy. |
| Remote TLS verification fails | Check matching CA, hostname, project and SSL enforcement; rotate expired CA material. Never use `rejectUnauthorized: false`, `sslmode=require`, or `NODE_TLS_REJECT_UNAUTHORIZED=0`. |
| Connection timeout / pool exhaustion | Check project health, network restrictions, egress, and IPv4/IPv6 compatibility. Use the supplied transaction pooler, inspect query duration and concurrency; do not increase pools blindly. |
| Authentication/grant failure | Confirm URL encoding, runtime role/project suffix, credential rotation and SUR-8 grants. Do not substitute an admin credential. |
| Deploy denied / wrong target | Inspect environment approval, allowed branch, token scope and project/team IDs without logging secrets. Verify the dedicated staging project before retrying. |
| Smoke check 401/403 | Check deployment protection and the staging bypass secret. Do not disable protection or add bypass secrets to the URL. |
| Healthy process but unavailable DB | Liveness is independent of the DB. Use readiness plus `check:db`; investigate sanitized provider diagnostics. |

## Acceptance evidence still required

Local configuration tests, build/type checks, and local connectivity can be executed
without cloud accounts. Closing SUR-7 additionally requires the populated ownership
inventory, approved environment/provider decisions, two successful staging deploys,
remote TLS and runtime-grant evidence, client-bundle secret isolation evidence for
the actual hosted config, and migration compatibility confirmation with SUR-8.
Use the deployment record fields above; leave pending entries explicit. A passing
local test is not evidence of cloud deployment or approved data handling.
