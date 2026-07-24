# IntelBridge Milestones 1–3

Date: 2026-07-23

Status: implementation complete; validation and production deployment recorded
in the final task handoff.

## Scope

Implemented:

- authenticated workspace shell and server-enforced workspace isolation
- project create, update, archive, list, and detail APIs
- mission create, update, list, detail, source assignment, and run history
- source connector create, update, list, detail, connectivity test, and health
- queued research runs with seven explicit ingestion steps
- idempotent run creation, controlled transitions, cooperative cancellation,
  retry, exponential backoff, and dead-letter state
- ordered durable run events with resumable SSE and heartbeat comments
- RSS/Atom, webpage, manual URL, file upload, public GitHub, and deterministic
  demo adapters behind one server-only interface
- public URL canonicalization, SSRF checks, DNS revalidation, redirect
  revalidation, timeout, retry, MIME, and byte-size controls
- HTML, text, Markdown, CSV, JSON, XML, and extractable text-PDF normalization
- prompt-injection labeling while preserving source text as untrusted content
- R2 raw upload storage and D1 normalized metadata/content
- canonical document records, immutable versions, hash deduplication, and
  `CREATED`, `UPDATED`, or `UNCHANGED` states
- document list filters, detail, and version inspection
- operational diagnostics, audit history, empty states, and safe API errors

Not implemented:

- evidence extraction
- claim generation or validation
- AI synthesis or recommendations
- monitoring alerts
- report generation

## Runtime decision

The product brief proposed PostgreSQL, Prisma, Redis, and BullMQ. The repository
already targets Sites, which provides Cloudflare Workers, D1, and R2 rather
than managed PostgreSQL or Redis. The release therefore uses the supported
repository equivalent:

```text
Browser
  -> Vinext / Worker route handlers
  -> authenticated services
  -> workspace-scoped repositories
  -> D1 relational records + durable job/event ledger
  -> R2 raw upload objects
```

`job_queue` is a persistent queue with attempt count, availability time, lease
expiry, retry limit, and dead-letter timestamp. A worker claims a job with a
conditional update. Run pages also start the same server-side processor while
opening SSE, so page refreshes do not restart work and reopening a queued run
resumes processing.

The worker exports a scheduled handler for queue draining. Recurring invocation
still requires a managed cron trigger on the hosting project.

## Data model

Milestones 1–3 use:

- `workspaces`, `users`
- `projects`
- `missions`, `mission_sources`
- `source_connectors`, `connector_configurations`,
  `connector_checkpoints`
- `research_runs`, `run_steps`, `run_events`, `job_queue`
- `source_documents`, `source_document_versions`
- `retrieval_failures`
- `audit_logs`

Run states:

```text
QUEUED -> RUNNING -> COMPLETED | PARTIALLY_COMPLETED | FAILED
                  -> CANCEL_REQUESTED -> CANCELLED
QUEUED -> CANCELLED
```

Retry creates a new run linked through `retry_of_run_id`; it never erases the
failed or cancelled record.

## Connector contract

Every adapter implements:

- `testConnection`
- `discover`
- `retrieve`
- `normalize`
- `getCheckpoint`
- `saveCheckpoint`

Checkpoints advance only after document persistence. Connector errors are
stored as safe structured retrieval failures without leaking credentials or
raw provider errors.

GitHub credentials are optional and server-only. Without `GITHUB_TOKEN`, the
adapter uses the public API's anonymous rate limits.

## Retrieval security

Remote retrieval:

- permits only HTTP and HTTPS
- rejects URL credentials and non-standard ports
- rejects localhost, private, link-local, documentation, multicast, and local
  IPv4/IPv6 address ranges
- resolves public hostnames through DNS-over-HTTPS immediately before fetch
- repeats URL and DNS validation after every redirect
- permits no more than four redirects
- uses bounded timeouts and two attempts for rate-limit/server failures
- enforces declared and observed byte limits
- rejects unsupported or mismatched content types
- marks normalized text as an untrusted source

Cloudflare's outbound resolver remains the final egress resolver. IntelBridge
does not expose an arbitrary proxy endpoint.

## Versioning and deduplication

Document identity is connector plus external ID or canonical URL. The current
document row points to its immutable version:

- new identity/hash: create document and version
- existing identity/new hash: append one version and update current pointer
- existing identity/same hash: update retrieval/checkpoint metadata only

Unique document/version and document/hash constraints make retries idempotent.
D1 batches keep a version insert and current-document update atomic.

## PDF behavior

Uploads store the raw object in R2. The built-in extractor supports
non-encrypted text PDFs that expose standard text operators. Encrypted,
malformed, scanned-image, or unsupported compressed PDFs fail explicitly with
a structured error; IntelBridge does not fabricate extracted text. A future
OCR/parser service would be a separate reviewed dependency.

## API surface

Projects:

- `GET|POST /api/projects`
- `GET|PATCH /api/projects/:projectId`

Missions:

- `GET|POST /api/missions`
- `GET|PATCH /api/missions/:missionId`
- `POST /api/missions/:missionId/sources`
- `DELETE /api/missions/:missionId/sources/:connectorId`

Sources:

- `GET|POST /api/sources`
- `GET|PATCH /api/sources/:sourceId`
- `POST /api/sources/:sourceId/test`
- `POST /api/sources/:sourceId/urls`
- `POST /api/uploads`

Runs:

- `GET|POST /api/missions/:missionId/runs`
- `GET|DELETE /api/runs/:runId`
- `GET /api/runs/:runId/steps`
- `GET /api/runs/:runId/events`
- `POST /api/runs/:runId/cancel`
- `POST /api/runs/:runId/retry`

Documents:

- `GET /api/documents`
- `GET /api/documents/:documentId`
- `GET /api/documents/:documentId/versions`
- `GET /api/documents/:documentId/versions/:versionId`

All handlers parse inputs with shared Zod schemas and return safe structured
errors with a request ID.

## Validation matrix

- formatting and lint
- TypeScript
- unit tests for domain schemas, URL policy, connector determinism, run
  transitions, environment parsing, mission input, and workspace scope
- production Worker build
- local D1/R2 HTTP smoke checks
- Playwright navigation, mission launch, queued-run UI, SSE event replay,
  document list/detail, source filters, search, diagnostics, and responsive
  layout
- production route and API smoke checks after Sites deployment

## Environment

Required bindings:

- `DB` — D1
- `FILES` — private R2

Optional server variables:

- `INTELBRIDGE_DEMO_USER_EMAIL`
- `GITHUB_TOKEN`

Sites authenticated-user headers determine the production user. Secrets must
never be committed or returned to clients.
