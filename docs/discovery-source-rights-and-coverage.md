# Discovery source rights and initial coverage

Status: **public-source assessment complete; access, coverage, and release approval pending**.
Evidence reviewed: **2026-10-30**. Decision coordinator: **Logan Barragan**, SUR-34 assignee.
Source: [SUR-34](https://linear.app/lb-sandbox/issue/SUR-34).

## Decision for review

Recommend **Watchmode paid-plan evaluation for both title metadata and regional
availability**. Its documented movie/TV interfaces, offer types, ID mappings,
commercial plans, and storage terms provide the most concrete evaluation path.
This is a candidate selection, not a purchase, approved integration, or coverage
claim. **Verified production sources and launch coverage are empty (`[]`).**
Do not launch discovery against these sources until gates G1–G6 below pass.

Evaluate US/English movie and TV discovery for Netflix, Hulu, and HBO Max on the
existing mobile-friendly web platform. All scope choices remain proposals; the
[discovery PRD](https://linear.app/lb-sandbox/project/title-discovery-and-cross-service-watchlists-4e4d14caa6e0)
leaves providers, countries, languages, budget, and thresholds unresolved.
No stakeholder agreement, source account approval, credential reference, signed
license, or live response fixture was supplied in the reviewed repository or issue
records. No account was created, terms accepted, paid plan purchased, or credential
store searched. Only public documentation was retrieved; no authenticated catalog
API or actual streaming destination was tested.

Coordinate names and markets with
[SUR-16's assessment at d230fdd](https://github.com/lpb-ship/master/blob/d230fdd766d86a01d6e660da2ab84500882502bc/docs/streaming-provider-access.md).
It proposes the same three services but verifies no authorized history-sync
provider. Its US/English baseline and interpretation of HBO as HBO Max are also
pending approval. Discovery catalog rights are independent of history rights:
SUR-16's no-go does not by itself forbid licensed catalog discovery, and a catalog
API does not authorize history import or verify a user's subscription. Do not
repeat SUR-16's consumer-account/history investigation here.

## Proposed launch coverage matrix

Every row is **unverified and disabled for production** until G1–G6 pass. “Target”
means a combination to validate, not an assurance that every title is offered.
The provider source IDs and plan/bundle mappings must come from authorized source
responses, not inferred names or hard-coded marketing lists.

| Provider/service | Region | Metadata and UI language | Content target | Offer target | Client platforms | Current coverage result |
| --- | --- | --- | --- | --- | --- | --- |
| Netflix direct service | US only | English (`en-US`); original title retained when supplied | Movies and TV series; season/episode limits explicit | Subscription; plan eligibility unresolved | Web matrix below | Public Watchmode docs list Netflix; no live title, plan, region, or destination audit |
| Hulu on-demand direct service | US only | English (`en-US`) | Movies and TV series; season/episode limits explicit | Subscription; exclude Live TV and unverified add-ons | Web matrix below | Public Watchmode docs list Hulu; no live audit; bundle/distributor mapping unresolved |
| HBO Max direct service (provisional HBO interpretation) | US only | English (`en-US`) | Movies and TV series; season/episode limits explicit | Subscription; exclude distributor/channel variants | Web matrix below | Public Watchmode docs list HBO Max; source ID, naming/aliases, tier mapping, and live audit unresolved |
| Rental/purchase storefronts | No launch region approved | No additional language scope | Evaluation cases only | Rental and purchase modeled separately; display disabled initially | No additional platform scope | No launch storefront selected; expansion requires G1–G6 |
| Free ad-supported services | No launch region approved | No additional language scope | Evaluation cases only | Free ad-supported modeled; display disabled initially | No additional platform scope | No launch service selected; expansion requires G1–G6 |

Web support inherits the **proposed**, not approved,
[foundation support matrix](quality-gates-and-data-handling.md): iOS/iPadOS Safari,
Android Chrome, Windows Chrome/Edge/Firefox, and macOS Safari/Chrome. Freeze actual
versions and run destination checks through SUR-48. Native apps, smart TVs,
embedded webviews, guaranteed app deep links, live sports/linear TV, other
countries/territories, and other UI languages are outside this baseline. An API's
worldwide coverage count does not enlarge it. English metadata does not establish
English audio/subtitle availability. Do not filter out non-English works solely
because their original language differs; show source-supported English details
or explicitly missing translations. Confirm that Watchmode can meet this language
contract in the live sample; an `original_language` field is not localization.

## Offer semantics and truthfulness

These are proposed adapter meanings for SUR-36/SUR-40, not new subscription storage.
Retain source, source title/provider IDs, country, offer type, title/season/edition
scope, observation time, and any plan/bundle restrictions with every observation.

| Normalized offer | Source evidence and display meaning | Subscription relevance |
| --- | --- | --- |
| Subscription-included | Watchmode `TitleSource.type = sub`: a subscription offer for the identified title/service/region. Show “Subscription required” unless plan-level inclusion is established. A subscription with ads is still this type. | “Included in your subscription” requires fresh applicable offer data plus the permitted, current subscription input and matching tier/add-on/region. A connected account, price of zero, or provider-name match alone is insufficient. Unknown tier eligibility stays unknown. |
| Rental | `rent`: temporary paid access; keep duration, price/currency, and edition only when source-supported. Display “Rent”; never treat null price as free. | Additional payment even if the user subscribes to that provider; excluded from initial display scope. |
| Purchase | `buy`: purchase offer under provider terms, not a promise of permanent ownership or DRM-free access. Display “Buy”; do not merge with rental. | Additional payment; excluded from initial display scope. |
| Free ad-supported | Watchmode `free` is explicitly defined as free/ad-supported in the reviewed schema. Display “Free with ads”; account or geographic restrictions may still apply. | Not evidence of a paid subscription; excluded from initial display scope. Preserve different semantics if another source uses `free` differently. |
| TV-provider login / unknown | Watchmode `tve` requires cable/TV-provider access; unknown enums or missing region/scope cannot be classified as subscription-included. | Excluded until separately validated; fail to unknown rather than invent an entitlement. |

A fresh successful empty response means **no offers returned within the checked
source/provider/region scope**, never “unavailable everywhere.” Unsupported region,
missing mapping, incomplete TV scope, stale response, rate limit, and outage are
separate unknown/error states. A series-level offer or season/episode count does
not establish that a particular season, episode, or edition is available.

## Official source evidence and selection

Sources below were inspected on 2026-10-30. Public documentation establishes
published capabilities and conditions only. Quotes and schema examples are not
live catalog observations, contracted guarantees, or legal approval.

| ID | Source / version | Observed evidence and selection consequence |
| --- | --- | --- |
| W1 | [Watchmode API documentation](https://api.watchmode.com/docs/) and [OpenAPI description](https://api.watchmode.com/openapi.json?v=beab88d9c4b39c2e), version 1.10.1 | Documents search, title details, movie/TV types, title sources by region, episode reads, changes feeds, and IMDb/TMDB mappings. API key access is documented, including `X-API-Key`; no application key was provided or tested. Claims 427 services/54 countries; this is vendor-reported breadth, not validated launch coverage. |
| W2 | [Watchmode terms](https://api.watchmode.com/tc), updated October 24, 2026, Meteoric, LLC | §3 permits non-image data in an owned website/app and combination with other data; prohibits resale/sharing with third parties. Paid accounts may store it while active and reasonably current; free caches must refresh/delete within 30 days; cancellation/termination requires deletion. Third-party images are explicitly excluded from the license. §6 grants revocable, limited access under the applicable plan. Legal must confirm intended display, recommendation, derived-data, and downstream processor uses. |
| W3 | [Watchmode pricing](https://api.watchmode.com/pricing) and W1 Account reference | USD/month: Developer free, 2,500 credits, noncommercial with attribution, up to three countries; Startup $349/40,000 credits; Business $599/100,000; Enterprise custom. Paid plans allow commercial use without Watchmode attribution. W1 documents default 120 requests/minute free, 240 paid, account overrides, and some legacy catalog headers incorrectly showing 1,000. Confirm actual account enforcement. Credits and request limits are distinct; extra pages, appends, and external-ID resolution can add cost. |
| T1 | [TMDB API terms](https://www.themoviedb.org/api-terms-of-use), updated October 20, 2023; rendered page inspected after HTTP fetch returned 403 | §1 prohibits caching beyond six months, derivatives, and use in connection with ML/AI applications; termination requires content purge. §2 requires a separate written commercial agreement and expressly discusses recommendation-related revenue. Treat recommendation/derived-use authorization as unresolved; do not assume a developer key or a commercial payment overrides every restriction. |
| T2 | [TMDB FAQ](https://developer.themoviedb.org/docs/faq) and [rate limits](https://developer.themoviedb.org/docs/rate-limiting) | Movie/TV metadata and images; free noncommercial use with attribution, commercial license by contact, no current SLA. TMDB disclaims ownership of API images/data. Approximate upper limit around 40 requests/second can change; respect 429. This is not a reserved quota or freshness guarantee. |
| T3 | [TMDB movie watch providers](https://developer.themoviedb.org/reference/movie-watch-providers) and [TV watch providers](https://developer.themoviedb.org/reference/tv-series-watch-providers) | Country/provider availability powered by JustWatch; JustWatch attribution mandatory. Does not return full provider deep links; supplies a TMDB destination. Potential limited alternative only if rights, coverage, and an intermediary destination are accepted. |
| J1 | [JustWatch partner API](https://www.justwatch.com/us/JustWatch-Streaming-API) | Advertises streaming data across over 120 countries and a commercial contact path. No project agreement, price, quota, caching terms, licensed artwork scope, or representative response was supplied. Commercial alternative for gaps, not an authorized public fallback API. |

**Fallback decision:** do not add a second runtime source initially. Watchmode
could cover both data domains and avoid an additional license/identity join.
First measure gaps. Evaluate TMDB for missing metadata only after T1 restrictions,
commercial rights, and artwork are resolved; evaluate direct JustWatch for missing
availability/destinations if a partner agreement is feasible. TMDB watch-provider
data is itself powered by JustWatch, so it is not independent coverage from a
direct JustWatch source. No fallback is currently qualified. If the primary cannot
meet approved coverage, either narrow the matrix with product approval, qualify
an alternative, or defer discovery. Never silently blend conflicting offers;
preserve provenance and resolve canonical mappings under SUR-36.

## Rights and operational obligations

| Use | Current evidence / requirement before production |
| --- | --- |
| Metadata and availability display | W2/W3 describe a paid commercial route; G2 must record the actual legal entity, accepted terms/plan, approved account/environments, and allowed use. TMDB requires its own written agreement for commercial use. No source rights transfer through an ID mapping. |
| Attribution | Watchmode free use requires a credit/link wherever its data is displayed; paid plans remove that Watchmode requirement, not third-party obligations. TMDB §3 requires a less prominent approved logo and prominent notice: “This application uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.” Its FAQ additionally specifies About/Credits placement with slightly different notice wording; legal must settle the applicable agreement and copy. TMDB watch-provider data separately requires JustWatch attribution. |
| Artwork, posters, backdrops, provider logos | Watchmode expressly grants no third-party image rights and prohibits hotlinking its CDN/server images. Independently clear display, download, hosting/proxying, resizing, and attribution rights before using any returned media URL. TMDB's ownership disclaimer is not clearance. Use text/service names and application-owned placeholders until cleared; assess trademark presentation separately. A no-artwork launch needs product approval. Honor takedown notices and purge affected assets. |
| Caching/storage | Separate non-image data from image assets. W2 permits paid non-image retention while active/current and requires deletion on cancellation/termination; free refresh/delete at 30 days is a legal ceiling, not acceptable availability freshness. T1 caps caches at six months and requires purge on termination. Record approved TTLs, backups, replicas, browser/CDN caches, logs, and deletion verification; do not retain raw responses indefinitely. |
| Recommendations and derived use | W1 describes recommendation features, but that does not clear every derivative, embedding, training, export, or personalization use. Obtain a documented interpretation covering intended filtering/ranking and stored derived results. T1 restrictions require explicit resolution before TMDB is used in recommendation pipelines. No training/embedding use is included in this proposal. Private/social inputs also require the separate visibility contract; do not send private history or friend activity to a catalog API. |
| Watchlist survival and license exit | Keep app-owned save identity/order separate from licensed display fields. Confirm rights to retain external ID mappings and minimum identifying text after cancellation; do not assume IDs or copied titles are exempt. Purge restricted enrichment/derived caches as required and preserve the user's app-owned saved entry with an unavailable-details state. G2 must settle a workable exit policy before source lock-in. |
| Costs, quotas, and security | Startup is a price reference, not an approved budget. Estimate monthly credits as the sum of calls/pages by endpoint cost, including cache misses, ID resolution, refreshes, retries, and QA; compare peak request rate separately. W1 lists search/details/sources at one credit each with Watchmode IDs, extra append/ID costs, and zero-credit quota status. Measure workload under SUR-36; no capacity result exists. Keep keys server-side, prefer the documented header, redact headers/query secrets, bound concurrency/retries, and stop quota-exhaustion loops. |

## Freshness and failure policy

SUR-36 must agree numeric metadata/availability ages, refresh cadence, acceptable
source lag, sample sizes/accuracy thresholds, workload, and request budgets using
[SUR-6's quality gates](quality-gates-and-data-handling.md). None is an approved
number here. W1's daily change feeds and W2's “reasonably current” are not a
contracted freshness SLA. **Unset freshness thresholds block positive production
availability claims.** Legal retention ceilings do not substitute for these targets.

- Record `fetchedAt` and, when available, the source's observation/update time.
  A new fetch of old upstream data does not prove a recent catalog observation.
  If source age cannot be bounded, disclose that limit and resolve it in G4.
- Cache by source, title identity/type, region, and applicable language/offer scope;
  keep private subscription relevance out of shared caches. Refresh metadata and
  offers independently. Refresh all pages of authorized changes feeds with overlap
  and deduplication; checkpoint only after successful processing. Reconcile missed
  windows before labeling affected cached offers fresh.
- On expiry, failed refresh, 429, timeout, malformed data, or missing region, mark
  availability unknown/stale and suppress confirmed-inclusion claims. Retry within
  agreed limits and source signals; never turn a failure into an empty successful
  result. Keep independently licensed metadata and app-owned saved entries usable.
- Invalidate affected offer caches when country, mapping, source rights, or provider
  scope changes. Recompute subscription relevance when permitted subscription inputs
  change/expire. Remove restricted content on takedown/termination even if its TTL
  has not expired. An outage does not extend licensing rights.
- SUR-48 validates source-supported HTTPS destinations and redirects against the
  approved provider domains and platform matrix. A missing URL, paid-plan placeholder
  string, or rejected redirect is not a watch link. Offer a clearly labeled fallback
  only after its destination is validated; no link is a playback guarantee.

## Representative data evidence and required live audit

**Executed:** inspected W1's public schema/examples. Its search/details examples
identify *Breaking Bad* (2008), Watchmode `3173903`, IMDb `tt0903747`, TMDB `tv/1396`.
The `/sources` example identifies Netflix `203` and includes `US` in its regions.
The title-source example has `sub`, `US`, a Netflix URL ending in `123456`, and
season/episode counts. These are **documentation examples with placeholder data**,
not a matched live title/provider result and not evidence that this title is now
available. The schema supports `sub/rent/buy/free/tve`; title-source `region` and
price can be null, and the reviewed schema has no currency or per-offer observation
time field. Prices and freshness therefore need further contract evidence.

**Not executed:** authenticated access, live movie/TV matching, actual provider
coverage, plan eligibility, destination behavior, latency, or accuracy audits.
The table below is the proposed audit queue; every row is **pending access (G2)**.
Titles are identification probes, never asserted current catalog assignments.

| Probe | Candidate title/provider/region | Evidence to collect / failure exposed |
| --- | --- | --- |
| V1 | *The Irishman* (2019 movie) and *Stranger Things* (2016 TV), Netflix/US | Authorized search → detail → sources; source/canonical IDs, year/type, provider ID, regional offer and URL; empty result remains a documented gap |
| V2 | *Palm Springs* (2020 movie) and *Only Murders in the Building* (2021 TV), Hulu/US | Same chain; separate direct Hulu from bundles/add-ons; validate a selected season/episode rather than extrapolating series coverage |
| V3 | *Dune* (2021 movie) and *The Last of Us* (2023 TV), HBO Max/US | Same chain; verify current service aliases and edition/season scope; no assumption that ownership or branding implies availability |
| V4 | *Dune* (1984 versus 2021), all three services/US | Distinguish remakes and cross-source movie IDs; test missing mapping, alternate edition, duplicate-save risk with SUR-36 |
| V5 | A title returned with rent/buy/free/tve by the authorized source; select and record IDs during audit | Preserve each distinct offer and price unknown; confirm out-of-scope offers are excluded rather than relabeled subscription-included |
| V6 | One matched title in US versus GB, plus unknown country, missing English details, null fields, and partial TV availability | No region leakage or translation/audio assumption; GB is a negative scope test, not launch expansion |
| V7 | Successful empty response, missing ID/404, expired observation, 401/403, quota/429, timeout, and invalid destination | Separate no-offer, unsupported, stale, and error states; no false entitlement; saved entries survive. Inject failure fixtures only after schema/fixture use is authorized; label simulations separately. |

For each live row record: execution time; approved account/plan reference (no
secrets); source/API version; sanitized request parameters; permitted evidence
reference or response digest; source IDs and canonical mapping; country; offered
plan/type/scope; source/fetch timestamps; destination/platform observation; expected
versus actual result; gap classification; pass/fail; reviewer and follow-up owner.
Keep licensed raw fixtures in approved restricted storage unless redistribution is
explicitly allowed. Record empty/missing results in the denominator. V1–V7 are
minimum diagnostic cases, not a statistically sufficient coverage audit; SUR-36
must approve the larger sample and accuracy criteria before SUR-40/SUR-58 acceptance.

## Release blockers and handoff

All gates are **open**. Logan coordinates assignment of named reviewers; the issue
assignee is not automatically the legal reviewer, billing approver, or on-call owner.

| Gate | Current blocker and required closure | Reviewers / downstream owner |
| --- | --- | --- |
| G1 Launch scope | Approve or revise every matrix dimension and offer exclusion, HBO service identity, no-artwork fallback, and consistency with SUR-16; no agreed launch list exists | Product plus streaming/discovery owners; Logan coordinates |
| G2 Rights and authorized access | Record approved legal entity/account/environments, credential reference, plan/contract version, permitted display/cache/recommendation/ID-retention uses, artwork decision, attribution, and termination duties; no approval or live key test supplied | Qualified legal/licensing + security + source integration reviewers; SUR-34 |
| G3 Coverage and data contract | Execute V1–V7 and approved broader sample, capture real movie/TV/provider/region gaps, resolve plan/season/edition/language limits and whether fallback is needed | Data/integration + QA + product; SUR-36 identities, SUR-38 identifying details, SUR-40 availability, SUR-48 destinations |
| G4 Freshness and capacity | Agree numerical freshness/accuracy/performance targets, source-lag handling, effective quota, monthly cost/budget, refresh and incident ownership; measure under representative load | Engineering/operations + billing/product + QA; SUR-36/SUR-40 |
| G5 Implementation evidence | Verify attribution, rights-aware caches/purges, unknown/stale UI, no false inclusion, outage-safe saved entries, and allowed platform links against approved contracts | Engineering/security + QA/accessibility; SUR-38/SUR-40/SUR-48 |
| G6 Release decision | Collect G1–G5 evidence and named approvals for exact commit/configuration, including gap/fallback disposition; merging research does not approve launch | Product release authority + domain reviewers; SUR-58 |

Record each decision with reviewer name/role, date, document revision, evidence
reference, accepted/change-required result, and any condition with an owner. Reopen
relevant gates on terms/plan changes, provider aliases, new markets/languages,
new offer types, broader data use, or material coverage degradation.

Acceptance tracking: explicit **proposed** coverage and offer semantics recorded;
public access paths, source capabilities, rights, and gaps assessed; freshness
behavior, live validation procedure, and release blockers documented. **Agreed
scope, authorized live access, representative coverage validation, and licensing
sign-off remain outstanding. SUR-34 is not fully accepted and remains in progress.**
