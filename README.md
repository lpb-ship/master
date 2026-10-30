# Seent It foundation

Foundation contracts and database baseline for the mobile-friendly web application.

- [Account lifecycle and shared profile contracts](docs/account-profile-contracts.md): proposed account flows, identity and profile boundaries, navigation, acceptance scenarios, and outstanding decisions.
- [Quality gates and data handling](docs/quality-gates-and-data-handling.md): proposed performance, support, accessibility, operations, and data-lifecycle requirements with approval gates.

- [Account/profile database baseline](docs/database-baseline.md): SQL migrations, access boundaries, local verification, secure connections, and backup/recovery responsibilities.

The database baseline is a non-production implementation of proposed contracts. Provider finalization and stakeholder approval remain deployment gates. Run `python3 tests/database/verify.py` to verify it with disposable PostgreSQL and synthetic data.
