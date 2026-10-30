# Account and profile database baseline

Status: **reviewable non-production implementation of proposed contracts**.
This baseline follows [SUR-5 v0.1](account-profile-contracts.md) and the
[SUR-4 draft architecture](https://github.com/lpb-ship/master/pull/1): Supabase
PostgreSQL, server-only SQL, independent application IDs and application sessions.
It does not record stakeholder approval or configure a hosted project. Logan
Barragan coordinates D3 (fields), D5 (storage/retention), D8 (identity mapping),
SUR-4 provider finalization, and SUR-6 recovery targets before deployment with real
data. No profile UI, credentials, streaming data, or public profile API is added.

## Stored data and boundary

| Relation | Purpose and invariants |
| --- | --- |
| `app_private.accounts` | Random UUID independent of the provider; active/restricted/deletion_pending status; creation time. |
| `app_private.identities` | Exact, case-sensitive `(issuer, subject)` mapping to one account. One identity per account while linking is deferred. Issuer must include the approved tenant/environment namespace; no email matching. |
| `app_private.profiles` | Exactly one shell created atomically with each account; nullable display name until completion, version, creation/update timestamps. Name is trimmed using Unicode White_Space, normalized to NFC, 1–80 code points, and excludes C0/C1 controls. Names are private and not unique. |
| `app_private.sessions` | SHA-256 hex digest of an opaque random cookie (at least 256 bits of entropy), account, creation/activity/expiry/revocation times. No raw cookies, provider tokens or email. Seven-day absolute and 24-hour action-idle limits implement the proposed D2 values. |
| `app_migrations.history` | Applied versions, file SHA-256 checksums and application times; accessible only to the migration administrator. |

All foreign keys cascade on an **operator-authorized** final account deletion.
No runtime deletion API is granted. Restrict first; retain the denied mapping while
deletion is pending to prevent reprovisioning. Final deletion, deletion-ledger
retention, re-registration and provider cleanup require the approved D5 workflow.
Do not delete the mapping early. Future feature references must target account UUIDs.

| Role | Grants and intended holder |
| --- | --- |
| `app_owner` | NOLOGIN object owner; used only by migrations and fixed-search-path SECURITY DEFINER routines. It bypasses its tables' RLS intentionally; never grant it to a runtime credential. |
| `app_runtime` | NOLOGIN permission group for the profile server: SELECT its session's own profile and execute `update_own_profile`. No direct writes, identity/session reads, provisioning, or DDL. |
| `app_auth_service` | NOLOGIN group for the trusted auth adapter: atomic provisioning; session creation/read; activity renewal and revocation only. No profile reads/writes, identity table reads, or account status changes. |
| Migration administrator | Separate direct/session connection credential, able to create roles/schemas and SET ROLE app_owner; never used by the application. |
| Supabase `anon`, `authenticated`, `service_role` | No schema/table/function privileges on this baseline. BYPASSRLS does not bypass SQL grants. Keep `app_private` and `app_api` outside Data API exposed schemas. |

Create separate LOGIN credentials per service/environment through a secret-managed
administrative process. Grant each only its permission group, with NOINHERIT,
NOSUPERUSER, NOCREATEDB, NOCREATEROLE and NOBYPASSRLS; the adapter uses `SET LOCAL ROLE`
in each transaction. Do not grant group roles to each other, to browser/Data API
roles, or to unrelated services. Provision passwords outside Git using SCRAM and
rotate them through the secret manager. Apply network allowlists and restrict
connection privileges at project setup. The migrations reserve the three role
names; existing roles with elevated attributes cause initialization to fail.

RLS protects profile SELECT; runtime writes are only possible through the update
function, which derives the actor from the current session and atomically compares
the expected version. Account/session locks held to transaction end serialize
protected operations with completed revocation/restriction. Use short READ COMMITTED
transactions; do not cache authorization across requests. The owner and database
administrator remain trusted operators, as they can change grants or data.

## Auth and profile adapter integration

SUR-9 must validate provider signature, issuer allowlist, audience, expiry,
verification, callback protections and provider account/session state **before**
calling `provision_account(issuer, subject)` or issuing a session. That function's
execute grant is a service assertion of verified identity; it is not a public
verification endpoint. The SQL layer cannot validate provider JWTs. The trusted
adapter must fail closed on provider/session lookup failure, enforce CSRF and
recent-auth rules, and never accept acting identity or session hashes from request
payload fields. A compromised auth service can impersonate accounts: keep its
credential separate from profile handling. Provider token encryption/refresh is
owned by SUR-9 and is deliberately absent here.

Provisioning is atomic and idempotent under concurrent retries. It returns the
existing account only if active. Separate issuers with identical subjects remain
separate accounts. The caller does not supply an application UUID. An invalid
mapping rolls back the account and shell together.

After authenticating the opaque cookie, hash it server-side. Each protected SQL
transaction uses the restricted runtime role and parameterized context:

```sql
BEGIN;
SET LOCAL ROLE app_runtime;
-- Bind $1 to the server-computed SHA-256 hex digest, never interpolate it.
SELECT set_config('app.session_hash', $1, true);
SELECT account_id, display_name, version, created_at, updated_at
FROM app_private.profiles;
-- For a save, bind the name and expected version instead of reading:
SELECT * FROM app_api.update_own_profile($2, $3);
COMMIT;
```

These are driver parameter placeholders, not a directly runnable psql script.
A missing, invalid, expired, revoked, restricted or deletion-pending actor sees no
rows and cannot update. A transaction-local setting clears at commit/rollback,
including when a pooled connection is reused. Do not set actor UUIDs, leave session
context on a connection, or let clients run arbitrary SQL. The runtime credential
is itself a trusted server boundary; possession of another session's hash would
allow acting as it. Treat hashes as sensitive and never log them.

The auth adapter renews `last_active_at` only for authenticated user actions, never
polls/refreshes, and never extends `expires_at`. Renewal must atomically require
an unrevoked session still within both deadlines; never renew an expired session. Revoke by setting `revoked_at`;
all-session revocation filters by account ID. Restriction/deletion status changes
are privileged lifecycle operations with no runtime grant. Keep those operations
behind a separately reviewed service workflow. Never un-revoke an old session.

The update function rejects null/empty/invalid names, normalizes valid text,
advances the version and timestamp, and returns the owner projection. Map SQLSTATE
`22023` to VALIDATION_FAILED, `28000` to UNAUTHENTICATED, `42501` to FORBIDDEN, and
its `40001`/CONFLICT to a stale-edit response. Other serialization failures should
be handled by the adapter separately. Do not blindly retry a stale edit. SQL errors,
rows, hashes, subjects and names must not appear in application logs; map to safe
contract errors. Profile completeness derives from a non-null name. Unknown input
fields must be rejected by the future server adapter; render names as plain text.

## Connections and migrations

Use PostgreSQL 17 and UTF-8. Keep a small bounded runtime pool through the supported
transaction pooler. Use direct/session connectivity for migrations and backups.
Require certificate verification (`sslmode=verify-full` and the provider CA), not
just encryption. Never disable verification to work around a pooler certificate
or hostname error. Validate driver compatibility in SUR-7. Store connection
settings/passwords in a secret store; do not put URLs/passwords in argv, source,
client bundles or logs. A service file and a mode-0600 passfile are suitable for
operator commands:

```sh
export PGSERVICE=seent_staging_migrations
export PGSERVICEFILE=/secure/pg_service.conf
export PGPASSFILE=/secure/pgpass
export PGSSLMODE=verify-full
export PGSSLROOTCERT=/secure/provider-ca.crt
python3 scripts/migrate.py
```

Install `psql`, `pg_dump` and `pg_restore` matching PostgreSQL 17 through your tool
manager. Local verification below needs only Python 3, Docker and OpenSSL. No
hosted credentials or application dependencies are required.

Versioned SQL lives in `supabase/migrations`. **Use `scripts/migrate.py` as the
single migration runner for this baseline**; do not mix it with Supabase CLI
`db push`/`db reset`, which use a different history ledger. SQL files depend on the
runner's transaction wrapper. Keep applied files immutable and add a new timestamped
file for changes. The runner serializes migration jobs with an advisory lock,
checks existing checksums, unknown versions and out-of-order additions, and commits pending SQL and ledger
entries in one transaction. Errors roll everything back, including DDL and role
creation. Nontransactional operations such as concurrent index creation need a
separately reviewed migration strategy before being introduced. Do not include
transaction control in a migration file. `--through VERSION` is for local upgrade
rehearsals only, not a downgrade mechanism.

One deployment job applies compatible expansions before deploying the app. Never
migrate at function startup. Backfills and later contract/removal changes need an
explicit rollback window and impact review. Record commit, migration versions,
environment, operator and results without personal data. Failed checks stop promotion.

Run the focused checks (also configured in GitHub Actions):

```sh
python3 tests/database/verify.py
```

The verifier uses a disposable isolated PostgreSQL container, synthetic identities,
and no published network ports. It checks clean initialization, baseline-to-upgrade
preservation, migration replay/checksum drift/failure rollback, concurrent
provisioning and edits, constraints, runtime/RLS/Data API denial, expiry/revocation,
logical backup/restore, session invalidation, and a verified TLS connection with
hostname mismatch rejection. It deletes the container and test certificate after
completion. Test-only local trust authentication must never be copied to a hosted
environment. PostgreSQL tests do not replace the full Supabase/provider, HTTP,
CSRF, pooler, and integrated account/profile tests in SUR-9/SUR-10/SUR-14.

Verification record, 2026-10-30: `python3 tests/database/verify.py` passed on
PostgreSQL 17.11, including both migration paths, concurrent provisioning/edits,
role and session denial checks, checksum/unknown/out-of-order history rejection,
failed-migration rollback, dump/restore, restored-session invalidation, and TLS
hostname verification. Python compilation and `git diff --check` also passed.
This evidence uses synthetic local data; hosted recovery targets are unmeasured.

## Backup configuration and responsibilities

The selected architecture proposes Supabase Pro daily backups with seven-day
retention, **RPO 24 hours / RTO 4 hours pending SUR-6 approval**. This PR does not
provision a paid plan, enable hosted backups, or claim measured hosted recovery.
Local dump/restore is a recovery mechanism demonstration, not a durable backup.

| Responsible owner | Configuration/evidence before release |
| --- | --- |
| Logan, provider/operations coordinator | Select approved region/plan, confirm daily backups and seven-day retention in the hosted project, record project/environment and latest successful recovery point. Check daily; alert the assigned responder if no usable point exists inside the approved RPO. |
| Logan with privacy reviewer (SUR-6) | Approve processing locations, deletion/backup retention and independent encrypted-export requirements; assign key custodian and backup access. No production data in local/preview environments. |
| Logan with release operator (SUR-14) | Rehearse isolated hosted restore, measure elapsed time and lost-write window against approved RTO/RPO, verify identity/profile and authorization, and attach dated evidence. Repeat before destructive schema changes and after material backup changes. |
| Deployment owner (SUR-7) | Store separate runtime/auth/migration credentials, CA and network configuration; ensure backups and recovery secrets remain available during primary-provider access failure. |

If approved RPO is below daily backup capability, choose and budget PITR before
release; do not assert daily backups satisfy it. Exports must be encrypted at rest,
restricted, stored in the approved location, lifecycle-expired, and restore-tested.
Custom role passwords, provider tokens/keys, SMTP/DNS/hosting settings and any future
Storage objects require separate recovery handling; a database dump alone is not
a full application backup. Preserve a reviewed configuration inventory without secrets.

## Migration failure and recovery procedure

1. Stop promotion, keep the prior compatible application, and record the failing
   version and safe error category. The runner transaction rolls back SQL and history;
   inspect history before retrying. Never edit a migration already applied elsewhere,
   forge its checksum, or drop populated tables to make a retry pass.
2. Prefer an additive forward fix. For a committed incompatible change, put the
   application in maintenance mode and block runtime/auth writes. Select a verified
   recovery point and record expected data loss with the incident owner.
3. Restore into an isolated database/project with traffic and Data API access
   disabled. For a logical rehearsal, export with `pg_dump -Fc` and restore with
   `pg_restore --exit-on-error` using separate operator credentials and verify-full
   TLS. The destination must have the reviewed NOLOGIN owner/runtime/auth roles
   created first (without running the schema migrations); `pg_dump` does not export
   cluster roles. Ensure the restore operator can SET ROLE app_owner. Restore the
   full application schemas and migration history, not individual profile rows.
4. Before enabling credentials or traffic, invalidate **all** restored app sessions
   (`UPDATE app_private.sessions SET revoked_at = statement_timestamp()`), invalidate
   provider refresh/session credentials via the provider, and rotate/re-provision
   credentials and configuration as needed. Do not restore old authenticated access.
5. Reapply deletion/restriction events newer than the recovery point from the
   approved separately protected deletion ledger. That ledger must survive this
   database restore. Until D5 defines it and operators can reconcile it, recovery
   cannot safely reopen production traffic.
6. Compare account IDs, exact identity pairs, profile counts/versions, constraints,
   grants, RLS and migration history. Run the two-user/anonymous denial checks with
   fresh synthetic sessions, then the integrated account/profile smoke tests.
   Apply any required compatible forward migrations. Recheck backup availability.
7. Record backup/recovery timestamps, actual lost-write window, restore duration,
   operator, schema versions, checks and approval to reopen. Cut over only after
   the release owner verifies data obligations, access denial and session revocation.
   Keep the old database isolated for the approved incident retention period.

The automated rehearsal restores into another isolated database on the same test
cluster, where roles already exist. It verifies IDs/mappings/profiles, migration
history, RLS and revoked-session denial. New-project role provisioning, managed
Supabase Auth restore, deletion replay, provider credentials and measured hosted
RPO/RTO remain release-rehearsal responsibilities, not completed evidence here.
