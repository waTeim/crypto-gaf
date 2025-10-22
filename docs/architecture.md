# Crypto GAF Architecture Overview

This document describes the refreshed Crypto Gramian Angular Field repository layout and the workloads that will be deployed to Kubernetes. The original Docker Compose artefacts are preserved under `archived/` for reference, while the active services now live as first-class directories at the repository root.

## Repository Layout (2024 refresh)

- `collect/` — Python worker that ingests Coinbase order book and market order data and persists samples into PostgreSQL (`collect/app.py`).
- `calculate/` — Python worker that transforms stored samples into Gramian Angular Field imagery and writes the results back to PostgreSQL (`calculate/app.py`).
- `api/` — Node/Express backend (relocated from the old `src/` tree) that serves the `/api` endpoints used by downstream UIs. The React SPA now lives separately in https://github.com/waTeim/crypto-gaf-ui.
- `chart/` — Helm chart that deploys the workers together with a Bitnami PostgreSQL dependency.
- `docs/` — Architecture notes (this file) and future documentation.
- `archived/` — Docker Compose files, helper scripts, and the historical PostgreSQL schema (`archived/docker-components/cgaf-infra/pg/crypto-gaf.sql`). These are retained for reference but no longer drive deployments.

## Runtime Components

- **coinbase-local** (external dependency) exposes a Coinbase Pro-compatible REST API on port 4201. It remains a separate deployment, but runs in the same namespace as the Crypto GAF services.
- **collect worker** (`collect/app.py`) polls coinbase-local for order book intervals and market order deltas, inserting samples into `crypto_gaf.samples` while trimming history to each product’s configured `max_size`.
- **calculate worker** (`calculate/app.py`) reads recent samples, generates GAF imagery with `pyts`, encodes the output as base64 PNGs, and updates `crypto_gaf.gafs` for consumption by the UI/API.
- **Node/Express API** (`api/`) exposes `/api/gaf/image` and related endpoints consumed by external UIs (see the crypto-gaf-ui repository).
- **PostgreSQL** (Bitnami Helm dependency) stores the raw samples and generated imagery. The legacy schema SQL remains in `archived/` and should be applied during database bootstrap.

## Data Flow

```
coinbase-local (HTTP 4201)
        │          ┌───────────────┐
        └─► collect worker ───────►│crypto_gaf.samples
                      │            └───────────────┘
                      │                        │
                      ▼                        ▼
               calculate worker ───────► crypto_gaf.gafs
                      │                        │
                      └──────────────► API (Express) ──► Browser/UI (PNG/Base64)
```

1. `collect` loops forever (default 1 s interval) requesting `/api/orderBook/interval` and `/api/orderBook/marketOrders` from coinbase-local.
2. Samples are appended into PostgreSQL arrays (`ask_prices`, `bid_sizes`, etc.) and pruned to the configured `max_size` per product.
3. `calculate` pulls the freshest samples, produces Gramian Angular Fields via `pyts.image.GramianAngularField`, converts matrices to RGB PNGs, and writes the imagery into `crypto_gaf.gafs`.
4. The Express API (now in `api/`) reloads data with `GAF.refresh` and returns imagery to whichever UI consumes it.

## Database Schema

`archived/docker-components/cgaf-infra/pg/crypto-gaf.sql` provisions two tables that continue to back the workers:

- `crypto_gaf.gafs(product PRIMARY KEY, max_size, size, midpoint, midpoint_images text[], orderbook_image text, buy_image text, sell_image text)` stores the derived imagery and metadata.
- `crypto_gaf.samples(sample_id bigserial, product FK→gafs.product, midpoint numeric, ask_/bid_ arrays, buys/sells numeric[3])` retains market depth snapshots used for regeneration.

## Runtime Behaviour Notes

- Environment variables (`POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_DB`, `POSTGRES_PW`, `SLEEP_INTERVAL`, `COINBASE_URL`) control connectivity and pacing across the workers. The Helm chart maps these from chart values and generated secrets.
- The Express layer relies on `ts-api` decorators to auto-generate route bindings; compiled assets and the CLI wrapper remain in `api/src/bin`.
- `api/src/lib/GAF.ts` caches PostgreSQL rows in-memory, so each API replica must warm the cache on startup.
- Worker containers now target Python 3.11 with psycopg v3, and the API container uses Node 20 multi-stage images.

## Kubernetes Target Shape

To mirror the refreshed structure on Kubernetes (with coinbase-local still managed out-of-band):

- **PostgreSQL (Bitnami) subchart** deploys the backing database; overrides to hostnames, credentials, or persistence can be applied through `values.yaml`.
- **collect Deployment** (1 replica) reads from coinbase-local and writes samples to PostgreSQL. Adjust `collect.sleepInterval` and `collect.httpTimeout` as needed.
- **calculate Deployment** (1 replica) generates imagery from stored samples. Scale cautiously to avoid duplicate updates.
- **API Deployment** is now rendered by this chart alongside the workers; it uses the shared image settings and product list declared in `api.*`.
- **Shared Config/Secret objects** replace legacy Compose environment variables. The Helm chart now expects database passwords via the Bitnami `postgresql.auth.*` values or an existing secret.

## Open Questions & Risks

- **coinbase-local dependency**: confirm the deployment method (Helm vs. bespoke) and ensure network policies allow access on port 4201.
- **UI assets**: React front-end builds are handled in the separate crypto-gaf-ui repository; decide whether to host them alongside this API or keep the split deployment.
- **Caching strategy**: multiple API pods will each maintain their own cache; evaluate whether to introduce a shared cache layer if the fleet grows.
- **Operational controls**: the workers still rely on simple loops; consider job scheduling, back-pressure, or queueing to handle spikes or outages.
- **Security**: continue to migrate secrets into Kubernetes primitives and add TLS/ingress protections before exposing the API publicly.

## Kubernetes Implementation Notes

- Helm chart now deploys the API alongside the collect and calculate workers, plus the Bitnami PostgreSQL dependency.
- Helm chart exposes `image.registry`, `image.name`, and `image.tag` values that map directly to the `make.env` generated by `make-config.py`, keeping image naming consistent across builds and releases.
  Pass them with `helm upgrade --install ... --set image.registry=$REGISTRY,image.name=$IMAGE_NAME,image.tag=$TAG` after running `python make-config.py`.
- Shared environment variables are populated from Helm values; workers resolve `COINBASE_URL` (default `http://coinbase-local:4201`) and PostgreSQL credentials from the Bitnami dependency.
- Collect pods run an init container that waits for PostgreSQL readiness and applies the schema from `schema.sql`, so the workers can safely assume the tables exist.
- Calculate pods also perform a readiness wait before starting their loop.
- API configuration (e.g. `api.products` in `chart/values.yaml`) describes which markets to expose without polluting worker sections.
- Postgres credentials inherit from the Bitnami `postgresql.auth.*` settings (or an existing secret), keeping passwords in one place.
- Containers expect `POSTGRES_PORT` and related settings so they can target the Bitnami release without code changes.
- Database schema and initial seed data must be applied separately (the legacy migration job was removed).
- API container builds now target Node 20 with a multi-stage image and rely on local npm scripts (typescript + ts-api) for codegen.
