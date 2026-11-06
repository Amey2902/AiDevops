# 🔥 DevOpsAI Chaos & Attack Laboratory

A real microservice (`checkout-api`) built for **Chaos Engineering & SRE Incident Simulation**. It can be attacked with memory leaks, database pool exhaustion, CPU starvation, and cache stampedes to test whether DevOpsAI autonomously detects, investigates, and produces root-cause analyses in real time.

---

## 🚀 How to Run (Choose One)

### Option 1: Run Locally with Python (Instant — 3 Seconds)
```bash
# Navigate to chaos_lab
cd chaos_lab

# Install dependencies (Flask & Requests)
pip install -r requirements.txt

# Start the Chaos Lab
python app.py
```
Open **`http://localhost:5000`** in your browser!

---

### Option 2: Run Locally with Docker
```bash
cd chaos_lab
docker compose up --build
```
Open **`http://localhost:5000`** in your browser.

---

### Option 3: Deploy on AWS EC2
1. Copy the `chaos_lab/` folder to your EC2 instance:
   ```bash
   scp -r chaos_lab/ ubuntu@<YOUR_EC2_IP>:~/
   ```
2. SSH into your EC2 instance:
   ```bash
   ssh ubuntu@<YOUR_EC2_IP>
   cd chaos_lab
   ```
3. Set your public DevOpsAI URL in `docker-compose.yml`:
   ```yaml
   - DEVOPSAI_WEBHOOK_URL=https://<your-ngrok-or-devopsai-domain>/api/webhook/
   ```
4. Start it:
   ```bash
   docker compose up -d
   ```
5. Open **`http://<YOUR_EC2_IP>:5000`** in your browser.

---

## 💥 The Built-In Attacks

| Attack | Trigger | What Happens in the Container | What DevOpsAI Does |
| :--- | :--- | :--- | :--- |
| **1. Memory Leak (OOMKill)** | `[ Fire Memory Attack ]` | Allocates 400MB+ in memory until Linux cgroup invokes SIGKILL (`Exit Code 137`). | P1 alert pops up. Telemetry spikes to 512MB. AI correlates exit 137 with Supabase runbook `oom_killed_137.md`. |
| **2. DB Pool Starvation** | `[ Starve Database Pool ]` | Saturated connection pool (100/100 backends). Subsequent queries return 504 Timeout. | P1 alert. Active connections curve pinned at 100. RCA cites `postgres_connection_exhaustion.md`. |
| **3. CPU Throttling** | `[ Burn CPU to 100% ]` | High-intensity mathematical loop triggers Linux CFS throttling (76%). | P2 alert. CPU chart hits 100%. Latency jump to 32,000ms. |
| **4. Redis Cache Stampede** | `[ Trigger Cache Stampede ]` | Simulates Redis cluster timeout. Cache miss spikes to 99%, stampeding DB. | P2 alert. Queries surge by +400%. RCA identifies Redis failure. |
| **5. Process Crash** | `[ Kill Process ]` | Process exits with unhandled `SIGSEGV` (`Exit Code 1`). | Watchdog detects dead container, prompts immediate restart. |
| **🔄 Reset Baseline** | `[ Reset Baseline ]` | Reclaims all allocated RAM (120MB) and resets connections to 14. | Restores healthy state. |

