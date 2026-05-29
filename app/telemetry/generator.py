"""
Continuous telemetry generator.

Runs as a background asyncio task and emits traces, metrics, and logs
on a fixed interval so Niriksha AI always has fresh data to display —
even when no real HTTP traffic is hitting the app.

Signals emitted every INTERVAL seconds:
  Traces  — simulated cache check, DB query, order processing spans
  Metrics — request counters, latency histograms, error rates, system gauges
  Logs    — INFO / WARNING / ERROR entries correlated to active spans
"""

import asyncio
import logging
import random
import time

from opentelemetry import metrics, trace

logger = logging.getLogger(__name__)

tracer = trace.get_tracer("telemetry.generator")
meter = metrics.get_meter("telemetry.generator")

INTERVAL = 10  # seconds between each emission cycle

# ── Metrics instruments ────────────────────────────────────────────────────────

request_counter = meter.create_counter(
    "http.server.requests",
    unit="1",
    description="Simulated incoming HTTP request count",
)
error_counter = meter.create_counter(
    "http.server.errors",
    unit="1",
    description="Simulated HTTP 5xx error count",
)
latency_histogram = meter.create_histogram(
    "http.server.duration",
    unit="ms",
    description="Simulated HTTP request latency",
)
active_users_gauge = meter.create_up_down_counter(
    "app.active_users",
    unit="1",
    description="Simulated number of active users",
)
db_query_counter = meter.create_counter(
    "db.queries.total",
    unit="1",
    description="Simulated database query count",
)
cache_hit_ratio = meter.create_histogram(
    "cache.hit_ratio",
    unit="1",
    description="Simulated cache hit ratio per cycle (0.0–1.0)",
)
queue_depth = meter.create_up_down_counter(
    "app.queue.depth",
    unit="1",
    description="Simulated background job queue depth",
)

# ── Simulation data ────────────────────────────────────────────────────────────

ENDPOINTS = [
    ("GET", "/api/v1/users"),
    ("GET", "/api/v1/products"),
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/users"),
]

DB_OPERATIONS = ["SELECT users", "SELECT products", "INSERT users", "UPDATE users"]


async def _emit_cycle() -> None:
    """One cycle: emit a batch of traces, metrics, and logs."""

    cycle_requests = random.randint(5, 20)
    cycle_errors = random.randint(0, 2)
    cycle_db_queries = random.randint(3, 10)
    hit_ratio = random.uniform(0.6, 0.98)
    active = random.randint(10, 200)
    q_delta = random.randint(-3, 5)

    # ── Traces ─────────────────────────────────────────────────────────────────
    with tracer.start_as_current_span("generator.cycle") as root:
        root.set_attribute("generator.requests", cycle_requests)
        root.set_attribute("generator.errors", cycle_errors)
        root.set_attribute("generator.db_queries", cycle_db_queries)

        # Simulate request processing spans
        for _ in range(min(cycle_requests, 5)):
            method, path = random.choice(ENDPOINTS)
            latency = random.uniform(5, 300)
            status = 500 if random.random() < 0.05 else 200

            with tracer.start_as_current_span("http.request") as span:
                span.set_attribute("http.method", method)
                span.set_attribute("http.route", path)
                span.set_attribute("http.status_code", status)
                span.set_attribute("http.duration_ms", round(latency, 2))
                if status >= 500:
                    span.set_status(trace.StatusCode.ERROR, "Internal Server Error")
                    logger.error("Simulated 500 on %s %s latency=%.0fms", method, path, latency)
                else:
                    logger.info("Simulated %s %s → %d latency=%.0fms", method, path, status, latency)

        # Simulate DB query spans
        with tracer.start_as_current_span("db.batch") as db_span:
            op = random.choice(DB_OPERATIONS)
            db_span.set_attribute("db.system", "postgresql")
            db_span.set_attribute("db.statement", op)
            db_span.set_attribute("db.rows", random.randint(0, 500))
            logger.info("Simulated DB: %s rows=%d", op, random.randint(0, 500))

        # Simulate cache span
        with tracer.start_as_current_span("cache.operation") as c_span:
            hit = random.random() < hit_ratio
            c_span.set_attribute("cache.hit", hit)
            c_span.set_attribute("cache.key", "users")
            if not hit:
                logger.warning("Simulated cache MISS — falling back to DB")

    # ── Metrics ────────────────────────────────────────────────────────────────
    for _ in range(cycle_requests):
        method, path = random.choice(ENDPOINTS)
        status_class = "5xx" if random.random() < 0.05 else "2xx"
        latency = random.uniform(5, 300)
        request_counter.add(1, {"http.method": method, "http.route": path, "http.status_class": status_class})
        latency_histogram.record(latency, {"http.method": method, "http.route": path})

    for _ in range(cycle_errors):
        method, path = random.choice(ENDPOINTS)
        error_counter.add(1, {"http.method": method, "http.route": path})

    db_query_counter.add(cycle_db_queries, {"db.system": "postgresql"})
    cache_hit_ratio.record(hit_ratio)
    active_users_gauge.add(active - getattr(_emit_cycle, "_last_active", 0))
    _emit_cycle._last_active = active  # type: ignore[attr-defined]
    queue_depth.add(q_delta)

    # ── Logs ───────────────────────────────────────────────────────────────────
    logger.info(
        "Generator cycle complete — requests=%d errors=%d db_queries=%d "
        "cache_hit_ratio=%.2f active_users=%d",
        cycle_requests, cycle_errors, cycle_db_queries, hit_ratio, active,
    )
    if cycle_errors > 0:
        logger.warning("Generator detected %d simulated errors this cycle", cycle_errors)


async def run_generator() -> None:
    """Loop forever, emitting one cycle every INTERVAL seconds."""
    logger.info("Continuous telemetry generator started — interval=%ds", INTERVAL)
    while True:
        try:
            await _emit_cycle()
        except Exception as exc:
            logger.error("Generator cycle failed: %s", exc)
        await asyncio.sleep(INTERVAL)
