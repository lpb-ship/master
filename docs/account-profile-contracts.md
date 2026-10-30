# Account lifecycle and shared profile integration contracts

Status: **proposed v0.1 — stakeholder sign-off pending**. Updated: 2026-10-30.
Accountable coordinator: **Logan Barragan**, current foundation issue assignee and initiative owner.
Source: [SUR-5](https://linear.app/lb-sandbox/issue/SUR-5).

## Purpose and decision status

Define the interfaces needed by account access, profile storage, the navigation shell, streaming, privacy, social, and discovery before implementation. This document does not select vendors or implement accounts, profiles, schemas, or dependent features. Operation and route names below are proposed application contracts, not existing endpoints or provider APIs.

The [foundation PRD](https://linear.app/lb-sandbox/project/app-foundation-and-mobile-web-experience-7af8e664b8d0) requires account creation, sign-in/out, persistent own-profile editing, and authorization at the data boundary. The [initiative](https://linear.app/lb-sandbox/initiative/seent-it-a-social-networking-streaming-app-25758940b77b) requires private activity by default and explicit sharing. These are source requirements; all specific methods, fields, route names, and numerical limits below are proposed decisions awaiting approval.

The proposal is internally normative: “must” describes the behavior to implement **after approval**, not a claim that a stakeholder or provider has accepted it. Open decisions D1–D8 and their implementation gates appear below. Do not silently substitute provider defaults or treat missing review as acceptance.

## Account lifecycle

### Methods, verification, and recovery

- First-release proposal: provider-managed **email and password**, verified email required for application access. Provider selection in [SUR-4](https://linear.app/lb-sandbox/issue/SUR-4) must validate this choice against D1. Do not build a custom credential store. Social login, phone login, passkeys, and MFA are outside this baseline until explicitly added to D1.
- Validate email syntax and the provider's documented size limits. Use the provider's canonical email handling; do not invent case folding or alias collapsing. Email is a credential/contact address, never a stable user key or a profile field.
- Proposed password policy: 15–128 Unicode characters, no arbitrary composition rules, support paste/password managers, and provider-supported compromised-password checks. Never trim or silently truncate passwords. The provider must support the approved policy; deviations require D1 review.
- Sign-up and verification/resend responses must avoid disclosing whether an address already exists. Rate-limit by account and request source without exposing account existence; provider thresholds and abuse controls are a D1 output. Credentials, link tokens, and full email addresses must not appear in application logs or analytics.
- Verification and recovery links must be provider-issued, single-use, time-limited, and bound to their intended operation. Proposed maximum lifetimes: verification 24 hours; password reset 30 minutes. A scanner or link preview must not consume a token or perform a mutation on a GET request. Exchange/confirm through the provider's supported flow, then remove secrets from the URL and prevent referrer leakage.
- Recovery request always returns a neutral acknowledgement. Invalid, used, or expired links offer a new request. A successful reset revokes all prior application sessions and requires a fresh sign-in; it does not bypass email verification. No security questions, manual email-only identity matching, or support bypass of identity proof.
- Email changes require recent authentication and verification of the new address; retain the old sign-in address until completion, notify the old address, and revoke prior sessions at completion. Password changes also require recent authentication and revoke other sessions. These are account operations, never profile edits. If no safe provider-supported flow exists, defer these controls explicitly through D1 rather than implementing an unsafe workaround.

### States and transitions

Account state, profile readiness, and session state are separate. An expired session does not delete the account; a failed profile load does not make a user anonymous.

| State | Permitted behavior | Transition |
| --- | --- | --- |
| Anonymous | Public shell, sign-up/in, verification and recovery entry points | Successful authentication yields a verified or unverified principal |
| Authenticated, unverified | Verification/resend, recovery, sign-out only; no feature/profile access | Verified provider claim enables application identity provisioning |
| Verified, provisioning | Retryable account setup screen; no feature mutations | Idempotent account/profile creation succeeds, or remains retryable |
| Active, profile incomplete | Own-profile completion, account controls, sign-out | Valid display name saved; then intended permitted destination |
| Active, profile complete | Own-profile access and authorized feature entry points | Sign-out/expiry removes session; restriction/deletion removes access |
| Restricted or deletion pending | Safe unavailable/support state and sign-out; deny feature access | Only authorized lifecycle handling can change status |
| Deleted | No usable identity mapping, session, or profile access | A later verified registration creates a new application identity, never revives old grants |

Provision only after verification. The first verified sign-in must atomically create an account, its identity mapping, and a profile shell, or retry without duplicates. The shell has no display name and is incomplete; do not infer a name from the email address. A database outage must not report successful setup or create a second account on retry. Recovery and provider webhooks must not independently create profiles.

Deletion and restriction states are integration requirements, not a request to implement a deletion product in this issue. D5 must settle retention, deletion propagation, and recovery rules before production use; retain a denied mapping tombstone only if the approved policy permits it and it is necessary to prevent reprovisioning during deletion. Deny provisioning while deletion is pending.

### Sessions

Proposed session limits, to approve under D2:

| Setting | Proposed contract |
| --- | --- |
| Persistence | Same-browser session survives reload and browser restart within its limits; no separate “remember me” mode |
| Idle timeout | 24 hours since the last authenticated user action; background polling does not extend it |
| Absolute lifetime | 7 days after authentication, even with activity or refresh |
| Recent authentication | At most 5 minutes old for credential changes, identity linking, or deletion confirmation |
| Refresh | Server-controlled rotation, bounded by both deadlines; replay revokes the affected session |
| Revocation | Next protected server request rejects a revoked session; no grace period for protected writes |

Use a server-validated session with Secure, HttpOnly cookies, an explicitly selected SameSite policy compatible with provider callbacks, and CSRF protection on mutations. No browser local-storage bearer tokens. Keep provider refresh credentials server-side. Cookie policy and deployment origins are SUR-4 outputs.

The server is authoritative on expiry and revocation. Serialize concurrent refreshes per session so tabs do not trigger false replay failures. App authorization must be able to reject a session immediately even when a provider access token has not expired; verify that capability during selection. If the provider cannot meet it, change the architecture or obtain an explicit D2 decision.

Sign-out is an idempotent mutation: revoke the current app session, expire its cookie, clear identity-scoped client state, and notify other tabs. “Sign out all sessions” revokes every session for the app user. Closing a tab is not sign-out. Neither action disconnects streaming services. After sign-out, browser Back must revalidate protected pages and must not reveal cached personal data. Use private/no-store responses for session and private profile data.

If sign-out cannot reach the server, hide protected local content and report that server sign-out is unconfirmed; retry revocation when connectivity returns. Never claim server revocation succeeded offline. During an auth/provider outage, fail protected authorization closed with a retryable unavailable state rather than treating the user as permanently signed out or repeatedly redirecting to login.

## Identity and profile boundaries

### Identity mapping

- Foundation owns an opaque, immutable `appUserId`, generated independently of any auth vendor. Downstream records reference this ID, never an email, display name, provider subject alone, or streaming account identifier.
- Map the trusted `(issuer, subject)` pair to exactly one application user; enforce uniqueness. Isolate environments/tenants in the issuer namespace or mapping key. Derive this pair only from a provider response/session validated for issuer, audience, signature, expiry, and applicable callback protections (state, nonce, PKCE).
- One application user has exactly one own-profile record keyed by `appUserId`. Multiple linked auth identities may map to that same user only through an approved, recently authenticated linking flow with proof of both identities. Linking is deferred under D1. Never automatically merge accounts with matching email addresses.
- Streaming provider identities and tokens belong to the streaming project's connection model, keyed by `appUserId`; connecting a service neither signs into the app nor grants profile/activity visibility. Provider migrations must preserve `appUserId` through a reviewed mapping migration rather than matching emails.
- Clients never choose their acting user ID. Authenticated server context supplies the actor; feature ownership and viewer permissions are checked on every data operation.

### Minimum profile and visibility

Minimum user-entered field: **display name**. No handle, avatar, bio, date of birth, location, gender, phone, streaming credentials, subscriptions, watch history, social graph, or consent flags are collected in the foundation profile. New fields require an explicit purpose, validation, visibility, and retention decision before addition.

| Field | Type and validation | Visibility and editability |
| --- | --- | --- |
| `appUserId` | Opaque application ID; immutable and unique | Owner and authorized services; not a credential or permission grant |
| `displayName` | Null only in the provisioning shell; required for completion; Unicode NFC, trim surrounding whitespace, 1–80 Unicode code points after normalization, no control characters; not unique | Owner only initially; owner editable; render as plain text, never trusted HTML |
| `version` | Server-managed monotonic integer, incremented on each successful update | Owner response; concurrency control, never client assignable |
| `createdAt`, `updatedAt` | Server-generated UTC timestamps | Owner and authorized operations only; never client assignable |

Profile completeness is derived from the display-name rule; do not maintain a conflicting client-controlled flag. Validate on the server before persistence; client validation mirrors those rules for feedback. Reject unknown or server-owned fields. Email/password edits must not be accepted by the profile write interface. Schema/storage limits must preserve the Unicode rule without byte truncation.

Baseline visibility is owner-only, including display name. The foundation provides no public profile directory or other-user profile endpoint. Knowledge of `appUserId`, an authenticated session, following a user, or connecting a streaming account does not grant profile access. D3 must approve a distinct viewer-authorized projection before social profile visits or friend search ship; do not make the private own-profile response public later.

Activity sharing and profile visibility are separate permissions. Future projections may contain only approved fields for the specific viewer. Privacy policy must apply at query time, including feeds, search, recommendations, caches, and derived data; a hidden title must not leak through recommendation explanations. Until that policy exists, cross-user reads are denied. No blanket `isPublic` profile flag may authorize access to viewing history.

### Logical operations and failures

These are language/transport-neutral contracts. SUR-4 chooses the transport; these meanings must survive SDK or endpoint adapters.

| Operation | Input and authorization | Result |
| --- | --- | --- |
| `resolveSession()` | Trusted server request/session; no client actor ID | `anonymous`, `verificationRequired`, `provisioning`, `active`, or `restricted`; active server context includes `appUserId`, session deadlines, recent-auth time, and profile completeness; clients receive only necessary fields |
| `readOwnProfile()` | Verified active actor (incomplete profiles allowed) | Exact owner projection listed above; incomplete shell is explicit |
| `updateOwnProfile()` | Verified active actor; `{displayName, expectedVersion}` | Atomically validated and persisted full owner projection with new version; no partial success |
| `signOut(scope)` | Valid session and CSRF protection; scope is `current` or `all` | Idempotent revoked outcome; already-expired session is safely signed out |
| Future `readVisibleProfile(target, viewer)` | Server-derived viewer plus privacy policy; **not available in foundation** | Allowlisted projection or indistinguishable unavailable result; never raw owner profile |

Update comparison and write occur atomically. A stale `expectedVersion` returns `CONFLICT`; preserve unsaved text and offer reload/review, never silently overwrite another tab's edit. An ambiguous network failure after save requires re-reading the profile/version before retrying or showing success. Other write failures retain the edit while the session remains valid; logout/expiry clears identity-scoped drafts and prevents another account seeing them.

| Error code | Meaning and caller behavior | HTTP equivalent if HTTP is chosen |
| --- | --- | --- |
| `UNAUTHENTICATED` | Absent, expired, or revoked session; clear protected state and offer sign-in | 401 |
| `VERIFICATION_REQUIRED` / `PROFILE_INCOMPLETE` | Guide to verification/completion without replaying the original mutation | 403 |
| `FORBIDDEN` | Denied operation on an otherwise visible resource; do not retry as a different actor | 403 |
| `NOT_FOUND` | Missing or inaccessible target; do not distinguish another user's private record from absence | 404 |
| `VALIDATION_FAILED` | Safe field errors; preserve input except secrets | 422 |
| `CONFLICT` | Version mismatch; reload/review needed | 409 |
| `RATE_LIMITED` | Explain cooldown; use a bounded retry-after signal | 429 |
| `UNAVAILABLE` | Provider/database/network failure; safe retry, no false success | 503 |

An unavailable authorization check must not return `anonymous`. Error payloads may contain a stable code, safe message, field errors, retry timing, and opaque correlation ID; never raw provider errors, tokens, personal data, or existence signals. Only explicitly authorized services can access identity mappings; downstream service access is purpose-scoped and must not bypass viewer/ownership policy. Clear client query caches on account switches and never reuse another actor's cached projection.

## Navigation and protected routes

Route names are proposed shell contracts for [SUR-11](https://linear.app/lb-sandbox/issue/SUR-11). Desktop and mobile expose the same destinations and authorization behavior.

| Destination | Access and entry point |
| --- | --- |
| `/` | Public landing page; signed-out navigation offers Create account and Sign in; signed-in navigation offers Home, My profile, Account, and Sign out |
| `/sign-up`, `/sign-in` | Anonymous forms; active users go to their permitted destination without an auth loop |
| `/verify-email`, `/recover`, `/reset-password`, `/auth/callback` | Operation-specific entry points; validate tokens/state before transitions; unverified users remain on verification |
| `/app` | Verified, complete profile; application home with honest dependent-feature placeholders |
| `/profile`, `/profile/edit` | Verified owner, including incomplete profile; View/Edit/Save/Cancel; completion returns to a safe intended destination |
| `/account` | Verified active account, including incomplete profile; account controls and session actions; changes requiring recent auth prompt reauthentication |
| `/connections`, `/privacy`, `/friends`, `/discover`, `/watchlist` | Reserved verified, complete-profile destinations for downstream projects; label placeholders “Not available yet”; no connect, sharing, follow, recommendation, or save actions until delivered |

On a protected direct link or refresh, resolve server session before rendering personal data. While resolving, show a non-personal loading state. Anonymous users go to sign-in; unverified users to verification; provisioning failures to retryable setup; incomplete profiles to editing; restricted accounts to a safe unavailable state. API calls return structured errors, not login HTML. Every backend operation rechecks authorization independently of route guards.

Keep an intended destination only if it matches an allowlisted local application route. Reject external URLs, protocol-relative URLs, encoded bypasses, auth callback/reset routes, and unexpected query values. Default to `/app`. After sign-in, verification, and completion, recheck route permission and availability. Never automatically replay a pending write, connection authorization, or sharing action; ask the user to perform it again. Cancel returns to a safe prior route or landing page without making a mutation.

An expired session during editing stops the save, clears protected data, explains the expiry, and offers sign-in; do not imply the edit persisted. Form validation and failure messages are associated with labelled fields, announced accessibly, and preserve keyboard focus appropriately. Navigation changes announce their destination and move focus predictably; menus and Sign out remain keyboard reachable. Final device/browser and accessibility gates are owned by [SUR-6](https://linear.app/lb-sandbox/issue/SUR-6).

## Acceptance scenarios for implementation

These are reviewable test requirements, **not executed application tests**. SUR-9 owns account cases, SUR-10 profile cases, SUR-11 navigation cases; SUR-12/SUR-14 integrate device, accessibility, and security verification.

| ID | Scenario | Required result |
| --- | --- | --- |
| A1 | New user registers, verifies, completes profile, reloads, signs out and back in | One mapping/profile; name persists; correct permitted destination; no duplicate setup |
| A2 | Malformed input, rejected credentials, duplicate registration, resend/recovery for known and unknown emails | Safe validation or neutral response; no account enumeration; secrets not logged |
| A3 | Unverified user follows a feature link or directly calls its API | Verification guidance in UI; server denies data and mutations |
| A4 | Used, expired, malformed, or wrong-operation verification/reset token; callback state mismatch | No account mutation or access; safe restart; valid reset revokes all old sessions |
| A5 | Browser restart, active use, background polling, idle and absolute expiry, concurrent tab refresh | Persistence only within approved deadlines; no polling extension, refresh race, or indefinite renewal |
| A6 | Sign-out/current vs all sessions; browser Back; another tab or device; revocation failure offline | Scope enforced on next server request, local data cleared, no cache leak; failure is explicit |
| A7 | Auth/database outage during sign-in or simultaneous first-login provisioning | Retryable unavailable state; no false anonymous state, duplicate records, or partial success |
| A8 | Account A tries to read/write B by forging IDs, changing payload fields, or calling data APIs directly | Server rejects; no existence signal, private fields, or mutation; permitted own-profile calls succeed |
| A9 | Empty/over-limit/control-character name, Unicode normalization, HTML-like name, unknown fields | Shared validation enforced; valid Unicode persists; output rendered as text; server fields immutable |
| A10 | Two tabs save the same version; database failure or dropped response during save | One atomic winning update; conflict or reconciliation for other tab; no false saved state |
| A11 | Protected deep link, hostile return URL, incomplete profile, canceled sign-in, expired session during edit | Safe navigation, no redirect loop/open redirect, no unauthorized replay or cached draft disclosure |
| A12 | Same email at two issuers, repeated provider callback, account switch, attempted automatic linking | Stable IDs and unique mappings; no email-based merge; caches isolated; linking rejected while deferred |
| A13 | Streaming connected/disconnected, friendship followed, profile viewed, discovery recommendation requested | None implicitly grants sharing; private activity/profile denied, including through caches and derived output |
| A14 | Restricted/deletion-pending user presents an unexpired token; deleted identity attempts reprovisioning | Access revoked; pending deletion cannot recreate account; final deletion/new registration follows approved D5 policy |
| A15 | Keyboard/mobile traversal, validation failures, pending saves, dependent-feature placeholders | Operable labelled controls, visible focus, announced feedback; placeholders make no availability claims |

## Cross-project review and unresolved decisions

Reviewed source requirements on 2026-10-30: foundation PRD, SUR-4/6/8/9/10/11, initiative, and the four project descriptions linked below. No existing contracts, reviewer approvals, project leads, or project members were recorded in those sources. This is a **requirements compatibility review**, not completed review with stakeholders. All stakeholder acknowledgements remain pending; SUR-5 must not be marked fully accepted until they are recorded.

Logan Barragan is the interim accountable coordination owner for every open decision below, based on his issue assignment and initiative ownership. This assigns follow-up responsibility, not unrecorded subject-matter approval. He must nominate a reviewer for each domain (or explicitly accept that review role) and record their response and evidence here. No reviews have been requested or acknowledgements inferred by this document.

| Stakeholder and source | Identity/data/profile/navigation contract to review | Compatibility finding and open question | Review status / coordinator |
| --- | --- | --- | --- |
| [Streaming](https://linear.app/lb-sandbox/project/streaming-connections-and-viewing-activity-sync-3d5b951b37ac) | `appUserId` ownership; separate connection credentials; private imports; `/connections` | Fits private imports; confirm disconnect/revocation/deletion propagation and authorized provider access; no assumption of verified integrations | Pending / Logan Barragan |
| [Privacy](https://linear.app/lb-sandbox/project/private-by-default-activity-and-sharing-controls-6344f4be29d6) | Separate profile/activity permissions; query-time enforcement; `/privacy` | Fits explicit sharing; settle profile audiences, policy authority, revocation/cache handling, retention/deletion | Pending / Logan Barragan |
| [Social](https://linear.app/lb-sandbox/project/friends-and-shared-viewing-feed-14fb20538100) | Stable user references; future viewer projection; no email search; `/friends` | Own-profile baseline intentionally does not yet satisfy friend finding/profile visits; agree discoverability, fields, and viewer grants before social implementation | Pending / Logan Barragan |
| [Discovery](https://linear.app/lb-sandbox/project/title-discovery-and-cross-service-watchlists-4e4d14caa6e0) | User-scoped subscriptions/watchlists; authorized recommendation inputs; `/discover`, `/watchlist` | Fits visibility requirement; confirm whether anonymous catalog browsing is needed and how revoked sharing invalidates derived recommendations | Pending / Logan Barragan |

| Decision | Proposed position / unresolved question | Accountable owner and required review | Gate / tracking |
| --- | --- | --- | --- |
| D1 Authentication capability | Approve email/password, verification, recovery/link lifetimes, credential-change behavior, password/abuse policy, and deferred methods; demonstrate provider support | Logan Barragan; provider/security reviewer to nominate | Before provider selection and SUR-9 implementation; [SUR-4](https://linear.app/lb-sandbox/issue/SUR-4) |
| D2 Session policy | Approve 24-hour idle, 7-day absolute, 5-minute recent auth, cookie strategy and immediate app revocation | Logan Barragan; provider/security reviewer to nominate | Before SUR-9 implementation; [SUR-4](https://linear.app/lb-sandbox/issue/SUR-4), [SUR-6](https://linear.app/lb-sandbox/issue/SUR-6) |
| D3 Profile surface | Approve minimum fields/validation and owner-only baseline; decide future searchable identifier, audience, projection, and consent separately | Logan Barragan; privacy and social reviewers to nominate | Baseline before [SUR-8](https://linear.app/lb-sandbox/issue/SUR-8)/[SUR-10](https://linear.app/lb-sandbox/issue/SUR-10); cross-user projection before social release |
| D4 Shared authorization | Confirm policy authority, service scopes, viewer context, cache invalidation and derived-data revocation; deny until decided | Logan Barragan; privacy, streaming, social, discovery reviewers to nominate | Before cross-user data integration; [SUR-5](https://linear.app/lb-sandbox/issue/SUR-5) |
| D5 Data lifecycle | Decide processors/storage locations, jurisdictions, residency, retention, deletion/backup deadlines, consent and propagation to connected services | Logan Barragan; privacy/operations reviewers to nominate | Storage-affecting choices before schema; complete policy before production; [SUR-6](https://linear.app/lb-sandbox/issue/SUR-6) |
| D6 Navigation | Approve paths, completion gate, placeholders, and whether discovery needs a public catalog route | Logan Barragan; shell and all downstream reviewers to nominate | Before dependent route integration; [SUR-11](https://linear.app/lb-sandbox/issue/SUR-11) |
| D7 Stakeholder acceptance | Name reviewers and obtain identity, data-access, profile and navigation responses for all four domains | Logan Barragan | Before closing SUR-5 and foundation handoff; [SUR-15](https://linear.app/lb-sandbox/issue/SUR-15) |
| D8 Provider identity mapping | Confirm trusted issuer/tenant namespace, provisioning transaction, callback replay handling and future migration strategy | Logan Barragan; provider/data reviewer to nominate | Before schema/provider adapters; [SUR-4](https://linear.app/lb-sandbox/issue/SUR-4), [SUR-8](https://linear.app/lb-sandbox/issue/SUR-8) |

For each review, record reviewer name/domain, date, document revision, accepted or change-required outcome, affected decisions, and a link to the actual review. A change-required outcome needs an owner and gate before downstream work proceeds. Update this document and the linked implementation issue when resolving a decision; do not resolve it only in private discussion. Breaking identity, visibility, operation, or route changes require affected consumers to re-review and agree migration/versioning before adoption.

SUR-5 acceptance tracking: account flows and scenarios documented; minimum profile and identity mapping documented; cross-project compatibility assessed from available requirements; **stakeholder review remains open under D7**, with D1–D8 explicitly owned. No implementation or production readiness is claimed.
