# Seent It foundation

Foundation contracts and database baseline for the mobile-friendly web application.

- [Account lifecycle and shared profile contracts](docs/account-profile-contracts.md): proposed account flows, identity and profile boundaries, navigation, acceptance scenarios, and outstanding decisions.
- [Foundation provider and architecture decision](docs/architecture/0001-foundation.md): selected baseline, provider limits, capacity/cost assumptions, and finalization gates.
- [Quality gates and data handling](docs/quality-gates-and-data-handling.md): proposed performance, support, accessibility, operations, and data-lifecycle requirements with approval gates.
- [Account/profile database baseline](docs/database-baseline.md): SQL migrations, access boundaries, local verification, secure connections, and backup/recovery responsibilities.
- [Private watchlist persistence](docs/watchlist-persistence.md): authenticated save/list/remove SQL API, canonical uniqueness, retained snapshots, and integration boundaries.
- [Whole-product launch acceptance](docs/launch-acceptance-matrix.md): journey traceability, reusable evidence, test setup, and unresolved release sign-off gates.
- [Foundation release evidence and downstream handoff](docs/foundation-release-handoff.md): blocked-readiness assessment, evidence and documentation inventory, follow-up owners, and downstream acceptance gates.

The database baseline is a non-production implementation of proposed contracts. Provider finalization and stakeholder approval remain deployment gates. Run `python3 tests/database/verify.py` to verify it with disposable PostgreSQL and synthetic data.
