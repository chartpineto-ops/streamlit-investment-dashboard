# IntelBridge

IntelBridge is an evidence-first research mission platform. It runs on the Sites worker runtime,
stores structured product state in Cloudflare D1, and uses the authenticated Sites user header for
workspace identity.

The current Milestone 1 application provides:

- a Next.js App Router interface compiled with Vinext for Cloudflare Workers
- a normalized Drizzle schema and generated D1 migration
- idempotent database initialization and deterministic demo records
- workspace-scoped user, project, connector, and mission queries
- a functional mission creation flow
- mission filtering and mission detail pages
- explicit unavailable states for research execution, evidence, insights, and monitoring
- loading, empty, not-found, and database-error states

Research execution, SSE, BullMQ, source retrieval, evidence extraction, model calls, reports, and
monitoring jobs remain later milestones.

The production Sites release is owner-only by default. Hosted requests use the authenticated Sites
user identity; the local demo identity fallback is disabled outside development.

## Local development

Prerequisites:

- Node.js 22.13 or newer
- pnpm 11

```powershell
pnpm install
pnpm db:generate
pnpm dev
```

The development server provides a local D1 binding through Miniflare. The first request creates the
Milestone 1 tables and idempotently seeds one workspace, two users, three projects, six connector
definitions, and three missions.

## Validation

```powershell
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm audit --prod
```

## Architecture

```text
intelbridge/
  .openai/hosting.json
  build/sites-vite-plugin.ts
  drizzle/
  src/
    app/
    components/
    server/
      auth/
      db/
      repositories/
      services/
    shared/
  worker/index.ts
  drizzle.config.ts
  vite.config.ts
```

Route components depend on application services. Services resolve the authenticated workspace and
call repositories. Repositories are the only UI-facing layer that reads or writes D1. Every mission
lookup is constrained through the owning project's `workspace_id`.

See [docs/MILESTONE_1.md](docs/MILESTONE_1.md) for the deployment architecture decision and
validation record.
