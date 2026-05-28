import logging

from opentelemetry import metrics, trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------
# PUBLIC SETUP ENTRY POINT
# ---------------------------------------------------

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
            "Valid: grpc-direct, http-direct, grpc-collector, http-collector"
        )


# ---------------------------------------------------
# SHARED HELPERS
# ---------------------------------------------------

def _make_resource() -> Resource:
    return Resource.create({
        SERVICE_NAME: "otel-fastapi-service",
        "deployment.environment": settings.APP_ENV,
        "service.version": "1.0.0",
    })


def _init_traces(resource: Resource, exporter) -> None:
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def _init_metrics(resource: Resource, exporter) -> None:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    reader = PeriodicExportingMetricReader(
        exporter,
        export_interval_millis=30_000,
    )
    mp = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(mp)


def _init_logs(resource: Resource, exporter) -> None:
    from opentelemetry import _logs
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    lp = LoggerProvider(resource=resource)
    lp.add_log_record_processor(BatchLogRecordProcessor(exporter))
    _logs.set_logger_provider(lp)

    # attach to root Python logger so every logging.getLogger() call is exported
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=lp)
    logging.getLogger().addHandler(handler)


# ---------------------------------------------------
# grpc-direct
# ---------------------------------------------------
# All three signals over gRPC/TLS directly to
# grpc-ingest.niriksha.ai:443.
#
# Note: the nirikshaai SDK (dev9) builds the gRPC
# endpoint as "grpc://host:port" which the OTel
# exporter treats as plaintext and fails against
# Niriksha's TLS-only port 443. We bypass the SDK
# and use raw OTel exporters with explicit
# ssl_channel_credentials.

def _setup_grpc_direct() -> None:
    import grpc
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    endpoint = settings.NIRIKSHA_GRPC_ENDPOINT
    creds = grpc.ssl_channel_credentials()
    headers = {"x-api-key": settings.NIRIKSHA_API_KEY or ""}
    resource = _make_resource()

    _init_traces(resource, OTLPSpanExporter(endpoint=endpoint, credentials=creds, headers=headers))
    _init_metrics(resource, OTLPMetricExporter(endpoint=endpoint, credentials=creds, headers=headers))
    _init_logs(resource, OTLPLogExporter(endpoint=endpoint, credentials=creds, headers=headers))


# ---------------------------------------------------
# http-direct
# ---------------------------------------------------
# All three signals over OTLP HTTP directly to
# https://ingest.niriksha.ai/{signal}.

def _setup_http_direct() -> None:
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    base = settings.NIRIKSHA_HTTP_ENDPOINT
    headers = {"X-API-Key": settings.NIRIKSHA_API_KEY or ""}
    resource = _make_resource()

    _init_traces(resource, OTLPSpanExporter(endpoint=f"{base}/v1/traces", headers=headers))
    _init_metrics(resource, OTLPMetricExporter(endpoint=f"{base}/v1/metrics", headers=headers))
    _init_logs(resource, OTLPLogExporter(endpoint=f"{base}/v1/logs", headers=headers))


# ---------------------------------------------------
# grpc-collector
# ---------------------------------------------------
# All three signals over gRPC to the OTel Collector.
# No API key — collector handles auth with Niriksha.

def _setup_grpc_collector() -> None:
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    endpoint = settings.OTEL_COLLECTOR_GRPC_ENDPOINT
    resource = _make_resource()

    _init_traces(resource, OTLPSpanExporter(endpoint=endpoint, insecure=True))
    _init_metrics(resource, OTLPMetricExporter(endpoint=endpoint, insecure=True))
    _init_logs(resource, OTLPLogExporter(endpoint=endpoint, insecure=True))


# ---------------------------------------------------
# http-collector
# ---------------------------------------------------
# All three signals over HTTP to the OTel Collector.
# No API key — collector handles auth with Niriksha.

def _setup_http_collector() -> None:
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    base = settings.OTEL_COLLECTOR_HTTP_ENDPOINT
    resource = _make_resource()

    _init_traces(resource, OTLPSpanExporter(endpoint=f"{base}/v1/traces"))
    _init_metrics(resource, OTLPMetricExporter(endpoint=f"{base}/v1/metrics"))
    _init_logs(resource, OTLPLogExporter(endpoint=f"{base}/v1/logs"))


# ---------------------------------------------------
# GLOBAL TRACER & METER
# Used throughout the application via import.
# Both are proxies — they delegate to whichever
# provider setup_tracing() installs.
# ---------------------------------------------------

tracer = trace.get_tracer("otel-fastapi-service")
meter = metrics.get_meter("otel-fastapi-service")
