# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Gramian Angular Field (GAF) visualization platform for cryptocurrency order book data. The system consists of three services that work together:

1. **collect** (Python) - Polls `coinbase-local` for order book snapshots and market order aggregates, stores them in PostgreSQL
2. **calculate** (Python) - Transforms stored samples into GAF imagery using pyts library, generates PNG visualizations
3. **api** (Node/Express/TypeScript) - Serves the latest GAF imagery through REST endpoints (Swagger at `/api/docs`)

A separate UI repository (`crypto-gaf-ui`) consumes the API to display visualizations.

## Common Commands

### API Development
```bash
cd api
npm install                    # Install dependencies
npm run build                  # Full build (clean, generate routes, compile, prepare bin)
npm run compile                # TypeScript compilation only
npm run generate-routes        # Generate ts-api routes
npm run clean                  # Remove dist, __routes, bin directories
```

The API uses the `ts-api` framework with decorators (`@controller`, `@get`, etc.) for route definition.

### Building Container Images
```bash
# Generate configuration first
python make-config.py --output make.env

# Build all images
make build

# Build individual services
make build-api
make build-collect
make build-calculate

# Push images to registry
make push               # Push all
make push-api          # Push individual
```

Images are tagged as `${REGISTRY}/${IMAGE_NAME}-<service>:${TAG}` based on `make.env`.

### Helm Deployment
```bash
# Update dependencies (pulls Bitnami PostgreSQL chart)
helm dependency update chart

# Install/upgrade
helm upgrade --install crypto-gaf chart \
  --namespace gaf --create-namespace \
  --values crypto-gaf.yaml \
  --set image.registry=$(grep REGISTRY make.env | cut -d= -f2) \
  --set image.name=$(grep IMAGE_NAME make.env | cut -d= -f2) \
  --set image.tag=$(grep TAG make.env | cut -d= -f2)
```

## Architecture

### Data Flow

1. **collect** → polls coinbase-local every `sleepInterval` seconds (default 0.25s)
   - Fetches order book snapshots (aggregated prices/sizes at depth levels)
   - Fetches rolling market order aggregates (buy/sell price/size/numOrders)
   - Inserts into `crypto_gaf.samples` table
   - Trims history to `max_size` samples per product (configured in Helm values `api.products`)

2. **calculate** → processes samples every `sleepInterval` seconds (default 0.5s)
   - Waits for minimum 21 samples before generating imagery
   - Uses pyts GramianAngularField to transform time series data
   - Generates 4 images:
     - Orderbook GAF (weighted ask/bid comparison across depth)
     - Buy market orders GAF
     - Sell market orders GAF
     - Midpoint GAF (summation and difference methods)
   - Stores base64-encoded PNGs in `crypto_gaf.gafs` table
   - Uses ThreadPoolExecutor for parallel field computation

3. **api** → serves cached imagery
   - On startup, calls `GAF.restore()` to load all products from DB into memory cache
   - `GET /api/gaf/image?product=BTC-USD` refreshes data from DB and returns latest imagery
   - Returns JSON with `png1` (orderbook), `png2` (buy), `png3` (sell), `png4` (midpoint), `midpoint`, `size`, `date`

### Database Schema

The schema is stored in `chart/templates/schema-configmap.yaml` and applied by the collect init container:

- **crypto_gaf.gafs** - Product configuration and latest imagery
  - `product` (PK), `max_size`, `midpoint`, `size`
  - `orderbook_image`, `buy_image`, `sell_image`, `midpoint_images[]` (base64 PNGs)

- **crypto_gaf.samples** - Raw time series data
  - `sample_id` (serial PK), `product` (FK), `midpoint`
  - `ask_prices[]`, `ask_sizes[]`, `bid_prices[]`, `bid_sizes[]`
  - `buys[]` (price, size, numOrders), `sells[]`

Products are seeded from Helm values `api.products` list.

### API Code Structure

- `src/main.ts` - Entrypoint, PostgreSQL connection setup from env vars
- `src/init/index.ts` - Express app initialization, calls `GAF.restore()`
- `src/init/Router.ts` - Registers ts-api controllers
- `src/controllers/GAFDataManager.ts` - Controller with `/gaf/image` endpoint
- `src/lib/GAF.ts` - Data access layer, maintains in-memory cache keyed by product
- `src/lib/db.ts` - PostgreSQL connection pool wrapper

The API uses `ts-api` code generation (`npm run generate-routes`) which creates `__routes` from controller decorators.

### Python Workers

Both `collect/app.py` and `calculate/app.py` follow similar patterns:
- Read config from environment variables or CLI args
- Use psycopg3 for PostgreSQL connectivity
- Implement exponential backoff on errors (DB connection, HTTP requests)
- Run continuous loops with precise timing using `startTime + iterations*sleepInterval`

## Configuration

### Environment Variables

**All services:**
- `POSTGRES_USER`, `POSTGRES_PW`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`

**API:**
- `PORT` (default 4202)
- `DATABASE_URL` or `PG` (alternative to individual vars)

**collect:**
- `COINBASE_URL` (default `http://coinbase-local:4201`)
- `SLEEP_INTERVAL` (default 1.0, Helm overrides to 0.25)
- `HTTP_TIMEOUT` (default 10)

**calculate:**
- `SLEEP_INTERVAL` (default 1.0, Helm overrides to 0.5)

### Helm Values

Key customization points in `chart/values.yaml`:
- `image.registry/name/tag` - Global image configuration
- `api.products[]` - List of products with `name` and `maxSize` (default 600)
- `collect.sleepInterval`, `calculate.sleepInterval` - Polling intervals
- `global.coinbase.host/port/scheme` - coinbase-local endpoint
- `api.ingress.*` - Optional ingress configuration (disabled by default)
- `postgresql.*` - Bitnami chart overrides

## Troubleshooting

- All init containers wait for PostgreSQL readiness before starting
- collect applies schema on startup (idempotent CREATE IF NOT EXISTS)
- calculate requires at least 21 samples before generating imagery (check `crypto_gaf.samples` row count)
- API logs requests as `[api] METHOD /path`, useful for debugging 404s
- collect/calculate log backoff messages when dependencies are unavailable
- Use `kubectl exec ... -- bash` to shell into pods (images include procps)

### Known Issues

**Division by zero in calculate (fixed)**: The `getOrderbookField` function at calculate/app.py:117 previously crashed with `decimal.InvalidOperation` when both ask and bid sizes were zero at a depth level. This can occur during low liquidity periods or data gaps. The code now checks the denominator and uses 0 when there's no size on either side.
