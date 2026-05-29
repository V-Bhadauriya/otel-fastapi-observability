# ---------------------------------------------------
# MAIN APPLICATION ENTRYPOINT
# ---------------------------------------------------
# This is the main startup file for the FastAPI app.
#
# Responsibilities:
# - initialize observability/tracing
# - configure instrumentation
# - register API routes
# - setup exception handling
# - start FastAPI application


import asyncio
import logging

# Console handler must be registered BEFORE setup_tracing() attaches the
# OTel LoggingHandler — basicConfig() is a no-op when handlers already exist.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

from fastapi import FastAPI

from app.core.config import settings
from app.db.database import engine, Base
import app.models.user_model  # noqa: F401 — registers model with Base

from app.telemetry.tracing import setup_tracing
from app.telemetry.generator import run_generator
from app.core.setup import register_routes, setup_instrumentation, setup_exception_handlers


# ---------------------------------------------------
# FASTAPI APPLICATION
# ---------------------------------------------------
# Creates FastAPI application instance.


app = FastAPI()


_generator_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    global _generator_task
    _generator_task = asyncio.create_task(run_generator())


@app.on_event("shutdown")
async def shutdown():
    if _generator_task:
        _generator_task.cancel()


# ---------------------------------------------------
# INITIALIZE OBSERVABILITY
# ---------------------------------------------------
# Initializes:
# - OpenTelemetry
# - Niriksha AI SDK
# - tracing/export pipeline
#
# This allows application telemetry data
# to be collected and exported.


setup_tracing()

logging.getLogger(__name__).info(
    "Telemetry active — mode: %s", settings.TELEMETRY_MODE
)


# ---------------------------------------------------
# SETUP INSTRUMENTATION
# ---------------------------------------------------
# Automatically traces:
# - incoming FastAPI requests
# - outgoing HTTP requests
#
# Observability platforms can then visualize:
# - request latency
# - spans/traces
# - request flow


setup_instrumentation(app)


# ---------------------------------------------------
# REGISTER ROUTES
# ---------------------------------------------------
# Connects all API routers/endpoints
# to FastAPI application.


register_routes(app)


# ---------------------------------------------------
# SETUP EXCEPTION HANDLERS
# ---------------------------------------------------
# Converts application exceptions into
# controlled API responses instead of
# raw crashes/unstructured errors.
#
# Example:
# returns HTTP 404 instead of internal failure.


setup_exception_handlers(app)


# ---------------------------------------------------
# HOME ENDPOINT
# ---------------------------------------------------
# Basic root endpoint used for
# testing application availability.


@app.get("/")

def home():

    return {

        "message": (

            "OPEN TELEMETRY FASTAPI APP"
        )

    }