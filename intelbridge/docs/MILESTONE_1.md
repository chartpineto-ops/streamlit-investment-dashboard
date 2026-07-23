# IntelBridge Milestone 1

Date: 2026-07-23

Status: implementation and automated code validation complete; database execution and browser
acceptance blocked by missing local PostgreSQL or Docker runtime.

## Repository inspection

### Current stack

The parent repository is PineTerminal. It uses:

- a Next.js 16, React 19, and TypeScript 6 frontend in `frontend/`
- a FastAPI backend in `backend/`
- SQLite for local development
- an active PineTerminal Milestone 5 browser-acceptance checkpoint
- a legacy Streamlit compatibility application

IntelBridge has different product entities, navigation, persistence requirements, and milestone
boundaries. It therefore lives in `intelbridge/` and does not replace or extend PineTerminal's
canonical investment contracts.

### Existing files and reusable components

Reusable patterns:

- App Router organization and strict TypeScript configuration
- a restrained workstation shell with dense tables and explicit state language
- server-only persistence boundaries
- canonical empty, loading, unavailable, and error states
- pnpm security overrides for the shared Next.js dependency graph

Not reused:

- PineTerminal portfolio, company, valuation, provider, and financial-data contracts
- PineTerminal navigation and dark investment-workstation tokens
- the FastAPI and SQLite domain layer, because the IntelBridge brief explicitly requires Prisma and
  PostgreSQL for this application

### Missing dependencies

The existing Next.js surface did not include Prisma, PostgreSQL schema tooling, Zod, Tailwind CSS,
Lucide icons, or Prettier. IntelBridge declares these dependencies inside its isolated package.

TanStack Query, BullMQ, Redis, OpenAI, Recharts, and Playwright are intentionally deferred until the
milestones that use them. Adding unused runtime dependencies would not complete a Milestone 1
requirement.

## Implemented folder structure

```text
intelbridge/
  docs/
  prisma/
    migrations/20260723000100_init/
    schema.prisma
    seed.ts
  src/
    app/
      [section]/
      missions/
        [missionId]/
        new/
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

The broader brief's `jobs`, `events`, `agents`, `connectors`, `security`, `reports`, `ask`, and
`workers` modules are not pre-created as empty architecture. They will be added with their first
coherent vertical slice.

## Prisma model

The normalized schema includes all core entities defined in the brief:

- `Workspace`, `User`, `Project`, and `Mission`
- `SourceConnector` and `MissionSource`
- `ResearchRun` and `RunStep`
- `SourceDocument` and `Evidence`
- `Claim`, `ClaimEvidence`, `Insight`, and `InsightClaim`
- `Monitor`, `Alert`, and `Report`

Key constraints:

- users, projects, and connectors are owned by a workspace
- mission access is scoped through the owning project's workspace
- mission/source, claim/evidence, and insight/claim joins use compound primary keys
- source-document versions are unique by connector and external identifier
- content hashes prevent duplicate source versions and duplicate evidence within a run
- run steps have a unique sequence within a run
- all parent-child delete behavior is explicit
- enums make mission, connector, run, validation, relationship, insight, monitoring, alert, and
  report states inspectable

The generated initial PostgreSQL migration contains 17 tables, 25 foreign keys, 8 unique indexes,
and 26 additional indexes.

## Seed scope

The idempotent seed creates:

- one clearly labeled demo workspace
- two users
- three projects
- six connector definitions
- three missions
- deterministic links from each mission to the available demo connector

Production connectors are seeded as `NOT_CONNECTED`; they are not presented as operational.
Research runs, documents, evidence, claims, and insights are not seeded in Milestone 1 because their
creation and validation logic belong to later milestones.

## Product behavior

Implemented:

- workspace overview from persisted counts
- mission list with project and status filters
- mission detail with objective, owner, scope, selected sources, timestamps, and record counts
- mission creation with workspace-scoped project and connector validation
- full primary navigation with explicit milestone placeholders
- visible demo source state and unavailable states
- disabled research, search, notification, and question-answering controls with reasons
- loading, not-found, and database-error states

Not implemented:

- research execution or cancellation
- live agent activity or SSE
- source retrieval
- evidence, claims, or insights
- AI model calls
- reporting or monitoring jobs

## Workspace isolation

The authentication stub resolves a user and workspace on the server. Repository mission queries
always include `project.workspaceId`. Mission creation verifies the selected project and every
connector against the same workspace before the transaction writes the mission. A unit test protects
the workspace predicate.

This is not full authentication or role-based authorization. Those remain Milestone 8 work.

## Risks

1. A PostgreSQL runtime is required. No Docker, Podman, PostgreSQL service, `pg_ctl`, or `psql`
   executable is installed in the current environment.
2. The parent repository has extensive pre-existing changes. IntelBridge is isolated so its commit
   can avoid staging those files.
3. The schema anticipates later domains, but business behavior for those domains is deliberately
   absent until its milestone.
4. The header-based user override is suitable only for development and integration tests.
5. Browser and screenshot acceptance cannot begin until the database migration and seed run against
   PostgreSQL.

## Validation record

Passed:

- Prisma schema format and validation
- Prisma Client generation
- generated PostgreSQL migration review
- Prettier
- ESLint
- TypeScript
- 6 Vitest tests across environment, mission-input, and workspace-scope behavior
- Next.js production build
- production dependency audit with no known vulnerabilities

Blocked:

- `prisma migrate deploy`: no PostgreSQL server is listening at the documented local endpoint
- `prisma db seed`: requires the migrated PostgreSQL database
- HTTP smoke, browser workflow, and visual screenshots: pages intentionally require persisted data
  and do not use a hard-coded fallback

Milestone 1 must remain open until the blocked checks pass.

## Next acceptance checkpoint

On a machine with Docker or PostgreSQL:

```powershell
docker compose up -d postgres
pnpm db:migrate
pnpm db:seed
pnpm dev
```

Then verify:

1. the workspace overview renders database counts
2. mission list filtering remains workspace-scoped
3. all three seeded mission details render
4. creating a mission writes and redirects to its detail page
5. a user from another workspace cannot read or select the first workspace's project, connector, or
   mission
6. desktop and narrow layouts pass keyboard, overflow, and screenshot review

Do not begin Milestone 2 before these checks pass.
