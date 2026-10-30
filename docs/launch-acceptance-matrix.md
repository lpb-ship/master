# Whole-product launch acceptance and test readiness

Status: **proposed v0.1; matrix approval, test readiness, and test sign-off blocked**.
Reviewed: 2026-10-30. Coordinator: **Logan Barragan**, [SUR-59] assignee.
This document assembles the release contract; it records no executed application
tests, provisioned accounts, verified external configuration, or stakeholder approval.

## Sources and scope decision

The [launch PRD] defines six critical journeys: J1 onboarding, J2 supported
connections (including failure), J3 sync and resulting visibility, J4
owner/friend/unauthorized privacy boundaries, J5 friends' feeds and empty states,
and J6 discovery/watchlists. Detailed behavior remains with the [foundation PRD],
[streaming PRD], [privacy PRD], [social PRD], and [discovery PRD]. The matrix below
maps those journeys to their existing criteria rather than creating feature suites.

Reviewed the six PRDs, [SUR-59]–[SUR-62], linked contract issues and their
discussions, and the feature validation issues listed below. The repository at
`9430566` contains planning documents only. No application test artifacts were
attached to the inspected validation issues. This is a dated inventory of the
reviewed sources, not a claim that evidence cannot exist elsewhere.

| Source | Available contract evidence | Readiness implication |
| --- | --- | --- |
| [SUR-5] / [account contract] | Proposed A1–A15, identity and route boundaries, D1–D8 | Stakeholder decisions and cross-feature handoffs remain open. |
| [SUR-6] / [quality contract] | Proposed P1–P5, N1–N4, support/accessibility matrix, Q1–Q7 | Issue is Done, but the document and discussion explicitly leave agreement, locations, legal obligations, and named reviewers unresolved. Status alone is not approval. |
| [SUR-16] / [provider assessment] at `d230fdd` | Candidate evidence, qualification G1–G6, proposed no-go fallback | No verified authorized sync provider. Hulu, Netflix, and HBO Max are candidates, not launch commitments. Scope/fallback approval is pending. |
| [SUR-17] / [streaming contract] at `d8ac532` | Proposed S1–S5, T1 metrics, [synthetic F01–F20 fixtures] | No completed per-provider acceptance record. Fixtures are scenario vectors, not executed adapter tests or proof of access. |
| [SUR-28] | Required sharing behavior matrix, propagation, usability, and compliance decisions | Approved transition semantics and measurable criteria not supplied in inspected records. |
| [SUR-33] | Required discovery/follow/profile/publication/feed contracts and quality gates | Relationship model, visible projection, publication rules, and handoffs require agreement. |
| [SUR-36] | Required canonical identities, subscription/taste inputs, fallbacks, and quality gates | Approved source coverage, identity/input contracts, and targets require evidence. |

The provider and streaming documents are versioned draft inputs from separate
branches; this matrix neither merges nor approves them. Refresh source revisions
and approvals at matrix freeze; do not silently inherit later contract changes.

**Scope decision L1 is open.** The proposed acceptance scope remains J1–J6 on the
mobile/desktop environments below. With no qualified provider, J2/J3 and the
stitched imported-activity journey are blocked; an empty provider list is not a
passing release. Product must either retain the complete scope and hold launch,
or explicitly approve a reduced scope with affected rows, user-facing availability,
and revised PRD/evidence obligations. A foundation-only release is a separate scope
decision, not acceptance of the whole product. A manual-export alternative needs
separate provider/legal/product approval; it does not satisfy ongoing sync.

Existing exclusions remain: native apps, playback, billing, unauthorized scraping,
automatic private-history publication, and unapproved providers/regions/features.
Social discovery and the feed remain gated by privacy approval. No feature is
excluded merely because it is untestable. Scope changes require product and all
affected domain reviewers; missing names/approvals block L1.

## Combined journey matrix

