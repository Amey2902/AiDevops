# DevOpsAI — AI-Powered DevOps Incident Investigation & RCA Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-092E20.svg)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38B2AC.svg)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ED.svg)](https://www.docker.com/)

**DevOpsAI** is an autonomous Site Reliability Engineering (SRE) incident investigation and Root Cause Analysis (RCA) platform. It monitors containerized applications, collects metrics, logs, and container states, queries an intelligent **RAG-based troubleshooting knowledge base**, and coordinates an **Autonomous AI SRE Agent** to isolate probable root causes and deliver evidence-backed remediation reports.

---

## Key Features

1. **Autonomous SRE Investigation Agent**:
   - Systematic diagnostic workflow: probes container health, clusters error logs, isolates metric anomalies, and matches runbooks.
   - Calculates verified confidence scores and outputs actionable immediate and preventative remediation steps.

2. **RAG Knowledge Base & Semantic Search**:
   - Indexes SRE Markdown runbooks and post-mortems using vector embeddings and cosine similarity ranking.
   - Matches failure patterns (e.g. Exit Code 137, DB connection pool leaks, CFS quota throttling) to operational playbooks.

3. **Multi-Source Telemetry Connectors**:
   - **Prometheus Connector**: Scrapes Golden Signals (latency, error rates, CPU, RAM).
   - **Container Health Connector**: Probes exit codes, restart loops, and OOMKilled flags.
   - **Log Clusterer**: Filters and extracts critical exceptions and stack traces.
   - **Chaos Simulator Engine**: Injects 3 high-fidelity failure scenarios for live demonstrations without external cluster dependencies.

4. **SRE Observability Dashboard**:
   - Modern dark-mode interface built with React, Vite, Lucide icons, and Tailwind CSS.
   - Visual sparkline metric charts and colored terminal log stream viewer.
   - Interactive **"Ask DevOpsAI" SRE Copilot** drawer with runbook citations.
   - **Chaos Simulation Trigger Modal** to inject faults and watch the AI investigate in real time.

---

## Project Structure

```
d:\AiDevops\
├── backend/
│   ├── devopsai/                  # Django project configuration & settings
│   ├── incidents/                 # Incident models, serializers, views, REST APIs
│   ├── core/
│   │   ├── rag/                   # Embeddings, Markdown chunker, vector store, knowledge manager
│   │   ├── agent/                 # SRE Investigator agent & RCA synthesizer
│   │   └── telemetry/             # Prometheus client, Docker inspector, Simulation engine
│   ├── manage.py
│   └── requirements.txt
├── knowledge_base/
│   ├── runbooks/
│   │   ├── oom_killed_137.md
│   │   ├── postgres_connection_exhaustion.md
│   │   └── cpu_throttling_thread_starvation.md
│   └── postmortems/
│       └── incident_sample_db_pool_leak.md
├── frontend/
│   ├── src/
│   │   ├── components/            # IncidentList, InvestigationReport, TelemetryViewer, CopilotChatDrawer, ChaosModal
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── docker/
│   ├── prometheus.yml
│   └── sample_app/                # Monitored service with fault injection endpoints
├── docker-compose.yml             # Full stack container configuration
└── run_dev.ps1                    # Local development launcher
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+ (tested on Node v22)
- Docker Desktop (optional for local simulation mode, required for full container stack)

### 1. Local Development (Instant Startup)

#### Backend:
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies (already prepared)
pip install -r backend/requirements.txt

# Run migrations & seed demo incidents
cd backend
python manage.py migrate
python manage.py seed_demo

# Start Django development server (Port 8000)
python manage.py runserver 127.0.0.1:8000
```

#### Frontend:
```bash
# In another terminal window:
cd frontend
npm install
npm run dev
```

Visit **http://localhost:3000** in your browser!

Or launch both with one click using:
```powershell
.\run_dev.ps1
```

---

### 2. Full Containerized Stack (Docker Compose)

To spin up the entire cluster including PostgreSQL (`pgvector`), Prometheus, the monitored sample app, Django backend, and React frontend:

```bash
docker compose up --build
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/incidents/
- **Prometheus**: http://localhost:9090
- **Sample App**: http://localhost:8080/metrics

---

## Simulated Chaos Scenarios

DevOpsAI comes with three pre-configured failure scenarios that can be triggered from the UI or via API:

| Scenario | Service | Symptoms | AI Investigation Finding |
| :--- | :--- | :--- | :--- |
| **OOM Memory Leak** | `checkout-api` | Memory climbs to 512MB limit $\rightarrow$ Exit Code 137 | Container OOMKilled; recommends memory limit expansion & heap profiling |
| **DB Connection Starvation** | `order-service` | Max 100 connections hit, 88 idle in transaction | Database connection pool exhaustion; recommends PgBouncer & session timeout |
| **CFS CPU Quota Throttling** | `auth-service` | 78% CFS periods throttled, probe timeouts | CPU quota starvation; recommends CPU allocation increase and async offloading |

---

## API Endpoints

- `GET /api/incidents/` — List all incidents with active investigation summaries
- `POST /api/incidents/` — Ingest a new incident
- `POST /api/incidents/{id}/investigate/` — Run autonomous AI investigation
- `POST /api/incidents/{id}/chat/` — Ask questions about an incident to DevOpsAI Copilot
- `POST /api/simulation/trigger/` — Inject a chaos scenario and create an incident
- `GET /api/knowledge/?q={query}` — Semantic search against SRE runbooks

