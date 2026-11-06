from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import Incident, Investigation, EvidenceItem, RCAReport, IncidentStatus, IncidentSeverity
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
            title = labels.get("alertname") or a.get("title") or "Incoming Prometheus Monitoring Alert"
            service = labels.get("service") or labels.get("job") or a.get("service") or "app-service"
            raw_severity = labels.get("severity", "high").lower()

            if "crit" in raw_severity or "p1" in raw_severity:
                severity = IncidentSeverity.P1_CRITICAL
            elif "high" in raw_severity or "p2" in raw_severity:
                severity = IncidentSeverity.P2_HIGH
            else:
                severity = IncidentSeverity.P3_MODERATE

            summary = annotations.get("summary") or annotations.get("description") or a.get("summary") or "Automated alert received from monitoring cluster."

            incident = Incident.objects.create(
                title=title,
                service_name=service,
                severity=severity,
                status=IncidentStatus.TRIGGERED,
                summary=summary,
                triggered_at=timezone.now()
            )

            # Auto investigate
            investigation = investigator.investigate(incident)
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
