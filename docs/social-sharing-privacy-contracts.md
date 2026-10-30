# Social experience, sharing, and privacy integration contracts

Status: **proposed v0.1 — decisions and dependency confirmations pending**. Updated: 2026-10-30.
Source: [SUR-33](https://linear.app/lb-sandbox/issue/SUR-33). Accountable decision coordinator: **Logan Barragan**, current issue assignee.

## Scope, sources, and decision authority

This document supplies a reviewable initial-release proposal for discovery, relationships, publications, profiles, feeds, and analytics. It implements no feature and makes no claim of stakeholder agreement. “Must” defines the proposed behavior after approval. All C1–C8 decisions below remain pending until a named reviewer records a response; assignment, tracker completion, or merging this document is not approval.

Reviewed sources on 2026-10-30:

- [Social project requirements](https://linear.app/lb-sandbox/project/friends-and-shared-viewing-feed-14fb20538100) and SUR-35/37/39/47/49/51/54: explicit sharing, current authorization on every surface, accurate cold starts, and zero known private-history disclosures are source requirements. Discovery/follow methods, formats, numeric budgets, and adoption thresholds are unresolved.
- [Account/profile contract](account-profile-contracts.md), SUR-5 D3–D5: reuse server-derived `appUserId`, account/session enforcement, owner-only profile storage and a separate viewer-authorized projection. This document proposes that projection; it does not change authentication or the own-profile schema.
- [Foundation quality/data handling](quality-gates-and-data-handling.md), SUR-6 Q1–Q7: reuse measurement conventions, support/accessibility review, processor inventory and lifecycle authority. Its tracker is Done, but the document still marks approvals pending; its proposed numbers are not approved social budgets.
- [Streaming data draft at d8ac532](https://github.com/lpb-ship/master/blob/d8ac5322e2d658cfe345a6f8e4e9223ffcfc1646/docs/streaming-data-contracts.md), SUR-17: stable event/catalog identity, provenance, timestamp precision, match and duplicate semantics. It does not guarantee reliable watching/completion signals or provider permission to share.
- [Streaming lifecycle draft at a512fff](https://github.com/lpb-ship/master/blob/a512fff345b7d08d0c7dc36b66c43013993ce3f8/docs/streaming-consent-retention-deletion.md), SUR-18: separate import consent, proposed delete-on-disconnect, denial before acknowledgement, scoped cleanup and restore fencing. These are unapproved upstream proposals; this document adds social consumers rather than replacing that policy.
- [Privacy project requirements](https://linear.app/lb-sandbox/project/private-by-default-activity-and-sharing-controls-6344f4be29d6): title hiding, pause/resume, past sharing, and fail-closed consumption are social-release prerequisites. Their semantics still need joint approval.

The streaming drafts are referenced at exact revisions because they are not in this branch. If those contracts change, re-review affected decisions before integration. No substantive approval was recorded in the reviewed dependency issue comments.

Initial-release exclusions proposed for C1–C4 approval: automatic publication/backfill, public or anonymous sharing, non-friend/custom audiences, contact imports, email/phone discovery, messaging, comments, reactions, notifications, algorithmic recommendations/ranking, new providers, broad profile redesign, and native-specific features. Recommendations mean a person's explicit title recommendation, not generated suggestions. No automatic shares for future events, bulk publication, free-text recommendation reviews, ratings, media uploads, or exported share links are proposed. Existing private history stays private through rollout and migration.

## Discovery and profile projection — C1

Proposed discovery method: authenticated, exact normalized **display-name lookup** among users who explicitly opt into discoverability. Reuse SUR-5 name normalization and validation; names remain non-unique. Return bounded results for collisions and ask the user to confirm the intended profile; never imply that a name uniquely proves identity. No fuzzy/prefix directory, suggested contacts, email lookup, or extra handle/avatar field. Query length, page size, rate limits and abuse controls require C5 approval. Do not log search text. Identity enumeration and name-collision usability must be reviewed before accepting this method.

Keep two independent social preferences, both off initially: `discoverable` and `socialProfileEnabled`. Enabling discovery requires an enabled social profile and explicit notice that the display name becomes visible to authenticated users. Disabling discovery removes lookup results but does not revoke existing follower access or shared items. Disabling the social profile disables discovery, denies all cross-user profile and publication access, and revokes existing publications; reopening it restores neither discovery nor publications automatically. Relationships can remain recorded, but cannot override this denial. The confirmation must explain these different effects.

An enabled social profile exposes only `appUserId`, current `displayName`, and the viewer's own relationship/control state to an active authenticated visitor who knows its identifier. It is not an activity grant. Discovery returns only that ID and name; no activity previews or graph totals. Other-user visits use a new allowlisted projection, never the own-profile response. No email, provider identity/subscription, watch history, provenance, profile timestamps, hidden-title status, social graph lists or follower/following totals. Activity cards are separately authorized publications. Profile edits reuse SUR-5; cached names must follow profile visibility and current profile versions.

Anonymous, blocked, restricted, deletion-pending, disabled and missing targets return indistinguishable unavailable results, with no field/count/preview hints. Dependency failure returns a generic retryable unavailable state without cached protected content. Direct links, lookup, profile cards and APIs apply the same policy; knowing an opaque ID grants nothing. Owners retain private management access under the foundation lifecycle even when their social profile is disabled.

## Relationships and audiences — C2

Proposed model: **directional approval-based following**. A requests to follow B; B's approval makes A an approved follower of B, not the reverse. “Friends” in sharing copy means the author's currently approved followers. Mutual following is unnecessary. Approval grants eligibility for an explicitly shared audience, never access to private history.

| Operation | Authorized actor and transition | Publication consequence |
| --- | --- | --- |
| Request follow | Active requester → visible active target; absent → pending; reject self-follow and either-direction block | Pending grants no activity access; repeated requests return the same pending relationship |
| Approve / decline | Target only; pending → approved / absent | Approval admits this viewer to active follower-audience publications, including older ones; decline grants nothing |
| Cancel / unfollow | Requester only; pending / approved → absent | Immediately denies this viewer's access; a later follow requires new approval |
| Remove follower | Target only; approved → absent | Same denial as unfollow; recipient cannot restore the grant |
| Block | Either party; create actor-owned block and remove both directions' pending/approved relationships | Deny lookup, profile, all publications and follow requests in both directions |
| Unblock | Block creator only; remove their block | Does not restore relationships or grants; an opposite-direction block still denies |

The proposed dynamic audience includes future approved followers. Show this explicitly before sharing and approving a follower; C2 must accept this historical-access consequence. No per-person or frozen audience lists in this baseline. Re-follow approval can expose still-active prior publications, but cannot revive a revoked publication. Minimal private relationship/request/block management is necessary for these transitions; no notifications or public graph browsing are implied.

Persist one relationship per ordered user pair with versioned, atomic transitions. Derive actor from the session; never accept a supplied acting user. Use idempotency keys and expected versions for mutations. A stale approval after cancel, removal, block or deletion cannot recreate a relationship. A block/deny fence wins a concurrent approval or publication commit. Record denial durably before reporting a removal/block successful; failures remain unconfirmed and cannot broaden access. Rate/cooldown limits and abuse review remain C5 blockers, not guessed constants.

## Explicit publication journey and formats — C3

**Ingestion is not publication.** Imports, sync corrections, connection authorization, a follow approval, a profile preference, or resuming sharing never create a publication. The private event store remains owner-only. Social reads use a separate publication record plus current authorization, not a filter that exposes imported history by default.

1. In the owner's private activity view, select a single eligible event and choose Share; for a recommendation, select a confirmed catalog title and choose Recommend. Viewing history is not required for a recommendation. Missing canonical identity or unsupported activity state offers an honest unavailable explanation, not a fabricated card.
2. Preview the exact card, its title/state, and audience: “Your approved followers, including people you approve later.” Show any applicable pause/hide restriction. No preselected publication on import; no mutation on opening the preview. Cancel creates no publication.
3. Explicit confirmation submits an owner-authorized, idempotent publish request bound to the previewed source, catalog, privacy and relationship-policy revisions. Revalidate inside the commit. Changed content requires a fresh preview; denied policy cannot be bypassed by a stale form. Success appears only after durable acknowledgement; ambiguous failure requires status/readback before retry.
4. A private “Manage shared activity” view lists the owner's active and revoked shares with Edit and Revoke. Edit previews and confirms the new permitted format/state, uses an expected version, preserves identity/order, and cannot switch to another title or source. No automatic watching → finished edit when an import changes; completion requires another explicit confirmation.
5. Revoke immediately denies all viewers before acknowledgement and schedules cleanup; revocation does not itself delete the private source event. Re-sharing is a new explicit preview/confirmation and publication generation. The old publication/cursor never becomes valid again.

These are logical interfaces to implement in SUR-39, not existing APIs:

| Contract | Internal fields / exposed projection |
| --- | --- |
| Publication | Opaque `publicationId`, `authorAppUserId`, `kind` (`watching`, `finished`, `recommendation`), confirmed `catalogEntityId` and media kind, `audience: approved_followers`, `status`, monotonic `version`, `publishedAt`, `updatedAt`, grant/policy revision and minimal consent receipt reference. Source event/revision and lineage references are server-only for activity; recommendation source is the owner's explicit action. |
| Activity input | SUR-17 `eventId`, owner, match/catalog revision, permitted source lineage and confirmed state evidence. Only `matched` canonical movies/episodes qualify. Unknown, ambiguous, unsupported or withdrawn data cannot produce a card. No series-only event is silently converted into an episode. |
| State mapping | Streaming/product owners must provide a versioned provider-field → watching/finished mapping with evidence and freshness rules. An observation, elapsed runtime, sync timestamp, or missing completion flag alone proves neither state. Stale watching observations must not imply “watching now”; use “shared as watching” and publication time. Until mapping is confirmed, affected activity publication is blocked. |
| Recommendation | Confirmed canonical movie/episode and the fixed intent “recommends”; no rating, text, URL or inferred viewing status. It does not claim the author watched or finished it. Additional types/formats require C3 review. |
| Viewer card | Publication ID/version, authorized author ID/display name, kind, approved catalog title/type and episode context, publication time; optional licensed artwork if independently available. No raw provider labels, event IDs, provenance, connection/subscription data, exact private watch time, or consent receipt. |

Publishing requires permitted source rights as well as user intent; import permission does not establish permission for onward sharing. Household/account-scoped attribution without confirmed authority cannot be published as the owner's viewing. Catalog/media access must be inventoried under SUR-6/SUR-18; a third-party artwork request must not receive viewer identity or private history. Missing optional artwork uses a neutral placeholder. Unverifiable canonical identity or mandatory title/state data suppresses the card; it never falls back to private provider text.

An unchanged source revision may retain its explicitly chosen publication. A source correction that changes canonical identity, ownership, state evidence or permitted provenance withdraws the affected publication until the owner previews and approves again. Imports cannot silently amend it or create a second share. SUR-17 retains authority over repeat-watch and source deduplication: different events for the same title remain distinct; suspected cross-provider overlap is not evidence for merging or publishing. Confirmed aliases must converge on one active publication per owner/canonical event; conflicting grants fail closed pending owner review. A recommendation has at most one active publication per author/title. An activity and a recommendation about the same title remain distinct explicit actions.

## Authorization, permission changes, and deletion — C4

For every cross-user publication read, the server requires: active authenticated viewer and author; enabled author social profile; no block in either direction; viewer is an approved follower of author; active explicit publication for this audience; current privacy policy permits this title/source; valid source/catalog eligibility and sharing rights; no deletion or revocation fence. Every term is required. Missing/stale/unknown authority denies access. Owner management uses a separate owner-only projection and cannot be reused for other viewers.

| Trigger | Proposed access behavior / restoration |
| --- | --- |
| Revoke one share | Deny that generation everywhere; source remains private; only a new explicit share can restore visibility |
| Hide a canonical title | Privacy authority denies all existing and future shares of that title, including recommendations and repeat watches; revoke existing publications. Unhide permits a new explicit share only. Series/episode scope must be shown and resolved by the privacy owner; no guessed cross-title matching. |
| Pause sharing | Deny and revoke existing publications and reject new shares while paused. Imports can continue privately if import consent remains valid. Resume permits future explicit shares only; no revival or publication of paused-period history. C4 must jointly approve this conservative proposal with the privacy project. |
| Unfollow, remove, block | Relationship table above controls denial for affected viewers; it does not delete unrelated authors' shares or private history |
| Disable social profile / restrict account | Deny all cross-user surfaces; profile disable revokes shares as above. Restriction cannot restore access on its own; restored account needs policy review before any publication reactivation. |
| Delete source / disconnect / withdraw import consent | Consume SUR-18 denial and lineage deletion. Revoke publications relying on the denied source; no copied card can survive as an independent recommendation. A separately authored recommendation may remain only if it has no deleted-source dependency and other rules permit it. Reconnect never restores grants. |
| Delete account | Deny discovery, profiles, relationships and every share immediately; fan out social erasure with SUR-5/SUR-6/SUR-18. Later registration gets a new identity and no old grants. |

Access denial is distinct from physical erasure. A successful restrictive mutation means its authoritative denial fence has committed. Every response authorized after that fence must exclude the affected content; no stale cache TTL is an authorization grace period. Concurrent reads must validate current policy/relationship/publication generations at response release; a change invalidates the assembled result. Responses already delivered cannot be recalled. Client removal of already-rendered cards needs a separately agreed maximum delay and offline/visibility-change behavior under C5, disclosed honestly. Cached protected content must not be displayed offline or after returning to the foreground until revalidated.

| Propagation target | Required treatment | Delivery owner / evidence |
| --- | --- | --- |
| Discovery index, profile and direct publication reads | Remove/deny projections; authoritative check after index lookup, including names and control state | SUR-37; denied lookup/direct-link cases |
| Feed pages, cursor reads, previews and counts | Authorize every result now; old cursors grant nothing; no hidden totals or placeholders | SUR-47; warmed-cache and pagination revocation tests |
| Server caches, CDN, replicas and materialized feeds | Private/no-store transport; no shared protected-response caching. Internal cached projections require current viewer/policy generations; lagging replicas cannot decide access | SUR-47 with privacy owner; stale replica/cache fault injection |
| Browser state, tabs, Back/forward and in-flight responses | Partition by account, drop obsolete responses, clear on logout/switch, invalidate on privacy changes and revalidate on resume; define/timestamp online removal delay under C5 | SUR-37/SUR-49; multiple-tab and offline/reconnect evidence |
| Derived recommendations, title aggregates and search consumers | Delete/recompute source-dependent outputs; no hidden-title explanations, counts or popularity signals | Privacy/discovery owner to be appointed; explicit consumer inventory and receipts |
| Queued jobs, retries, exports/processors, logs and analytics | Fence stale generations; idempotent cleanup with target receipts. No exports proposed; any existing downstream copy still requires inventory and erasure handling | SUR-39/SUR-51 plus SUR-18 lifecycle owner |
| Backups and recovery | Inherit approved upstream limits and replay independently durable denial/deletion records before reads/workers restart; never resurrect shares | Foundation operations + SUR-26/SUR-54 restore evidence |

Persist a minimal invalidation/deletion operation with scope, generation, target statuses and retry ownership. Partial consumer failures keep access denied and cleanup pending; do not report completed erasure without all required receipts/backup disposition. Cleanup time limits, retry/escalation windows and custody require C6; this proposal adds no competing retention numbers.

## Feed reads, layouts, and empty states — C5

Feed membership is active, authorized publications by authors the viewer currently follows; the viewer's own shares belong in private management. Sort descending by immutable server `publishedAt`, then opaque `publicationId` as a deterministic tie-breaker. Publication time means share time, never viewing/import time. Edits do not bump items. Each deliberate re-share has a new ID/time and replaces the revoked generation. Do not collapse different authors, repeat watches, or an activity and a recommendation merely because titles match.

Use bounded keyset pagination, not offsets. A signed/opaque cursor binds viewer, query/contract revision, first-page high-water tuple, last scanned position and expiry. Recheck session, audience and all permissions on every page; reject tampering, expiry and reuse by another account without leaking cursor content. New publications above the high-water mark appear after refresh. Permission reductions take effect even within an existing traversal; permission expansions require refresh to reliably see newly eligible older items. This is a stable ordering boundary, not an authorization snapshot. Clients deduplicate by publication ID and replace versions; server retries cannot create duplicate publications.

C5 must approve maximum page items, response bytes, scan work, cursor lifetime and rate/concurrency limits. Query an authorized candidate set and enforce a bounded scan. If filtering or a scan bound prevents filling a page, do not expose scanned/hidden counts or label a partial page as the end. An opaque continuation conveys only that traversal can continue, not a hidden-item count. Terminal empty state is allowed only after an authorized query establishes no visible results; an incomplete/failed query shows retry/continue state. Test restricted-candidate variations for count, cursor, payload and timing side channels; unresolved leakage blocks release. No total count, private-item placeholder, or hidden-content preview is proposed. Any future count must count only currently authorized content and requires review.

Reuse the SUR-6 support matrix and SUR-11 shell as a **proposal**, subject to C5 confirmation of exact devices/browser versions. Social journeys must work at mobile portrait/landscape widths, tablet and desktop layouts, narrow reflow, enlarged text/zoom, keyboard and screen readers. SUR-49 must provide labelled Follow/Approve/Share/Edit/Revoke and pagination controls, focus/error announcements, readable card text, reduced-motion behavior and no hover-only action. This adds no native layouts or replacement navigation shell. Accept the foundation WCAG 2.2 AA target explicitly before claiming it as a social release gate.

Safe states: new accounts and any exhausted permitted feed use “No shared activity to show yet” with Find friends; do not say friends have private/unshared activity. Loading contains no private preview. Authorization dependency failure clears protected stale content and offers Retry, not a misleading empty feed. Missing optional metadata uses a neutral fallback; missing required data remains suppressed. Delayed imports never imply live watching or trigger publication. Cold-start usability must establish that participants understand who can see shares and can identify the next step without inferring hidden activity; participant coverage and pass thresholds remain C7 decisions.

## Measurement definitions and numeric agreement — C5/C7

The only fixed numeric release requirement established in the social PRD is **zero known private-history disclosures**, with all required authorization cases passing. No approved social latency, payload, propagation, adoption or usability targets were found. The following values are deliberately **unset**, not defaults. Each needs a named reviewer, selected numeric value/unit, conditions, rationale, revision and evidence before its gate can pass.

| Measure to agree | Exact boundary / required conditions | Owner and gate |
| --- | --- | --- |
| Discovery/profile/feed latency | User submit/navigation → authorized result rendered; first and subsequent pages measured separately, include dependency authorization and network time | Engineering + product + QA via C5; before performance acceptance |
| Mutation latency | Confirm follow/approve/share/edit/revoke → durable result and accurate UI; measure restrictive fence commit and open-client removal separately | Engineering/privacy + QA via C5; before integration acceptance |
| Payload and capacity | Maximum encoded response bytes, items/page, cursor lifetime, bounded scan, request/abuse limits; representative user/follower/publication sizes, sparse visible ratios, concurrency and request mix | Engineering/operations via C5; before query/API finalization |
| Propagation | Mutation receipt → authoritative fence; fence → each live client/derived consumer invalidated; physical erasure separately under C6. Record p95 and maximum, online/offline cases and failure handling | Privacy + engineering/operations via C5/C6; before release |
| Adoption and return/engagement | Cohort, observation/attribution/return windows, thresholds, minimum eligible sample and evaluation period for each definition below | Product + analytics via C7; before instrumentation acceptance and launch |
| Cold-start comprehension | Participant coverage and number, task script, correct explanation/next-step rubric, pass threshold | Product + accessibility/QA via C7; before usability validation |

Reuse SUR-6's measurement protocol only after explicit approval of its test conditions for social: frozen runner/device/network/region, production-equivalent build, synthetic representative data, warm/cold and loaded cohorts, raw redacted outcomes, nearest-rank percentiles and failures retained. C5 must select trial counts, load duration, percentiles and limits for each social operation. Include blocked/non-friend viewers, mostly filtered pages, slow privacy lookups, stale caches, metadata outage, restrictive writes racing reads and offline return. A fast response that skips authorization is a failed trial. SUR-54 records approved values next to measured results; blanks and unresolved security defects cannot pass.

Proposed event vocabulary for C7, limited to existing scoped actions:

| Event / metric | Qualification and denominator |
| --- | --- |
| `discovery_result_opened` → `follow_approved` | First user-initiated open of a visible profile from a permitted discovery result; conversion numerator is distinct viewer/target pairs whose request becomes approved in the agreed attribution window; denominator is distinct discovered pairs in that cohort/window. A click or pending request is not a successful connection. Count retries and repeated opens once per pair/window. |
| New-user follow adoption | Distinct eligible new activated accounts reaching an approved outgoing follow within the approved onboarding window / all eligible new activated accounts with a fully observed window. Activation uses SUR-5 active/complete state; no-connect accounts remain in the denominator. |
| `feed_visit` / return visits | User-initiated foreground feed entry reaches a successful authorized content or terminal-empty state; count once per visit ID. Refreshes, pagination, background polls, errors and retries do not create visits. Return is a distinct visit by the same eligible viewer in the agreed return window; denominator is viewers with an initial successful visit and full follow-up coverage. |
| `shared_item_opened` / engagement | Deliberate activation of an authorized feed card reaches its permitted detail/title destination after revalidation. Count once per visit/publication for the engagement measure. Scrolling, impressions, auto-prefetch, dwell guesses, own previews and denied/revoked clicks do not qualify. Engaged visits / successful visits displaying at least one authorized item; report terminal-empty visits separately. |

An approved outgoing follow is counted even if later removed; measure current approved relationships separately, without rewriting past conversion. Account/analytics deletion may remove events and must be reflected in cohort reporting. Define observation windows, identity rotation, attribution linkage and handling of withdrawn analytics consent before implementation; window names above are parameters, not accepted values. Exclude synthetic/test accounts using controlled environment markers; report eligible consented coverage and never generalize opt-in metrics to all users without qualification. A zero denominator reports insufficient data, not zero success.

Optional product analytics is separate from SUR-6 operational diagnostics. Proposed payload allowlist: event name/schema version, event time at approved precision, short-lived dedup/visit key, coarse surface/outcome and policy version; cross-visit cohort and pair/publication dedup require separately approved purpose-limited pseudonymous keys in restricted measurement storage. These keys are personal data, not anonymization. No raw user/target/publication/catalog/event identifiers, display names, searches, titles, watch times, recommendations, provider metadata, graph lists, bodies or URLs in general analytics/logs. C6/C7 must approve any pseudonymous linkage, processor, notice/basis, consent, deletion and retention before it exists. No new external analytics service is assumed. Refusal/withdrawal disables optional collection and queued sends; analytics failure cannot block the journey or change authorization.

## Social consent and data lifecycle — C6

Keep discovery opt-in, profile visibility, per-publication audience consent, provider import consent, and optional analytics permission separate. Present scope and historical/future audience consequences in accessible copy; record minimal owner, purpose/audience, notice/policy revision, grant time and withdrawal time as necessary. Refusal leaves private account/history functions usable. A publication receipt does not override a later privacy restriction, provider deletion obligation or relationship loss.

Extend SUR-6 Q5–Q7 and SUR-18's inventory with relationship/request/block records, discoverability preferences and indexes, publications/catalog references, sharing receipts, cached/derived copies, invalidation/deletion records and optional measurement keys. Name purpose, processor/location, access, normal retention, withdrawal/deletion trigger, live purge deadline, backup/replica disposition and implementer for each. Do not copy streaming raw history into social storage or choose a new retention period here. Pending requests, removed relationships, revoked share content, block records, receipts and analytics all need explicit approved retention; a tombstone retains only the identifiers/generations needed to prevent resurrection, for an approved duration.

Qualified privacy/legal and product reviewers must extend the existing applicability assessment for the launch entity, markets and ages, household data authority, onward sharing/provider terms, profile discoverability, consent or other applicable basis, withdrawal, rights/deletion requests, processors/transfers and legal holds. No jurisdiction or certification is assumed. A hold, if lawful and approved, is isolated from social reads. User copy must distinguish loss of access, pending physical erasure and backup expiry. Previously seen/copied content cannot be remotely erased; no notification/export surface is introduced to enlarge this limitation. No real social personal data or production launch until these records and implementations are accepted.

## Dependency readiness and decision register

All rows below are **blocked/pending as of 2026-10-30**. Logan coordinates decisions and named appointments; issue assignment does not establish acceptance of specialist ownership. No owner-confirmed integration readiness was found. These are recorded blockers, not requests to silently choose defaults.

| Domain / accountable coordinator | Confirmation required and current blocker | Delivery / decision |
| --- | --- | --- |
| Identity — Logan; foundation reviewer to name | Stable actor mapping and restriction/deletion/session fences; SUR-5 D4/D5 approval and integration evidence missing | SUR-5/SUR-35; C2/C4 |
| Profile — Logan; profile/product reviewer to name | Viewer projection, exact-name discovery consent, visibility and name-collision usability; SUR-5 D3 and C1 not approved | SUR-37; C1 |
| Activity — Logan; streaming/catalog reviewer to name | SUR-17 matched identity/state/lineage interface, verified provider sharing rights and correction/delete signals; watching/finished mapping unresolved | SUR-17/SUR-18/SUR-39; C3 |
| Privacy — Logan; privacy/security/legal reviewers to name | Authority and hide/pause semantics, revocation consumers, applicable obligations and deadlines; privacy project and SUR-18 decisions pending | Privacy project, SUR-39/SUR-47/SUR-54; C4/C6 |
| Analytics — Logan; analytics/product reviewer to name | Event definitions, windows/targets and permitted linkage/consent/retention; no signed measurement plan | SUR-51; C7 |
| Operations and QA — Logan; implementers/release reviewers to name | Approved budgets/support matrix, consumer monitoring/cleanup custody and release evidence; no social measured results | SUR-47/SUR-49/SUR-54; C5/C8 |

| Decision | Proposed resolution / approval needed | Required reviewers and gate |
| --- | --- | --- |
| C1 Discovery/profile | Exact-name opt-in discovery, field projection and independent visibility controls; approve exclusions and abuse/usability findings | Product + profile + privacy; before SUR-37 contract finalization |
| C2 Relationships | Approval-based directional follow, future-follower audience, removal/block transitions and private management | Product + identity + privacy/security; before SUR-35 contract finalization |
| C3 Publications | Per-item preview/confirm/edit/revoke, formats, source-state/rights mapping, duplicate handling and exclusions | Product + streaming/catalog + privacy; before SUR-39 integration |
| C4 Authorization/propagation | Authoritative policy, privacy-project hide/pause semantics, restrictive commit fence, client behavior and complete consumer inventory | Privacy/security + identity + profile/feed/discovery owners; before cross-user integration |
| C5 Quality/capacity/support | Select every unset numeric operating target and test condition; approve support matrix, accessibility, pagination and abuse limits | Engineering + operations + QA/accessibility + product + privacy for propagation; before acceptance configuration, measured pass before release |
| C6 Social obligations | Extend approved upstream data inventory, source rights, purpose/basis/consent, retention/deletion/restore and processors; name cleanup custody | Qualified privacy/legal + product + operations; storage choices before schema, full approval before real data |
| C7 Success/usability | Approve event definitions, cohorts/windows/linkage, numeric thresholds and usability rubric/sample | Product + analytics + privacy + QA; before instrumentation/usability acceptance and launch |
| C8 Handoff/release authority | Named dependency responses and implementation owners; accepted C1–C7, signed evidence and zero known private-history disclosures | Product + security/privacy + engineering + QA + operations; before closing SUR-33 and releasing SUR-54 |

For each decision or dependency response record: named reviewer/domain, date, exact document commit, accepted/changes-required/rejected outcome, chosen values, rationale, evidence link, named implementer/issue, blocker and next gate. A coordinator must obtain a response, not fill in another owner's confirmation. Breaking changes reopen affected decisions and consumers; migrate with grants denied until the new semantics are accepted. Downstream work can evaluate synthetic cases against this draft, but must not treat it as an agreed implementation or launch contract.

## Testable acceptance and release handoff

These are requirements for future tests and review, **not executed application tests**. SUR-54 collects evidence at the implementation/configuration revision and reuses upstream account/streaming checks without rerunning unrelated suites.

| ID | Scenario and required result | Delivery |
| --- | --- | --- |
| SC01 | New user/import/sync/follow/profile enable, without explicit share: no cross-user activity, counts, preview or analytics content | SUR-39/SUR-47 |
| SC02 | Opt-out lookup, exact-name collisions, disabled/missing/blocked profiles and direct ID access: only allowlisted permitted fields; indistinguishable denial; no query logs | SUR-37 |
| SC03 | A follows B: pending denies, B alone approves, reverse relationship unchanged; duplicate/self/spoofed/stale transitions rejected or idempotent | SUR-35 |
| SC04 | Remove/unfollow/block during approval or read, then unblock/re-follow: denial wins; no implicit restored relationship; fresh approval affects only still-active shares | SUR-35/SUR-47 |
| SC05 | Preview cancel, publish retry/timeout, stale edit, revoke and explicit re-share: truthful durable result, one active generation, old IDs remain denied | SUR-39 |
| SC06 | Unknown state/date, unmatched title, household ambiguity, missing optional artwork and catalog/source correction: no inferred watching/completion, identity or private-text fallback | SUR-39/SUR-47 |
| SC07 | Retry/alias merge, same-title repeats, different authors, activity plus recommendation, edit and re-share: agreed identities/order with no replay duplicates or lost legitimate shares | SUR-39/SUR-47 |
| SC08 | Author hide/pause/profile disable then unhide/resume/enable: existing and future denied while restricted, old publications never automatically revived | SUR-39/SUR-47 |
| SC09 | Restrict/delete viewer or author, delete source, disconnect with mixed-source provenance, reconnect and restore: no stale grant/copy/job resurrected; scoped cleanup receipts | SUR-39/SUR-47/SUR-54 with SUR-26 |
| SC10 | Anonymous/non-friend/former-friend/blocked users on direct reads, profiles, every page, warmed cache, counts/previews and derived outputs: no restricted fields or existence signals | SUR-37/SUR-47 |
| SC11 | Revoke between page loads and concurrent response release; stale replica, old/tampered/other-user cursor, edit/new share and sparse authorized pages: current policy enforced, bounded work and accurate continuation | SUR-47 |
| SC12 | Authorization outage, delayed updates, partial scan and metadata failure: fail closed, safe retry, no false empty/success or private fallback | SUR-47/SUR-49 |
| SC13 | Tabs, account switch, browser Back, offline and foreground resume with revocation: no cross-account/stale protected display; observed client removal within approved limit | SUR-37/SUR-49 |
| SC14 | Find friend → profile → request/approve → explicitly share → permitted feed, plus cold starts on approved layouts: keyboard/screen-reader access and agreed comprehension evidence | SUR-37/SUR-49/SUR-54 |
| SC15 | Representative feed/load and restrictive writes: all selected latency, payload, scan and propagation gates measured with failures retained; no authorization shortcut | SUR-47/SUR-54 |
| SC16 | Repeated discovery/approval/visit/card actions, errors, denied clicks, consent refusal/withdrawal and deletion: exact metric denominators/dedup, no sensitive payloads, core journey survives analytics outage | SUR-51/SUR-54 |
| SC17 | Advance approved retention deadlines, fail one cleanup consumer, restore older state: durable denial, honest pending status, retries/escalation and verified purge/backup disposition | SUR-39/SUR-51/SUR-54 with operations |

SUR-33 acceptance tracking: proposed decisions/exclusions, owned blockers, ingestion/publication separation, lifecycle/read rules, measurement definitions and test requirements are documented. **Agreement on C1–C8, selected numeric targets, confirmed obligations and named dependency responses remain outstanding. SUR-33 is not fully accepted and social launch remains blocked.** SUR-54 must attach accepted decisions, implemented-surface inventory, SC01–SC17 results, quality/usability/analytics evidence and signed release review before launch.
