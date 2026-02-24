# Vastgoedcalculator SaaS (Belgium)

Production-grade, deterministic Belgian real-estate investment analysis platform implemented with Next.js + Prisma + Zod + Pino.

## What is included

- Rule-driven acquisition-cost engine (region aware, JSON ruleset, explainability trace).
- Mortgage annuity model and operational rental model.
- KPI engine with strict formula definitions.
- Sensitivity matrix (rent, interest, vacancy).
- Weighted scoring model with narrative recommendations.
- Deterministic report payload with calculation hash + ruleset metadata.
- API-level validation, in-memory rate-limiting, and structured logging.
- Prisma models for `Project`, `Assumptions`, `Ruleset`, `ReportSnapshot`.
- Seed scripts for initial ruleset and sample project.
- Jest unit tests + Playwright E2E scenario (wizard → report link).

## Architecture

- `app/` Next.js App Router UI and API routes.
- `lib/finance/` pure deterministic finance functions.
- `lib/server/` validation, logging, db client, and rate limiting.
- `rules/` versioned JSON rulesets.
- `prisma/` schema and seed.
- `tests/` unit and e2e tests.

## Local run

```bash
cp .env.example .env
npm install
npx prisma migrate dev --name init
npm run prisma:seed
npm run dev
```

Open `http://localhost:3000`.

## Testing

```bash
npm run test
npm run test:e2e
```

## Determinism guarantees

- Pure functions for all finance computation in `lib/finance/engine.ts`.
- Rounded values to 2 decimals at the engine level.
- Result includes ruleset version, timestamp, assumptions, trace and SHA-256 hash.
- Rule logic is data-driven from `rules/v2026-01.be.json`.

## Disclaimer

Legal/fiscal rates and incentives can change. Always validate with a notary and tax advisor before investment decisions.
