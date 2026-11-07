import os
import time
import json
import logging
import threading
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2 import pool
import redis

# Configure logging with standard timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("shop-api")

app = FastAPI(title="CloudSneakers Shop API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from Environment
DB_HOST = os.getenv("DB_HOST", "shop-postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "shopdb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "shoppassword")
REDIS_HOST = os.getenv("REDIS_HOST", "shop-redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Global states
db_pool: Optional[pool.SimpleConnectionPool] = None
redis_client: Optional[redis.Redis] = None

# Chaos/Leak states
MEMORY_LEAK_BUFFER: List[bytes] = []
LEAKED_DB_CONNECTIONS: List[Any] = []
IS_DB_LEAK_ACTIVE = False
IS_CPU_BURN_ACTIVE = False

# Baseline products
INITIAL_PRODUCTS = [
    {"name": "Air Kinetic SRE Pro", "price": 189.99, "icon": "👟", "desc": "Adaptive carbon fiber plate with telemetry dampening midsole."},
    {"name": "VaporMax Kubernetes Edition", "price": 219.00, "icon": "⚡", "desc": "Zero-latency air cushion designed for high-throughput sprints."},
    {"name": "Zoom Pegasus Zero-Downtime", "price": 145.50, "icon": "🏃", "desc": "High-mileage daily trainer with multi-region grip matrix."},
    {"name": "Infinity Run Vector Runner", "price": 169.95, "icon": "🎯", "desc": "Supportive rocker geometry preventing early fatigue crashes."},
    {"name": "Invincible 3 Thundering Herd", "price": 199.99, "icon": "🔥", "desc": "Maximum stack height engineered to withstand severe shockwaves."},
    {"name": "Metcon Turbo Quota Burner", "price": 155.00, "icon": "🏋️", "desc": "Reinforced heel clip for heavy duty multi-thread workouts."}
]


def init_db():
    """Initializes PostgreSQL connection pool and tables with retries."""
    global db_pool
    for attempt in range(15):
        try:
            logger.info(f"Connecting to PostgreSQL at {DB_HOST}:{DB_PORT} (Attempt {attempt+1}/15)...")
            db_pool = pool.SimpleConnectionPool(
                minconn=2,
                maxconn=25,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                connect_timeout=3
            )
            
            # Setup tables
            conn = db_pool.getconn()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(120) NOT NULL,
                    price NUMERIC(10, 2) NOT NULL,
                    icon VARCHAR(20),
                    description TEXT
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    total_amount NUMERIC(10, 2) NOT NULL,
                    items_count INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

            # Seed if empty
            cur.execute("SELECT COUNT(*) FROM products;")
            count = cur.fetchone()[0]
            if count == 0:
                for p in INITIAL_PRODUCTS:
                    cur.execute(
                        "INSERT INTO products (name, price, icon, description) VALUES (%s, %s, %s, %s)",
                        (p["name"], p["price"], p["icon"], p["desc"])
                    )
                conn.commit()
                logger.info("Successfully seeded product catalog into PostgreSQL.")

            cur.close()
            db_pool.putconn(conn)
            logger.info("PostgreSQL initialization complete and connection pool ready.")
            break
        except Exception as e:
            logger.warning(f"Postgres not ready yet ({e}). Retrying in 2 seconds...")
            time.sleep(2)


def init_redis():
    """Initializes Redis client."""
    global redis_client
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
            decode_responses=True
        )
        redis_client.ping()
        logger.info(f"Connected to Redis cache at {REDIS_HOST}:{REDIS_PORT}.")
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {e}")


@app.on_event("startup")
def startup_event():
    threading.Thread(target=init_db, daemon=True).start()
    init_redis()


# --- Pydantic Models ---
class CheckoutItem(BaseModel):
    id: int
    name: str
    price: float

class CheckoutPayload(BaseModel):
    items: List[CheckoutItem]
    total_amount: float


# --- SRE Deep Health Check ---
@app.get("/health")
def healthcheck():
    """
    SRE Deep Dependency Health Check.
    Validates PostgreSQL connection, Redis ping, and heap memory limits.
    """
    health_status = {
        "status": "healthy",
        "service": "shop-api",
        "postgres": "unknown",
        "redis": "unknown",
        "active_db_leak": IS_DB_LEAK_ACTIVE,
        "memory_leak_mb": len(MEMORY_LEAK_BUFFER) * 50
    }

    # 1. Check PostgreSQL
    if db_pool:
        try:
            conn = db_pool.getconn()
            cur = conn.cursor()
            cur.execute("SELECT 1;")
            cur.fetchone()
            cur.close()
            db_pool.putconn(conn)
            health_status["postgres"] = "connected"
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["postgres"] = f"failed: {str(e)}"
            logger.error(f"PostgreSQL health check failure: {e}")
    else:
        health_status["status"] = "unhealthy"
        health_status["postgres"] = "pool_not_initialized"

    # 2. Check Redis
    try:
        if redis_client and redis_client.ping():
            health_status["redis"] = "connected"
        else:
            raise ConnectionError("Redis ping did not return PONG")
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["redis"] = f"failed: {str(e)}"
        logger.warning(f"Redis health check failed: {e}")

    # 3. Check Memory Leak
    current_leak = len(MEMORY_LEAK_BUFFER) * 50
    if current_leak >= 350:
        health_status["status"] = "unhealthy"
        health_status["memory"] = f"Exceeded threshold: {current_leak}MB / 512MB"

    # 4. Check DB Connection Starvation
    if IS_DB_LEAK_ACTIVE or len(LEAKED_DB_CONNECTIONS) > 10:
        health_status["status"] = "unhealthy"
        health_status["postgres"] = f"Connection pool exhausted ({len(LEAKED_DB_CONNECTIONS)} connections held open without release)"

    # 5. Check CPU Throttling Burn
    if IS_CPU_BURN_ACTIVE:
        health_status["status"] = "degraded"
        health_status["cpu"] = "CFS CPU Quota throttled: High compute burn active (98% CPU saturation)"

    # Return 503 if not fully healthy
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_status)

    return health_status


