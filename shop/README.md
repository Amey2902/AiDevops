# CloudSneakers — Real High-Performance E-Commerce Target App

This is a production-grade multi-container e-commerce application built for realistic fault injection and autonomous SRE incident investigation by **DevOpsAI**.

---

## 🏗️ Architecture

* **`shop-nginx` (`http://localhost:5001`)**: Reverse proxy with SRE JSON access logging recording `$request_time` and `$upstream_response_time`.
* **`shop-api`**: High-performance FastAPI backend under Docker limits (`mem_limit: 512m`, `cpus: 0.5`, `restart: unless-stopped`).
* **`shop-postgres` (`localhost:5433`)**: PostgreSQL 16 database with `max_connections=100`.
* **`shop-redis` (`localhost:6380`)**: Redis 7 cache cluster.
* **Storefront UI**: Modern Sneaker storefront (`/static/index.html`) with interactive cart, live stock, and checkout. Zero attack buttons.

---

## 🚀 Quickstart Commands

### 1. Launch the Shop Stack
Ensure Docker Desktop is open, then run:
```bash
cd shop
docker compose up -d --build
```
Open **`http://localhost:5001`** in your browser to view the storefront!

---

### 2. Run Continuous Background Customer Traffic
Simulates 10-15 customers browsing, caching, and purchasing sneakers:
```bash
python shop/traffic_generator.py
```
Produces an organic baseline with natural variance on your telemetry graphs.

---

### 3. Run the Autonomous Headless Chaos Monkey
Runs silently in the background, automatically scheduling and injecting real faults:
```bash
python shop/chaos_daemon.py --auto --interval 180
```
Or fire an individual fault on demand:
```bash
# Memory Leak (Linux Kernel OOM SIGKILL Exit 137)
python shop/chaos_daemon.py --attack oom

# Database Connection Pool Starvation (100/100 slots exhausted)
python shop/chaos_daemon.py --attack db

# Redis Cache Cluster Failure (docker stop shop-redis)
python shop/chaos_daemon.py --attack redis

# Linux CFS CPU Quota Throttling (Pegs CPU to 98%)
python shop/chaos_daemon.py --attack cpu

# Restore healthy baseline
python shop/chaos_daemon.py --attack reset
```
*Note: Every fault is recorded into `shop/chaos_ground_truth.jsonl` for independent accuracy grading.*

---

### 4. Run the DevOpsAI Autonomous Watchdog
Listens to real Docker container telemetry, CFS throttling rates, and logs:
```bash
python backend/core/telemetry/docker_watcher.py
```

---

### 5. Benchmark & Accuracy Scorecard
Compares DevOpsAI's diagnoses against the ground truth:
```bash
python scripts/evaluate_accuracy.py
```

---

### 🛑 Clean Shutdown & Space Reclamation
Stops all containers and frees 100% of RAM and CPU:
```bash
docker compose down
```
To remove images and reclaim every byte of storage:
```bash
docker compose down --rmi all -v
```

