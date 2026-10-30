# Ongoing streaming sync readiness

Status: **implementation blocked on dependency evidence; proposed verification plan**.
Reviewed: 2026-10-30. Source: [SUR-24](https://linear.app/lb-sandbox/issue/SUR-24).

## Evidence and implementation boundary

The inspected repository revision, `9430566`, contains only the README and two
foundation contract documents. There is no shared import executor, provider
adapter, normalization implementation, persistence layer, or runnable import
fixture suite to extend. The issue descriptions, comments, and linked documents
for SUR-16, SUR-17, and SUR-23 were checked on the review date; all three issues
were in progress with no attached decision or implementation evidence.
This is a snapshot of missing evidence, not a finding that a provider cannot
support authorized access.

| Dependency | Evidence needed before implementation |
| --- | --- |
| [SUR-16: authorized provider access](https://linear.app/lb-sandbox/issue/SUR-16) | Agreed launch list and authorized access proof for each provider; supported profiles, history depth, pagination, quotas, permissions, and access-expiry behavior; explicit fallback if none qualify. |
| [SUR-17: data contracts and targets](https://linear.app/lb-sandbox/issue/SUR-17) | Accepted ownership and event identity rules, timestamp precision and ambiguity handling, overlap rules, backfill scope, cadence/manual-refresh policy, and measurable per-provider completeness, freshness, volume, concurrency, and reliability targets. |
| [SUR-23: first-provider import](https://linear.app/lb-sandbox/issue/SUR-23) | Merged shared executor and first verified adapter, fixture results, durable checkpoint and idempotency behavior, and its persistence, authorization/disconnect, and normalization dependencies. |

Do not select a provider, fabricate access credentials or API behavior, or build
a parallel import engine to fill these gaps. Reuse the first-provider primitives
when available. Foundation contracts remain proposed, as recorded in
[account/profile contracts](account-profile-contracts.md) and
[quality/data-handling requirements](quality-gates-and-data-handling.md).

No verified launch count is recorded yet. Zero verified providers must not be
treated as a single-provider launch. If SUR-16 approves exactly one provider,
record its name and decision evidence here, state that no additional adapter is
required, and run its ongoing recovery fixtures. If multiple providers qualify,
extend only those adapters and run the same suite for each. If none qualify,
follow the explicit SUR-16 fallback/go-no-go decision.

## Proposed extension behavior

These are review inputs for SUR-17 and the shared executor, not approved API,
storage, or scheduling contracts. No cadence, retry budget, matching tolerance,
or quota value is inferred from an unverified provider.

- Isolate execution, checkpoints, retry budgets, and failure status by the
  approved connection/account/profile scope. A provider failure must not cancel
  unrelated work or roll back another provider's committed records. Bound worker
  occupancy so one slow provider cannot starve healthy providers.
- Preserve committed pages and mark interrupted work incomplete. Advance a
  durable checkpoint only with the corresponding durable records, using SUR-23
  primitives. Retry ambiguous commits idempotently. Keep last successful coverage
  separate from last attempt time; partial work cannot claim complete freshness.
- Classify transient errors, quota deferrals, authorization failures, invalid
  records, and permanent failures separately. Use bounded retries with jitter for
  retryable failures, respect provider retry-after and applicable shared quota
  scopes, and require reauthorization for expired/revoked credentials when the
  supported refresh flow cannot recover. No busy-loop retries.
- Route scheduled and manual refresh through the same quota and concurrency
  controls. Coalesce overlapping requests for the same import scope, and retain
  deferred work without advancing its successful coverage. Scheduling and retry
  values must come from the accepted SUR-16/SUR-17 evidence.
- Check current connection authorization before dispatch, provider calls, and
  committing fetched results. Fence stale workers against disconnect/reconnect
  generations using the shared lifecycle primitives. After disconnect, cancel
  queued/retry work and reject in-flight results; already-issued network requests
  may finish but must not create new activity or revive the connection.
- Reuse normalization and event identity rules. Deduplicate replayed source
  records while preserving distinct repeat watches and source provenance.
  Cross-provider reconciliation must use approved evidence of the same event;
  title equality alone is insufficient. Missing/coarse timestamps or ambiguous
  identity must remain explicitly unresolved under SUR-17's policy. Reconciliation
  must be atomic under concurrent imports and scoped to the authorized owner.

## Shared verification scenarios

Use synthetic, provider-shaped fixtures derived from verified schemas. Fixture
providers used for failure injection do not count as supported launch adapters.
For every approved adapter, record the fixture version, source record count,
expected accessible coverage, expected normalized events/provenance, actual
result, and exact implementation revision. Measure numerical pass thresholds
against accepted SUR-17 targets; they are currently unavailable.

| Scenario | Required observable result |
| --- | --- |
| Complete history and ongoing delta | Import all records in the agreed accessible range across pagination boundaries, then import newly available records; reconcile counts and coverage against the fixture. Include provider-supported late/out-of-order records under the approved refresh window. |
| Independent failures | Inject timeout, transient error, expired authorization, and permanent failure into provider A while B imports. B completes within its agreed target; A alone reports its failure and retains its checkpoint. Repeat with each launch adapter in the failing role. |
| Slow or stalled provider | Exhaust A's allowed concurrent work while B is queued. B still makes progress; A times out according to the approved policy and releases capacity. |
| Partial success and restart | Fail after a committed page, before a page commit, and after a commit whose acknowledgement is lost. Restart execution; no accessible record is lost or duplicated, and incomplete coverage remains explicit until recovery finishes. |
| Replay and concurrency | Run the same pages repeatedly and concurrently, including overlapping scheduled/manual requests. One source event is retained once, two real watches of the same title remain distinct, and checkpoint ordering cannot skip records. |
| Cross-provider overlap | Import two provider representations of a confirmed same event in both orders and concurrently. Produce the approved single event with both provenance records. Include distinct repeat watches, identical titles belonging to different works, different owners, and ambiguous/missing timestamps as negative merge cases. |
| Quota and recovery | Inject quota exhaustion and retry-after, including any shared application quota. No request occurs before eligibility; manual refresh cannot bypass it. Healthy providers outside that quota scope continue, retries are bounded, and deferred work resumes without losing coverage. |
| Credential recovery | Exercise supported token refresh, unrecoverable expiry, and explicit reauthorization. Only the affected connection pauses; resumption reuses approved checkpoints without duplicate events or reviving stale workers. |
| Disconnect races | Disconnect before dispatch, during fetch, before commit, and during backoff. No later call or commit is authorized by the old connection generation. Reconnect and deliver the old worker's result; it remains rejected. |
| Cadence and freshness | Advance a controlled clock through accepted scheduled/manual cooldowns, retry delays, and delayed provider availability. Measure successful coverage freshness independently from attempts, within approved quotas. |
| Single-provider launch | With documented one-provider approval, run completeness, replay, partial failure, quotas, expiry, ongoing delta, and disconnect scenarios on that adapter. Use synthetic peer work to test executor isolation; do not introduce an unverified second adapter. |

## Completion evidence still required

SUR-24 remains incomplete. This document supplies a handoff and test plan only;
no runtime behavior, fixture pass, or provider support is claimed.

Before acceptance, link the approved launch decision and target revisions, the
merged first-provider proof, and implementation/test results for every applicable
scenario above. Record the chosen cadence, manual-refresh and retry limits,
quota scopes, overlap policy, and the evidence for meeting them. Explicitly
record the single-provider exception only if that launch decision is confirmed.
