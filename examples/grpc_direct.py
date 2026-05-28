"""
grpc_direct.py — Send traces directly to Niriksha AI via gRPC.

Transport:  App  →  Niriksha SDK (gRPC/TLS)  →  grpc-ingest.niriksha.ai:443

Run:
    pip install "nirikshaai[all]" fastapi uvicorn
    export NIRIKSHA_API_KEY=nai_your_key_here
    uvicorn examples.grpc_direct:app --port 8001
"""

import os

import nirikshaai
from fastapi import FastAPI
from opentelemetry import trace

nirikshaai.init(
    endpoint="https://app.niriksha.ai",
    otlp_endpoint="grpc-ingest.niriksha.ai:443",
    api_key=os.environ["NIRIKSHA_API_KEY"],
    service_name="example-grpc-direct",
    environment="development",
    enable_metrics=True,
    enable_logs=True,
)

app = FastAPI()
tracer = trace.get_tracer(__name__)


@app.get("/ping")
def ping():
    with tracer.start_as_current_span("ping.handler") as span:
        span.set_attribute("transport", "grpc-direct")
        return {"pong": True, "transport": "grpc-direct"}
