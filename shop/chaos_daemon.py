"""
Headless Chaos Monkey Daemon for CloudSneakers.
Silently injects real infrastructure and application faults on automated schedules or triggers.
Logs ground truth to private file `chaos_ground_truth.jsonl` for independent accuracy scoring.
"""

import os
import sys
import time
import json
import uuid
import random
import argparse
from datetime import datetime, timezone
import requests
try:
    import docker
except ImportError:
    docker = None

GROUND_TRUTH_FILE = os.path.join(os.path.dirname(__file__), "chaos_ground_truth.jsonl")
SHOP_BASE_URL = os.getenv("SHOP_BASE_URL", "http://localhost:5001")


def record_ground_truth(fault_type: str, target: str, details: str):
    """Writes private ground-truth entry that DevOpsAI never reads directly."""
    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fault_type": fault_type,
        "target_service": target,
        "details": details,
        "status": "injected"
    }
    with open(GROUND_TRUTH_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] Logged Ground Truth: {fault_type} on {target}")
    return entry


def get_docker_client():
    if not docker:
        return None
    try:
        return docker.from_env()
    except Exception as e:
        # Fallback to local named pipe on Windows
        try:
            return docker.DockerClient(base_url="npipe:////./pipe/docker_engine")
        except Exception:
            return None


# --- The 4 Real Injected Faults ---

def inject_oom_memory_leak():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] 🔥 Ingesting real OOM Memory Leak (Limit 512MB)...")
    record_ground_truth("OOM_MEMORY_LEAK", "shop-api", "Unbounded 50MB buffer allocation until Linux OOM Killer SIGKILL 137")
    try:
        resp = requests.post(f"{SHOP_BASE_URL}/internal/fault/memory", timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def inject_db_pool_exhaustion():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] 🔥 Ingesting PostgreSQL Connection Pool Starvation...")
    record_ground_truth("DB_CONNECTION_STARVATION", "shop-api", "Acquires 100 raw PostgreSQL connections without pool release")
    try:
        resp = requests.post(f"{SHOP_BASE_URL}/internal/fault/db-leak", timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def inject_cpu_saturation():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] 🔥 Ingesting Linux CFS CPU Quota Saturation...")
    record_ground_truth("CPU_THROTTLING_STARVATION", "shop-api", "Pegs 4 compute threads to trigger 78% CFS Quota Throttling")
    try:
        resp = requests.post(f"{SHOP_BASE_URL}/internal/fault/cpu", timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def inject_redis_outage():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] 🔥 Ingesting Redis Container Crash (docker stop shop-redis)...")
    record_ground_truth("REDIS_CACHE_TIMEOUT", "shop-redis", "Physical container stop causing cache miss stampede to PostgreSQL")
    import subprocess
    subprocess.run(["docker", "stop", "shop-redis"], capture_output=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] Successfully stopped container 'shop-redis'.")
    return {"status": "redis_stopped"}


def recover_all():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] 🔄 Restoring all services to healthy baseline...")
    import subprocess
    subprocess.run(["docker", "start", "shop-redis"], capture_output=True)

    # 1. Reset app internal leaks
    try:
        requests.post(f"{SHOP_BASE_URL}/internal/fault/reset", timeout=3)
    except Exception:
        pass

    # 2. Verify health; recycle shop-api if not 200 OK
    is_healthy = False
    for _ in range(3):
        try:
            r = requests.get(f"{SHOP_BASE_URL}/health", timeout=2)
            if r.status_code == 200:
                is_healthy = True
                break
        except Exception:
            pass
        time.sleep(1)

    if not is_healthy:
        subprocess.run(["docker", "restart", "shop-api"], capture_output=True)
        for _ in range(5):
            try:
                r = requests.get(f"{SHOP_BASE_URL}/health", timeout=2)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(1)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] Baseline recovery complete.")


def run_automated_loop(interval_sec: int = 10):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] Starting Fast Autonomous Chaos Monkey (Every {interval_sec}s)...")
    scenarios = ["oom", "db", "redis", "cpu"]
    scenario_idx = 0

    while True:
        choice = scenarios[scenario_idx % len(scenarios)]
        scenario_idx += 1

        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] ⚡ Ingesting automated attack: {choice.upper()}...")
        if choice == "oom":
            inject_oom_memory_leak()
        elif choice == "db":
            inject_db_pool_exhaustion()
        elif choice == "redis":
            inject_redis_outage()
        elif choice == "cpu":
            inject_cpu_saturation()

        # Allow 15s for DevOpsAI SRE Watchdog to detect
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] Fault active! Allowing 15s for DevOpsAI SRE detection...")
        time.sleep(15)

        # Recover system back to healthy green
        recover_all()

        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ChaosDaemon] System restored healthy. Waiting {interval_sec}s before next attack...\n")
        time.sleep(interval_sec)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CloudSneakers Headless Chaos Daemon")
    parser.add_argument("--attack", choices=["oom", "db", "redis", "cpu", "reset"], help="Inject a specific fault immediately")
    parser.add_argument("--auto", action="store_true", help="Run automated chaos loop on schedule")
    parser.add_argument("--interval", type=int, default=120, help="Interval between automated faults in seconds")

    args = parser.parse_args()

    if args.attack == "oom":
        inject_oom_memory_leak()
    elif args.attack == "db":
        inject_db_pool_exhaustion()
    elif args.attack == "redis":
        inject_redis_outage()
    elif args.attack == "cpu":
        inject_cpu_saturation()
    elif args.attack == "reset":
        recover_all()
    elif args.auto:
        run_automated_loop(args.interval)
    else:
        print("Usage: python chaos_daemon.py --attack [oom|db|redis|cpu|reset] OR python chaos_daemon.py --auto")

