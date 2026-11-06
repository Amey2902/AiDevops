# Runbook: CPU Throttling, CFS Quota Exhaustion & Thread Starvation

## Overview
Containers running on Linux with CPU limits enforced by the Completely Fair Scheduler (CFS) quota (`cpu.cfs_quota_us` and `cpu.cfs_period_us`) can experience severe CPU throttling even when average CPU utilization appears moderate. When threads are throttled, response times balloon, worker thread pools starve, and health check endpoints fail, leading to cascading HTTP 504 Gateway Timeouts.

## Symptoms & Indicators
1. **Prometheus Metrics**:
   - `container_cpu_cfs_throttled_periods_total / container_cpu_cfs_periods_total > 0.2` (>20% periods throttled).
   - High P95/P99 latency with low throughput.
   - CPU spikes reaching 100% of the assigned container limit (e.g. 1.0 or 2.0 cores).
2. **Application Symptoms**:
   - Thread pool exhaustion (`ThreadPoolExecutor`, Puma/Gunicorn worker timeouts).
   - Health check endpoints (`/healthz`, `/livez`) failing or timing out.
   - Synchronous network calls hanging waiting for worker CPU dispatch.
3. **Container State**:
   - Readiness probe failure events recorded.
   - Orchestrator killing and restarting pods due to failed liveness probes.

## Diagnostic Workflow
1. **Analyze Throttling Metrics**:
   - Query: `rate(container_cpu_cfs_throttled_periods_total{name="<container_name>"}[5m]) / rate(container_cpu_cfs_periods_total{name="<container_name>"}[5m]) * 100`.
   - Any rate above 10-15% indicates significant CFS quota throttling.
2. **Inspect Process CPU Profile**:
   - Check if heavy computational tasks (regex matching, cryptographic hashing, JSON parsing of huge payloads) are being performed on the HTTP request thread.
   - Check worker concurrency settings vs available CPU cores.

## Recommended Remediation Steps
### Immediate Mitigation (Short-term)
- Increase container CPU limit in `docker-compose.yml` or Kubernetes deployment manifest (e.g., increase `cpus: '0.5'` to `cpus: '2.0'`).
- In Kubernetes, remove CPU limits while keeping CPU requests (allowing burstability without CFS throttling).
- Scale horizontal replicas to distribute compute load across more CPU cores.

### Root Cause Resolution (Long-term)
- Offload heavy compute tasks to asynchronous Celery/Redis background worker queues.
- Optimize high-CPU hotspots identified in application profiling.
- Separate latency-critical HTTP request handling from background batch operations.
