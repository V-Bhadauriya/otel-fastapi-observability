import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings

logger = logging.getLogger(__name__)


def setup_tracing() -> None:
    mode = settings.TELEMETRY_MODE
    logger.info("Initializing telemetry — mode: %s", mode)

    if mode == "grpc-direct":
        _setup_grpc_direct()
    elif mode == "http-direct":
        _setup_http_direct()
    elif mode == "grpc-collector":
        _setup_grpc_collector()
    elif mode == "http-collector":
        _setup_http_collector()
    else:
        raise ValueError(
            f"Unknown TELEMETRY_MODE '{mode}'. "
            "Valid values: grpc-direct, http-direct, grpc-collector, http-collector"
        )


# ---------------------------------------------------
# grpc-direct
# ---------------------------------------------------
# Uses the Niriksha SDK which handles TracerProvider
# setup internally and exports via gRPC/TLS to
# grpc-ingest.niriksha.ai:443.

def _setup_grpc_direct() -> None:
    import nirikshaai

    nirikshaai.init(
        endpoint="https://app.niriksha.ai",
        otlp_endpoint=settings.NIRIKSHA_GRPC_ENDPOINT,
        api_key=settings.NIRIKSHA_API_KEY,
        service_name="otel-fastapi-service",
        environment=settings.APP_ENV,
        enable_llm=True,
        enable_metrics=True,
        enable_logs=True,
    )


# ---------------------------------------------------
# http-direct
# ---------------------------------------------------
# Bypasses the Niriksha SDK and uses a raw
# OTLP HTTP exporter pointed directly at
# https://ingest.niriksha.ai/v1/traces.
# Authentication is via the X-API-Key header.

def _setup_http_direct() -> None:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )

    resource = Resource.create({SERVICE_NAME: "otel-fastapi-service"})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(
        endpoint=f"{settings.NIRIKSHA_HTTP_ENDPOINT}/v1/traces",
        headers={"X-API-Key": settings.NIRIKSHA_API_KEY or ""},
    )

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


# ---------------------------------------------------
# grpc-collector
# ---------------------------------------------------
# Sends OTLP spans over gRPC to a locally running
# OTel Collector (otel-collector:4317).
# The collector is responsible for forwarding to
# Niriksha AI with authentication.
# No API key is needed on the app side.

def _setup_grpc_collector() -> None:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )

    resource = Resource.create({SERVICE_NAME: "otel-fastapi-service"})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_COLLECTOR_GRPC_ENDPOINT,
        insecure=True,
    )

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


# ---------------------------------------------------
# http-collector
# ---------------------------------------------------
# Sends OTLP spans over HTTP to a locally running
# OTel Collector (http://otel-collector:4318/v1/traces).
# The collector forwards to Niriksha AI via gRPC.

def _setup_http_collector() -> None:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )

    resource = Resource.create({SERVICE_NAME: "otel-fastapi-service"})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(
        endpoint=f"{settings.OTEL_COLLECTOR_HTTP_ENDPOINT}/v1/traces",
    )

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


tracer = trace.get_tracer(__name__)
