# ---------------------------------------------------
# APPLICATION CONFIGURATION
# ---------------------------------------------------
# Centralized configuration management.
#
# This file loads environment variables
# from .env file and exposes them through
# a reusable Settings object.
#
# Keeping configuration centralized helps:
# - avoid hardcoding secrets
# - support multiple environments
# - simplify deployment configuration
#
# Example environments:
# - development
# - staging
# - production


from dotenv import load_dotenv

import os


# load environment variables from .env file
load_dotenv()


# ---------------------------------------------------
# SETTINGS CLASS
# ---------------------------------------------------
# Stores reusable application configuration values.
#
# Environment variables are used instead of
# hardcoding sensitive values directly in code.


class Settings:


    # database connection URL
    DATABASE_URL = os.getenv(

        "DATABASE_URL"
    )


    # Redis connection URL
    REDIS_URL = os.getenv(

        "REDIS_URL",

        "redis://localhost:6379/0"
    )

    # Niriksha AI API key used for
    # observability authentication
    NIRIKSHA_API_KEY = os.getenv(

        "NIRIKSHA_API_KEY"
    )

    # current application environment
    # defaults to "development"
    APP_ENV = os.getenv(

        "APP_ENV",

        "development"
    )

    # ---------------------------------------------------
    # TELEMETRY MODE
    # ---------------------------------------------------
    # Controls how telemetry data is exported.
    #
    # grpc-direct    — Niriksha SDK gRPC → grpc-ingest.niriksha.ai:443
    # http-direct    — OTLP HTTP        → ingest.niriksha.ai
    # grpc-collector — OTLP gRPC        → OTel Collector → Niriksha AI
    # http-collector — OTLP HTTP        → OTel Collector → Niriksha AI

    TELEMETRY_MODE = os.getenv(

        "TELEMETRY_MODE",

        "grpc-direct"
    )

    # Niriksha AI ingestion endpoints
    NIRIKSHA_GRPC_ENDPOINT = os.getenv(

        "NIRIKSHA_GRPC_ENDPOINT",

        "grpc-ingest.niriksha.ai:443"
    )

    NIRIKSHA_HTTP_ENDPOINT = os.getenv(

        "NIRIKSHA_HTTP_ENDPOINT",

        "https://ingest.niriksha.ai"
    )

    # OTel Collector endpoints
    # (used when TELEMETRY_MODE is grpc-collector or http-collector)
    OTEL_COLLECTOR_GRPC_ENDPOINT = os.getenv(

        "OTEL_COLLECTOR_GRPC_ENDPOINT",

        "otel-collector:4317"
    )

    OTEL_COLLECTOR_HTTP_ENDPOINT = os.getenv(

        "OTEL_COLLECTOR_HTTP_ENDPOINT",

        "http://otel-collector:4318"
    )


# reusable settings object
settings = Settings()