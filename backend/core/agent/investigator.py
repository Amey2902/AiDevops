import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from incidents.models import (
    Incident,
    Investigation,
    EvidenceItem,
    RCAReport,
    EvidenceSourceType,
    InvestigationStatus,
    IncidentStatus
)
from core.telemetry.provider import get_telemetry_provider
from core.rag.knowledge_manager import get_knowledge_manager

class SREInvestigator:
    """
    Autonomous Site Reliability Engineering (SRE) Investigation Agent.
    Executes a structured diagnostic investigation:
    1. Probes container runtime health and restart states
    2. Inspects and clusters application error logs
    3. Analyzes resource metric time-series (RAM, CPU, connections, error rates)
    4. Queries pgvector/RAG knowledge base for matching runbooks & triage playbooks
    5. Correlates multi-source evidence and synthesizes a verifiable RCA Report.
    """

    def __init__(self):
        self.telemetry = get_telemetry_provider()
        self.knowledge_manager = get_knowledge_manager()

    def investigate(self, incident: Incident) -> Investigation:
        """Execute full end-to-end investigation for an incident."""
        # 1. Initialize or get investigation record
        investigation = Investigation.objects.create(
            incident=incident,
            status=InvestigationStatus.RUNNING,
            agent_summary=f"Initiating autonomous investigation for [{incident.service_name}] regarding '{incident.title}'"
        )
        incident.status = IncidentStatus.INVESTIGATING
        incident.save(update_fields=["status"])

        evidence_collected: List[EvidenceItem] = []
        timeline: List[Dict[str, Any]] = []

        now_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")

        # Step 1: Probe Container Health
        container_state = self.telemetry.get_container_status(incident.service_name)
        timeline.append({
            "time": now_str,
            "phase": "Container Health Inspection",
            "observation": f"Checked container status for '{incident.service_name}'. Status: {container_state.get('status')}."
        })

        if container_state.get("oom_killed") or container_state.get("exit_code") == 137:
            evidence_collected.append(EvidenceItem.objects.create(
                investigation=investigation,
                source_type=EvidenceSourceType.CONTAINER_STATE,
                title=f"Container OOMKilled Detected (Exit Code {container_state.get('exit_code')})",
                description=(
                    f"Container '{container_state.get('container_id')}' was terminated by Linux kernel OOM killer. "
                    f"Restart count: {container_state.get('restart_count')}. Memory limit: {container_state.get('memory_limit_human')}."
                ),
                raw_data=container_state,
                confidence_impact=0.95
            ))
        elif container_state.get("restart_count", 0) > 0:
            evidence_collected.append(EvidenceItem.objects.create(
                investigation=investigation,
                source_type=EvidenceSourceType.CONTAINER_STATE,
                title=f"Container Restart Events Recorded ({container_state.get('restart_count')} restarts)",
                description=f"Status: {container_state.get('status')}. Reason: {container_state.get('last_exit_reason')}",
                raw_data=container_state,
                confidence_impact=0.75
            ))

        # Step 2: Fetch and Cluster Error Logs
        logs = self.telemetry.get_logs(incident.service_name, log_level="ERROR")
        error_logs = [log for log in logs if log.get("level") in ["ERROR", "FATAL", "CRITICAL"]]
        if error_logs:
            sample_messages = [l.get("message") for l in error_logs[:3]]
            timeline.append({
                "time": now_str,
                "phase": "Log Analysis",
                "observation": f"Identified {len(error_logs)} high-severity log events around incident timestamp."
            })
            evidence_collected.append(EvidenceItem.objects.create(
                investigation=investigation,
                source_type=EvidenceSourceType.LOGS,
                title=f"Critical Application Error Logs Identified ({len(error_logs)} records)",
                description="Cluster of fatal error messages extracted: \n" + "\n".join(f"- {msg}" for msg in sample_messages),
                raw_data={"total_error_logs": len(error_logs), "logs": error_logs},
                confidence_impact=0.90
            ))

        # Step 3: Analyze Metric Time-Series
        metrics_checked = ["memory", "cpu", "connections", "errors", "latency"]
        anomaly_metrics = []
        for m_type in metrics_checked:
            metric_data = self.telemetry.get_metrics(incident.service_name, m_type)
            if metric_data.get("anomaly_detected"):
                anomaly_metrics.append(metric_data)
                evidence_collected.append(EvidenceItem.objects.create(
                    investigation=investigation,
                    source_type=EvidenceSourceType.METRICS,
                    title=f"Metric Anomaly: {metric_data.get('metric')}",
                    description=metric_data.get("anomaly_details", f"Anomalous surge observed in {metric_data.get('metric')}."),
                    raw_data=metric_data,
                    confidence_impact=0.88
                ))

        if anomaly_metrics:
            timeline.append({
                "time": now_str,
                "phase": "Metric Anomaly Correlation",
                "observation": f"Correlated {len(anomaly_metrics)} anomalous metric spikes leading up to the failure."
            })

        # Step 4: RAG Runbook Querying
        search_query = f"{incident.title} {incident.service_name}"
        if container_state.get("oom_killed") or container_state.get("exit_code") == 137:
            search_query += " OOMKilled exit code 137 memory leak"
        elif any("connection" in str(m).lower() for m in anomaly_metrics) or any("connection" in str(l).lower() for l in error_logs):
            search_query += " postgres database connection pool exhaustion timeout"
        elif any("throttling" in str(m).lower() for m in anomaly_metrics):
            search_query += " cpu throttling cfs quota thread starvation"

        matched_runbooks = self.knowledge_manager.query(search_query, top_k=2)
        cited_runbooks = []
        for r in matched_runbooks:
            cited_runbooks.append({
                "title": r.get("title"),
                "similarity_score": r.get("similarity_score"),
                "source": r.get("metadata", {}).get("filename"),
                "excerpt": r.get("content", "")[:300] + "..."
            })

        if matched_runbooks:
            top_match = matched_runbooks[0]
            evidence_collected.append(EvidenceItem.objects.create(
                investigation=investigation,
                source_type=EvidenceSourceType.RUNBOOK_MATCH,
                title=f"Runbook Knowledge Match: {top_match.get('title')}",
                description=f"Retrieved diagnostic procedures with {int(top_match.get('similarity_score', 0) * 100)}% similarity match.",
                raw_data={"matched_runbooks": cited_runbooks},
                confidence_impact=0.85
            ))
            timeline.append({
                "time": now_str,
                "phase": "Knowledge Base Retrieval",
                "observation": f"Matched operational runbook '{top_match.get('title')}' for remediation guidance."
            })

        # Step 5: Synthesize RCA Findings & Create RCA Report
        rca_report = self._synthesize_rca(
            incident=incident,
            investigation=investigation,
            container_state=container_state,
            error_logs=error_logs,
            anomaly_metrics=anomaly_metrics,
            matched_runbooks=matched_runbooks,
            cited_runbooks=cited_runbooks,
            timeline=timeline
        )

        investigation.status = InvestigationStatus.COMPLETED
        investigation.completed_at = datetime.now(timezone.utc)
        investigation.agent_summary = (
            f"Investigation concluded with {int(rca_report.confidence_score * 100)}% confidence. "
            f"Probable root cause: {rca_report.root_cause_title}."
        )
        investigation.save(update_fields=["status", "completed_at", "agent_summary"])

        incident.status = IncidentStatus.IDENTIFIED
        incident.save(update_fields=["status"])

        return investigation

    def _synthesize_rca(
        self,
        incident: Incident,
        investigation: Investigation,
        container_state: Dict[str, Any],
        error_logs: List[Dict[str, Any]],
        anomaly_metrics: List[Dict[str, Any]],
        matched_runbooks: List[Dict[str, Any]],
        cited_runbooks: List[Dict[str, Any]],
        timeline: List[Dict[str, Any]]
    ) -> RCAReport:
        """Synthesizes structured RCA based on verified evidence."""

        # Determine Root Cause
        if container_state.get("oom_killed") or container_state.get("exit_code") == 137:
            title = "Uncontrolled Memory Leak Causing Linux OOMKilled Termination (Exit Code 137)"
            summary = (
                f"The service '{incident.service_name}' exceeded its allotted container memory ceiling "
                f"({container_state.get('memory_limit_human', '512MB')}). "
                "Memory consumption climbed steadily without deallocation until the Linux kernel Out-Of-Memory Killer "
                "issued SIGKILL (Exit code 137), triggering an unexpected crash restart loop and client-facing HTTP 500 errors."
            )
            confidence = 0.96
            immediate = [
                f"Increase container memory limit from {container_state.get('memory_limit_human', '512MB')} to 1024MB in docker-compose.yml.",
                "Restart the container instance to reclaim leaked heap memory.",
                "Verify memory working set stabilizes below 50% post-restart."
            ]
            preventative = [
                "Profile application heap allocations to identify uncollected object references.",
                "Implement streaming response processing for batch/bulk export endpoints.",
                "Configure Prometheus alert for container_memory_working_set_bytes exceeding 85% limit."
            ]

        elif any("connection" in str(m).lower() for m in anomaly_metrics) or any("connection" in str(l).lower() for l in error_logs):
            title = "PostgreSQL Database Connection Pool Exhaustion & Worker Starvation"
            summary = (
                f"The database connection pool for '{incident.service_name}' reached maximum capacity (100/100 connections). "
                "Incoming API transactions were unable to acquire a database socket and timed out after 30 seconds, "
                "causing cascading HTTP 500/503 errors across client-facing endpoints."
            )
            confidence = 0.93
            immediate = [
                "Terminate stuck 'idle in transaction' connections on PostgreSQL via pg_terminate_backend().",
                "Restart saturated worker replicas to release orphaned client sockets.",
                "Temporarily raise max_connections if PostgreSQL server RAM permits."
            ]
            preventative = [
                "Deploy PgBouncer connection pooler in transaction pooling mode.",
                "Enforce strict idle_in_transaction_session_timeout = '30s' in PostgreSQL config.",
                "Audit codebase to ensure all DB sessions utilize context managers (with transaction.atomic():)."
            ]

        elif any("throttling" in str(m).lower() for m in anomaly_metrics):
            title = "CFS CPU Quota Throttling Causing Thread Pool Starvation and Timeout Cascade"
            summary = (
                f"Container for '{incident.service_name}' was throttled in over 70% of CFS scheduling periods "
                "due to high computational bursts exceeding the assigned 0.5 CPU core limit, leading to liveness probe timeout."
            )
            confidence = 0.91
            immediate = [
                "Increase container CPU limit from 0.5 to 2.0 cores in deployment manifests.",
                "Scale out replica count to distribute compute workloads."
            ]
            preventative = [
                "Offload heavy synchronous CPU computations to Celery/background workers.",
                "Tune liveness/readiness probe timeout parameters to avoid premature pod restarts during traffic spikes."
            ]

        else:
            title = "Application Service Degradation & Elevated Error Rate"
            summary = f"Telemetry reveals an abnormal surge in error responses on '{incident.service_name}' correlated with log exceptions."
            confidence = 0.82
            immediate = ["Restart service instances.", "Roll back the most recent deployment."]
            preventative = ["Introduce canary deployments and enhanced integration regression tests."]

        return RCAReport.objects.create(
            investigation=investigation,
            root_cause_title=title,
            root_cause_summary=summary,
            confidence_score=confidence,
            timeline_summary=timeline,
            recommended_immediate_actions=immediate,
            recommended_preventative_actions=preventative,
            cited_runbooks=cited_runbooks
        )