# --- Storefront Catalog ---
@app.get("/api/products")
def get_products():
    """
    Retrieves product catalog.
    Checks Redis cache first. If cache miss or Redis down, stamps direct query to Postgres.
    """
    # 1. Attempt Redis Cache
    if redis_client:
        try:
            cached = redis_client.get("products:catalog")
            if cached:
                return {"source": "redis_cache", "products": json.loads(cached)}
        except Exception as e:
            logger.error(f"redis.exceptions.ConnectionError: Connection to redis://{REDIS_HOST}:{REDIS_PORT} timed out after 2000ms. Connection refused.")
            logger.warning("Cache miss stampede: Fallback query storm initiated against postgres primary.")

    # 2. Fallback to PostgreSQL
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database initializing")

    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, price, icon, description FROM products;")
        rows = cur.fetchall()
        cur.close()
        db_pool.putconn(conn)

        products = [
            {"id": r[0], "name": r[1], "price": float(r[2]), "icon": r[3], "desc": r[4]}
            for r in rows
        ]

        # Write to cache if Redis is accessible
        if redis_client:
            try:
                redis_client.setex("products:catalog", 30, json.dumps(products))
            except Exception:
                pass

        return {"source": "postgres_direct", "products": products}
    except Exception as e:
        logger.error(f"psycopg2.OperationalError: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failure: {str(e)}")


# --- Checkout / Order Endpoint ---
@app.post("/api/checkout")
def checkout(payload: CheckoutPayload):
    """
    Creates order in database.
    If database leak is triggered, connection is deliberately held open and never closed.
    """
    global LEAKED_DB_CONNECTIONS
    
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database initializing")

    # If DB leak attack is active, acquire extra raw socket connections without releasing
    if IS_DB_LEAK_ACTIVE:
        try:
            raw_conn = psycopg2.connect(
                host=DB_HOST, port=DB_PORT, database=DB_NAME,
                user=DB_USER, password=DB_PASSWORD, connect_timeout=2
            )
            LEAKED_DB_CONNECTIONS.append(raw_conn)
            logger.warning(f"ConnectionPool: Active connections leaking! Held open: {len(LEAKED_DB_CONNECTIONS)}/100")
        except Exception as e:
            logger.error(f"psycopg2.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections (max_connections=100)")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FATAL: remaining connection slots are reserved for non-replication superuser connections (max_connections=100)"
            )

    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO orders (total_amount, items_count) VALUES (%s, %s) RETURNING id;",
            (payload.total_amount, len(payload.items))
        )
        order_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        db_pool.putconn(conn)

        return {"status": "confirmed", "order_id": order_id, "amount": payload.total_amount}
    except Exception as e:
        logger.error(f"django.db.utils.OperationalError: could not connect to server: Connection refused. Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Checkout failed: {str(e)}"
        )


# =========================================================================
# INTERNAL REAL FAULT INJECTION (Triggered Headless by Chaos Daemon)
# =========================================================================

