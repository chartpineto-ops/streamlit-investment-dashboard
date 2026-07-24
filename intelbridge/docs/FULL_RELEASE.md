# IntelBridge Full Vertical Slice

Date: 2026-07-23

Status: production release; implementation, automated validation, and Sites
deployment complete.

## Release scope

This release expands the Milestone 1 foundation into the complete workspace
surface defined by the IntelBridge product brief:

- research missions and projects
- manual and scheduled research runs
- ordered, reconnectable Server-Sent Events
- inspectable agent steps
- versioned source documents
- governed public-URL retrieval
- text, Markdown, CSV, JSON, XML, and PDF uploads
- evidence, claims, support and contradiction relationships
- confidence, novelty, source quality, and deterministic materiality
- source-backed insights with assumptions and limitations
- evidence-grounded questions with citation allow-list validation
- monitoring policies, checkpoints, thresholds, and alerts
- executive brief, source appendix, competitor matrix, evidence CSV, and JSON
  report generation
- normalized dataset catalog
- agent prompt/tool registry
- workspace search
- diagnostics and audit activity

Every seeded research record is explicitly `status=demo` and `is_demo=true`.
The deterministic corpus uses fictional publishers on reserved `.example`
domains. User-ingested records are not relabeled as demo.

## Sites architecture

IntelBridge retains the supported Sites runtime:

- Vinext compiles the Next.js App Router application for Cloudflare Workers.
- Cloudflare D1 is the authoritative relational store.
- Cloudflare R2 stores binary and larger governed uploads.
- Drizzle defines the 22-table schema and generated migrations.
- Sites authenticated-user headers identify the current user.
- Every repository query enforces workspace scope on the server.

The original PostgreSQL, Redis, and BullMQ proposal is not used in the hosted
release because Sites does not provision those services. Durable D1 run steps
and run events replace the Redis event layer. The worker exports a scheduled
handler for due monitors, while the UI also provides an immediate Run now path.

## Seed contract

The idempotent deterministic seed includes:

- one workspace
- two users
- three projects
- six connector definitions
- three missions
- two completed research runs
- one active research run
- 20 fictional source documents
- 60 source-bound evidence records
- 15 claims
- 8 insights
- supporting, contextualizing, and contradicting relationships
- three monitors
- three material-change alerts
- three generated reports
- six governed agent definitions

Seed initialization is split into bounded D1 batches. Every write uses
`INSERT OR IGNORE`, so worker cold starts are safe to retry.

## Research-run behavior

`POST /api/missions/:missionId/runs` creates a durable run and its six
inspectable steps. Caller-supplied idempotency keys prevent duplicate runs.
`GET /api/runs/:runId/events` replays the ordered event ledger and honors the
SSE `Last-Event-ID` header. Completed records survive page refreshes. Active
runs may be cancelled through the UI or `DELETE /api/runs/:runId`.

The deterministic provider never creates an unsupported conclusion. A mission
without approved documents completes with a structured
`NO_APPROVED_SOURCE_DOCUMENTS` limitation and no invented insight.

## Ingestion controls

Public URL retrieval:

- requires HTTPS
- rejects credentials, non-standard ports, localhost, private IPv4 ranges,
  link-local hosts, and internal hostnames
- follows only revalidated public redirects
- enforces content-type, byte-size, and timeout limits
- strips untrusted markup before normalization
- labels prompt-injection patterns
- hashes normalized content
- returns `NEW`, `CHANGED`, or `UNCHANGED`
- increments document versions without duplicating identical content

Uploads enforce a 10 MB limit and MIME allow-list. Small textual files are
normalized in D1. PDFs, binary files, and larger text files use private R2
storage with D1 metadata. PDF text extraction remains unavailable in the Sites
runtime and is stated in the record rather than simulated.

## Model-provider boundary

`AI_PROVIDER=mock` is the default and requires no API key. The deterministic
provider returns schema-validated answers and citation IDs.

`AI_PROVIDER=openai` activates the server-only Responses API provider. It uses:

- configurable `OPENAI_MODEL`
- strict JSON Schema structured output
- Zod validation
- two bounded attempts
- request timeout
- token-usage capture
- citation allow-list validation
- prompt-injection boundaries
- `store=false`

The deployed Sites environment remains in mock mode until an API key is
configured through Sites environment variables. No key is committed or exposed
to client code.

## Known integration boundaries

- RSS, public-web configuration, and GitHub public connectors are shown as Not
  connected until a user configures and validates them.
- Google Drive, Gmail, Slack, Notion, CRM, warehouses, and paid-data providers
  are intentionally absent rather than simulated.
- The scheduled worker handler is implemented, but recurring invocation
  requires a managed cron binding on the hosting project.
- PDF bytes are stored securely; text extraction requires a future approved
  extraction service.
- Production OpenAI calls require a server-side key and explicit provider
  switch.

These are external configuration boundaries, not fake application controls.

## Validation

Required release checks:

```powershell
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm audit --prod
```

HTTP smoke checks cover every product route, report download, run creation, run
detail persistence, and SSE completion replay.

Validation record:

- Drizzle generated and inspected `0001_icy_beast.sql` and
  `0002_powerful_gargoyle.sql`.
- Prettier verification passed.
- ESLint passed.
- TypeScript passed.
- 15 tests across 7 files passed.
- Vinext worker production build passed.
- Production dependency audit found no known vulnerabilities.
- All product workspace routes returned HTTP 200.
- Report download returned the expected content type.
- A new research run persisted and replayed all eight ordered events.
- Repeating the same idempotency key returned the original run instead of
  creating a duplicate.
