# OpenTelemetry FastAPI Observability — Niriksha AI

FastAPI application with full observability integration via the [Niriksha AI SDK](https://github.com/san-data-systems/niriksha-sdk-python).
Supports four telemetry transport modes selectable via a single environment variable.

---

## Telemetry Modes

| `TELEMETRY_MODE` | App sends to | Forwarded by |
|---|---|---|
| `grpc-direct` (default) | Niriksha SDK → `grpc-ingest.niriksha.ai:443` | SDK (gRPC/TLS) |
| `http-direct` | OTLP HTTP → `ingest.niriksha.ai/v1/traces` | Direct (HTTPS) |
| `grpc-collector` | OTLP gRPC → OTel Collector `:4317` | Collector → Niriksha gRPC |
| `http-collector` | OTLP HTTP → OTel Collector `:4318` | Collector → Niriksha gRPC |

---

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — set NIRIKSHA_API_KEY and TELEMETRY_MODE
```

### 2a. Run with Docker Compose (grpc-direct or http-direct)

No collector needed — app sends directly to Niriksha AI.

```bash
TELEMETRY_MODE=grpc-direct docker compose up
# or
TELEMETRY_MODE=http-direct docker compose up
```

### 2b. Run with Docker Compose + OTel Collector

```bash
# App → OTLP gRPC → Collector → Niriksha AI
TELEMETRY_MODE=grpc-collector docker compose --profile collector up

# App → OTLP HTTP → Collector → Niriksha AI
TELEMETRY_MODE=http-collector docker compose --profile collector up
```

### 2c. Run locally (without Docker)

```bash
pip install -r requirements.txt
export NIRIKSHA_API_KEY=nai_your_key_here
export TELEMETRY_MODE=grpc-direct
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/appdb
uvicorn app.main:app --reload --port 8000
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NIRIKSHA_API_KEY` | — | Required. API key from app.niriksha.ai |
| `TELEMETRY_MODE` | `grpc-direct` | Transport mode (see table above) |
| `APP_ENV` | `development` | Environment label shown in Niriksha dashboard |
| `DATABASE_URL` | — | PostgreSQL connection string |
| `NIRIKSHA_GRPC_ENDPOINT` | `grpc-ingest.niriksha.ai:443` | gRPC ingest endpoint |
| `NIRIKSHA_HTTP_ENDPOINT` | `https://ingest.niriksha.ai` | HTTP ingest endpoint |
| `OTEL_COLLECTOR_GRPC_ENDPOINT` | `otel-collector:4317` | Collector gRPC address |
| `OTEL_COLLECTOR_HTTP_ENDPOINT` | `http://otel-collector:4318` | Collector HTTP address |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root health check |
| `GET` | `/api/v1/health` | Health status |
| `GET` | `/api/v1/users` | Fetch users (cache → DB) |
| `POST` | `/api/v1/users` | Create user |
| `GET` | `/api/v1/products` | Product list |

Swagger UI: `http://localhost:8000/docs`

---

## Standalone Examples

Each script in `examples/` is a self-contained FastAPI app showing one transport mode.

```bash
# gRPC direct to Niriksha AI (uses SDK)
NIRIKSHA_API_KEY=nai_... uvicorn examples.grpc_direct:app --port 8001

# HTTP direct to Niriksha AI
NIRIKSHA_API_KEY=nai_... uvicorn examples.http_direct:app --port 8002

# gRPC via OTel Collector (start collector first)
uvicorn examples.grpc_via_collector:app --port 8003

# HTTP via OTel Collector (start collector first)
uvicorn examples.http_via_collector:app --port 8004
```

---

## Continuous Telemetry Generator

The app runs a background task (`app/telemetry/generator.py`) that emits
synthetic telemetry every 10 seconds regardless of real HTTP traffic.
This ensures Niriksha AI always has fresh data to display.

Signals emitted per cycle:
- **Traces** — simulated cache checks, DB queries, HTTP request spans
- **Metrics** — request counters, latency histograms, error rates, active-user gauge
- **Logs** — INFO / WARNING / ERROR entries correlated to active spans

To watch it live:
```bash
docker compose logs -f app | grep "Generator cycle"
```

---

## OTel Collector

The collector config lives at `collector/otel-collector-config.yaml`.

It accepts spans/metrics/logs on both gRPC (`:4317`) and HTTP (`:4318`) and
forwards everything to `grpc-ingest.niriksha.ai:443` authenticated with
`NIRIKSHA_API_KEY`.

To verify the collector is forwarding correctly, check its logs:

```bash
docker compose --profile collector logs -f otel-collector
```

Look for `"Everything is ready"` on startup and span export confirmations.

---

## gRPC-Direct Mode — Infrastructure Requirements

`grpc-direct` sends OTLP gRPC over TLS directly to `grpc-ingest.niriksha.ai:443`.
This requires the Niriksha platform to be running a correctly configured nginx
ingress in front of the gateway. If you are operating the Niriksha platform
yourself, the ingress must satisfy these constraints:

| Requirement | Why |
|---|---|
| `nginx.ingress.kubernetes.io/backend-protocol: GRPC` | Makes nginx use `grpc_pass` instead of `proxy_pass`, enabling proper HTTP/2 framing |
| Single catch-all path `/ Prefix` | gRPC methods use arbitrary paths; per-method path rules miss most RPC calls |
| TLS termination at nginx (not at the gateway) | gRPC clients send a direct HTTP/2 preface; Cloudflare Tunnel's H2C upgrade mechanism is incompatible — TLS must terminate at nginx so it can negotiate HTTP/2 via ALPN |
| `ssl-redirect: "true"` | Forces the gRPC client to the TLS listener |

Minimal working ingress annotation set:
```yaml
nginx.ingress.kubernetes.io/backend-protocol: GRPC
nginx.ingress.kubernetes.io/ssl-redirect: "true"
nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
nginx.ingress.kubernetes.io/proxy-send-timeout: "120"
```

The Python OTLP gRPC exporter sends `x-api-key` as per-call gRPC metadata.
nginx forwards it to the upstream via `grpc_pass_request_headers on` (the default).
No custom header configuration is needed on the ingress side.

---

## Project Structure

```
.
├── app/
│   ├── main.py                   # FastAPI entrypoint
│   ├── api/                      # Route handlers
│   ├── core/
│   │   ├── config.py             # Settings (all env vars)
│   │   └── setup.py              # Route + instrumentation registration
│   ├── db/                       # SQLAlchemy engine + session
│   ├── models/                   # ORM models
│   ├── schema/                   # Pydantic schemas
│   ├── services/                 # Business logic with manual spans
│   └── telemetry/
│       └── tracing.py            # Mode-aware telemetry init (4 modes)
├── collector/
│   └── otel-collector-config.yaml
├── examples/
│   ├── grpc_direct.py
│   ├── http_direct.py
│   ├── grpc_via_collector.py
│   └── http_via_collector.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