Each row inherits **E1–E5** and the applicable network/accessibility conditions
below. O/F/U are the account roles and D0–D4 the data sets defined later. Every row
is currently **BLOCKED / not run** by L1–L9 as applicable. “Reuse” names the feature
evidence to obtain, not an existing passing result. Logan coordinates all rows;
the contributing domain and issue identify delivery responsibility. Named domain
reviewers still need to accept those roles under L2.

SUR-60 executes only the listed uncovered boundaries after feature evidence is
mapped. If an existing case proves the exact boundary for the release revision,
link its case/run instead of rerunning it. SUR-61 follows the same rule for quality
evidence. Never count a proposed case, a test filename, or a merged PR as a pass.

| Row / PRD journey | Expected behavior and authoritative criteria | Contributing owner / readiness prerequisite | Reuse evidence; specific uncovered boundary | Accounts / data |
| --- | --- | --- | --- | --- |
| M01 / J1 onboarding → feature entry | Register/verify/complete profile, persist after reload and sign-in; enter permitted feature route with stable identity. [Account contract] A1, A3, A11, A12; no action replay or implicit sharing. | Foundation + consumers; SUR-5 D1–D8, integrated routes and [SUR-12] handoff | Reuse SUR-12 account/navigation results. SUR-60: first verified login → connections/discovery, then sign-out and switch actor; verify server actor and cleared caches at the feature boundary. | O/F/U; D0 |
| M02 / J2 connect/disconnect | Only qualified providers connect through approved consent; subscription unknown/unavailable stays distinct from inactive; connection grants no sharing. [SUR-16] G1–G6, [SUR-17] S1/S5, [SUR-26] criteria. | Streaming + foundation/privacy; qualified provider, approved scopes/callbacks and lifecycle policy, working adapter | Reuse SUR-26 security and [SUR-27] connection evidence. SUR-60: authorize as O, return into O's app session, inspect status/subscription downstream, attempt U direct reads, disconnect and verify no new imports. | O/F/U; D1/D2 |
| M03 / J3 first import → history/discovery | Show honest pending/partial/complete state; preserve canonical identity, repeats and provenance; imports remain private. [SUR-17] S2–S4 and fixtures F01–F13/F15–F20 govern identity and completeness. | Streaming + discovery; approved source/catalog mapping, representative authorized fixtures, durable jobs, [SUR-36] inputs | Reuse SUR-27 normalization/import evidence. SUR-60: complete authorized import, compare owner history and discovery inputs to the approved fixture manifest; repeat refresh and verify stable identity/counts and no social publication. | O/F/U; D1/D2 |
| M04 / J2–J3 failure/recovery | Consent refusal, expired/revoked access, callback rejection, partial sync, quota/outage and retry exhaustion produce truthful actionable states; recovery neither duplicates activity nor leaks accounts. Feature rules remain [SUR-17]/SUR-27. | Streaming + foundation; approved recovery/callback behavior and controllable authorized failure cases | Reuse SUR-26/SUR-27 fault evidence. SUR-60: fail connection then retry; interrupt import after a committed page, resume and observe history/discovery; expire app session during callback and verify no wrong-user attachment. | O/U; D2/D4 |
| M05 / J3–J4 private default → explicit share | Without applicable consent, only owner sees activity; F sees only explicitly permitted content after sharing, U sees none. [SUR-28], [SUR-33], account A13; ingestion is not publication. | Privacy + social/streaming; approved audience/history semantics, viewer projection and [SUR-46] prerequisite | Reuse [SUR-44], SUR-26 and [SUR-54] authorization evidence. SUR-60: import → no-consent reads → approved share → feed/profile/recommendation reads at UI and server boundaries for O/F/U, including counts/previews. | O/F/U; D1/D3 |
| M06 / J4 privacy transitions → all consumers | Hide, pause/resume, prior-share edit/revoke, friend removal, disconnect/reconnect and migration apply the approved past/future rules and propagation budget; failures/concurrency never broaden access. Do not choose unresolved [SUR-28]/[SUR-33] semantics here. | Privacy + streaming/social/discovery; approved transition matrix and delay, consumer/path inventory, deletion/derived-data contracts | Reuse SUR-44/SUR-46/SUR-54 and [SUR-58]. SUR-60: while F has cached feed/profile/recommendations and an import is in flight, apply each approved visibility reduction; check direct reads, pagination, caches and background refresh against its expected result/deadline. | O/F/U; D3/D4 |
| M07 / J5 find friend → profile → follow → feed | Approved discovery/projection and relationship rules expose only permitted watching/finished/recommendation items; pagination/order/duplicates follow [SUR-33]. Following does not itself publish history. | Social + foundation/privacy; approved discoverability/relationship/publication contract, SUR-46 privacy approval | Reuse SUR-54 complete social journey. SUR-60: use the same newly onboarded O/F and imported shared event from M03/M05 across profile → relationship → feed; verify title and viewer identity at each handoff. | O/F/U; D1/D3 |
| M08 / J1/J3/J5 empty states | New account, empty import, no friends, and no permitted activity show truthful distinct explanations and approved next steps; no counts or wording reveal hidden activity. [Streaming PRD], [social PRD], SUR-33/SUR-54. | Streaming + social/privacy; approved empty vs pending/failure states and cold-start guidance | Reuse SUR-27/SUR-54 empty-state and comprehension evidence. SUR-60: D0 → populated private D1 → permitted D3 → revoked visibility; confirm empty states remain accurate and do not imply successful sync when pending/failed. | O/F/U; D0/D1/D3/D4 |
| M09 / J6 search → details → save → destination | Canonical movie/TV identity is consistent; save/remove persists across sessions without duplicates; changed availability does not delete saved titles; outbound intent is not playback. [SUR-36], [discovery PRD], SUR-58. | Discovery + streaming/foundation; licensed sources/coverage, canonical IDs, region/subscription semantics, persistence | Reuse SUR-58 search/watchlist/destination results. SUR-60: import/subscription update → discovery detail → save → reload/sign-in → watchlist → allowed destination; verify same canonical title and U cannot read/mutate O's list. | O/U; D1/D2 |
| M10 / J6 missing inputs/outage/empty | No subscription/taste/friend inputs still permit approved non-social discovery; no results, stale/unknown availability, invalid destinations and upstream outages make no unsupported claims; saved titles remain accessible. [SUR-36]/SUR-58. | Discovery + streaming; approved absent/stale/error fallbacks and controllable sources | Reuse SUR-58 outage/empty evidence. SUR-60: change subscription input to unknown and fail availability source after saving; verify saved-list access, honest availability, safe outbound fallback and no false save confirmation. | O/U; D0/D2/D4 |
| M11 / J4/J6 social discovery → revocation | Only viewer-permitted activity influences recommendations/explanations; revoked or deleted activity cannot leak through derived output, caches or telemetry. [SUR-28]/[SUR-33]/[SUR-36] and SUR-58 visibility/revocation criteria. | Privacy + social/discovery; agreed derived-data contract, invalidation policy and SUR-46 gate | Reuse SUR-44/SUR-54/SUR-58. SUR-60: consume a permitted share in discovery, revoke/remove relationship, then query warm/cold recommendations as F and U; compare to approved propagation semantics and inspect explanations/logs. | O/F/U; D3/D4 |
| M12 / J1–J6 expiry, isolation and deletion | Session expiry/sign-out/account switch cannot retain another actor's drafts or protected data; deletion/revocation cannot be undone by jobs or retries. Account A5–A8/A11/A14, [SUR-26], SUR-44. | Foundation + every consumer; approved session/lifecycle policy and deletion fences | Reuse SUR-12/SUR-26/SUR-44. SUR-60: sign out/switch actor while sync and watchlist requests complete; exercise Back/multiple tabs and queued retry after deletion; inspect server enforcement and all affected caches. | O/F/U; D1/D3/D4 |
| M13 / J1–J6 integrated quality | Complete processes meet approved performance/accessibility/data-handling criteria; credentials and private titles stay out of unauthorized client output/errors/logs. [SUR-6] plus feature quality contracts. | QA/accessibility + security/privacy + all domains; approved targets, representative load/configuration and feature evidence | Reuse SUR-12/13/14/27/45/46/54/58. SUR-61: measure uncovered route/provider-return transitions, focus/error handoffs and cross-service diagnostics on M01–M12; retain criterion-level evidence and defects. | O/F/U; D0–D4 |

