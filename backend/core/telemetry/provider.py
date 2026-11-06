import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import requests

class TelemetryProvider:
    """Base interface for telemetry sources."""
    def get_metrics(self, service_name: str, metric_type: str, window_minutes: int = 15) -> Dict[str, Any]:
        raise NotImplementedError

    def get_logs(self, service_name: str, log_level: str = "ERROR", limit: int = 50, keyword: str = "") -> List[Dict[str, Any]]:
        raise NotImplementedError

    def get_container_status(self, service_name: str) -> Dict[str, Any]:
        raise NotImplementedError


class SimulationTelemetryProvider(TelemetryProvider):
    """
    High-fidelity simulation telemetry engine.
    Generates realistic time-series metrics, structured logs, and container states
    for chaos scenarios (OOMKilled, DB connection leak, CPU throttling).
    """

    def __init__(self, active_scenario: str = "oom_memory_leak"):
        self.active_scenario = active_scenario

    def set_scenario(self, scenario_name: str):
        self.active_scenario = scenario_name

    def get_metrics(self, service_name: str, metric_type: str, window_minutes: int = 15) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        timestamps = [(now - timedelta(minutes=i)).strftime("%H:%M") for i in range(window_minutes, -1, -1)]

        if self.active_scenario == "oom_memory_leak":
            if metric_type in ["memory", "ram", "container_memory_working_set_bytes"]:
                # Climbing from 150MB to 512MB limit, then sharp drop
                values = [150 + i * 24 for i in range(len(timestamps) - 2)] + [512, 120]
                return {
                    "metric": "container_memory_working_set_bytes_mb",
                    "unit": "MB",
                    "limit_mb": 512,
                    "timestamps": timestamps,
                    "values": values,
                    "anomaly_detected": True,
                    "anomaly_details": "Memory usage saturated 512MB container limit at 99.8% before sharp cliff drop (crash restart)."
                }
            elif metric_type in ["cpu", "container_cpu_usage_seconds_total"]:
                values = [25 + (i % 5) * 4 for i in range(len(timestamps))]
                return {
                    "metric": "cpu_utilization_percent",
                    "unit": "%",
                    "timestamps": timestamps,
                    "values": values,
                    "anomaly_detected": False
                }
            elif metric_type in ["errors", "http_requests_total"]:
                values = [0 if i < len(timestamps) - 4 else 18 for i in range(len(timestamps))]
                return {
                    "metric": "http_5xx_errors_per_minute",
                    "unit": "errors/min",
                    "timestamps": timestamps,
                    "values": values,
                    "anomaly_detected": True
                }

        elif self.active_scenario == "db_connection_starvation":
            if metric_type in ["connections", "db_pool", "pg_stat_database_numbackends"]:
                values = [20 + i * 6 for i in range(len(timestamps) - 3)] + [100, 100, 100]
                return {
                    "metric": "postgres_active_connections",
                    "unit": "connections",
                    "max_connections": 100,
                    "timestamps": timestamps,
                    "values": values,
                    "anomaly_detected": True,
                    "anomaly_details": "Connection pool reached max limit of 100 connections with 88 idle in transaction."
                }
            elif metric_type in ["errors", "http_requests_total"]:
                values = [0 if i < len(timestamps) - 5 else 45 for i in range(len(timestamps))]
                return {
                    "metric": "http_500_errors_per_minute",
                    "unit": "errors/min",
                    "timestamps": timestamps,
                    "values": values,
                    "anomaly_detected": True
                }
            elif metric_type in ["latency", "p99_latency"]:
                values = [120 if i < len(timestamps) - 5 else 32000 for i in range(len(timestamps))]
                return {
                    "metric": "p99_latency_ms",
                    "unit": "ms",
                    "timestamps": timestamps,
                    "values": values,
                    "anomaly_detected": True,
                    "anomaly_details": "Latency jumped from 120ms to 32,000ms (32 seconds) due to connection wait timeouts."
                }

        elif self.active_scenario == "cpu_throttling":
            if metric_type in ["cpu", "container_cpu_usage_seconds_total"]:
                values = [40 if i < len(timestamps) - 6 else 98 for i in range(len(timestamps))]
                return {
                    "metric": "cpu_utilization_percent",
                    "unit": "%",
                    "timestamps": timestamps,
                    "values": values,
                    "anomaly_detected": True,
                    "anomaly_details": "CPU utilization hit 98% cap for container cgroup."
                }
            elif metric_type in ["throttling", "cfs_throttled"]:
                values = [0 if i < len(timestamps) - 6 else 76 for i in range(len(timestamps))]
                return {
                    "metric": "cfs_throttled_periods_percentage",
                    "unit": "%",
                    "timestamps": timestamps,
                    "values": values,
                    "anomaly_detected": True
                }

        # Fallback normal baseline
        values = [10 + (i % 3) * 5 for i in range(len(timestamps))]
        return {
            "metric": metric_type,
            "unit": "count",
            "timestamps": timestamps,
            "values": values,
            "anomaly_detected": False
        }

    def get_logs(self, service_name: str, log_level: str = "ERROR", limit: int = 50, keyword: str = "") -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        
        if self.active_scenario == "oom_memory_leak":
            return [
                {
                    "timestamp": (now - timedelta(minutes=4)).isoformat(),
                    "level": "WARN",
                    "service": service_name,
                    "message": "Memory heap utilization exceeded 85% threshold (435MB/512MB)."
                },
                {
                    "timestamp": (now - timedelta(minutes=3)).isoformat(),
                    "level": "WARN",
                    "service": service_name,
                    "message": "Garbage collection execution took 1820ms (> pause target)."
                },
                {
                    "timestamp": (now - timedelta(minutes=2)).isoformat(),
                    "level": "ERROR",
                    "service": service_name,
                    "message": "MemoryError: Unable to allocate 32.0 MiB buffer for batch transaction processing."
                },
                {
                    "timestamp": (now - timedelta(minutes=1)).isoformat(),
                    "level": "FATAL",
                    "service": service_name,
                    "message": "Process terminated by SIGKILL (Signal 9 / Exit Code 137). Linux OOM Killer invoked."
                },
                {
                    "timestamp": now.isoformat(),
                    "level": "INFO",
                    "service": service_name,
                    "message": "Container restarted by Docker daemon. Initializing worker threads..."
                }
            ]

        elif self.active_scenario == "db_connection_starvation":
            return [
                {
                    "timestamp": (now - timedelta(minutes=5)).isoformat(),
                    "level": "WARN",
                    "service": service_name,
                    "message": "ConnectionPool: Active connections 95/100, wait queue size: 14."
                },
                {
                    "timestamp": (now - timedelta(minutes=4)).isoformat(),
                    "level": "ERROR",
                    "service": service_name,
                    "message": "django.db.utils.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections"
                },
                {
                    "timestamp": (now - timedelta(minutes=3)).isoformat(),
                    "level": "ERROR",
                    "service": service_name,
                    "message": "TimeoutError: QueuePool limit of size 20 overflow 80 reached, connection timed out after 30.00 seconds"
                },
                {
                    "timestamp": (now - timedelta(minutes=2)).isoformat(),
                    "level": "ERROR",
                    "service": service_name,
                    "message": "Internal Server Error 500: Failed to checkout cart ID #94821 due to database pool exhaustion."
                }
            ]

        elif self.active_scenario == "cpu_throttling":
            return [
                {
                    "timestamp": (now - timedelta(minutes=5)).isoformat(),
                    "level": "WARN",
                    "service": service_name,
                    "message": "CFS Throttling: 78.4% of scheduling periods throttled on cgroup."
                },
                {
                    "timestamp": (now - timedelta(minutes=3)).isoformat(),
                    "level": "ERROR",
                    "service": service_name,
                    "message": "HTTP 504 Gateway Timeout: Worker thread failed to respond within 15000ms."
                },
                {
                    "timestamp": (now - timedelta(minutes=1)).isoformat(),
                    "level": "WARN",
                    "service": service_name,
                    "message": "Liveness probe failed: HTTP probe to /healthz timed out after 2 seconds."
                }
            ]

        return [
            {
                "timestamp": now.isoformat(),
                "level": "INFO",
                "service": service_name,
                "message": "Normal baseline application operation. No critical errors detected."
            }
        ]

    def get_container_status(self, service_name: str) -> Dict[str, Any]:
        if self.active_scenario == "oom_memory_leak":
            return {
                "container_id": f"cnt_{service_name}_d938fa",
                "service_name": service_name,
                "status": "restarting",
                "running": False,
                "restarting": True,
                "exit_code": 137,
                "oom_killed": True,
                "restart_count": 4,
                "memory_limit_bytes": 536870912,  # 512MB
                "memory_limit_human": "512MB",
                "cpu_limit": "1.0",
                "last_exit_reason": "OOMKilled: Linux kernel Out-Of-Memory Killer terminated process."
            }
        elif self.active_scenario == "db_connection_starvation":
            return {
                "container_id": f"cnt_{service_name}_b112fc",
                "service_name": service_name,
                "status": "running",
                "running": True,
                "restarting": False,
                "exit_code": 0,
                "oom_killed": False,
                "restart_count": 0,
                "memory_limit_human": "1GB",
                "cpu_limit": "2.0",
                "last_exit_reason": "Running healthy container state, but downstream connection pool saturated."
            }
        elif self.active_scenario == "cpu_throttling":
            return {
                "container_id": f"cnt_{service_name}_e448ab",
                "service_name": service_name,
                "status": "unhealthy",
                "running": True,
                "restarting": False,
                "exit_code": 0,
                "oom_killed": False,
                "restart_count": 1,
                "memory_limit_human": "1GB",
                "cpu_limit": "0.5",
                "last_exit_reason": "Readiness/Liveness probe timeout failure."
            }

        return {
            "container_id": f"cnt_{service_name}_0001",
            "service_name": service_name,
            "status": "running",
            "running": True,
            "restarting": False,
            "exit_code": 0,
            "oom_killed": False,
            "restart_count": 0
        }


