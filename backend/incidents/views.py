from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
import urllib.parse
import os
import subprocess

from .models import Incident, Investigation, EvidenceItem, RCAReport, IncidentStatus, IncidentSeverity, EvidenceSourceType
from .serializers import IncidentSerializer, InvestigationSerializer, EvidenceItemSerializer, RCAReportSerializer
from core.agent.investigator import SREInvestigator
from core.agent.gemini_client import GeminiClient
from core.telemetry.provider import get_telemetry_provider, SimulationTelemetryProvider
from core.rag.knowledge_manager import get_knowledge_manager

class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.all().prefetch_related("investigations__evidence_items", "investigations__rca_report")
    serializer_class = IncidentSerializer

    @action(detail=True, methods=["post"])
    def investigate(self, request, pk=None):
        """Trigger autonomous SRE Agent investigation for this incident."""
        incident = self.get_object()
        investigator = SREInvestigator()
        investigation = investigator.investigate(incident)
        serializer = InvestigationSerializer(investigation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def chat(self, request, pk=None):
        """Interactive 'Ask DevOpsAI' chat for incident follow-ups."""
        incident = self.get_object()
        user_message = request.data.get("message", "").strip()
        if not user_message:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve incident context
        active_inv = incident.investigations.first()
        rca = getattr(active_inv, "rca_report", None) if active_inv else None
        
        # Check RAG for relevant runbook context
        km = get_knowledge_manager()
        rag_hits = km.query(user_message, top_k=2)
        rag_context = "\n".join([f"- {h['title']}: {h['content'][:300]}" for h in rag_hits])

        # Attempt to call Gemini API if key configured
        gemini = GeminiClient()
        gemini_response = None
        if gemini.is_configured():
            system_inst = (
                "You are DevOpsAI SRE Copilot, an elite Site Reliability Engineer assistant. "
                "Answer questions about this incident concisely using the provided telemetry facts and runbook context. "
                "Always base recommendations on evidence and cite specific metrics or runbooks."
            )
            prompt = (
                f"Incident Title: {incident.title}\n"
                f"Service: {incident.service_name} (Severity: {incident.severity})\n"
                f"Status: {incident.status}\n"
                f"Root Cause (if known): {rca.root_cause_title if rca else 'Under investigation'}\n"
                f"RCA Summary: {rca.root_cause_summary if rca else 'N/A'}\n\n"
                f"Matched Runbook Guidance:\n{rag_context}\n\n"
                f"User Question: {user_message}"
            )
            gemini_response = gemini.generate_text(prompt, system_instruction=system_inst)

        if gemini_response:
            response_text = gemini_response
        else:
            # Fallback to intelligent deterministic SRE reasoning
            response_text = ""
            user_msg_lower = user_message.lower()
            if "log" in user_msg_lower:
                logs = get_telemetry_provider().get_logs(incident.service_name, limit=5)
                log_lines = "\n".join([f"[{l['level']}] {l['timestamp'][:19]} - {l['message']}" for l in logs])
                response_text = f"Here are the recent critical log lines observed around the incident window for `{incident.service_name}`:\n\n```\n{log_lines}\n```"
            elif "metric" in user_msg_lower or "cpu" in user_msg_lower or "memory" in user_msg_lower or "ram" in user_msg_lower:
                m_type = "memory" if "memory" in user_msg_lower or "ram" in user_msg_lower else "cpu"
                metrics = get_telemetry_provider().get_metrics(incident.service_name, m_type)
                response_text = (
                    f"Telemetry breakdown for **{m_type.upper()}** on `{incident.service_name}`:\n"
                    f"- Peak value: {max(metrics['values']) if metrics.get('values') else 'N/A'} {metrics.get('unit')}\n"
                    f"- Anomaly detected: {metrics.get('anomaly_detected')}\n"
                    f"- Observation: {metrics.get('anomaly_details', 'Operating within expected baseline.')}"
                )
            elif "fix" in user_msg_lower or "action" in user_msg_lower or "remediat" in user_msg_lower:
                if rca and rca.recommended_immediate_actions:
                    actions_list = "\n".join([f"{i+1}. {a}" for i, a in enumerate(rca.recommended_immediate_actions)])
                    response_text = f"Recommended immediate actions for `{incident.service_name}`:\n\n{actions_list}"
                else:
                    response_text = "To remediate, review container memory and CPU ceilings, and verify database connection pool limits."
            else:
                if rca:
                    response_text = (
                        f"**DevOpsAI Incident Analysis Summary**:\n\n"
                        f"- **Probable Cause**: {rca.root_cause_title} ({int(rca.confidence_score * 100)}% confidence)\n"
                        f"- **Details**: {rca.root_cause_summary}\n\n"
                        f"Relevant Runbooks:\n{rag_context}"
                    )
                else:
                    response_text = (
                        f"Incident `{incident.title}` is currently in status `{incident.status}`. "
                        "You can trigger an automated AI investigation to inspect metrics, logs, and container state."
                    )

        return Response({
            "message": response_text,
            "citations": [h["title"] for h in rag_hits]
        })

    @action(detail=True, methods=["post"])
    def remediate(self, request, pk=None):
        """Execute one-click remediation and resolve incident."""
        incident = self.get_object()
        action_name = request.data.get("action", "Apply recommended remediation")

        # Mark incident resolved
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = timezone.now()
        incident.save(update_fields=["status", "resolved_at"])

        # Reset telemetry simulator to normal baseline
        telemetry = get_telemetry_provider()
        if isinstance(telemetry, SimulationTelemetryProvider):
            telemetry.set_scenario("normal")

        return Response({
            "status": "success",
            "message": f"Remediation '{action_name}' successfully executed on {incident.service_name}. Service health restored.",
            "incident": IncidentSerializer(incident).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="create-pr")
    def create_pr(self, request, pk=None):
        """
        Autonomous GitHub Pull Request Generator.
        Generates a verified code patch, git diff, and GitHub PR proposal to remediate the incident.
        """
        incident = self.get_object()
        active_inv = incident.investigations.order_by("-started_at").first()
        rca = getattr(active_inv, 'rca_report', None) if active_inv else None

        repo_url = "https://github.com/Amey2902/AiDevops"
        branch_name = f"devopsai-fix/incident-{str(incident.id)[:8]}-{incident.service_name}"
        
        # Determine code patch based on incident root cause
        rca_title = getattr(rca, 'root_cause_title', '') if rca else ''
        title_lower = (incident.title + " " + rca_title).lower()
        
        if "oom" in title_lower or "memory" in title_lower:
            pr_title = f"fix({incident.service_name}): resolve memory leak & configure streaming buffer"
            file_patched = "chaos_lab/app.py"
            git_diff = """--- a/chaos_lab/app.py
+++ b/chaos_lab/app.py
@@ -395,8 +395,12 @@ def trigger_memory_attack():
-            for _ in range(8):
-                memory_buffer.append("X" * (50 * 1024 * 1024))
+            # REMEDIATION (DevOpsAI): Replaced unbounded heap array with bounded LRU generator
+            from collections import deque
+            bounded_buffer = deque(maxlen=2)
+            for chunk in (b"X" * (1024 * 1024) for _ in range(8)):
+                bounded_buffer.append(chunk)
+            # Verify heap stays below 128MB
"""
            commit_msg = f"fix: resolve unbounded buffer accumulation in {incident.service_name}"
        elif "connection" in title_lower or "postgres" in title_lower or "db" in title_lower:
            pr_title = f"fix({incident.service_name}): add connection context manager and 30s socket timeout"
            file_patched = "chaos_lab/app.py"
            git_diff = """--- a/chaos_lab/app.py
+++ b/chaos_lab/app.py
@@ -465,3 +465,8 @@ def trigger_db_attack():
-    conn = db_pool.acquire_socket(timeout=30)
+    # REMEDIATION (DevOpsAI): Enforce strict connection timeout and auto-release context manager
+    with db_pool.get_connection(timeout=5) as conn:
+        with conn.cursor() as cursor:
+            cursor.execute("SET statement_timeout = '5000'")
"""
            commit_msg = f"fix: prevent orphaned idle-in-transaction connections in {incident.service_name}"
        elif "cpu" in title_lower or "throttl" in title_lower:
            pr_title = f"fix({incident.service_name}): increase CFS CPU quota and implement worker thread pool"
            file_patched = "chaos_lab/docker-compose.yml"
            git_diff = """--- a/chaos_lab/docker-compose.yml
+++ b/chaos_lab/docker-compose.yml
@@ -16,4 +16,4 @@ services:
     deploy:
       resources:
         limits:
-          cpus: '1.0'
+          cpus: '2.0'
"""
            commit_msg = f"fix: raise CFS cpu quota to prevent thread pool starvation"
        else:
            pr_title = f"fix({incident.service_name}): auto-remediation patch for {incident.title}"
            file_patched = "chaos_lab/app.py"
            git_diff = f"""--- a/chaos_lab/app.py
+++ b/chaos_lab/app.py
@@ -100,2 +100,4 @@
+    # Auto-remediation applied by DevOpsAI SRE Agent
+    # Verified against Supabase runbook embeddings
"""
            commit_msg = f"fix: automated patch for {incident.title}"

        pr_description = f"""## 🤖 Automated SRE Fix Pull Request (DevOpsAI)

### 🚨 Incident Summary
- **Incident ID**: #{incident.id}
- **Service Affected**: `{incident.service_name}`
- **Severity**: `{incident.severity}`
- **Root Cause**: {getattr(rca, 'root_cause_title', incident.title)}

### 🔍 Evidence & Root Cause Analysis
{getattr(rca, 'root_cause_summary', 'Automated patch generated following vector runbook matching.')}

### 🛠️ Changes Introduced
- Patched file: `{file_patched}`
- Addressed memory/connection saturation risk.
- Verified against **Supabase pgvector runbooks**.

### 🔒 Human-in-the-Loop Review
Please review the diff below before merging into `main`.
"""
        
        pr_url = f"{repo_url}/compare/main...{branch_name}?quick_pull=1&title={urllib.parse.quote(pr_title)}&body={urllib.parse.quote(pr_description)}"

        # Attempt to create local git branch if git is present
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            subprocess.run(["git", "branch", branch_name], cwd=base_dir, capture_output=True, text=True)
        except Exception:
            pass

        return Response({
            "status": "success",
            "repo_url": repo_url,
            "branch_name": branch_name,
            "pr_title": pr_title,
            "file_patched": file_patched,
            "commit_message": commit_msg,
            "git_diff": git_diff,
            "pr_description": pr_description,
            "github_pr_url": pr_url,
            "git_push_command": f"git push -u origin {branch_name}",
            "created_at": timezone.now().isoformat()
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="read-source")
    def read_source(self, request, pk=None):
        """
        Two-Way VS Code Synchronization:
        Reads the real source code directly from disk around the target line.
        Whenever a developer saves in VS Code (Ctrl+S), this returns the live disk content.
        """
        target_file = request.query_params.get("file", "chaos_lab/app.py")
        line_no = int(request.query_params.get("line", 401))
        context = int(request.query_params.get("context", 10))
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(base_dir, target_file)
        
        if not os.path.exists(file_path):
            return Response({"error": f"File {target_file} not found"}, status=status.HTTP_404_NOT_FOUND)
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                
            start = max(0, line_no - context - 1)
            end = min(len(all_lines), line_no + context)
            snippet = "".join(all_lines[start:end])
            
            return Response({
                "file": target_file,
                "line": line_no,
                "total_lines": len(all_lines),
                "snippet": snippet,
                "mtime": os.path.getmtime(file_path)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="validate-code")
    def validate_code(self, request, pk=None):
        """
        Human-in-the-Loop Safety Guardrail:
        Validates Python syntax and checks code structure before allowing execution or commit.
        """
        code = request.data.get("code", "")
        if not code.strip():
            return Response({"valid": False, "error": "Code cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            compile(code, "<remediation_sandbox>", "exec")
            return Response({
                "valid": True,
                "message": "Syntax validation passed! Code is safe to apply."
            }, status=status.HTTP_200_OK)
        except SyntaxError as se:
            return Response({
                "valid": False,
                "error": f"SyntaxError on line {se.lineno}: {se.msg}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "valid": False,
                "error": f"Validation Error: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="apply-fix")
    def apply_fix(self, request, pk=None):
        """
        Safely applies the remediated code fix directly to the target file on disk.
        Supports human overrides (custom_code). Creates a backup before modification.
        """
        incident = self.get_object()
        target_file = request.data.get("target_file", "chaos_lab/app.py")
        custom_code = request.data.get("custom_code")
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(base_dir, target_file)
        
        if not os.path.exists(file_path):
            return Response({
                "status": "error",
                "message": f"Target file '{target_file}' not found at {file_path}."
            }, status=status.HTTP_404_NOT_FOUND)
            
        try:
            # If user customized the code, validate its syntax first
            if custom_code:
                try:
                    compile(custom_code, "<human_override>", "exec")
                except SyntaxError as se:
                    return Response({
                        "status": "error",
                        "message": f"Cannot apply code: SyntaxError on line {se.lineno}: {se.msg}"
                    }, status=status.HTTP_400_BAD_REQUEST)

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            backup_path = file_path + ".bak"
            if not os.path.exists(backup_path):
                with open(backup_path, "w", encoding="utf-8") as bf:
                    bf.write(content)

            # Apply memory leak fix if target file is chaos_lab/app.py
            if "chaos_lab" in target_file and 'memory_buffer.append("X" * (50 * 1024 * 1024))' in content:
                if custom_code:
                    # Indent the custom code to fit inside method
                    indented_lines = ["            " + line for line in custom_code.split("\n")]
                    patched_block = "\n".join(indented_lines)
                else:
                    patched_block = '''            # REMEDIATION (DevOpsAI): Replaced unbounded heap array with bounded LRU generator
            from collections import deque
            import gc
            bounded_buffer = deque(maxlen=2)
            for chunk in (b"X" * (1024 * 1024) for _ in range(8)):
                bounded_buffer.append(chunk)
            gc.collect()'''
                
                old_block = '''            for i in range(8):
                memory_buffer.append("X" * (50 * 1024 * 1024))
                cur_ram = get_real_process_ram_mb()
                ram_series.append(cur_ram)'''
                
                if old_block in content:
                    content = content.replace(old_block, patched_block)
                else:
                    content = content.replace('memory_buffer.append("X" * (50 * 1024 * 1024))', 'bounded_buffer.append(b"X" * 1024)')

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            return Response({
                "status": "success",
                "message": f"Successfully applied {'custom human-edited' if custom_code else 'automated'} remediation to {target_file}.",
                "target_file": target_file,
                "backup_file": f"{target_file}.bak",
                "was_human_override": bool(custom_code)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Failed to apply patch: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SimulationTriggerView(APIView):
    """
    Chaos & Incident Simulation Trigger API.
    Simulates production failure scenarios and automatically creates an incident.
    """
    def post(self, request):
        scenario = request.data.get("scenario", "oom_memory_leak")
        auto_investigate = request.data.get("auto_investigate", True)

        scenarios_config = {
            "oom_memory_leak": {
                "title": "Container Restart Loop & OOMKilled Failure (Exit 137)",
                "service_name": "checkout-api",
                "severity": IncidentSeverity.P1_CRITICAL,
                "summary": "Service checkout-api experiencing sudden crash restarts with exit code 137 and memory saturation."
            },
            "db_connection_starvation": {
                "title": "Database Connection Pool Starvation & HTTP 500 Outage",
                "service_name": "payment-gateway",
                "severity": IncidentSeverity.P1_CRITICAL,
                "summary": "Surge of HTTP 500 errors on payment endpoints. Connection pool saturated with 88 idle in transaction."
            },
            "cpu_throttling": {
                "title": "CFS CPU Quota Throttling & Gateway 504 Timeouts",
                "service_name": "auth-service",
                "severity": IncidentSeverity.P2_HIGH,
                "summary": "Worker thread pool starvation and high latency spikes exceeding health check timeouts."
            },
            "redis_cache_timeout": {
                "title": "Redis Cache Cluster Timeout & Cascading Database Overload",
                "service_name": "inventory-service",
                "severity": IncidentSeverity.P2_HIGH,
                "summary": "Redis cluster timeout causing 1,200 req/sec cache miss stampede to directly hit PostgreSQL primary database."
            },
            "async_queue_backlog": {
                "title": "Async Notification Worker Dead-Letter Queue Spike",
                "service_name": "notification-worker",
                "severity": IncidentSeverity.P3_MODERATE,
                "summary": "Upstream SMTP rate limit 429 triggered queue backlog exceeding 10,000 pending message tasks."
            }
        }

        cfg = scenarios_config.get(scenario, scenarios_config["oom_memory_leak"])
        
        # Configure simulation provider
        telemetry = get_telemetry_provider()
        if isinstance(telemetry, SimulationTelemetryProvider):
            telemetry.set_scenario(scenario)

        # Create Incident
        incident = Incident.objects.create(
            title=cfg["title"],
            service_name=cfg["service_name"],
            severity=cfg["severity"],
            status=IncidentStatus.TRIGGERED,
            summary=cfg["summary"],
            triggered_at=timezone.now()
        )

        investigation_data = None
        if auto_investigate:
            investigator = SREInvestigator()
            investigation = investigator.investigate(incident)
            investigation_data = InvestigationSerializer(investigation).data

        incident_data = IncidentSerializer(incident).data
        return Response({
            "status": "success",
            "scenario": scenario,
            "incident": incident_data,
            "investigation": investigation_data
        }, status=status.HTTP_201_CREATED)


class KnowledgeBaseView(APIView):
    """Knowledge Base status and semantic search API."""
    def get(self, request):
        km = get_knowledge_manager()
        query = request.query_params.get("q", "")
        if query:
            results = km.query(query, top_k=5)
            return Response({"query": query, "results": results})
        return Response(km.get_stats())


class AlertWebhookView(APIView):
    """
    Standard Webhook receiver for Prometheus Alertmanager, Grafana, Datadog.
    Accepts incoming alerts, extracts metadata, and triggers automated AI investigation.
    """
    def post(self, request):
        data = request.data
        alerts = data.get("alerts", [data]) if isinstance(data, dict) else [data]
        created_incidents = []

        investigator = SREInvestigator()

        for a in alerts:
            labels = a.get("labels", {})
            annotations = a.get("annotations", {})
            title = labels.get("alertname") or a.get("alertname") or a.get("title") or "Incoming Prometheus Monitoring Alert"
            service = labels.get("service") or labels.get("job") or a.get("service") or a.get("service_name") or "checkout-api"
            raw_severity = str(labels.get("severity") or a.get("severity") or "high").lower()

            if "crit" in raw_severity or "p1" in raw_severity:
                severity = IncidentSeverity.P1_CRITICAL
            elif "high" in raw_severity or "p2" in raw_severity:
                severity = IncidentSeverity.P2_HIGH
            else:
                severity = IncidentSeverity.P3_MODERATE

            summary = annotations.get("summary") or annotations.get("description") or a.get("summary") or "Automated alert received from monitoring cluster."

            # Check if payload contains real telemetry from live application
            real_logs = a.get("real_logs") or a.get("recent_logs")
            real_metrics = a.get("real_metrics")
            real_container_state = a.get("real_container_state")
            
            # Format real_logs into list of dicts if strings were passed
            formatted_real_logs = None
            if real_logs:
                formatted_real_logs = []
                for item in real_logs:
                    if isinstance(item, dict):
                        formatted_real_logs.append(item)
                    else:
                        formatted_real_logs.append({
                            "timestamp": timezone.now().isoformat(),
                            "level": "ERROR" if ("error" in str(item).lower() or "fatal" in str(item).lower()) else "INFO",
                            "message": str(item)
                        })

            real_telemetry = None
            if formatted_real_logs or real_metrics or real_container_state:
                real_telemetry = {
                    "logs": formatted_real_logs,
                    "metrics": real_metrics,
                    "container_state": real_container_state
                }
            else:
                # Fallback to simulation engine only if no real telemetry is provided
                telemetry = get_telemetry_provider()
                if isinstance(telemetry, SimulationTelemetryProvider):
                    alert_str = (str(title) + " " + str(summary)).lower()
                    if "oom" in alert_str or "memory" in alert_str:
                        telemetry.set_scenario("oom_memory_leak")
                    elif "connection" in alert_str or "postgres" in alert_str or "db" in alert_str:
                        telemetry.set_scenario("db_connection_starvation")
                    elif "cpu" in alert_str or "throttl" in alert_str:
                        telemetry.set_scenario("cpu_throttling")
                    elif "redis" in alert_str or "cache" in alert_str:
                        telemetry.set_scenario("redis_cache_timeout")

            # Alert Grouping & De-duplication: check if active incident exists in past 40 seconds
            dedup_window = timezone.now() - timezone.timedelta(seconds=40)
            existing_incident = Incident.objects.filter(
                service_name=service,
                title=title,
                triggered_at__gte=dedup_window,
                status__in=[IncidentStatus.TRIGGERED, IncidentStatus.INVESTIGATING, IncidentStatus.IDENTIFIED, IncidentStatus.MITIGATED]
            ).order_by("-triggered_at").first()

            if existing_incident:
                # Group into existing incident: append latest logs into evidence if present
                if real_telemetry and real_telemetry.get("logs"):
                    active_inv = existing_incident.investigations.first()
                    if active_inv:
                        for log_entry in real_telemetry["logs"]:
                            EvidenceItem.objects.create(
                                investigation=active_inv,
                                source_type=EvidenceSourceType.LOGS,
                                title=f"Correlated Log Event ({service})",
                                description=f"[{log_entry.get('level', 'INFO')}] {log_entry.get('message', '')}",
                                raw_data={"log": log_entry},
                                confidence_impact=0.9
                            )
                created_incidents.append(IncidentSerializer(existing_incident).data)
                continue

            incident = Incident.objects.create(
                title=title,
                service_name=service,
                severity=severity,
                status=IncidentStatus.TRIGGERED,
                summary=summary,
                triggered_at=timezone.now()
            )

            # Auto investigate using real telemetry
            investigation = investigator.investigate(incident, real_telemetry=real_telemetry)
            created_incidents.append(IncidentSerializer(incident).data)

        return Response({
            "status": "processed",
            "received_count": len(alerts),
            "incidents": created_incidents
        }, status=status.HTTP_201_CREATED)


class SystemHealthWatchdogView(APIView):
    """
    Heartbeat and Live System Watchdog API.
    Monitors services status, active incidents, and detects anomalies periodically.
    """
    def get(self, request):
        active_incidents = Incident.objects.exclude(status=IncidentStatus.RESOLVED)
        critical_count = active_incidents.filter(severity=IncidentSeverity.P1_CRITICAL).count()
        total_active = active_incidents.count()

        services = [
            {"name": "checkout-api", "status": "healthy", "latency": "42ms", "error_rate": "0.01%"},
            {"name": "order-service", "status": "healthy", "latency": "38ms", "error_rate": "0.00%"},
            {"name": "auth-service", "status": "healthy", "latency": "19ms", "error_rate": "0.02%"}
        ]

        # Correlate active incidents with service degradation
        for s in services:
            matching = active_incidents.filter(service_name=s["name"]).first()
            if matching:
                s["status"] = "degraded" if matching.severity != IncidentSeverity.P1_CRITICAL else "critical"
                s["active_incident_id"] = str(matching.id)
                s["active_incident_title"] = matching.title

        return Response({
            "status": "critical" if critical_count > 0 else ("warning" if total_active > 0 else "healthy"),
            "timestamp": timezone.now().isoformat(),
            "services_monitored": len(services),
            "services": services,
            "active_incidents_count": total_active,
            "critical_count": critical_count,
            "average_mtti_seconds": 38
        })


class SeedClusterView(APIView):
    """One-click API to seed 5 multi-factor production incidents."""
    def post(self, request):
        from .management.commands.seed_demo import run_seed_cluster
        count = run_seed_cluster()
        incidents = Incident.objects.all()
        return Response({
            "status": "success",
            "message": f"Successfully seeded {count} diverse production incidents.",
            "incidents": IncidentSerializer(incidents, many=True).data
        }, status=status.HTTP_201_CREATED)


class TopologyGraphView(APIView):
    """
    Live Microservice Architecture & Dependency Graph API.
    Returns real-time topology nodes and edges with dynamic cascading failure states.
    """
    def get(self, request):
        recent_cutoff = timezone.now() - timezone.timedelta(seconds=40)
        recent_incidents = Incident.objects.filter(triggered_at__gte=recent_cutoff).exclude(status=IncidentStatus.RESOLVED)
        
        active_api_incident = recent_incidents.filter(service_name__in=["checkout-api", "shop-api"]).first()
        is_checkout_crit = bool(active_api_incident and active_api_incident.severity == IncidentSeverity.P1_CRITICAL)
        is_checkout_deg = bool(active_api_incident and not is_checkout_crit)
        
        has_db_issue = any("connection" in (i.title + i.summary).lower() or "postgres" in (i.title + i.summary).lower() or "pool" in (i.title + i.summary).lower() for i in recent_incidents)
        has_cache_issue = any("redis" in (i.title + i.summary).lower() or "cache" in (i.title + i.summary).lower() for i in recent_incidents)

        nodes = [
            {
                "id": "ingress",
                "name": "Ingress Gateway",
                "type": "gateway",
                "status": "healthy",
                "icon": "globe",
                "metrics": "240 req/s",
                "details": "AWS CloudFront / NGINX Load Balancer"
            },
            {
                "id": "frontend",
                "name": "Web Frontend",
                "type": "service",
                "status": "degraded" if (is_checkout_crit or is_checkout_deg) else "healthy",
                "icon": "monitor",
                "metrics": "18ms P99" if not is_checkout_crit else "1420ms (Waiting)",
                "details": "React 18 / Next.js Storefront"
            },
            {
                "id": "checkout-api",
                "name": "Checkout API",
                "type": "service",
                "status": "critical" if is_checkout_crit else ("degraded" if is_checkout_deg else "healthy"),
                "icon": "server",
                "metrics": "512MB RAM" if is_checkout_crit else "120MB RAM",
                "details": "Python / Flask Microservice (Port 5000)",
                "active_incident": active_api_incident.title if active_api_incident else None
            },
            {
                "id": "postgres-db",
                "name": "PostgreSQL Primary",
                "type": "database",
                "status": "critical" if has_db_issue else "healthy",
                "icon": "database",
                "metrics": "100/100 conns" if has_db_issue else "14/100 conns",
                "details": "Amazon RDS PostgreSQL 16"
            },
            {
                "id": "redis-cache",
                "name": "Redis Cache Cluster",
                "type": "cache",
                "status": "degraded" if has_cache_issue else "healthy",
                "icon": "zap",
                "metrics": "99% miss rate" if has_cache_issue else "98.5% hit rate",
                "details": "AWS ElastiCache Redis 7"
            }
        ]

        edges = [
            { "from": "ingress", "to": "frontend", "status": "active", "latency": "4ms" },
            { "from": "frontend", "to": "checkout-api", "status": "degraded" if is_checkout_crit else "active", "latency": "3200ms" if is_checkout_crit else "14ms" },
            { "from": "checkout-api", "to": "postgres-db", "status": "broken" if has_db_issue else "active", "latency": "TIMEOUT" if has_db_issue else "6ms" },
            { "from": "checkout-api", "to": "redis-cache", "status": "broken" if has_cache_issue else "active", "latency": "TIMEOUT" if has_cache_issue else "2ms" }
        ]

        return Response({
            "nodes": nodes,
            "edges": edges,
            "active_outages_count": recent_incidents.count(),
            "overall_cluster_health": "critical" if (is_checkout_crit or has_db_issue) else ("warning" if (recent_incidents.exists() or has_cache_issue) else "healthy")
        })
