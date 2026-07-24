# IntelBridge

IntelBridge is a persistent, workspace-scoped research operations platform.
This release implements Milestones 1–3: foundation, the durable research-run
engine, and governed connectors with versioned document ingestion.

Active product areas:

- Home
- Missions
- Sources
- Runs
- Documents
- Projects
- Settings
- workspace search and operational diagnostics

Evidence extraction, claims, AI synthesis, monitoring alerts, and report
generation are intentionally outside this release.

## Runtime

The hosted application uses Vinext, React, TypeScript, Cloudflare Workers, D1,
R2, Drizzle, Zod, and Vitest. Sites supplies authenticated-user headers and
keeps the production deployment owner-only.

D1 and R2 are the repository-equivalent persistence services for the Sites
runtime. The durable `job_queue`, `run_steps`, and `run_events` tables replace
the PostgreSQL/Redis/BullMQ proposal without introducing in-memory state.

## Local development

Use Node.js 22.13 or newer and pnpm 11:

```powershell
pnpm install
pnpm dev
```

The Cloudflare development runtime provides local D1 and R2 bindings from
`vite.config.ts`. Do not commit `.env` files or credentials.

Optional server environment:

```text
INTELBRIDGE_DEMO_USER_EMAIL=alex.parker@intelbridge.demo
GITHUB_TOKEN=optional_server_only_token_for_higher_github_api_limits
```

Production secrets must be configured through Sites environment variables.

## Validation

```powershell
pnpm db:generate
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Frontend validation uses Playwright through the connected in-app browser at
desktop and mobile viewport widths.

## Data states

The deterministic fixture corpus uses fictional sources and always stores
`status=demo` with `is_demo=true`. Live connector records retain source,
retrieval timestamp, MIME type, content hash, current version, change state,
and raw-object reference where applicable. Unavailable values are never
converted to zero.

## Documentation

- [Milestones 1–3 architecture and operations](docs/MILESTONES_1_3.md)
- [Milestone 1 historical checkpoint](docs/MILESTONE_1.md)
