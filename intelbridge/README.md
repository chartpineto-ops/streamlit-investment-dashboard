# IntelBridge

IntelBridge is an evidence-first research mission platform. This directory is an isolated
application inside the existing repository so it does not change PineTerminal's active milestone,
contracts, or dirty worktree.

Milestone 1 provides:

- Next.js App Router, TypeScript, Tailwind CSS, and accessible semantic controls
- a normalized Prisma schema targeting PostgreSQL
- a Docker Compose definition for local PostgreSQL
- strict server environment validation with Zod
- a workspace-scoped authentication stub
- deterministic seed records for one workspace, two users, three projects, six connector
  definitions, and three missions
- a persisted workspace overview, mission registry, mission detail page, and mission creation flow
- explicit empty and unavailable states for research-run features scheduled for later milestones

Research execution, SSE, BullMQ, Redis, ingestion connectors, evidence extraction, OpenAI calls,
reports, and monitoring jobs are intentionally not implemented in Milestone 1.

## Local setup

Prerequisites:

- Node.js 24 or a compatible supported release
- pnpm 11
- Docker with Compose, or PostgreSQL 17 reachable through `DATABASE_URL`

Copy `.env.example` to `.env` and replace the local database password in both the PostgreSQL and
connection-string values.

```powershell
docker compose up -d postgres
pnpm install
pnpm db:generate
pnpm db:migrate
pnpm db:seed
pnpm dev
```

Open `http://localhost:3000`.

The demo user is selected by `INTELBRIDGE_DEMO_USER_EMAIL`. A request may also supply
`x-intelbridge-user-email` during local integration testing. This is an authentication stub, not a
production identity system.

## Validation

```powershell
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm db:validate
pnpm db:migrate
pnpm db:seed
```

The application never falls back to hard-coded mission rows when PostgreSQL is unavailable. It
renders a structured database error state instead.

## Architecture

```text
intelbridge/
  prisma/
    migrations/
    schema.prisma
    seed.ts
  src/
    app/
      missions/
      [section]/
    components/
    server/
      auth/
      db/
      repositories/
      services/
    shared/
      schemas/
  docker-compose.yml
  prisma.config.ts
```

Route components depend on the service layer. Services resolve the authenticated workspace and call
repositories. Repositories are the only UI-facing layer that queries Prisma. Every mission lookup
is constrained through its parent project's `workspaceId`.

See [docs/MILESTONE_1.md](docs/MILESTONE_1.md) for the inspection findings, decisions, validation
record, and current acceptance status.
