from fastapi import APIRouter
from opentelemetry import trace

router = APIRouter(prefix="/api/v1", tags=["Health"])
tracer = trace.get_tracer(__name__)


@router.get("/health")
def health_check():
    with tracer.start_as_current_span("health.check") as span:
        span.set_attribute("health.status", "healthy")
        return {"status": "healthy"}
