import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from app.api.health import router as health_router
from app.api.products import router as product_router
from app.api.users import router as user_router
from app.core.exceptions import UserNotFoundException
from app.db.database import engine

logger = logging.getLogger(__name__)


def register_routes(app: FastAPI) -> None:
    app.include_router(user_router)
    app.include_router(product_router)
    app.include_router(health_router)


def setup_instrumentation(app: FastAPI) -> None:
    # HTTP framework — traces every incoming request automatically
    FastAPIInstrumentor.instrument_app(app)

    # Outgoing HTTP calls (requests library)
    RequestsInstrumentor().instrument()

    # SQLAlchemy — traces every query with db.statement, db.operation
    SQLAlchemyInstrumentor().instrument(engine=engine, enable_commenter=True)

    # psycopg2 — low-level PostgreSQL driver spans
    Psycopg2Instrumentor().instrument()

    # Redis — traces every get/set/del with db.statement
    RedisInstrumentor().instrument()

    logger.info("All instrumentors active: FastAPI, Requests, SQLAlchemy, psycopg2, Redis")


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UserNotFoundException)
    async def user_not_found_handler(request: Request, exc: UserNotFoundException):
        return JSONResponse(status_code=404, content={"error": exc.message})
