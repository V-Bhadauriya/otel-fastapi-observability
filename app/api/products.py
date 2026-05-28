from fastapi import APIRouter
from opentelemetry import trace

router = APIRouter(prefix="/api/v1", tags=["Products"])
tracer = trace.get_tracer(__name__)

PRODUCTS = ["Laptop", "Phone", "Keyboard"]


@router.get("/products")
def get_products():
    with tracer.start_as_current_span("products.list") as span:
        span.set_attribute("products.count", len(PRODUCTS))
        return {"products": PRODUCTS}