class PrometheusTelemetryProvider(TelemetryProvider):
    """Live Prometheus HTTP Client."""
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("PROMETHEUS_URL", "http://localhost:9090")

    def get_metrics(self, service_name: str, metric_type: str, window_minutes: int = 15) -> Dict[str, Any]:
        query_map = {
            "memory": f'container_memory_working_set_bytes{{name=~".*{service_name}.*"}} / 1024 / 1024',
            "cpu": f'rate(container_cpu_usage_seconds_total{{name=~".*{service_name}.*"}}[5m]) * 100',
            "errors": f'rate(http_requests_total{{status=~"5..",service="{service_name}"}}[5m])',
        }
        query = query_map.get(metric_type, metric_type)
        try:
            resp = requests.get(f"{self.base_url}/api/v1/query", params={"query": query}, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                return {"metric": metric_type, "live_data": data, "anomaly_detected": False}
        except Exception as e:
            pass
        # Fallback to simulation if Prometheus is offline
        return SimulationTelemetryProvider().get_metrics(service_name, metric_type, window_minutes)

    def get_logs(self, service_name: str, log_level: str = "ERROR", limit: int = 50, keyword: str = "") -> List[Dict[str, Any]]:
        return SimulationTelemetryProvider().get_logs(service_name, log_level, limit, keyword)

    def get_container_status(self, service_name: str) -> Dict[str, Any]:
        return SimulationTelemetryProvider().get_container_status(service_name)


# Global singleton
_GLOBAL_TELEMETRY_PROVIDER: Optional[TelemetryProvider] = None

def get_telemetry_provider(force_simulation: bool = True) -> TelemetryProvider:
    global _GLOBAL_TELEMETRY_PROVIDER
    if _GLOBAL_TELEMETRY_PROVIDER is None:
        if force_simulation or not os.getenv("USE_LIVE_MONITORING"):
            _GLOBAL_TELEMETRY_PROVIDER = SimulationTelemetryProvider()
        else:
            _GLOBAL_TELEMETRY_PROVIDER = PrometheusTelemetryProvider()
    return _GLOBAL_TELEMETRY_PROVIDER
