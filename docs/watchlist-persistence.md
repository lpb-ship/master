# Private watchlist persistence

This is a server-only PostgreSQL API built on the account/session baseline from
[SUR-8](https://github.com/lpb-ship/master/pull/4). It implements persistence without
rebuilding accounts, provider watchlist synchronization, history imports, or UI.
The HTTP/auth adapter in SUR-9 and approved catalog mappings in SUR-36 are still
integration dependencies. Synthetic database tests do not claim a working browser
sign-in journey or approved catalog coverage.

## Identity and storage

`app_private.watchlist_catalog_titles` is the minimal local projection consumed by
watchlists: stable `catalog_entity_id` UUID, `media_kind` (`movie` or `series`),
`display_title`, and optional `release_year`. Only trusted catalog ingestion or a
migration administrator can populate it; there are deliberately no runtime or auth
service write grants. The ingestion service's least-privilege adapter is a follow-up
once SUR-36 defines the catalog interface. Do not give ingestion the `app_owner`
credential or expose these schemas through the Supabase Data API.

The catalog must resolve provider references to the same internal ID before saving.
Never generate an ID per save, infer identity from a title string, or use a provider
ID as an application ID. Unknown IDs are rejected. Movies, series, and remakes with
the same label remain distinct. Season/episode/edition inputs must be resolved to
an approved watchlist title by SUR-36, or rejected as unresolved; this implementation
does not guess those mappings. The UUID projection is a provisional integration
boundary, not approval of a catalog vendor or crosswalk. Catalog acceptance must
include real cross-provider mapping fixtures before the whole feature ships.

`watchlist_entries` has a primary key on `(account_id, catalog_entity_id)` and a
stable display snapshot plus `saved_at`. Simultaneous saves and retries return the
original row/time, without replacing its snapshot or moving it in the list. A
remove followed by a save creates a fresh snapshot/time. Only account deletion
cascades entries; deleting a referenced catalog identity is restricted. Availability,
region, subscription, and provider health are not membership predicates or foreign
keys. Catalog ingestion must retain identity tombstones when offers disappear and
must not recycle canonical IDs. Identity merges require an explicit reviewed
migration that reconciles per-account collisions; arbitrary remapping is unsupported.

List and remove read only saved rows and the local account/session baseline; save
also reads the local catalog projection. No operation calls an external source.
Availability enrichment is optional, separate from this API, and must never filter
saved rows or turn an outage into an empty watchlist. Saved labels are historical
plain text, not a claim of current streaming availability. Render them as text.

## Server integration

Use short READ COMMITTED transactions with the restricted `app_runtime` role and
transaction-local `app.session_hash`, as in the [database baseline](database-baseline.md).
The session digest is computed by the server from a validated cookie, never accepted
from request fields. The existing session resolver checks active account status,
revocation, idle and absolute expiry, and locks authorization through transaction
end. These functions also require a completed profile. No function takes an owner
ID, and neither runtime nor auth service has direct watchlist table access.

| Function | Result / behavior |
| --- | --- |
| `app_api.save_watchlist_title(uuid)` | One saved row; idempotent for an existing canonical title. |
| `app_api.list_watchlist(limit, before_saved_at, before_catalog_entity_id)` | Own saved rows, newest first, ID descending as tie breaker. Default 50, maximum 100. Both cursor fields must be provided together or both omitted. Use the last row's unmodified timestamp and ID for the next page; an empty page ends traversal. |
| `app_api.remove_watchlist_title(uuid)` | Void success whether the title was saved or absent; affects only the current account. |

Every row returns only `catalog_entity_id`, `media_kind`, `display_title`,
`release_year`, and `saved_at`. Pagination is a live keyset traversal, not a snapshot
across requests: newly saved rows appear after refreshing the first page. Titles
removed during traversal disappear. Use parameter binding for every value.

The HTTP adapter must validate its exact input shape (no actor or extra fields),
validate UUIDs, enforce CSRF on save/remove, and use `Cache-Control: private, no-store`.
Map SQLSTATE `28000` to UNAUTHENTICATED (401), `42501` with PROFILE_INCOMPLETE to
profile completion (403), `22023`/invalid UUID input to VALIDATION_FAILED (422), and
`P0002` to NOT_FOUND (404). Database failure is UNAVAILABLE (503), never an empty list
or a successful mutation. Do not return raw SQL errors. Retrying a save/remove after
an ambiguous network result is safe. Clear owner-scoped client state on sign-out or
account switch; do not log cookies, digests, saved titles, or account IDs.

## Verification and lifecycle

Apply the additive migration with `python3 scripts/migrate.py`; prior migrations
remain immutable. Run `python3 tests/database/watchlists.py` for disposable
PostgreSQL integration tests. It covers upgrade/replay with existing accounts,
concurrent first/repeated saves, new sessions and a database restart, removal and
re-save, owner/role/session isolation, unknown canonical IDs, snapshot retention,
pagination ties, and account-deletion cascades. The baseline verifier also covers
clean initialization, migration rollback, and backup/restore with the new schema.
Both checks run in the database CI workflow.

Account restriction and deletion-pending immediately deny access through the shared
resolver; an operator-authorized final deletion removes that account's entries.
Backups include entries and the catalog projection. Follow the existing restore
procedure, including invalidating restored sessions and replaying deletion records.
Retention, metadata caching rights, hosted auth/HTTP integration, and canonical
season/edition mapping remain the existing foundation/catalog deployment gates.
