"""
CloudSneakers Continuous Traffic Generator
Simulates realistic customer browsing and purchasing traffic against http://localhost:5001.
Produces natural baseline telemetry with realistic jitter.
"""

import time
import random
import requests
import sys
from datetime import datetime

TARGET_URL = "http://localhost:5001"

SAMPLE_ITEMS = [
    {"id": 1, "name": "Air Kinetic SRE Pro", "price": 189.99},
    {"id": 2, "name": "VaporMax Kubernetes Edition", "price": 219.00},
    {"id": 3, "name": "Zoom Pegasus Zero-Downtime", "price": 145.50},
    {"id": 4, "name": "Infinity Run Vector Runner", "price": 169.95},
    {"id": 5, "name": "Invincible 3 Thundering Herd", "price": 199.99},
    {"id": 6, "name": "Metcon Turbo Quota Burner", "price": 155.00}
]

def run_traffic_loop(rps: float = 8.0):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [TrafficGen] Starting background customer traffic (~{rps} req/sec)...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [TrafficGen] Target: {TARGET_URL} (Storefront, API, Checkout)")

    total_requests = 0
    ok_count = 0
    err_count = 0
    recent_latencies = []

    last_report_time = time.time()
    session = requests.Session()

    while True:
        try:
            start_t = time.time()
            action_roll = random.random()

            # 70% browse products, 20% health probe, 10% checkout purchase
            if action_roll < 0.70:
                resp = session.get(f"{TARGET_URL}/api/products", timeout=4)
            elif action_roll < 0.90:
                resp = session.get(f"{TARGET_URL}/health", timeout=3)
            else:
                item = random.choice(SAMPLE_ITEMS)
                payload = {
                    "items": [item],
                    "total_amount": item["price"]
                }
                resp = session.post(f"{TARGET_URL}/api/checkout", json=payload, timeout=6)

            elapsed_ms = (time.time() - start_t) * 1000.0
            recent_latencies.append(elapsed_ms)
            if len(recent_latencies) > 100:
                recent_latencies.pop(0)

            total_requests += 1
            if resp.status_code == 200:
                ok_count += 1
            else:
                err_count += 1

        except Exception as e:
            total_requests += 1
            err_count += 1
            recent_latencies.append(5000.0)

        # Periodic status banner every 5 seconds
        if time.time() - last_report_time >= 5.0:
            if recent_latencies:
                sorted_lat = sorted(recent_latencies)
                p95_lat = sorted_lat[int(len(sorted_lat) * 0.95)]
                avg_lat = sum(recent_latencies) / len(recent_latencies)
            else:
                p95_lat, avg_lat = 0, 0

            error_rate = (err_count / total_requests * 100.0) if total_requests > 0 else 0.0
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] [TrafficGen] "
                f"Sent: {total_requests:5d} | "
                f"200 OK: {ok_count:5d} | "
                f"Errors: {err_count:3d} ({error_rate:4.1f}%) | "
                f"Latency: {avg_lat:5.1f}ms (p95: {p95_lat:5.1f}ms)"
            )
            last_report_time = time.time()

        # Jitter interval around target RPS
        sleep_interval = (1.0 / rps) * random.uniform(0.7, 1.3)
        time.sleep(sleep_interval)

if __name__ == "__main__":
    target_rps = 8.0
    if len(sys.argv) > 1:
        try:
            target_rps = float(sys.argv[1])
        except ValueError:
            pass
    run_traffic_loop(target_rps)