## Browser, viewport, and execution coverage

These aliases reference the **proposed**, not yet agreed, [SUR-6 support matrix].
L3 must approve its whole-product applicability with feature owners and freeze
exact devices/OS/browser versions. No wider support or new numerical target is
introduced here. All M01–M13 rows require applicable E1–E5 coverage; record each
row × environment × provider/region × relevant account/data variation separately.
No aggregate pass can hide a missing mobile/browser cell. A not-applicable cell
needs a named reviewer, rationale and approved scope reference.

| ID | Inherited platform/browser coverage | Inherited viewport and interaction checks |
| --- | --- | --- |
| E1 | iPhone SE 3 / iPhone 13 class; Safari current and previous major iOS | 375/390 CSS px widths; portrait/landscape, touch, keyboard, VoiceOver, verification/provider returns |
| E2 | Pixel 6a class; Chrome current and previous major on supported Android | 360–412 CSS px widths; portrait/landscape, touch, keyboard, TalkBack, Back navigation |
| E3 | iPad class; Safari current and previous major iPadOS | 768/820 CSS px widths; portrait/landscape, touch/hardware keyboard |
| E4 | Windows 11; Chrome/Edge/Firefox current and previous major | 1280 × 720 and 1440 × 900; keyboard/mouse; NVDA with current Firefox/Chrome |
| E5 | Supported macOS; Safari current and previous major, Chrome current | 1440 × 900; keyboard; VoiceOver with current Safari |

