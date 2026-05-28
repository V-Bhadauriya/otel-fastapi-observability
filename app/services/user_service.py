import json
import logging

import redis as redis_lib
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user_model import User
from app.telemetry.tracing import meter, tracer

logger = logging.getLogger(__name__)

# ---------------------------------------------------
# REDIS CLIENT
# ---------------------------------------------------

redis_client = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)
CACHE_KEY = "users"
CACHE_TTL = 300  # seconds

# ---------------------------------------------------
# METRICS
# ---------------------------------------------------

cache_hits = meter.create_counter(
    "cache.hits",
    unit="1",
    description="Number of times user list was served from Redis cache",
)
cache_misses = meter.create_counter(
    "cache.misses",
    unit="1",
    description="Number of times Redis cache was empty and DB was queried",
)
db_queries = meter.create_counter(
    "db.queries",
    unit="1",
    description="Number of database SELECT queries executed",
)
users_created = meter.create_counter(
    "users.created",
    unit="1",
    description="Number of users created",
)
cache_size = meter.create_up_down_counter(
    "cache.entries",
    unit="1",
    description="Current number of entries held in Redis cache",
)


# ---------------------------------------------------
# CACHE HELPERS
# ---------------------------------------------------

async def check_cache() -> list[str] | None:
    with tracer.start_as_current_span("cache.check") as span:
        try:
            raw = redis_client.get(CACHE_KEY)
        except redis_lib.RedisError as exc:
            logger.warning("Redis unavailable during cache check: %s", exc)
            span.set_attribute("cache.error", str(exc))
            return None

        if raw:
            users = json.loads(raw)
            span.set_attribute("cache.hit", True)
            span.set_attribute("cache.key", CACHE_KEY)
            span.add_event("Cache HIT")
            cache_hits.add(1, {"cache.key": CACHE_KEY})
            logger.info("Cache HIT for key=%s count=%d", CACHE_KEY, len(users))
            return users

        span.set_attribute("cache.hit", False)
        span.set_attribute("cache.key", CACHE_KEY)
        span.add_event("Cache MISS")
        cache_misses.add(1, {"cache.key": CACHE_KEY})
        logger.info("Cache MISS for key=%s", CACHE_KEY)
        return None


async def write_cache(users: list[str]) -> None:
    with tracer.start_as_current_span("cache.write") as span:
        try:
            redis_client.setex(CACHE_KEY, CACHE_TTL, json.dumps(users))
            span.set_attribute("cache.key", CACHE_KEY)
            span.set_attribute("cache.ttl", CACHE_TTL)
            cache_size.add(1)
        except redis_lib.RedisError as exc:
            logger.warning("Redis unavailable during cache write: %s", exc)
            span.set_attribute("cache.error", str(exc))


async def invalidate_cache() -> None:
    with tracer.start_as_current_span("cache.invalidate") as span:
        try:
            redis_client.delete(CACHE_KEY)
            span.set_attribute("cache.key", CACHE_KEY)
            cache_size.add(-1)
            logger.info("Cache invalidated for key=%s", CACHE_KEY)
        except redis_lib.RedisError as exc:
            logger.warning("Redis unavailable during cache invalidate: %s", exc)
            span.set_attribute("cache.error", str(exc))


# ---------------------------------------------------
# DATABASE HELPERS
# ---------------------------------------------------

async def query_database(db: Session) -> list[str]:
    with tracer.start_as_current_span("db.query.users") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.operation", "SELECT")
        span.set_attribute("db.sql.table", "users")

        logger.info("Executing SELECT on users table")
        db_queries.add(1, {"db.operation": "SELECT", "db.table": "users"})

        rows = db.query(User).all()
        names = [u.name for u in rows]

        span.set_attribute("db.rows_returned", len(names))
        return names


# ---------------------------------------------------
# SERVICE FUNCTIONS
# ---------------------------------------------------

async def fetch_users(db: Session) -> list[str]:
    cached = await check_cache()
    if cached is not None:
        return cached

    users = await query_database(db)
    await write_cache(users)
    return users


async def create_new_user(name: str, db: Session) -> dict:
    with tracer.start_as_current_span("user.create") as span:
        span.set_attribute("user.name", name)

        with tracer.start_as_current_span("db.insert.user") as db_span:
            db_span.set_attribute("db.system", "postgresql")
            db_span.set_attribute("db.operation", "INSERT")
            db_span.set_attribute("db.sql.table", "users")

            logger.info("Creating new user: %s", name)
            db_queries.add(1, {"db.operation": "INSERT", "db.table": "users"})

            new_user = User(name=name)
            db.add(new_user)
            db.commit()

        users_created.add(1)
        await invalidate_cache()

        return {"message": f"{name} added successfully"}
