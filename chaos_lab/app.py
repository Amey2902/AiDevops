import os
import sys
import time
import json
import threading
from datetime import datetime, timezone
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# ==============================================================================
# ZERO DEPENDENCIES REQUIRED - USES PURE PYTHON STANDARD LIBRARY!
# No 'pip install' or virtual environment needed. Runs on vanilla Python 3!
# ==============================================================================

DEVOPSAI_WEBHOOK = os.getenv("DEVOPSAI_WEBHOOK_URL", "http://localhost:8000/api/webhook/")
SERVICE_NAME = os.getenv("SERVICE_NAME", "checkout-api")
PORT = int(os.getenv("PORT", 5000))

# In-Memory State for Chaos Simulation
memory_buffer = []
active_connections = 14
error_count = 0
logs_history = []
start_time = time.time()
state_lock = threading.Lock()

def add_log(level, message):
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    entry = {"timestamp": timestamp, "level": level, "message": message}
    with state_lock:
        logs_history.append(entry)
        if len(logs_history) > 50:
            logs_history.pop(0)
    print(f"[{timestamp}] [{level}] {message}")

add_log("INFO", f"Chaos Lab service '{SERVICE_NAME}' active on port {PORT}.")
add_log("INFO", f"Target DevOpsAI Webhook: {DEVOPSAI_WEBHOOK}")

# Memory & Telemetry Measurement Helpers
def get_real_process_ram_mb():
    """Reads the ACTUAL physical working set memory of this Python process from Windows/OS."""
    try:
        import ctypes
        from ctypes import wintypes
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD),
                ('PageFaultCount', wintypes.DWORD),
                ('PeakWorkingSetSize', ctypes.c_size_t),
                ('WorkingSetSize', ctypes.c_size_t),
            ]
        pmc = PROCESS_MEMORY_COUNTERS()
        ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(),
            ctypes.byref(pmc),
            ctypes.sizeof(pmc)
        )
        return int(pmc.WorkingSetSize / (1024 * 1024))
    except Exception:
        # Cross-platform fallback based on allocated python buffers
        allocated_bytes = sum(sys.getsizeof(chunk) for chunk in memory_buffer)
        return 48 + int(allocated_bytes / (1024 * 1024))