Record actual width **and height**, scale factor, orientation, input mode and
physical vs emulated execution. “Current” must become exact freeze versions.
Reuse the source's physical mobile requirement and its reflow, zoom, text-size,
reduced-motion and high-contrast checks. Use [quality contract] N1 for approved
timings, N2 broadband and N3 degraded/N4 offline for applicable recovery boundaries;
retain their exact parameters rather than inventing a second network profile.
Apply feature-specific provider load/latency conditions only after their approval.
Emulated or stubbed results remain labelled and cannot prove live provider access.

## Accounts, representative data, and external configuration

**None of these accounts or configurations is confirmed.** L4/L5 require named
custodians, redacted setup evidence and successful preflight before a row is ready.
Use isolated non-production accounts and synthetic application identities; real
provider access requires provider-authorized controlled accounts and approved data
handling. Do not put passwords, tokens, cookies, raw exports or personal data in
this document, fixtures, screenshots, or public evidence.

| Account role | Required state and access | Custodian / confirmation |
| --- | --- | --- |
| O — owner | Verified complete app identity; owns connection, private activity and watchlist; can deliberately start fresh onboarding | Foundation + streaming QA; named custodian and account reference pending L4 |
| F — permitted friend | Separate identity/session; relationship and grant established by approved SUR-28/SUR-33 flow; only explicitly permitted projection | Social/privacy QA; custodian, relation/grant IDs and successful allow/deny preflight pending L4 |
| U — unauthorized viewer | Separate authenticated non-friend with no grant; also exercise signed-out request and former-friend state after F's removal | Security/privacy QA; custodian and denial evidence pending L4 |

Use separate browser profiles for O/F/U and controlled shared-profile account-switch
cases for M12. Account-role labels describe test identities, not acceptance of an
unresolved follow model. Record provisioning/reset instructions and opaque fixture
references, relationship/consent versions, environment, last validation date, cleanup
policy, and the custodian's acknowledgement. Reset sharing and caches as well as
database rows; do not let an earlier share make a private-default test pass falsely.

