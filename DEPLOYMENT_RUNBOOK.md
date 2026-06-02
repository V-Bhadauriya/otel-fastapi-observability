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

---

## Verifying gRPC-Direct End-to-End

Use these commands to confirm data is flowing all the way from the app
through the Niriksha gRPC ingest pipeline.

### 1. Confirm the app is in gRPC-direct mode
```bash
docker compose logs app | grep "Telemetry active"
# Expected: Telemetry active — mode: grpc-direct
```

### 2. Probe the gRPC ingest endpoint
```bash
grpcurl grpc-ingest.niriksha.ai:443 grpc.health.v1.Health/Check
# Expected: Unimplemented (health service not registered) — confirms TLS+gRPC works
```

### 3. Send a test OTLP trace export with your API key
```bash
echo '{"resourceSpans":[]}' | grpcurl -d @ \
  -H "x-api-key: $NIRIKSHA_API_KEY" \
  grpc-ingest.niriksha.ai:443 \
  opentelemetry.proto.collector.trace.v1.TraceService/Export
# Expected: {} — auth passed, empty batch accepted
```

If this returns `{}` with no error, your API key is valid and the gRPC
transport is working correctly. If you see `Code: Unauthenticated`, check the
key value in `.env`.

### 4. Confirm data reaches Niriksha (gateway logs are silent on success)

The gateway only logs `WARN` on auth failures — silence means success. To
verify data is flowing into the pipeline, check whether the NATS JetStream
`TELEMETRY` stream sequence number is advancing:

```bash
# Run twice 30 seconds apart — last_seq should increase
kubectl exec -n niriksha-saas nats-0 -c nats -- \
  wget -qO- "http://localhost:8222/jsz?streams=1" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
st = d['account_details'][0]['stream_detail'][0]['state']
print(f\"last_seq={st['last_seq']}  messages_pending={st['messages']}\")
"
```

`last_seq` advancing + `messages_pending=0` means the processor is consuming
messages as fast as they arrive (healthy state).

---

## gRPC-Direct Infrastructure Notes

These notes document the Niriksha platform-side configuration required for
`grpc-direct` mode to work. Relevant when operating your own Niriksha instance.

### Why nginx must terminate TLS (not the gateway)

Cloudflare Tunnel's H2C (`h2c://`) scheme uses the HTTP/1.1 Upgrade mechanism
to negotiate HTTP/2 cleartext. gRPC servers send a direct HTTP/2 connection
preface (`PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n`) without the upgrade handshake —
these are incompatible. Routing Cloudflare directly to the gRPC gateway
produces:

```
net/http: HTTP/1.x transport connection broken: malformed HTTP response
"\x00\x00\x06\x04..."
```

The fix is to route Cloudflare → `https://ingress-nginx` so nginx terminates
TLS and negotiates HTTP/2 via ALPN, then uses `grpc_pass` to the upstream.

### nginx ingress configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nirikshaai-saas-ingest-grpc
  annotations:
    nginx.ingress.kubernetes.io/backend-protocol: GRPC
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: 50m
    nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "120"
spec:
  ingressClassName: nginx
  rules:
  - host: grpc-ingest.niriksha.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: nirikshaai-saas-gateway
            port:
              number: 4317
  tls:
  - hosts:
    - grpc-ingest.niriksha.ai
```

The path must be `/` with `Prefix` — per-method paths miss most gRPC calls
because the OTel exporter uses paths like
`/opentelemetry.proto.collector.trace.v1.TraceService/Export`.

### Header forwarding

nginx-ingress with `backend-protocol: GRPC` enables `grpc_pass_request_headers on`
by default, which forwards all incoming gRPC metadata (including `x-api-key`)
to the upstream gateway unchanged. No annotation snippets are needed.

Note: if your nginx-ingress version has snippet annotations disabled
(`--allow-snippet-annotations` not set), `configuration-snippet` annotations
will be rejected. The default `grpc_pass_request_headers on` behavior is
sufficient and does not require snippets.
