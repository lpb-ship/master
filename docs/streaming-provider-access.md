# Streaming provider access and launch scope

Status: **research recorded; launch decision and specialist reviews pending**.
Evidence checked: **2026-10-30**. Decision coordinator: **Logan Barragan**, SUR-16 assignee.
Source: [SUR-16](https://linear.app/lb-sandbox/issue/SUR-16).

## Decision for review

**Verified launch providers: none (`[]`). Recommend no-go for automated streaming
connections, subscription verification, and viewing-history sync.** None of the
reviewed evidence establishes permission and a usable integration contract for
this application. This is an evidence-based qualification result, not proof that
private partner APIs do not exist. No provider support or delivery date is promised.

The proposed fallback is to defer the streaming feature while independently
approved foundation work continues. Keep `/connections` at the existing
“Not available yet” contract; do not present named providers as connectable, claim
import success, or infer an inactive subscription from unavailable data. If
streaming sync is essential to the product launch, the product launch is also
no-go until a provider qualifies. A foundation-only release requires an explicit
product scope decision and its own release gates.

This recommendation has **not been agreed by stakeholders**. Logan must record
the scope choice and named reviewers below before SUR-16's agreement criterion
can be closed. Merging this document is not provider approval or legal sign-off.

## Scope and method

Evaluate authorized third-party access to subscriptions and individual viewing
history for Hulu, Netflix, and HBO. “HBO” is provisionally interpreted as the
current US HBO Max service: the official Max help site redirects to HBO Max.
Linear-channel HBO, legacy HBO GO/NOW, and distributor-specific services are not
interchangeable integrations. Product must confirm the service and launch markets.
US/English sources are an evaluation baseline, not an agreed launch jurisdiction.

Reviewed the streaming project requirements, SUR-16 and its discussion,
SUR-4 and its architecture draft, SUR-23, SUR-24, and the official public sources
below. Reviewed consumer help and terms; did not access customer accounts, request
exports, probe private endpoints, collect credentials, or run provider API tests.
No project-specific partner agreement, application approval, credential reference,
API specification, or authorized fixture was supplied in the reviewed records.
Credentials were not searched for in secret stores. Unknown means **not verified**,
not unavailable forever, zero quota, or an empty history.

Reuse [SUR-4](https://linear.app/lb-sandbox/issue/SUR-4) and its
[foundation architecture draft](https://github.com/lpb-ship/master/pull/1) for
hosting, authentication, storage, and runtime. This document selects none of those
again and implements no adapter. Preserve the stable `appUserId`, separate
streaming credentials, and owner-only defaults from the
[account/profile contract](account-profile-contracts.md). Privacy, retention,
regions, and operations also depend on the
[quality and data-handling gates](quality-gates-and-data-handling.md).

## Official evidence register

All sources below were inspected on 2026-10-30. Quotes are short evidence anchors;
consumer features do not establish a developer API or permission to reuse data.
Recheck current regional terms before any agreement or implementation commitment.

| ID | Official source and version | Observed evidence and limit |
| --- | --- | --- |
| N1 | [Netflix viewing history](https://help.netflix.com/en/node/101917) | History is available for each profile; “Show More” expands the UI and “Download all” produces CSV. An inactive account must request a copy of its information. No API pagination, export schema, retention guarantee, or third-party authorization is specified. |
| N2 | [Netflix personal-information requests](https://help.netflix.com/en/node/100624) | Account page exposes plan selection, billing information, profiles, and content interaction history. Account owners can request data; a profile user with an associated email can contact Netflix privacy, with notice to the account owner. Production may take up to 30 days after verification. This is a personal-data request process, not a sync SLA. |
| N3 | [Netflix Terms of Use](https://help.netflix.com/legal/termsofuse), updated April 10, 2026; retrieved text identifies Netflix, Inc. | §1.8 conditions rights on express authorization and, unless explicitly authorized, restricts commercial use, use of service information, automated access, reverse engineering, and data gathering/extraction. Subscriber consent alone does not establish the required provider permission. |
| H1 | [Hulu watch history](https://help.hulu.com/article/hulu-watch-history) | Continue Watching shows recently watched shows/movies, not individual episodes; episode progress appears on series details. Removal resets progress. This does not establish a durable event ledger, timestamps, repeat-watch records, or complete backfill. |
| H2 | [Hulu profile management](https://help.hulu.com/article/hulu-manage-profiles), displayed November 28, 2025 | One primary plus up to six additional profiles; “Each profile ... will have unique viewing history.” Kids profiles and PIN protection exist. Consumer profile selection/transfer is not delegated third-party profile access. |
| H3 | [Disney+, ESPN, and Hulu Subscriber Agreement](https://www.hulu.com/subscriber_agreement), updated February 5, 2026 | §1 limits use to personal/noncommercial use and Hulu to the US and certain territories. §2 describes tiers, billing, bundles, pauses, and third-party billing. §3(b) requires express written permission for listed restricted uses, including business use and automated access/extraction. MyDisney sign-in is not evidence of an app authorization grant. |
| M1 | [HBO Max My List and Continue Watching](https://help.hbomax.com/us/Answer/Detail/000002505) | Each profile has its own My Stuff area. Continue Watching contains unfinished items and the next episode; “Titles are automatically removed ... after 90 days.” This is a UI removal window, not a verified history API retention limit or a complete watched-history feed. |
| M2 | [Manage an HBO Max subscription](https://help.hbomax.com/us/Answer/Detail/000002529) | Subscription screen identifies the base-plan biller; management options depend on WarnerMedia versus app-store/other billing. No third-party subscription response schema or entitlement-verification permission is established. |
| M3 | [HBO Max terms selector](https://www.hbomax.com/terms-of-use) and its [US English terms link](https://www.hbomax.com/terms-of-use/en-us) | Selector and regional link were retrieved. The US page's text fetch contained only the site shell; rendered navigation returned Access Denied. **Substantive US terms were not verified.** Legal must obtain and review the applicable version; no clause or permission is inferred from the shell. |

## Candidate capability and access assessment

The integration requirements below are separate from consumer-account features.
No candidate currently passes qualification. Subscription fields may remain
explicitly unknown in an approved integration, but history permission and a usable
history interface are mandatory for this project's automated-sync scope.

| Dimension | Hulu | Netflix | HBO Max (provisional HBO scope) |
| --- | --- | --- | --- |
| Documented access path found | Consumer history/profile UI (H1/H2); no authorized third-party sync contract verified | Consumer per-profile CSV and personal-data request (N1/N2); no authorized third-party sync contract verified | Consumer Continue Watching and subscription UI (M1/M2); no authorized third-party sync contract verified |
| Terms / approvals | Express written permission for restricted uses must be established under H3; no project approval recorded | Explicit authorization for proposed uses must be established under N3; no project approval recorded | Applicable substantive terms and project-specific permissions both unresolved (M3) |
| Credentials and permissions | No approved app registration, client credential reference, consent scopes, token lifecycle, or revocation contract verified; MyDisney credentials are not an integration | No approved app registration, client credential reference, consent scopes, token lifecycle, or revocation contract verified; consumer login/CSV is not an OAuth grant | No approved app registration, client credential reference, consent scopes, token lifecycle, or revocation contract verified; distributor sign-in is not permission for our app |
| History depth / fields | Recent titles and episode progress observed in docs; earliest accessible date, event IDs, timestamps/time zones, completion, repeat watches, deleted items, and export coverage unknown | “Download all” documented; earliest date, hidden/deleted coverage, stable event/title IDs, timestamp precision, completion, and repeat-watch semantics unverified without authorized schema/fixtures | Unfinished items/next episode and 90-day UI removal documented; completed viewing events, earliest history, IDs, timestamps, and repeat watches unknown |
| Pagination / resumability | No API cursor, page size, ordering, checkpoint lifetime, or incremental boundary verified | “Show More” is UI behavior, not an API contract; API cursor, page size, ordering, checkpoints, and incremental boundary unknown | Scrolling a consumer list is not an API contract; cursor, page size, ordering, checkpoints, and incremental boundary unknown |
| Quotas / cadence | Request, account/app limits, concurrency, retry signals, pricing, and allowed polling unknown | API quotas, concurrency, retry signals, pricing, and allowed polling unknown; N2's up-to-30-day request time is not an API quota | Request, account/app limits, concurrency, retry signals, pricing, and allowed polling unknown |
| Subscription fields | Tiers, bundles, pauses, third-party billing described (H3); authorized status/plan/biller/entitlement/renewal fields and freshness unknown | Plan selection and billing visible to owner (N2); authorized status/plan/entitlement/renewal fields and freshness unknown | Base-plan biller visible (M2); authorized status/plan/entitlement/renewal fields and freshness unknown |
| Profiles / household scope | Distinct histories and Kids/PIN controls (H2); stable IDs, delegated profile enumeration/selection, and rights to household members' history unknown | Per-profile history (N1/N2); stable IDs, delegated profile scope, Kids/extra-member access, and household consent unknown | Per-profile lists (M1); stable IDs, delegated selection, Kids/PIN handling, and household consent unknown |
| Qualification result | **Excluded pending permission and technical evidence** | **Excluded from automated sync; export feasibility only** | **Excluded pending service/terms/permission and technical evidence** |

Successful login, a playback entitlement, a catalog API, and ownership of a
subscription do not prove permission to import history or identify a paid active
plan. Never infer `inactive` from unknown subscription data. Do not substitute
unofficial libraries, copied cookies, browser extensions reading sessions,
automated account scraping, or reverse-engineered endpoints for missing access.

## Qualification gates and approval blockers

Logan coordinates every row until named domain owners accept responsibility.
Reviewer roles below are **required and unassigned**, not completed reviews.
Provider application processes, eligibility, fees, approval lead times, and
commercial terms are unknown for all three candidates; no outreach has occurred.

| Gate | Evidence required before an implementation commitment | Required reviewer / current blocker |
| --- | --- | --- |
| G1 Service and permitted use | Exact service, country, legal entity, intended use, applicable terms/version, and an agreement or authoritative provider permission covering account data, history, storage, normalization, and any proposed sharing/derived use; restrictions and termination/deletion duties recorded | Provider-authorized representative plus legal/privacy reviewer; all candidates lack project permission; HBO Max substantive terms also unresolved |
| G2 Approved access | Provider application/approval reference, approved environments and redirect origins, credential location/reference (never secret values), permitted scopes and consent flow, profile selection, refresh/expiry/revocation/disconnect behavior | Provider integration reviewer and security reviewer; no approved access evidence for any candidate |
| G3 Usable data contract | Authorized specification and representative redacted fixtures: account/profile identifiers, event/title/episode IDs, timestamps/precision/time zone, repeats, completion, earliest accessible date, missing/deleted/hidden data; subscription field meanings, provenance, freshness, and unsupported fields | Integration/data reviewer with product; all unknown capabilities must be resolved or explicitly bounded. Lack of usable authorized history fails this gate |
| G4 Feasible operations | Documented pagination/order, page limits, cursor expiry, resumability or supported alternative, incremental boundaries, quotas by account/app, retry-after/backoff, allowed cadence/concurrency, costs, and change/deprecation policy; provider-supported validation plan | Integration and operations reviewers; no verified contract or quotas. SUR-17 cannot promise numeric backfill/freshness targets yet |
| G5 Privacy and ownership | Legal basis and provider permission for intended processing; account-owner versus profile-user consent, minors/Kids exclusion or approved policy, minimum scopes, private defaults, retention/deletion, disconnect treatment, and downstream sharing controls | Legal/privacy and security reviewers with streaming/social/discovery owners; reuse SUR-5/SUR-6 decisions, do not treat account access as household consent |
| G6 Launch decision | Exact qualified provider/service/region list, capability limits, fallback, budget, owner/date, reviewed document revision, and links to G1–G5 approvals; remaining release tests assigned | Logan as product decision coordinator with named domain reviewers; no agreement recorded |

Provider-specific next evidence requests, to be sent by an authorized owner:

- **Hulu:** identify an approved Disney/Hulu partner route for third-party history
  and subscription access, obtain written permitted-use terms, and confirm whether
  profile-specific historical events exist beyond recent progress UI.
- **Netflix:** obtain an authorized partner history/subscription interface and
  explicit permitted uses, or confirm the legal and technical limits of a separate
  user-supplied export proposal. N1/N2 do not authorize a recurring sync service.
- **HBO Max:** confirm the intended HBO service and market, obtain the applicable
  substantive terms and partner permission, and verify access to completed history
  independently of Continue Watching and distributor billing/entitlement flows.

Before commitments, approved docs and fixtures must establish feasibility.
After access is approved, dependent implementation must provide authorized
connect/disconnect, pagination/recovery, quota, completeness, and privacy test
results before release. This research records no successful API test or provider
certification. Store agreements and credential references in access-controlled
systems; commit only non-sensitive summaries and evidence references.

## Fallback and dependency handoff

1. **No provider qualifies (current evidence):** adopt the proposed no-go for
   streaming sync. Defer provider-specific work in
   [SUR-20](https://linear.app/lb-sandbox/issue/SUR-20),
   [SUR-23](https://linear.app/lb-sandbox/issue/SUR-23), and
   [SUR-24](https://linear.app/lb-sandbox/issue/SUR-24). Do not reinterpret zero
   providers as a successful first-provider delivery. Issue statuses are not
   changed by this document.
2. **One provider qualifies later:** record the G6 decision and implement only
   that provider in SUR-23. SUR-24 covers ongoing sync and recovery for it, with
   no additional adapter required. Each further provider independently passes
   G1–G6; one provider's permissions do not transfer to another.
3. **Possible export alternative:** Netflix's user-initiated CSV is the strongest
   documented export lead. It requires a separately approved scope and legal
   review of ingestion/reuse, profile consent, sample schema, completeness, and
   retention. It would be a dated snapshot, with no connected-account, verified
   subscription, ongoing-sync, or full-history guarantee. No importer is approved
   or implemented here. Hulu/HBO Max exports are not verified by this research.

[SUR-17](https://linear.app/lb-sandbox/issue/SUR-17) should consume capability
bounds after qualification, then agree backfill depth, first-import latency,
freshness, quota budgets, supported volume, and completeness fixtures. Preserve
unknown subscription fields and incomplete history explicitly. Foundation work
continues under SUR-4's separate approvals; synthetic planning does not qualify a
real provider or authorize collection of personal data.

## Decision record and acceptance status

| Decision | Proposed outcome | Approval record |
| --- | --- | --- |
| Launch provider list | Empty; Hulu, Netflix, and HBO Max excluded until independently qualified | Pending Logan and G1–G5 reviewers; no acceptance date |
| Fallback | Defer streaming; decide separately whether a foundation-only product release is useful. If sync is mandatory, defer product launch | Pending Logan/product decision; no release authorized |
| HBO and jurisdiction | Evaluate US HBO Max provisionally; confirm intended service and every launch market | Pending product and legal/privacy review |
| Export alternative | Research lead only; no scope expansion or implementation commitment | Pending separate product, legal/privacy, security, and data review |

Record each decision with reviewer name/role, date, document commit, accepted or
change-required outcome, evidence references, and any conditions with an owner.
Do not mark SUR-16 fully accepted until the launch list and fallback are explicitly
agreed. Reopen qualification on new partner evidence, material terms/API changes,
new markets, or broader data use; recheck terms before implementation and release.

Acceptance tracking: candidate evidence and limitations **recorded**, including
the unresolved HBO Max terms retrieval; launch-list/fallback agreement **pending**;
approval blockers and required reviewer roles **identified**, appointments and
reviews **pending**. No provider integration or production readiness is claimed.
