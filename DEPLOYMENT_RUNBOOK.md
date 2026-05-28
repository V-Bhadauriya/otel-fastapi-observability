# Deployment Runbook — 6-Way Validation

Follow each section in order. Validate data in the Niriksha dashboard before cleanup.

**Prerequisites**
- `.env` file exists with a valid `NIRIKSHA_API_KEY`
- Docker Desktop is running
- Port 8000, 4317, 4318, 5432 are free

---

## Mode 1 — gRPC Direct

**Flow:** App → gRPC → `grpc-ingest.niriksha.ai:443`

### Deploy
```bash
TELEMETRY_MODE=grpc-direct docker compose up --build -d
```

### Validate
```bash
# 1. App is healthy
curl http://localhost:8000/api/v1/health

# 2. Generate traces
curl http://localhost:8000/api/v1/users
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "mode1-grpc-direct"}'

# 3. Check app logs for telemetry mode confirmation
docker compose logs app | grep "Telemetry active"
```

**Check Niriksha dashboard** → `https://app.niriksha.ai`
Look for service `otel-fastapi-service` with traces from this run.

### Cleanup
```bash
docker compose down -v
```

---

## Mode 2 — HTTP Direct

**Flow:** App → HTTP → `https://ingest.niriksha.ai`

### Deploy
```bash
TELEMETRY_MODE=http-direct docker compose up --build -d
```

### Validate
```bash
curl http://localhost:8000/api/v1/health

curl http://localhost:8000/api/v1/users
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "mode2-http-direct"}'

docker compose logs app | grep "Telemetry active"
```

**Check Niriksha dashboard** → confirm new traces from this run.

### Cleanup
```bash
docker compose down -v
```

---

## Mode 3 — gRPC → Collector → gRPC → Niriksha

**Flow:** App →gRPC→ OTel Collector →gRPC→ `grpc-ingest.niriksha.ai:443`

### Deploy
```bash
TELEMETRY_MODE=grpc-collector \
COLLECTOR_EXPORTER=grpc \
  docker compose --profile collector up --build -d
```

### Validate
```bash
curl http://localhost:8000/api/v1/health

curl http://localhost:8000/api/v1/users
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "mode3-grpc-collector-grpc"}'

# Confirm collector received and forwarded spans
docker compose logs otel-collector | grep -E "Exporting|TracesExporter|Everything is ready"
docker compose logs app | grep "Telemetry active"
```

**Check Niriksha dashboard** → confirm traces arrived via collector.

### Cleanup
```bash
docker compose --profile collector down -v
```

---

## Mode 4 — gRPC → Collector → HTTP → Niriksha

**Flow:** App →gRPC→ OTel Collector →HTTP→ `https://ingest.niriksha.ai`

### Deploy
```bash
TELEMETRY_MODE=grpc-collector \
COLLECTOR_EXPORTER=http \
  docker compose --profile collector up --build -d
```

### Validate
```bash
curl http://localhost:8000/api/v1/health

curl http://localhost:8000/api/v1/users
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "mode4-grpc-collector-http"}'

docker compose logs otel-collector | grep -E "Exporting|TracesExporter|Everything is ready"
docker compose logs app | grep "Telemetry active"
```

**Check Niriksha dashboard** → confirm traces arrived.

### Cleanup
```bash
docker compose --profile collector down -v
```

---

## Mode 5 — HTTP → Collector → gRPC → Niriksha

**Flow:** App →HTTP→ OTel Collector →gRPC→ `grpc-ingest.niriksha.ai:443`

### Deploy
```bash
TELEMETRY_MODE=http-collector \
COLLECTOR_EXPORTER=grpc \
  docker compose --profile collector up --build -d
```

### Validate
```bash
curl http://localhost:8000/api/v1/health

curl http://localhost:8000/api/v1/users
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "mode5-http-collector-grpc"}'

docker compose logs otel-collector | grep -E "Exporting|TracesExporter|Everything is ready"
docker compose logs app | grep "Telemetry active"
```

**Check Niriksha dashboard** → confirm traces arrived.

### Cleanup
```bash
docker compose --profile collector down -v
```

---

## Mode 6 — HTTP → Collector → HTTP → Niriksha

**Flow:** App →HTTP→ OTel Collector →HTTP→ `https://ingest.niriksha.ai`

### Deploy
```bash
TELEMETRY_MODE=http-collector \
COLLECTOR_EXPORTER=http \
  docker compose --profile collector up --build -d
```

### Validate
```bash
curl http://localhost:8000/api/v1/health

curl http://localhost:8000/api/v1/users
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "mode6-http-collector-http"}'

docker compose logs otel-collector | grep -E "Exporting|TracesExporter|Everything is ready"
docker compose logs app | grep "Telemetry active"
```

**Check Niriksha dashboard** → confirm traces arrived.

### Cleanup
```bash
docker compose --profile collector down -v
```

---

## Troubleshooting

**App fails to start**
```bash
docker compose logs app
```

**Collector not forwarding**
```bash
# Watch collector logs live
docker compose --profile collector logs -f otel-collector
```

**No traces in Niriksha dashboard**
- Allow 30–60 seconds after generating traffic (BatchSpanProcessor has a flush delay)
- Confirm `NIRIKSHA_API_KEY` in `.env` is valid
- Check for `401` or `403` errors in collector logs

**Port already in use**
```bash
# Check what is holding a port
lsof -i :8000
lsof -i :4317
lsof -i :4318
```

**Full reset between modes**
```bash
docker compose --profile collector down -v --remove-orphans
docker system prune -f
```
