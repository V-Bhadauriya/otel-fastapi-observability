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
