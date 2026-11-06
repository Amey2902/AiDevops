# Runbook: Investigating Container OOMKilled (Exit Code 137)

## Overview
When a container exceeds its configured memory limit or when the host operating system runs critically low on memory, the Linux kernel Out-Of-Memory (OOM) Killer terminates the offending process. Docker / Kubernetes reports this container termination with **Exit Code 137** (`128 + SIGKILL (9)`).

## Symptoms & Indicators
1. **Container State**:
   - Exit code: `137`
   - OOMKilled flag: `true` (visible in `docker inspect` or `kubectl describe pod`)
   - Container restart count increments abruptly.
2. **Prometheus Metrics**:
   - `container_memory_working_set_bytes` steadily climbing towards `container_spec_memory_limit_bytes`.
   - Sharp cliff drop in memory usage at the exact timestamp of container termination.
   - High swap usage if swap is enabled on host.
3. **Application Logs**:
   - Abrupt cessation of log activity without graceful shutdown messages.
   - Possible preceding `java.lang.OutOfMemoryError: Java heap space` (JVM) or `JavaScript heap out of memory` (Node.js) or Python `MemoryError`.
4. **Kernel Logs (`dmesg` / `syslog`)**:
   - `invoked oom-killer: gfp_mask=...`
   - `Killed process <pid> (<process_name>) total-vm:... anon-rss:...`

## Diagnostic Workflow
1. **Inspect Container Termination Reason**:
   - Check if `OOMKilled: true` is present in Docker/container inspect state.
   - Note the last known memory reading before exit.
2. **Analyze Memory Telemetry**:
   - Query Prometheus: `container_memory_usage_bytes{name="<container_name>"}` over the last 1 hour.
   - Differentiate between a gradual linear climb (memory leak) vs a sudden spike (unbounded batch payload processing).
3. **Correlate with Application Traffic**:
   - Check request rate: `rate(http_requests_total[5m])`. Did traffic surge, or did memory climb on steady traffic?

## Recommended Remediation Steps
### Immediate Mitigation (Short-term)
- Temporarily increase the container memory limit (e.g. increase from 512MB to 1GB or 2GB) to restore service availability.
- Scale out replicas if using an orchestrator to distribute request load and memory footprint.
- Restart the container to reclaim leaked heap memory.

### Root Cause Resolution (Long-term)
- Profile application memory allocations to identify memory leaks (e.g. unclosed connections, unmanaged global caches, circular references).
- Implement streaming/chunked processing for large file uploads or database bulk queries rather than buffering in-memory.
- Configure runtime-specific memory boundaries (e.g. JVM `-Xmx`, Node.js `--max-old-space-size`) below the container cgroup limit to allow graceful logging before kernel kills.