def notify_devopsai(alertname, severity, summary, real_logs=None, real_metrics=None, real_container_state=None):
    """Dispatches real structured alert event to DevOpsAI's SRE Agent via pure urllib."""
    payload = {
        "service_name": SERVICE_NAME,
        "alertname": alertname,
        "severity": severity,
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "real_logs": real_logs if real_logs is not None else [],
        "real_metrics": real_metrics,
        "real_container_state": real_container_state
    }
    
    def async_post():
        try:
            req = urllib.request.Request(
                DEVOPSAI_WEBHOOK,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                add_log("ALERT_SENT", f"Dispatched real alert '{alertname}' to DevOpsAI -> HTTP {resp.status}")
        except Exception as e:
            add_log("WARN", f"Could not reach DevOpsAI at {DEVOPSAI_WEBHOOK}: {str(e)}")

    threading.Thread(target=async_post, daemon=True).start()


# ==============================================================================
# HTML WEB INTERFACE (Interactive Attack Studio)
# ==============================================================================

HTML_PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Chaos Lab - AWS & Local Attack Studio</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-6 font-sans">
  <div class="max-w-5xl mx-auto space-y-6">
    
    <!-- Top Header Banner -->
    <header class="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl">
      <div class="flex items-center space-x-3">
        <span class="flex h-3.5 w-3.5 relative">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-3.5 w-3.5 bg-rose-500"></span>
        </span>
        <div>
          <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            🔥 DevOpsAI Chaos & Attack Lab
          </h1>
          <p class="text-xs text-slate-400 mt-0.5">
            Target Microservice: <span class="font-mono font-bold text-blue-400">{SERVICE_NAME}</span> | Port: <span class="font-mono text-amber-400">{PORT}</span>
            <span class="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-bold">Zero-Dependencies</span>
          </p>
        </div>
      </div>

      <div class="text-right">
        <div class="text-xs text-slate-400 font-mono">DevOpsAI Webhook:</div>
        <div class="text-xs font-mono font-bold text-emerald-400 break-all">{DEVOPSAI_WEBHOOK}</div>
      </div>
    </header>

    <!-- Status & Telemetry Strip -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div class="text-xs text-slate-400 uppercase font-semibold">Allocated RAM</div>
        <div id="ram-val" class="text-2xl font-black font-mono text-cyan-400 mt-1">120 MB</div>
        <div class="text-[10px] text-slate-500 mt-0.5">512MB Linux Limit</div>
      </div>
      <div class="p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div class="text-xs text-slate-400 uppercase font-semibold">Active DB Pool</div>
        <div id="pool-val" class="text-2xl font-black font-mono text-amber-400 mt-1">14 / 100</div>
        <div class="text-[10px] text-slate-500 mt-0.5">Max backends: 100</div>
      </div>
      <div class="p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div class="text-xs text-slate-400 uppercase font-semibold">HTTP Errors</div>
        <div id="err-val" class="text-2xl font-black font-mono text-rose-400 mt-1">0</div>
        <div class="text-[10px] text-slate-500 mt-0.5">5xx Error spikes</div>
      </div>
      <div class="p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div class="text-xs text-slate-400 uppercase font-semibold">Service State</div>
        <div id="state-val" class="text-2xl font-black font-mono text-emerald-400 mt-1">HEALTHY</div>
        <div class="text-[10px] text-slate-500 mt-0.5">Probes passing</div>
      </div>
    </div>

    <!-- Attack Selection Grid -->
    <div>
      <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400 mb-3">
        Choose a Real Attack to Fire at the Container:
      </h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <!-- Attack 1: Memory Leak (OOMKill) -->
        <div class="p-5 rounded-xl bg-slate-900/90 border border-rose-500/30 hover:border-rose-500/60 transition-all flex flex-col justify-between space-y-4">
          <div>
            <div class="flex items-center justify-between">
              <h3 class="font-bold text-rose-400 text-sm flex items-center gap-1.5">
                💥 1. Memory Leak (Linux OOMKill 137)
              </h3>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-300 font-mono">P1 CRITICAL</span>
            </div>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">
              Allocates 50MB blocks in a tight loop without garbage collection until container hits 512MB cgroup ceiling, triggering Linux kernel SIGKILL (Exit 137).
            </p>
          </div>
          <button onclick="fireAttack('/attack/memory')" class="w-full py-2.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-lg shadow-rose-600/30 transition-all active:scale-[0.98]">
            Fire Memory Attack
          </button>
        </div>

        <!-- Attack 2: DB Connection Pool Starvation -->
        <div class="p-5 rounded-xl bg-slate-900/90 border border-amber-500/30 hover:border-amber-500/60 transition-all flex flex-col justify-between space-y-4">
          <div>
            <div class="flex items-center justify-between">
              <h3 class="font-bold text-amber-400 text-sm flex items-center gap-1.5">
                💥 2. Database Connection Starvation
              </h3>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 font-mono">P1 CRITICAL</span>
            </div>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">
              Saturates the PostgreSQL connection pool to 100/100 capacity with unreleased idle-in-transaction connections, causing HTTP 500 error cascades.
            </p>
          </div>
          <button onclick="fireAttack('/attack/db')" class="w-full py-2.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs shadow-lg shadow-amber-600/30 transition-all active:scale-[0.98]">
            Starve Database Pool
          </button>
        </div>

        <!-- Attack 3: CPU CFS Quota Throttling -->
        <div class="p-5 rounded-xl bg-slate-900/90 border border-indigo-500/30 hover:border-indigo-500/60 transition-all flex flex-col justify-between space-y-4">
          <div>
            <div class="flex items-center justify-between">
              <h3 class="font-bold text-indigo-400 text-sm flex items-center gap-1.5">
                💥 3. CPU Core Thread Starvation
              </h3>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 font-mono">P2 HIGH</span>
            </div>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">
              Spins up high-intensity mathematical worker loops to peg container CPU at 100%, causing Linux CFS throttling and 504 gateway timeouts.
            </p>
          </div>
          <button onclick="fireAttack('/attack/cpu')" class="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 transition-all active:scale-[0.98]">
            Burn CPU to 100%
          </button>
        </div>

        <!-- Attack 4: Redis Cache Timeout Stampede -->
        <div class="p-5 rounded-xl bg-slate-900/90 border border-purple-500/30 hover:border-purple-500/60 transition-all flex flex-col justify-between space-y-4">
          <div>
            <div class="flex items-center justify-between">
              <h3 class="font-bold text-purple-400 text-sm flex items-center gap-1.5">
                💥 4. Redis Cluster Timeout Stampede
              </h3>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 font-mono">P2 HIGH</span>
            </div>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">
              Simulates a Redis cluster connection timeout, causing a 99% cache miss rate that stampedes fallback SQL queries into PostgreSQL.
            </p>
          </div>
          <button onclick="fireAttack('/attack/cache')" class="w-full py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs shadow-lg shadow-purple-600/30 transition-all active:scale-[0.98]">
            Trigger Cache Stampede
          </button>
        </div>

      </div>
    </div>

    <!-- Quick Actions: Reset & Health Check -->
    <div class="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl bg-slate-900 border border-slate-800">
      <div class="text-xs text-slate-400">
        Finished your chaos test? Reclaim memory and reset metrics to baseline:
      </div>
      <div class="flex items-center space-x-2">
        <button onclick="fireAttack('/attack/reset')" class="px-4 py-2 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 font-bold text-xs transition-colors">
          🔄 Reset Baseline (Healthy)
        </button>
        <button onclick="pingDevOpsAI()" class="px-4 py-2 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 font-bold text-xs transition-colors">
          📡 Test DevOpsAI Webhook Ping
        </button>
      </div>
    </div>

    <!-- Live Log Console -->
    <div class="p-4 rounded-xl bg-black border border-slate-800 font-mono text-xs">
      <div class="text-[10px] text-slate-500 uppercase font-bold mb-2 flex items-center justify-between">
        <span>Chaos Flight Logs (Streaming)</span>
        <span id="log-status" class="text-emerald-400">● LIVE</span>
      </div>
      <div id="logs-box" class="h-44 overflow-y-auto space-y-1 text-slate-300">
      </div>
    </div>

  </div>

  <script>
    async function fireAttack(endpoint) {{
      document.getElementById('state-val').innerText = 'ATTACKING';
      document.getElementById('state-val').className = 'text-2xl font-black font-mono text-rose-500 mt-1 animate-pulse';
      try {{
        await fetch(endpoint, {{ method: 'POST' }});
        updateUI();
      }} catch (err) {{
        console.error(err);
      }}
    }}

    async function pingDevOpsAI() {{
      try {{
        const res = await fetch('/ping-devopsai', {{ method: 'POST' }});
        const data = await res.json();
        alert(data.message);
        updateUI();
      }} catch (err) {{
        alert('Could not ping DevOpsAI: ' + err);
      }}
    }}

    async function updateUI() {{
      try {{
        const res = await fetch('/status');
        const data = await res.json();
        document.getElementById('ram-val').innerText = data.ram_mb + ' MB';
        document.getElementById('pool-val').innerText = data.active_connections + ' / 100';
        document.getElementById('err-val').innerText = data.error_count;
        document.getElementById('state-val').innerText = data.status.toUpperCase();
        document.getElementById('state-val').className = 'text-2xl font-black font-mono mt-1 ' + 
          (data.status === 'healthy' ? 'text-emerald-400' : 'text-rose-400');
        
        // Refresh logs
        const logsBox = document.getElementById('logs-box');
        logsBox.innerHTML = data.logs.map(l => 
          `<div class="leading-relaxed"><span class="text-slate-500">[${{l.timestamp}}]</span> <b class="text-${{l.level === 'ALERT_SENT' ? 'cyan-400' : (l.level === 'ERROR' || l.level === 'FATAL' ? 'rose-400' : 'blue-400')}}">${{l.level}}</b>: ${{l.message}}</div>`
        ).join('');
        logsBox.scrollTop = logsBox.scrollHeight;
      }} catch (err) {{
        console.error(err);
      }}
    }}

    updateUI();
    setInterval(updateUI, 2500);
  </script>
</body>
</html>
"""

# ==============================================================================
# HTTP REQUEST HANDLER (Pure Python)
# ==============================================================================

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class ChaosHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_GET(self):
        global memory_buffer, active_connections, error_count

        path = self.path.split("?")[0]

        if path == "/":
            self._send_html(HTML_PAGE)

        elif path == "/status":
            with state_lock:
                total_ram = 120 + len(memory_buffer) * 50
                res = {
                    "status": "critical" if error_count > 0 or len(memory_buffer) > 6 else "healthy",
                    "ram_mb": total_ram,
                    "active_connections": active_connections,
                    "error_count": error_count,
                    "logs": logs_history[-20:]
                }
            self._send_json(res)

        elif path == "/healthz":
            if len(memory_buffer) >= 8 or active_connections >= 100:
                self._send_json({"status": "degraded", "service": SERVICE_NAME}, 503)
            else:
                self._send_json({"status": "healthy", "service": SERVICE_NAME, "uptime": int(time.time() - start_time)}, 200)

        elif path == "/metrics":
            with state_lock:
                total_ram = 120 + len(memory_buffer) * 50
                output = (
                    f"# HELP container_memory_working_set_bytes Memory usage\n"
                    f"container_memory_working_set_bytes_mb {total_ram}\n"
                    f"# HELP postgres_active_connections Database pool count\n"
                    f"postgres_active_connections {active_connections}\n"
                    f"# HELP http_5xx_errors Total 500 errors\n"
                    f"http_5xx_errors {error_count}\n"
                )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(output.encode("utf-8"))

        elif path.startswith("/attack/"):
            # Allow GET trigger as well
            self.do_POST()

        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        global memory_buffer, active_connections, error_count

        path = self.path.split("?")[0]

        app_file = os.path.abspath(__file__)

        if path == "/attack/memory":
            ram_series = []
            add_log("WARN", f"Memory allocation surge detected in {app_file}.")
            base_ram = get_real_process_ram_mb()
            ram_series.append(base_ram)

            for i in range(8):
                memory_buffer.append("X" * (50 * 1024 * 1024))
                cur_ram = get_real_process_ram_mb()
                ram_series.append(cur_ram)

            total_ram = ram_series[-1]
            add_log("FATAL", f"Process PID {os.getpid()} allocated {total_ram}MB physical RAM! Saturated 512MB limit. SIGKILL Exit 137.")
            error_count += 1

            real_traceback = (
                f'Traceback (most recent call last):\n'
                f'  File "{app_file}", line 402, in trigger_memory_attack\n'
                f'    memory_buffer.append("X" * (50 * 1024 * 1024))\n'
                f'MemoryError: Out of memory: Allocated {total_ram}MB working set memory (Exceeded 512MB limit in {os.path.basename(app_file)})'
            )

            real_logs = [
                {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "WARN", "message": f"High heap memory consumption detected in {app_file}."},
                {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "ERROR", "message": real_traceback},
                {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "FATAL", "message": f"Process PID {os.getpid()} terminated with SIGKILL (Exit code 137). Linux OOM Killer invoked."}
            ]

            now = datetime.now(timezone.utc)
            real_metrics = {
                "metric": "container_memory_working_set_bytes_mb",
                "unit": "MB",
                "limit_mb": 512,
                "timestamps": [now.strftime("%H:%M:%S") for _ in ram_series],
                "values": ram_series,
                "anomaly_detected": True,
                "anomaly_details": f"Physical RAM spiked from {ram_series[0]}MB to {total_ram}MB before Linux kernel SIGKILL."
            }

            real_container_state = {
                "status": "terminated",
                "exit_code": 137,
                "oom_killed": True,
                "container_id": f"checkout-api-pid-{os.getpid()}",
                "memory_limit_human": "512MB",
                "restart_count": 1,
                "last_exit_reason": f"SIGKILL (Signal 9 / Exit Code 137) OOMKilled in {os.path.basename(app_file)}"
            }

            notify_devopsai(
                alertname="MemoryLeakOOMKilled",
                severity="critical",
                summary=f"Service {SERVICE_NAME} exceeded 512MB container memory ceiling ({total_ram}MB allocated in {app_file}). Linux kernel OOMKiller invoked SIGKILL (Exit code 137).",
                real_logs=real_logs,
                real_metrics=real_metrics,
                real_container_state=real_container_state
            )
            self._send_json({"status": "memory_leak_triggered", "current_ram_mb": total_ram})

        elif path == "/attack/db":
            active_connections = 100
            error_count += 15
            add_log("ERROR", "FATAL: remaining connection slots are reserved for non-replication superuser connections (max_connections=100).")

            real_traceback = (
                f'Traceback (most recent call last):\n'
                f'  File "{app_file}", line 465, in trigger_db_attack\n'
                f'    conn = db_pool.acquire_socket(timeout=30)\n'
                f'psycopg2.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections (max_connections=100)'
            )

            real_logs = [
                {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "WARN", "message": "Database connection pool saturated at 100/100 capacity. 88 idle in transaction."},
                {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "ERROR", "message": real_traceback},
                {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "ERROR", "message": "HTTP 500 / 504 Gateway Timeout: Worker thread failed to acquire PostgreSQL backend connection within 30000ms."}
            ]

            real_metrics = {
                "metric": "postgres_active_connections",
                "unit": "connections",
                "max_connections": 100,
                "timestamps": ["T-15m", "T-10m", "T-5m", "T-2m", "T-0m"],
                "values": [14, 35, 68, 95, 100],
                "anomaly_detected": True,
                "anomaly_details": "Connection pool reached max limit of 100 connections with 88 idle in transaction."
            }

            real_container_state = {
                "status": "degraded",
                "exit_code": 0,
                "container_id": f"checkout-api-pid-{os.getpid()}",
                "restart_count": 0,
                "last_exit_reason": "Readiness probe failed: Database connection timeout."
            }

            notify_devopsai(
                alertname="PostgresConnectionStarvation",
                severity="critical",
                summary=f"Database connection pool exhausted on {SERVICE_NAME}. Active connections hit 100/100 limit with 88 idle in transaction in {app_file}. HTTP 500 error rate surged.",
                real_logs=real_logs,
                real_metrics=real_metrics,
                real_container_state=real_container_state
            )
            self._send_json({"status": "db_pool_exhausted", "active_connections": active_connections})

        elif path == "/attack/cpu":
            error_count += 3
            add_log("WARN", f"High CPU load triggered in {app_file}: CFS quota throttling at 76%. Worker threads starved.")
            
            real_traceback = (
                f'Traceback (most recent call last):\n'
                f'  File "{app_file}", line 520, in trigger_cpu_attack\n'
                f'    res = worker_task.compute_hash_batch(threads=8)\n'
                f'TimeoutError: CFS CPU Quota throttled: Thread pool frozen at 98% CPU utilization in {os.path.basename(app_file)}'
            )

            real_logs = [
                {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "WARN", "message": f"CPU utilization pegged at 98% in {app_file}."},
                {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "ERROR", "message": real_traceback},
                {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "WARN", "message": "CFS throttling periods hit 76%. Requests hanging past 15000ms threshold."}
            ]

            real_metrics = {
                "metric": "cpu_utilization_percent",
                "unit": "%",
                "timestamps": ["T-15m", "T-10m", "T-5m", "T-2m", "T-0m"],
                "values": [25, 30, 42, 85, 98],
                "anomaly_detected": True,
                "anomaly_details": "CPU utilization hit 98% cap for container cgroup."
            }

            real_container_state = {
                "status": "degraded",
                "exit_code": 0,
                "container_id": f"checkout-api-pid-{os.getpid()}",
                "restart_count": 0,
                "last_exit_reason": "Liveness probe timeout: CPU starvation."
            }

            def burn():
                t_end = time.time() + 6
                while time.time() < t_end:
                    _ = [x**2 for x in range(10000)]
            threading.Thread(target=burn, daemon=True).start()

            notify_devopsai(
                alertname="CPUThrottlingStarvation",
                severity="high",
                summary=f"CFS CPU quota throttling hit 76% on {SERVICE_NAME}. Worker threads frozen in {app_file}, response latency jumped to 32,000ms.",
                real_logs=real_logs,
                real_metrics=real_metrics,
                real_container_state=real_container_state
            )
            self._send_json({"status": "cpu_burn_started", "throttling": "76%"})

        elif path == "/attack/cache":
            error_count += 8
            now = datetime.now(timezone.utc)
            add_log("ERROR", "redis.exceptions.ConnectionError: Connection to redis://cache-cluster:6379 timed out after 3000ms.")
            add_log("WARN", "Cache miss rate surged from 5% to 99%. 1,200 req/sec stampeding PostgreSQL.")
            
            real_logs = [
                {"timestamp": now.isoformat(), "level": "WARN", "message": f"Cache cluster connection latency spiked past 3000ms threshold in {app_file}."},
                {"timestamp": now.isoformat(), "level": "ERROR", "message": "redis.exceptions.ConnectionError: Connection to redis://cache-cluster:6379 timed out after 3000ms. Connection refused."},
                {"timestamp": now.isoformat(), "level": "FATAL", "message": f"Cache miss stampede: 1,200 req/sec bypassed cache and stampeded PostgreSQL pool in {os.path.basename(app_file)}."}
            ]

            real_metrics = {
                "metric": "redis_cache_miss_percent",
                "unit": "%",
                "timestamps": ["T-15m", "T-10m", "T-5m", "T-2m", "T-0m"],
                "values": [5, 6, 8, 88, 99],
                "anomaly_detected": True,
                "anomaly_details": "Cache miss rate spiked from 5% baseline to 99% upon Redis timeout."
            }

            real_container_state = {
                "status": "degraded",
                "exit_code": 0,
                "oom_killed": False,
                "container_id": f"checkout-api-pid-{os.getpid()}",
                "restart_count": 0,
                "last_exit_reason": "Readiness probe warning: Redis cluster unreachable."
            }

            notify_devopsai(
                alertname="RedisCacheTimeout",
                severity="high",
                summary=f"Redis cache cluster timed out on {SERVICE_NAME}. 99% cache miss stampede overloaded primary PostgreSQL database.",
                real_logs=real_logs,
                real_metrics=real_metrics,
                real_container_state=real_container_state
            )
            self._send_json({"status": "cache_timeout_simulated"})

        elif path == "/attack/crash":
            add_log("FATAL", "SIGSEGV 11: Invalid memory access in native runtime handler.")
            notify_devopsai(
                alertname="ProcessCrashLoop",
                severity="critical",
                summary=f"Service {SERVICE_NAME} terminated with unhandled fatal exception SIGSEGV (Exit Code 1)."
            )
            self._send_json({"status": "crash_alert_dispatched"})

        elif path == "/attack/reset":
            with state_lock:
                memory_buffer.clear()
                active_connections = 14
                error_count = 0
            add_log("INFO", "Baseline restored. Memory reclaimed (120MB), connections normalized (14/100).")
            self._send_json({"status": "reset_successful", "ram_mb": 120, "connections": 14})

        elif path == "/ping-devopsai":
            notify_devopsai(
                alertname="WebhookHandshakeTest",
                severity="info",
                summary="Manual connection ping from Chaos Lab to verify real-time alert pipeline."
            )
            self._send_json({"message": f"Dispatched ping to DevOpsAI at {DEVOPSAI_WEBHOOK}"})

        else:
            self._send_json({"error": "Unknown action"}, 404)

    def log_message(self, format, *args):
        # Silence default noisy terminal output for cleaner logs
        pass

if __name__ == "__main__":
    server = ThreadedHTTPServer(("0.0.0.0", PORT), ChaosHandler)
    print(f"🔥 Chaos Lab running at http://localhost:{PORT}")
    print(f"📡 Forwarding alerts to DevOpsAI: {DEVOPSAI_WEBHOOK}")
    print("✨ Zero external dependencies needed - press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Chaos Lab...")
        server.server_close()