| Data set | Required contents / provenance | Confirmation needed / consumer |
| --- | --- | --- |
| D0 Empty | Fresh/incomplete then complete account; no connections/history/friends/watchlist; independently empty authorized provider result | Foundation/streaming/social/discovery confirm true emptiness vs pending/failure; M01/M08/M10 |
| D1 Populated | Approved movie/episode identities, repeated watches, authorized subscription observations, private imports, persisted watchlist | Streaming supplies gold records/canonical mapping and expected counts; discovery validates identity/region; M02/M03/M07/M09 |
| D2 Ambiguous/missing | SUR-17 F01–F20 reused where applicable: duplicate/replay, missing/coarse time, unmatched titles, profile isolation, partial import; unknown/stale subscriptions, no availability and ambiguous discovery editions | Streaming/discovery adapt existing vectors; confirm actual authorized provider fields, catalog/source revision and unavailable fields; M02–M04/M09/M10 |
| D3 Shared/denied | Distinct explicitly shared and private events, hidden title, paused/prior activity, permitted and removed friend, revoked/deleted event and warm derived caches | Privacy/social supply expected visibility per approved transition for O/F/U; do not invent past/future semantics; M05–M08/M11/M12 |
| D4 Failures | Authorized consent cancellation/expiry/revocation, partial pages, quota/outage, interrupted response, offline, failed privacy save and concurrent read/job | Feature owners supply controllable failure setup and recovery oracle; distinguish injected tests from real provider results; M04/M06/M08/M10–M13 |

Record fixture revision, seed/reset method, canonical/provider crosswalk, expected
counts and visibility, populated/empty assertions and approved representative
volumes before execution. Reuse SUR-17/SUR-36 volumes once approved; no new size
or load is selected here. Synthetic vectors cannot confirm provider permissions.

| Configuration preflight | Evidence required before acceptance execution | Contributor / current state |
| --- | --- | --- |
| Build and environment | Staging URL, commit, schema/config revisions, isolated tenants, release access, production-equivalence differences and approved processor/region inventory | Foundation/operations; unconfirmed L5; production verification belongs to [SUR-62] |
| Auth and email | Selected service/tenant, controlled inbox delivery, approved origins and exact environment callback URLs, session/verification/reset flows and negative callback evidence | Foundation/security; unconfirmed L5 |
| Streaming, per qualified provider | Exact service/market/access method; SUR-16 G1–G6 approval links; app-registration ID, permitted scopes, account/profile permission, test-account rights, quotas, history bounds and secret-manager reference only | Streaming/security/privacy; no qualified provider, blocked L1/L5 |
| Streaming callback/token lifecycle | Exact registered callback/redirect origins per environment where applicable; approved state/nonce/PKCE or equivalent, replay/wrong-session rejection, expiry/refresh/revoke/disconnect results | Streaming/security; unconfirmed L5. Do not assume a candidate offers OAuth; non-callback methods need approved applicability rationale. |
| Catalog and availability | Licensed metadata/artwork/availability sources, attribution/caching rights, credential reference, provider/region/content coverage, canonical mapping revision, freshness policy and validated destinations | Discovery/legal; unconfirmed L5/L8 through SUR-36/SUR-58 source-rights prerequisites |
| Jobs and derived state | Scheduler/worker revision, approved cadence/quotas, reset and failure controls, privacy-aware caches, deletion/revocation fences and redacted diagnostics | Streaming/privacy/social/discovery/operations; unconfirmed L5/L6 |

Preflight requires an authorized successful path and negative/failure evidence,
not just the existence of an environment variable. Keep actual secrets and
sensitive agreements in access-controlled systems; link redacted attestations.
Never probe unsupported interfaces or use real user data to fill a readiness gap.

## Quality targets and evidence inheritance

