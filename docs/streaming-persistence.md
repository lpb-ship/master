# Private streaming persistence

Status: **provisional, synthetic-data implementation for contract review**.
This additive migration uses the account/profile baseline from PR #4, including
`app_private.current_account()` and its session/restriction locks. It does not
recreate accounts or profiles. SUR-17 had no published streaming contract at
implementation time; the rules below are explicit proposals, not agreed provider
capabilities. SUR-17 and SUR-5/SUR-6 lifecycle decisions must be reconciled before
provider integration or real data. No provider is claimed to be supported. The later [normalization proposal
(PR #7)](https://github.com/lpb-ship/master/pull/7) and [retention proposal
(PR #8)](https://github.com/lpb-ship/master/pull/8) were also reviewed. This draft
preserves date-only values and uses terminal connection generations with immediate
read/import denial. Those proposals remain unapproved; their complete observation,
consent, suppression, physical erasure and raw-backup requirements are not claimed
as implemented here.

## Records and invariants

Every table has a non-null `account_id` derived from trusted session context. A
connection references the existing profile's `account_id`, which also identifies
its one foundation account. Provider profiles are opaque connection attributes,
not additional application profiles. Composite foreign keys carry the same owner
and connection through imports, source events and normalized events. Service
column grants prevent replacing ownership, parent references, IDs, or occurrence
keys after insertion.

| Relation | Contract |
| --- | --- |
| `connections` | One live generation per owner/provider/provider-account/provider-profile tuple. An empty provider profile key means account-level scope. Separate provider profiles/accounts remain separate. No credentials or email; pending by default. Connected/revoked/disconnected state controls imported-data reads and writes. Reconnect requires a new connection UUID. |
| `subscriptions` | Latest observation per connection. `supported_fields` explicitly allowlists status, plan name and renewal timestamp. Unsupported values must be null; null is never evidence of inactivity. Adapter capability evidence must distinguish unsupported from not-yet-observed fields; an absent row means no observation. |
| `imports` | Unique caller request key within a connection; one queued/running/partial job at a time. Bounded opaque cursor, explicit cursor expiry, processed count, coverage, safe error category and terminal timestamp. Completed means the declared accessible coverage, not all-time history. |
| `source_events` | Stable occurrence key within a connection, initial import, provider title reference, instant timestamp or date-only value with instant/date/unknown precision, optional minimized raw object with explicit expiry. Source identity and provenance persist after raw cleanup. |
| `viewing_events` | One normalized movie or episode per source occurrence. Matched requires a catalog namespace and title ID; unmatched/ambiguous require neither. An episode ID identifies an episode, not a series. Normalization version/time explain derivation. The source join supplies timestamp and import/provider provenance without conflicting copies. |

No title/time uniqueness constraint exists. Distinct provider event IDs at the
same timestamp, repeat watches, and separate undated occurrences all survive.
Reimporting a stable occurrence key is idempotent across import jobs and concurrent
writers within the same connection generation. Cross-provider observations stay separate; this schema makes no automatic
claim that two sources represent the same watch. Matching may be revised in place
without creating a second normalized row for the occurrence.

SUR-22/SUR-23 adapters must use a provider event ID or a documented stable source
locator. A title hash, a page-relative offset that changes between exports, or a
new random key on every retry is insufficient. If stable occurrence identity is
unavailable, pause that adapter for a contract decision rather than silently
merging repeat watches or claiming idempotency. Missing timestamps remain null;
date precision uses `occurred_on` without inventing a midnight instant. An instant
requires verified offset/zone evidence from the adapter. Canonical catalog selection remains SUR-17's decision.

## Access and write protocol

`app_runtime` has owner-only reads of safe columns, no writes, and no access to
provider account/profile keys, raw payloads, source keys or import cursors. There
is no public/shared projection or visibility flag. Connecting, importing or
following someone does not grant access to their activity.

`app_streaming_service` is a separate NOLOGIN permission group for a trusted
server adapter. It has owner-only reads and column-scoped writes. Like the baseline,
use a separate NOINHERIT login, `SET LOCAL ROLE`, and a server-supplied
`app.session_hash` inside a short READ COMMITTED transaction. Never accept a client
actor ID or expose this role through Supabase Data API. Anonymous, authenticated,
service-role and auth-adapter credentials have no streaming access. Migration
administrator and `app_owner` remain trusted and can bypass RLS.

```sql
BEGIN;
SET LOCAL ROLE app_streaming_service;
-- Bind the validated session digest using the server driver's parameter binding:
-- SELECT set_config('app.session_hash', $1, true);
-- Insert/upsert source occurrences and normalized events for one page.
-- Update the import checkpoint and processed_count in this same transaction.
COMMIT;
```

Use `ON CONFLICT (account_id, connection_id, source_key) DO NOTHING` for source
replay, then read the existing occurrence and compare immutable evidence; quarantine
conflicting reuse of a key rather than silently dropping the conflict. Lock the import row `FOR UPDATE` and
compare the expected checkpoint before advancing it; the schema provides atomic
transactions, not a worker lease/retry algorithm. Do not report success before the
transaction commits. A failed page leaves both events and checkpoint unchanged;
partial imports remain partial until explicitly completed with `finished_at`.
A later import request reuses source occurrence keys while retaining first-import
provenance. Imports referenced by source records cannot be independently deleted.

Reads and writes to subscriptions, imports, sources and normalized events lock/check the
connection's connected state. A completed disconnect/revocation prevents further
import writes; a transaction already holding the lock completes before disconnect
commits. Imported data becomes inaccessible when a connection is revoked or disconnected;
only the owner-visible connection metadata remains for lifecycle status. The
lifecycle adapter must cancel pending jobs before setting terminal state in its
transaction, and erase/revoke external secrets in its workflow. Secrets are not
stored here. Reconnection creates a new connection UUID after renewed consent;
the trigger prevents reactivating an old generation. Stale jobs cannot attach old
results to the new generation because their parent keys are immutable.
Physical deletion remains an explicit lifecycle operation: deleting an owned
connection cascades through all its feature records. Final operator-authorized
account deletion also cascades, without touching another owner. Durable erasure
requests, consent receipts, per-event reimport suppression and non-session deletion
workers are integration work; immediate denial alone is not completed erasure.

Background workers must not invent an account-ID setting or receive `app_owner`.
The current service boundary requires a valid foundation session. A durable,
revocable connection-scoped worker authorization mechanism and worker leasing are
SUR-20/SUR-23 integration work; this migration does not implement them. Paused jobs
must remain paused if the available authorization has expired.

## Retention and recovery

No retention duration is guessed. Raw objects and cursors require caller-supplied
expiry timestamps whenever populated. Store only approved, minimized provider
fields; never put tokens, passwords, cookies, email or unsanitized provider errors
in raw objects, checkpoints or error codes. Raw material is service-only even
before expiration. The retention role cannot read it.

`app_streaming_retention` is a separate NOLOGIN cleanup permission group. Its only
feature operation is `SELECT streaming_private.purge_expired_material()`, which
erases expired raw objects and cursors globally, including for restricted accounts
and disconnected connections. It cannot read rows, modify deadlines, create
records, or erase unexpired material. Run it in short transactions from the approved
scheduler; schedule frequency and provider-specific deadlines require the retention
policy. This change supplies the cleanup operation, not deployment infrastructure.
Deadlines are not an autonomous database timer: an operator must monitor successful
cleanup before any real data is stored.

Source occurrence keys, normalized history and import provenance remain stored until
explicit deletion, with imported-data reads denied for terminal connections, so raw cleanup cannot cause duplicate watches on replay.
Their final retention/deletion limits, subscription history requirements, backup
expiration and deletion-ledger replay remain unresolved policy inputs, not a claim
of indefinite retention approval. Do not enable real imports until those choices
and cleanup scheduling are implemented. In particular, PR #8 proposes raw staging
excluded from backups. Inline raw payloads here are included in ordinary database
backups: keep `raw_payload` null for any real provider integration until an approved
staging/backup design replaces that storage. The synthetic tests exercise its expiry
mechanism only; they do not establish compliant raw-data retention. Restore with the baseline runbook, then
reapply deletions, disable restored connections, cancel pending imports, erase
restored cursors/raw material past expiry, and reauthorize before starting workers.
Never resume from restored authorization or a stale cursor automatically.

## Verification

Run `python3 tests/database/verify.py` with Docker and Python 3. The existing
PostgreSQL 17 harness applies the original baseline, creates accounts, upgrades
through the profile migration and streaming migration, replays migrations, and
also initializes an empty database. Failed migrations roll back SQL and the ledger.
It then exercises every streaming relation with two owners, absent/invalid/revoked/
expired sessions, inactive accounts and unrelated service roles. Feature checks
cover parent/owner spoofing, private column grants, concurrent replay, repeats and
unknown timestamps, matching constraints/provenance, checkpoint rollback/resume,
disconnect/revocation and generation isolation, expiry cleanup and final account deletion. Existing profile,
backup/restore and TLS checks remain part of the same database CI job.

These checks verify PostgreSQL persistence, not provider capability, agreed
retention durations, catalog matching accuracy or a deployed resumable worker.
