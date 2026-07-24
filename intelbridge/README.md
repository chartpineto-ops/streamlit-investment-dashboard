# IntelBridge

IntelBridge is a persistent intelligence-gathering and synthesis workspace. It
turns approved sources into versioned documents, structured evidence, validated
claims, decision-ready insights, monitored changes, and exportable reports with
an inspectable source trail.

The hosted application uses Vinext, React, TypeScript, Cloudflare Workers, D1,
R2, Drizzle, Zod, Vitest, and the OpenAI Responses API provider boundary.

## Local development

Use Node.js 22.13 or newer and pnpm 11:

```powershell
pnpm install
pnpm dev
```

The local identity fallback is configured in `.env.example`. Sites production
uses authenticated-user headers.

## Validation

```powershell
pnpm db:generate
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm audit --prod
```

## Data mode

The default `AI_PROVIDER=mock` release contains a deterministic fictional corpus
and is visibly labeled `DEMO`. Live user-ingested documents retain their own
state and are not mixed silently into demo aggregates.

Set `AI_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL` through server-side
environment configuration to activate the Responses API provider. Never commit
API keys.

## Documentation

- [Milestone 1](docs/MILESTONE_1.md)
- [Full vertical slice](docs/FULL_RELEASE.md)
