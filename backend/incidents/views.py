from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import Incident, Investigation, EvidenceItem, RCAReport, IncidentStatus, IncidentSeverity
from .serializers import IncidentSerializer, InvestigationSerializer, EvidenceItemSerializer, RCAReportSerializer
from core.agent.investigator import SREInvestigator
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
        rag_context = "\n".join([f"- {h['title']}: {h['content'][:200]}" for h in rag_hits])

        # Generate intelligent contextual reply
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
                "service_name": "order-service",
                "severity": IncidentSeverity.P1_CRITICAL,
                "summary": "Surge of HTTP 500 errors on order-service. Connection timeout exceptions recorded."
            },
            "cpu_throttling": {
                "title": "CFS CPU Quota Throttling & Gateway 504 Timeouts",
                "service_name": "auth-service",
                "severity": IncidentSeverity.P2_HIGH,
                "summary": "Worker thread pool starvation and high latency spikes exceeding health check timeouts."
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