This register records required **sources** of targets without selecting new
values or converting proposals into agreement. At approval, record source commit,
criterion ID, selected values/conditions, named approver/date and evidence link.
No criterion with an unknown threshold or missing applicability decision can pass.

| Required gate | Authoritative criteria / current approval state | Existing evidence owner → uncovered integration work |
| --- | --- | --- |
| Page load, auth, profile, navigation, interactions | SUR-6 P1–P5/N1–N4 and Q1; proposed only. Foundation numbers do not define sync/search/feed budgets. | SUR-13 → SUR-61 maps M01/M13 and uncovered stitched transitions |
| Import completeness, matching, duplicates, first-import time, freshness, volume/concurrency and reliability | SUR-17 T1-C/M/D/L/F/V/N/R/U, S4 per qualified provider; no approved provider target records | SUR-27 → SUR-61 maps M02–M04 under approved provider conditions |
| Privacy reads, revocation delay, comprehension | SUR-28 approved behavior/latency/load/propagation/participant thresholds required; unresolved | SUR-44/45/46 → SUR-60/61 map M05/M06/M11 and consumer paths |
| Feed/profile quality and success measures | SUR-33 latency, payload, propagation, representative feeds, cold-start comprehension and qualifying events; unresolved | SUR-54 → SUR-61 maps M07/M08; no invented engagement threshold |
| Discovery/search/detail/watchlist/freshness | SUR-36 response budgets, representative volumes/upstream delay, freshness and missing-input rules; unresolved | SUR-58 → SUR-61 maps M09–M11 |
| Accessibility/support | SUR-6 Q2 proposes WCAG 2.2 AA and E1–E5; whole-process applicability/approval still required, including provider-hosted steps | SUR-12/45/54/58 plus SUR-27 accessible flow evidence → SUR-61 covers cross-route focus, labels/errors, keyboard and assistive technology |
| Security and compliance | SUR-6 Q5–Q7 processors/locations, jurisdiction, markets/ages, consent, retention/deletion; SUR-16 provider rights; SUR-17 S5/SUR-26 lifecycle; SUR-28/33/36 domain obligations and SUR-58 licensing. Unresolved; no regulatory regime/certification presumed. | SUR-14/26/44/46/54/58 → SUR-61 traces credentials/private data across UI, responses, errors, jobs, caches and logs |
| Operations/recovery | SUR-6 Q3/Q4 and feature operations gates remain subject to named owners and approval | SUR-14/15/27/46 and discovery monitoring evidence → SUR-62 rollout/rollback handoff; test sign-off alone does not authorize deployment |

## Blockers, decisions, and sign-off

A **launch blocker** is any unintended activity/personal-data exposure, credential
leak, unauthorized mutation, lost/corrupt cross-feature data, misleading completion
of a critical operation, or defect preventing an approved critical journey on a
supported environment. Failure of an approved quality/compliance/provider gate is
also blocking. Missing contracts, approvals, configuration, accounts, test paths
or evidence are **readiness blockers**, even before a failing test exists. Any
unintended exposure blocks launch regardless of frequency or aggregate pass rate.

Non-blocking defects must have an explained impact, affected rows/environments,
reproduction, owner, disposition and named product/QA/domain risk acceptance.
Unknown severity remains blocking until triaged. No performance reviewer can
waive privacy/security/legal requirements, and no unresolved exposure can be
accepted as residual risk. A scope change requires L1 approval and revalidation;
it cannot relabel an included failing scenario as not applicable.

Logan is the accountable coordinator for every open decision below based on issue
assignment; this does **not** appoint him legal reviewer, QA signer or release
authority. Proposed authority follows SUR-6 Q4: product approves scope, each domain
accepts its contracts/evidence, QA/accessibility accepts coverage, security/privacy
and qualified legal reviewers accept their obligations, and operations accepts
configuration/readiness. L2 must name those people and a final release decision
maker (or explicitly accepted overlapping roles). Until then, there is no recorded
authority to sign off the combined matrix or authorize launch.

