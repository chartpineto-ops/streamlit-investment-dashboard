# IntelBridge Milestone 1

Date: 2026-07-23

Status: complete; the owner-only production release is managed through Sites.

## Runtime decision

The initial implementation targeted a local PostgreSQL and Prisma runtime. That version built
successfully but could not run or publish because the workspace had no PostgreSQL or container
runtime, and Sites does not provision PostgreSQL.

IntelBridge now uses the supported Sites architecture:

- Vinext compiles the Next.js App Router application for Cloudflare Workers.
- Cloudflare D1 stores durable structured state.
- Drizzle defines the relational schema and generates reviewed migrations.
- The Sites authenticated-user header identifies the current user.
- New authenticated users are provisioned into the demo workspace with the `ANALYST` role.
- Repository queries retain server-side workspace constraints.

This replaces the blocked local persistence path rather than introducing a browser-storage or
in-memory fallback.

## Implemented structure

```text
intelbridge/
  .openai/hosting.json
  build/
  drizzle/
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
  worker/
  drizzle.config.ts
  vite.config.ts
```

## Persistent model

Milestone 1 creates:

- `workspaces`
- `users`
- `projects`
- `source_connectors`
- `missions`
- `mission_sources`

The schema includes primary keys, foreign keys, compound uniqueness constraints, workspace/status
indexes, mission ownership, and cascading behavior. Run, document, evidence, claim, insight,
monitoring, alert, and report tables will be added with the milestone that implements their business
logic.

Database initialization executes one statement per prepared query. Seed writes use
`INSERT OR IGNORE`, making cold-start initialization safe to retry.

## Seed scope

The deterministic seed creates:

- one clearly labeled demo workspace
- two users
- three projects
- six connector definitions
- three missions
- a demo connector link for each mission

Production connectors remain `NOT_CONNECTED`; they are not presented as operational.

## Product behavior

Implemented:

- persistent workspace overview
- mission list with project and status filters
- mission detail with objective, owner, scope, selected sources, timestamps, and record counts
- mission creation with workspace-scoped project and connector validation
- authenticated user provisioning
- stable primary navigation with explicit milestone placeholders
- disabled research, search, notification, and question-answering controls with reasons
- loading, empty, not-found, and D1 error states

Not implemented:

- research execution or cancellation
- live agent activity or SSE
- source retrieval
- evidence, claims, or insights
- AI model calls
- reporting or monitoring jobs

## Workspace isolation

The server resolves the Sites authenticated-user email, loads or provisions that user, and carries
the workspace identifier into every repository call. Mission reads join through
`projects.workspace_id`. Mission writes validate the project and every connector against the same
workspace before a single D1 batch writes the mission and source links.

The header-based local identity fallback remains development-only. Hosted access is controlled by
the Sites access policy.

## Validation requirements

- Drizzle migration generation
- formatting
- ESLint
- TypeScript
- unit tests for environment, mission input, and workspace scope
- worker-compatible production build
- local HTTP and browser verification
- production dependency audit
- private Sites deployment and production smoke check

Milestone 2 must not begin until these checks pass.

## Validation record

The Milestone 1 release passed:

- Drizzle migration generation
- Prettier formatting verification
- ESLint
- TypeScript
- 6 fixed-fixture unit tests
- Vinext production build
- production dependency audit with no known vulnerabilities
- in-app browser review of the workspace overview, mission form, mission detail, and responsive navigation
- browser creation of a durable mission record followed by a clean redirect with no client errors

The browser-created verification records use the local Miniflare database only and are not included
in the production seed.
