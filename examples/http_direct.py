"""
http_direct.py — Send traces directly to Niriksha AI via OTLP HTTP.

Transport:  App  →  OTLP HTTP  →  https://ingest.niriksha.ai/v1/traces

Run:
    pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http \
                opentelemetry-instrumentation-fastapi fastapi uvicorn
    export NIRIKSHA_API_KEY=nai_your_key_here
    uvicorn examples.http_direct:app --port 8002
"""

import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

NIRIKSHA_API_KEY = os.environ["NIRIKSHA_API_KEY"]
NIRIKSHA_HTTP_ENDPOINT = os.getenv(
    "NIRIKSHA_HTTP_ENDPOINT", "https://ingest.niriksha.ai"
)

resource = Resource.create({SERVICE_NAME: "example-http-direct"})
provider = TracerProvider(resource=resource)

exporter = OTLPSpanExporter(
    endpoint=f"{NIRIKSHA_HTTP_ENDPOINT}/v1/traces",
    headers={"X-API-Key": NIRIKSHA_API_KEY},
)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
tracer = trace.get_tracer(__name__)


@app.get("/ping")
def ping():
    with tracer.start_as_current_span("ping.handler") as span:
        span.set_attribute("transport", "http-direct")
        return {"pong": True, "transport": "http-direct"}