| Gap | Resolution and closure evidence | Required decision owners / tracking | Blocks |
| --- | --- | --- | --- |
| L1 Scope | Versioned included journeys/providers/regions and exclusions; explicit hold or approved reduced-scope/fallback decision, with source approvals | Product + affected domains; SUR-16 G6 and SUR-59 | Matrix approval and J2/J3 execution; whole-product sign-off |
| L2 Ownership/authority | Named contributors, account custodians, QA/accessibility, security/privacy/legal, operations and final release approver; role acceptance and escalation path | Logan coordinates product/domain appointments; SUR-6 Q3/Q4, SUR-59, SUR-62 | Matrix approval and all sign-off |
| L3 Environments/targets | Accepted SUR-6 Q1/Q2, E1–E5 freeze versions/heights, network conditions, feature budgets and whole-process accessibility scope | Product + engineering + QA/accessibility; SUR-6/17/28/33/36 | Final test configuration and quality sign-off |
| L4 Accounts/data | O/F/U and D0–D4 manifest, permissions, seed/reset/cleanup and populated/empty preflight evidence, accepted custodians | Feature QA + security/privacy; SUR-59 with feature evidence owners | Affected journey execution and sign-off |
| L5 External configuration | Completed redacted preflight register for build/auth/email/provider/catalog/jobs, permitted callbacks/scopes and authorized account evidence | Foundation + streaming + discovery + operations/security; SUR-16, SUR-27, SUR-58, SUR-62 | Affected journey execution and sign-off |
| L6 Feature handoffs | Approved identity, import/catalog, sharing/relationship/derived-data and failure/lifecycle contracts with consumer acknowledgements | Foundation/streaming/privacy/social/discovery; SUR-5/17/28/33/36 and SUR-46 privacy prerequisite | Dependent tests, feed/social discovery and sign-off |
| L7 Evidence coverage | Feature case/run links, missing boundary results for every required matrix cell, defect fixes and retests | Feature validation owners + QA; SUR-60/SUR-61 | Test sign-off |
| L8 Rights/data obligations | Reviewed processor/market/lifecycle decisions, authorized provider use, source licensing/attribution and implemented obligations | Product + qualified legal/privacy/security + domains; SUR-6 Q5–Q7, SUR-16, SUR-26/46/54/58 | Real personal data use and release sign-off |
| L9 Operational handoff | Named release/support/rollback owners; tested recovery references, production configuration checks and smoke/rollback plan | Operations + final release authority; SUR-62 using SUR-14/15/27/46 | Deployment authorization; cannot be inferred from passing tests |

Every L1–L9 entry is **open**, with no approval date or evidence of closure in this
review. Resolve in its authoritative issue/contract first, then record here the
selected outcome, named reviewer/role, date, exact revision, evidence link and
remaining conditions. Silence, issue status and merging this document do not close
these gaps. Do not mark SUR-59 fully accepted until matrix approval and test
readiness inputs are confirmed.

Evidence records use one entry per matrix cell with: row/Journey IDs; approved
scope and contract revisions; contributing owner; existing feature case/run or
specific boundary case; build/schema/config revisions and environment; exact
device/browser/viewport/network; provider/region and account/data fixture versions;
preconditions/actions; expected vs actual UI **and enforcement-boundary** outcome;
redacted artifacts; result (`blocked`, `not run`, `pass`, `fail`, or approved
`not applicable`); defect/reproduction/severity/owner; retest link; reviewer/date.
A reused artifact must match the contract, build/config and coverage or have an
explicit reviewed equivalence rationale; otherwise the affected boundary is open.

Sign-off sequence:

1. **Matrix approval:** resolve L1–L3, agree row expectations from feature contracts
   and record named domain/product/QA/security/privacy approvals of this revision.