@app.post("/internal/fault/memory")
def trigger_memory_leak():
    """
    Allocates real 50MB byte buffers in a loop until container approaches
    the 512MB cgroup limit. Logs Linux OOM Killer SIGKILL (Exit code 137) and triggers 503.
    """
    global MEMORY_LEAK_BUFFER
    logger.info("Chaos Engine: Initiating unconstrained memory leak buffer...")

    try:
        for block_idx in range(12):
            chunk = b"X" * (50 * 1024 * 1024)
            MEMORY_LEAK_BUFFER.append(chunk)
            current_mb = len(MEMORY_LEAK_BUFFER) * 50
            logger.warning(f"High heap memory consumption: Allocated {current_mb}MB working set memory (Exceeded 512MB limit in app.py)")
            time.sleep(0.2)
            if current_mb >= 450:
                logger.error("Traceback (most recent call last):")
                logger.error('  File "main.py", line 328, in trigger_memory_leak')
                logger.error('    chunk = b"X" * (50 * 1024 * 1024)')
                logger.error(f"MemoryError: Out of memory: Allocated {current_mb}MB working set memory (Exceeded 512MB limit in app.py)")
                logger.fatal("Process terminated with SIGKILL (Exit code 137). Linux OOM Killer invoked.")
                break
    except MemoryError:
        logger.error("Traceback (most recent call last):")
        logger.error('  File "main.py", line 265, in trigger_memory_leak')
        logger.error('    chunk = b"X" * (50 * 1024 * 1024)')
        logger.error("MemoryError: Out of memory: Allocated 450MB working set memory (Exceeded 512MB limit in app.py)")
        logger.fatal("Process terminated with SIGKILL (Exit code 137). Linux OOM Killer invoked.")

    return {"status": "memory_leak_executed", "allocated_mb": len(MEMORY_LEAK_BUFFER) * 50}


@app.post("/internal/fault/db-leak")
def trigger_db_connection_starvation():
    """
    Starves the PostgreSQL connection pool to 100/100 capacity with unreleased connections.
    """
    global IS_DB_LEAK_ACTIVE, LEAKED_DB_CONNECTIONS
    IS_DB_LEAK_ACTIVE = True
    logger.info("Chaos Engine: Triggering PostgreSQL connection pool saturation...")

    acquired = 0
    for i in range(110):
        try:
            raw_conn = psycopg2.connect(
                host=DB_HOST, port=DB_PORT, database=DB_NAME,
                user=DB_USER, password=DB_PASSWORD, connect_timeout=1
            )
            LEAKED_DB_CONNECTIONS.append(raw_conn)
            acquired += 1
        except Exception as e:
            logger.error("Traceback (most recent call last):")
            logger.error('  File "main.py", line 290, in trigger_db_connection_starvation')
            logger.error('    raw_conn = psycopg2.connect(...)')
            logger.error("psycopg2.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections (max_connections=100)")
            logger.error("HTTP 500 / 504 Gateway Timeout: Worker thread failed to acquire PostgreSQL backend connection within 30000ms.")
            break

    return {"status": "db_starvation_active", "leaked_connections": acquired}


@app.post("/internal/fault/cpu")
def trigger_cpu_saturation():
    """
    Spins up compute worker threads to saturate 100% of container CPU under CFS quota.
    """
    global IS_CPU_BURN_ACTIVE
    IS_CPU_BURN_ACTIVE = True
    logger.info("Chaos Engine: Burning container CPU cores under Linux CFS quota...")

    def burn_core():
        start = time.time()
        while time.time() - start < 15 and IS_CPU_BURN_ACTIVE:
            _ = [x**2 for x in range(20000)]
        logger.warning("CFS throttling periods hit 76%. Requests hanging past 15000ms threshold.")

    threads = [threading.Thread(target=burn_core, daemon=True) for _ in range(4)]
    for t in threads:
        t.start()

    logger.error("Traceback (most recent call last):")
    logger.error('  File "main.py", line 325, in trigger_cpu_saturation')
    logger.error('    res = worker_task.compute_hash_batch(threads=4)')
    logger.error("TimeoutError: CFS CPU Quota throttled: Thread pool frozen at 98% CPU utilization in app.py")

    return {"status": "cpu_burn_active", "threads": 4}


@app.post("/internal/fault/reset")
def reset_faults():
    """Reclaims resources and restores baseline operation."""
    global MEMORY_LEAK_BUFFER, LEAKED_DB_CONNECTIONS, IS_DB_LEAK_ACTIVE, IS_CPU_BURN_ACTIVE
    
    MEMORY_LEAK_BUFFER.clear()
    import gc
    gc.collect()
    IS_DB_LEAK_ACTIVE = False
    IS_CPU_BURN_ACTIVE = False

    # Close leaked DB connections
    closed = 0
    for conn in LEAKED_DB_CONNECTIONS:
        try:
            conn.close()
            closed += 1
        except Exception:
            pass
    LEAKED_DB_CONNECTIONS.clear()

    logger.info(f"Chaos Engine: System restored to healthy baseline. Reclaimed {closed} DB sockets.")
    return {"status": "reset_complete", "closed_connections": closed}

