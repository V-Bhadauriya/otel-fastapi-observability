"""
grpc_via_collector.py — Send traces to OTel Collector via gRPC.

Transport:  App  →  OTLP gRPC  →  OTel Collector:4317
                                        ↓
                                   gRPC/TLS → Niriksha AI

The collector handles authentication with Niriksha AI.
No API key is required on the application side.

Prerequisites — start the collector first:
    NIRIKSHA_API_KEY=nai_your_key docker compose --profile collector up otel-collector

Run:
    pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc \
                opentelemetry-instrumentation-fastapi fastapi uvicorn
    uvicorn examples.grpc_via_collector:app --port 8003
"""

import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

COLLECTOR_GRPC = os.getenv("OTEL_COLLECTOR_GRPC_ENDPOINT", "localhost:4317")

resource = Resource.create({SERVICE_NAME: "example-grpc-collector"})
provider = TracerProvider(resource=resource)

exporter = OTLPSpanExporter(endpoint=COLLECTOR_GRPC, insecure=True)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
tracer = trace.get_tracer(__name__)


@app.get("/ping")
def ping():
    with tracer.start_as_current_span("ping.handler") as span:
        span.set_attribute("transport", "grpc-collector")
        span.set_attribute("collector.endpoint", COLLECTOR_GRPC)
        return {"pong": True, "transport": "grpc-collector"}
