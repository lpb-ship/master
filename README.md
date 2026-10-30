# Seent It foundation

Next.js infrastructure baseline for the mobile-friendly web application. It exposes
`/api/health` (process health) and `/api/ready` (database connectivity); feature UI,
authentication, and account/profile schemas are separate work.

## Local setup

Install [mise](https://mise.jdx.dev/getting-started.html) and Docker with Compose v2.
From a fresh checkout:

```sh
mise install
mise exec -- npm ci
cp .env.example .env.local
docker compose up -d --wait
mise exec -- npm run check:config
mise exec -- npm run check:db
mise exec -- npm run dev
```

In another terminal, `curl --fail http://127.0.0.1:3000/api/ready` returns
`{"status":"ready"}`. The root URL has no feature page yet. The disposable local
PostgreSQL database is bound to loopback with a public development-only password;
it contains no application schema or Supabase Auth service. SUR-8 owns migration
setup and alignment with the full Supabase local stack when those features land.

Run checks and the production server:

```sh
mise exec -- npm test
mise exec -- npm run build
mise exec -- npm run typecheck
mise exec -- npm start
```

Stop the development server before starting the production server on the same port.
`docker compose down` preserves local data. Only for a disposable local reset,
`docker compose down --volumes` deletes it. Never use the sample credentials remotely.

## Contracts and operations

- [Development and deployment runbook](docs/development-deployment.md): configuration,
  secret handling, environment ownership, staging delivery, rollback, and evidence gaps.
- [Account lifecycle and shared profile contracts](docs/account-profile-contracts.md):
  proposed flows, identity/profile boundaries, navigation, and outstanding decisions.
- [Provider architecture proposal](https://github.com/lpb-ship/master/blob/9e166fdd0f7340d1495f42eac0e5d9b698874ef4/docs/architecture/0001-foundation.md):
  Next.js/Vercel and Supabase direction from SUR-4, pending finalization.

No cloud resources are provisioned by local setup. Remote deployment needs the
approved environment inventory and secrets described in the runbook. Production
readiness and live staging deployment are not established by this scaffold.