2. **Ready for acceptance execution:** resolve applicable L4–L6/L8 preconditions
   and feature handoffs. Independent synthetic exploratory work may continue but
   cannot close blocked acceptance cells. No feed release before SUR-46 approval.
3. **Test sign-off:** SUR-60/SUR-61 consolidate reusable evidence and fill gaps;
   every included required cell passes, all required criteria/obligations have
   evidence, L1–L8 are closed, and no blockers remain. Named QA and domain reviewers
   sign the exact release candidate; product records non-blocking dispositions.
4. **Release decision:** SUR-62 closes L9 and verifies production differences,
   health/privacy smoke checks and rollback ownership. The named final authority
   records go/no-go with domain decisions; test sign-off is not deployment approval.

Any changed contract, sharing/identity boundary, source/provider permission,
region, fixture, build or material configuration reopens affected approvals and
matrix cells. Retest affected journeys and cross-boundary consumers; do not repeat
unrelated feature suites. Preserve earlier results and the reason for supersession.

[launch PRD]: https://linear.app/lb-sandbox/project/end-to-end-validation-and-web-launch-00fc923f8563
[foundation PRD]: https://linear.app/lb-sandbox/project/app-foundation-and-mobile-web-experience-7af8e664b8d0
[streaming PRD]: https://linear.app/lb-sandbox/project/streaming-connections-and-viewing-activity-sync-3d5b951b37ac
[privacy PRD]: https://linear.app/lb-sandbox/project/private-by-default-activity-and-sharing-controls-6344f4be29d6
[social PRD]: https://linear.app/lb-sandbox/project/friends-and-shared-viewing-feed-14fb20538100
[discovery PRD]: https://linear.app/lb-sandbox/project/title-discovery-and-cross-service-watchlists-4e4d14caa6e0
[account contract]: account-profile-contracts.md
[quality contract]: quality-gates-and-data-handling.md
[SUR-6 support matrix]: quality-gates-and-data-handling.md#supported-devices-browsers-and-accessibility
[provider assessment]: https://github.com/lpb-ship/master/blob/d230fdd766d86a01d6e660da2ab84500882502bc/docs/streaming-provider-access.md
[streaming contract]: https://github.com/lpb-ship/master/blob/d8ac5322e2d658cfe345a6f8e4e9223ffcfc1646/docs/streaming-data-contracts.md
[synthetic F01–F20 fixtures]: https://github.com/lpb-ship/master/blob/d8ac5322e2d658cfe345a6f8e4e9223ffcfc1646/docs/fixtures/streaming-contract-cases.json
[SUR-5]: https://linear.app/lb-sandbox/issue/SUR-5
[SUR-6]: https://linear.app/lb-sandbox/issue/SUR-6
[SUR-12]: https://linear.app/lb-sandbox/issue/SUR-12
[SUR-16]: https://linear.app/lb-sandbox/issue/SUR-16
[SUR-17]: https://linear.app/lb-sandbox/issue/SUR-17
[SUR-26]: https://linear.app/lb-sandbox/issue/SUR-26
[SUR-27]: https://linear.app/lb-sandbox/issue/SUR-27
[SUR-28]: https://linear.app/lb-sandbox/issue/SUR-28
[SUR-33]: https://linear.app/lb-sandbox/issue/SUR-33
[SUR-36]: https://linear.app/lb-sandbox/issue/SUR-36
[SUR-44]: https://linear.app/lb-sandbox/issue/SUR-44
[SUR-46]: https://linear.app/lb-sandbox/issue/SUR-46
[SUR-54]: https://linear.app/lb-sandbox/issue/SUR-54
[SUR-58]: https://linear.app/lb-sandbox/issue/SUR-58
[SUR-59]: https://linear.app/lb-sandbox/issue/SUR-59
[SUR-60]: https://linear.app/lb-sandbox/issue/SUR-60
[SUR-61]: https://linear.app/lb-sandbox/issue/SUR-61
[SUR-62]: https://linear.app/lb-sandbox/issue/SUR-62
