# Crypto GAF Platform

This repository contains the backend services and Helm chart used to generate and serve Gramian Angular Field (GAF) imagery for cryptocurrency order book data. The project collects market snapshots from `coinbase-local`, stores them in PostgreSQL, transforms them into GAF imagery, and exposes the latest imagery through an Express-based API. A separate UI project (`crypto-gaf-ui`, https://github.com/waTeim/crypto-gaf-ui) consumes the API to render visuals.

## Repository structure

```
api/          Node/Express API (TypeScript via ts-api, exposes `/api` endpoints)
collect/      Python worker that polls coinbase-local and writes samples to PostgreSQL
calculate/    Python worker that generates Gramian Angular Field imagery from samples
chart/        Helm chart (Bitnami PostgreSQL dependency + api/collect/calculate deployments)
docs/         Architecture reference and design notes
make-config.py  Helper script to generate `make.env` image/registry/tag/platform configuration
Makefile      Convenience targets for building/pushing container images
```

## Prerequisites

- Docker 20+
- Python 3.11 (used inside the worker containers)
- Node.js 20 (for local API builds/tests)
- Helm 3.13+
- Access to a Docker registry and a Kubernetes cluster if you intend to deploy

## Generating configuration

The `make-config.py` script inspects the repository (branch, tags, user) and writes a `make.env` file containing the registry, image name, tag, and build platform used by both the Makefile and the Helm chart.

```bash
python make-config.py --output make.env
```

The resulting file looks like:

```
REGISTRY=docker.io/myuser
IMAGE_NAME=crypto-gaf
TAG=v1.2.2
PLATFORM=linux/amd64
```

## Building container images

```bash
# build all services (api, collect, calculate)
make build

# push all images to the configured registry
after running make build, use:
make push

# build/push a single service
make build-api
make push-api
```

Images are tagged as `${REGISTRY}/${IMAGE_NAME}-<service>:${TAG}`.

## Helm chart

The chart deploys:

- Bitnami PostgreSQL (`^18.0.0`) with persistence
- `collect` Deployment + init container (schema bootstrap & readiness wait)
- `calculate` Deployment + init container
- `api` Deployment + init container
- Service for the API (ClusterIP by default, port 4202)
- ConfigMap containing the schema (`crypto_gaf` tables + seeded product rows based on `api.products`)

### Values overview (`chart/values.yaml`)

- `image.*` — global registry/name/tag/pullPolicy defaults shared by all services
- `api.*`, `collect.*`, `calculate.*` — per-service configuration (replicas, env vars, init image overrides, etc.)
- `api.ingress.*` — optional HTTP ingress configuration (disabled by default).
- `global.coinbase.*` — endpoint for `collect` to reach `coinbase-local`
- `postgresql.*` — overrides for the Bitnami chart

Example values override (`crypto-gaf.yaml`):

```yaml
image:
  registry: docker.io/myuser
  name: crypto-gaf
  tag: v1.2.2

api:
  service:
    type: ClusterIP
    port: 4202
    targetPort: 4202
  products:
    - name: BTC-USD
      maxSize: 600

collect:
  sleepInterval: 0.25

calculate:
  sleepInterval: 0.5
```

### Install / upgrade

```bash
helm dependency update chart
helm upgrade --install crypto-gaf chart   --namespace gaf --create-namespace   --values crypto-gaf.yaml   --set image.registry=$(grep REGISTRY make.env | cut -d= -f2)   --set image.name=$(grep IMAGE_NAME make.env | cut -d= -f2)   --set image.tag=$(grep TAG make.env | cut -d= -f2)
```

Swagger documentation is served at `/api/docs` once the API pod is running.

## Runtime behaviour

- **Collect** continuously polls `coinbase-local` for order book snapshots and rolling market order aggregates, storing them in `crypto_gaf.samples`. History is trimmed to `maxSize` samples per product.
- **Calculate** waits for a full window of data (default 21 samples) before generating Gramian Angular Field imagery (order book, buy/sell, midpoints) and persisting the encoded PNGs to `crypto_gaf.gafs`.
- **API** restores/caches the latest imagery on startup and serves it through endpoints such as `GET /api/gaf/image?product=BTC-USD`.
- All deployments include init containers that wait for PostgreSQL to accept connections; `collect` additionally applies the schema stored in `schema-configmap.yaml`.

Pod logs:

- `collect` reports backoff when the database or coinbase-local are unavailable.
- `calculate` emits a minute-by-minute summary (`processed N updates in the last 60s`) and logs any data shape issues it skips.
- `api` logs every request (`[api] METHOD /path`) and 404s/errors for troubleshooting.

## Working with the UI

The React front-end lives in https://github.com/waTeim/crypto-gaf-ui. Deploy it separately and point it at the API’s `/api` endpoints. The API exposes product configuration via `api.products` so the UI knows which markets to display.

## Tips & troubleshooting

- Use `kubectl exec … -- bash` to shell into pods; the images include `procps` so tools like `ps` are available.
- If you need additional debugging tools (vim, etc.), run `apt-get update && apt-get install <pkg>` inside the container.
- To seed additional products, edit `api.products` and redeploy (the ConfigMap inserts rows into `crypto_gaf.gafs`).
- Customize polling/aggregation timings via `collect.sleepInterval`, `calculate.sleepInterval`, or add env vars to the respective `env` lists.

## License / attribution

This backend is derived from the original `crypto-gaf` project by waTeim. The UI portion (formerly co-located) now lives in the `crypto-gaf-ui` repository. Respect the upstream licensing terms when reusing the code.
