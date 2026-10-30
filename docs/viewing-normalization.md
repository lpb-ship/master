# Viewing record normalization proposal

Status: **proposed v0.1 — implementation blocked on dependencies**. Updated: 2026-10-30.
Source: [SUR-22](https://linear.app/lb-sandbox/issue/SUR-22).

The repository currently has no application, catalog adapter, import pipeline, or streaming persistence. [SUR-17](https://linear.app/lb-sandbox/issue/SUR-17) has not recorded an agreed catalog, streaming contracts, or provider-specific accuracy/duplicate targets; [SUR-19](https://linear.app/lb-sandbox/issue/SUR-19) has not supplied persistence here. This proposal and its synthetic fixtures make normalization behavior reviewable without selecting a catalog, database schema, runtime, or launch provider. They do not implement normalization or establish acceptance against the pending targets.

## Boundary and ownership

Normalization consumes persisted source records plus evidence from the agreed catalog adapter. It returns match decisions and event/provenance updates for an authorized import transaction. It does not fetch provider history, authorize a connection, change sharing, or edit history manually.

The server must establish `appUserId` and the connection/profile binding before normalization, following the [shared identity contract](account-profile-contracts.md). Provider profile IDs are not application profile IDs. Unknown or ambiguous ownership must stop ingestion into personal history, not default to the importing user's profile. Never match, deduplicate, or link events across different application owners or provider-profile bindings without an approved mapping. All records and match candidates remain private by default.

## Proposed inputs and outputs

These are logical fields, not a migration or a replacement for SUR-17's contract.

| Record | Required information and semantics |
| --- | --- |
| Source | Immutable `sourceId` assigned by persistence; application owner; connection and provider-profile binding; provider namespace; nullable provider occurrence ID; observed title/type/year/episode fields; available timestamp; import observation reference. Provider content IDs identify titles, not watch occurrences. |
| Timestamp | Original value, precision (`instant`, `date`, `unknown`), and supplied offset/time-zone evidence. An instant requires an unambiguous offset or verified zone conversion. Preserve date-only values as dates and absent values as null. |
| Catalog evidence | Catalog namespace and revision; verified external-ID mappings or title-search candidates; kind; movie ID or series/season/episode identity; evidence method. Candidates are not confirmed identity. |
| Match decision | `matched`, `ambiguous`, or `unmatched`; canonical reference only for a confident match; explicit reason; candidate references where applicable; matcher version and catalog revision. Catalog failures are retryable processing failures, not proof of an unmatched title. |
| Event | Immutable `eventId`, owner/binding, nullable canonical reference, available viewing time/precision, and linked source IDs. Unresolved records remain represented with a null canonical reference; they must not masquerade as matched movies or episodes. |
| Provenance | Each original source and its import observation references; evidence and normalization version used for each decision. Reprocessing updates decisions while retaining source linkage and event identity. Raw payload retention is subject to the approved retention policy. |

Do not use import time, observation time, midnight, or the current time as a substitute for viewing time. Invalid dates or ambiguous local times remain unknown with a reason, retaining the original source value. Sort presentation separately; a fallback sort key is not a viewing timestamp.

## Matching proposal

1. Prefer a verified provider-to-catalog identity mapping. Check content kind and any explicit episode coordinates against the mapping. Conflicting identifiers or episode evidence produce `ambiguous` with reason `conflicting_identity`, not a selected winner.
2. For movies without a verified mapping, require a unique exact normalized title **and release year** in the agreed catalog. Normalize Unicode to NFC, surrounding/repeated whitespace, and case only. Do not remove punctuation, translate titles, or pick the first search result. Missing year leaves even one title-only candidate ambiguous under this conservative proposal.
3. For episodes, require a confidently identified series plus explicit season and episode numbers, or a verified episode mapping. A series ID or episode title alone is insufficient. Specials (season zero), alternate numbering, double episodes, and different cuts require catalog evidence; never infer numbering from row order or parse arbitrary title text into a confident identity.
4. Multiple candidates or conflicting evidence produce `ambiguous`; no candidate produces `unmatched`. Preserve candidate IDs and a safe reason for later processing. Do not create a new canonical title to fill a gap.
5. Reprocessing may resolve a previously ambiguous/unmatched record after new catalog evidence. Keep its existing event ID and source links; identity must not depend on mutable title strings, match state, catalog revision, or matcher version.

SUR-17 must approve these confidence rules and any eventual fuzzy matching thresholds using representative provider data. Synthetic exact matches do not establish production match accuracy.

## Duplicate and repeat-watch proposal

| Evidence | Proposed outcome |
| --- | --- |
| Same scoped provider occurrence ID seen on retry/overlapping pages | One source occurrence and one event; append distinct observation references idempotently. Scope includes owner, connection, provider profile, and provider namespace. |
| No provider occurrence ID; replay of the same persisted source ID | Reuse its event and preserve provenance. |
| No occurrence ID; separate persisted source rows with identical fields | Preserve separate events; mark possible duplication if useful. A hash of title/time cannot prove a shared watch. SUR-17 must define a verified stable import locator before deduplicating across imports. |
| Same content, distinct provider occurrence IDs or viewing times | Preserve distinct watches, including repeated watches on the same day. |
| Same content and timestamp across providers | Preserve separate events and flag possible overlap; timestamp equality alone is not shared-occurrence proof. Missing/date-only times are still weaker evidence. |
| Cross-provider shared occurrence supported by verified lineage | Link both sources to one existing event only after SUR-17 defines and approves that evidence. Retain all provenance and resolve old IDs through an alias if two events already exist. This merge path is deferred in this proposal. |
| Reused source key with conflicting immutable occurrence evidence | Quarantine the conflict for review/retry; do not silently overwrite or collapse two watches. |

SUR-19 must atomically create or retrieve source occurrences under the scoped occurrence key and store a unique source-to-event link. The normalizer must reuse that link on every retry. Never enforce uniqueness on `(owner, canonical title)`, `(owner, title, date)`, or a time-window bucket. Event IDs originate from persistence and are not regenerated on reprocessing. Concurrent workers need transactional uniqueness and retry handling; an in-memory set is insufficient.

Until a cross-provider lineage contract exists, preserve possible overlaps explicitly. This avoids false merges, but does **not** claim elimination of all cross-provider duplicates or achievement of an unapproved duplicate target.

## Fixture corpus and verification handoff

[`fixtures/streaming/viewing-normalization.json`](../fixtures/streaming/viewing-normalization.json) is a synthetic, provider-neutral acceptance proposal. `fixture-catalog`, `provider-a`, and `provider-b` are invented namespaces, not vendor selections or verified integrations. `catalogEvidence` represents the proposed adapter boundary, not a live catalog search result. Each case starts with fresh state unless it provides `existingEvents`.

`sourceId` refers to a persisted occurrence; `observationId` identifies an import observation. Repeated observations of the same source exercise retry behavior. Distinct source IDs represent distinct persisted occurrences, even if their content is identical. `eventKey` is a symbolic assertion label, not an ID generation algorithm. `existingEvents` supplies stable IDs where identity preservation is being asserted. Expected source/observation arrays have set semantics.

The corpus covers mapped movies and episodes, title/year matching, remakes and sparse title-only evidence, unmatched titles, incomplete episodes, missing/date-only/invalid timestamps, repeated watches, import replay, independent identical records, cross-provider overlap, ownership separation, and reprocessing with improved catalog evidence. It contains no real viewing history or credentials.

After SUR-17 and SUR-19 land, implement an executable harness that submits each case through the catalog adapter and persistence boundary, checks every expected field and source link, and repeats the imports. Add adapter fixtures from authorized provider samples, concurrent retry tests, transactional failure recovery, and cross-user access tests. Current JSON structural checks only establish fixture consistency; they do not test an implementation.

Measure per verified provider and record corpus size, revision, and denominators:

- Match precision: correct confirmed canonical movie/episode matches divided by all confirmed matches. Report wrong matches separately from ambiguous/unmatched abstentions.
- Match coverage: correctly matched eligible source occurrences divided by all eligible source occurrences; report unavailable identity fields separately.
- False merges: distinct ground-truth watches collapsed into one event, with affected watch counts. Report repeat-watch preservation explicitly.
- Residual duplicates: extra events for a ground-truth occurrence after retry/overlap processing; report unresolvable possible overlaps separately, not as proven unique watches.
- Reprocessing stability: pre-existing event IDs retained and source/observation links preserved across reruns and matcher revisions.

Numerical targets, minimum sample sizes, verified provider corpus, and approved overlap evidence remain **unset**, owned by SUR-17. No pass/fail performance or accuracy claim is possible yet.

## Remaining implementation gates

| Dependency | Required deliverable |
| --- | --- |
| SUR-17 | Agreed catalog/adapter, input/output contract, account/profile mapping, occurrence-key scope, time semantics, cross-provider evidence, reviewed fixture outcomes, and measurable targets. |
| SUR-19 | Source/event/provenance schema, scoped uniqueness, atomic source-to-event upsert, ownership authorization, retention behavior, and migration/access tests. |
| SUR-22 | Implement normalization against those contracts; wire it into import persistence; execute approved fixtures and provider-specific accuracy/duplicate evaluation. |

SUR-22 remains incomplete until those gates and acceptance checks pass. This proposal does not change account contracts, persistence, recommendations, catalog providers, or manual-history behavior.
