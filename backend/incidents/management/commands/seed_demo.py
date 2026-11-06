from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from incidents.models import (
    Incident, 
    Investigation, 
    EvidenceItem, 
    RCAReport, 
    IncidentSeverity, 
    IncidentStatus, 
    InvestigationStatus,
    EvidenceSourceType
)
from core.agent.investigator import SREInvestigator
from core.telemetry.provider import get_telemetry_provider, SimulationTelemetryProvider

def run_seed_cluster():
    """Seeds 5 diverse, realistic production incidents with multi-factor evidence."""
    now = timezone.now()
    telemetry = get_telemetry_provider()
    investigator = SREInvestigator()

    # 1. P1 Critical: OOMKilled Memory Leak
    if isinstance(telemetry, SimulationTelemetryProvider):
        telemetry.set_scenario("oom_memory_leak")

    inc1 = Incident.objects.filter(service_name="checkout-api", title__icontains="OOM").first()
    if not inc1:
        inc1 = Incident.objects.create(
            title="Container Crash Loop & Linux OOMKiller (Exit 137)",
            service_name="checkout-api",
            environment="production",
            severity=IncidentSeverity.P1_CRITICAL,
            status=IncidentStatus.TRIGGERED,
            summary="Service checkout-api crashed repeatedly during promotion event. Linux kernel invoked OOM killer (Signal 9 / Exit 137).",
            triggered_at=now - timedelta(minutes=42)
        )
    if not inc1.investigations.exists():
        investigator.investigate(inc1)

    # 2. P1 Critical: DB Connection Pool Starvation & 500 Outage
    if isinstance(telemetry, SimulationTelemetryProvider):
        telemetry.set_scenario("db_connection_starvation")

    inc2 = Incident.objects.filter(service_name="payment-gateway", title__icontains="Connection").first()
    if not inc2:
        inc2 = Incident.objects.create(
            title="Database Connection Pool Starvation & HTTP 500 Outage",
            service_name="payment-gateway",
            environment="production",
            severity=IncidentSeverity.P1_CRITICAL,
            status=IncidentStatus.TRIGGERED,
            summary="Surge of HTTP 500 errors on payment endpoints. PostgreSQL connection pool saturated with 88 connections stuck idle in transaction.",
            triggered_at=now - timedelta(minutes=28)
        )
    if not inc2.investigations.exists():
        investigator.investigate(inc2)

    # 3. P2 High: CPU Throttling & 504 Gateway Timeouts
    if isinstance(telemetry, SimulationTelemetryProvider):
        telemetry.set_scenario("cpu_throttling")

    inc3 = Incident.objects.filter(service_name="auth-service", title__icontains="CFS").first()
    if not inc3:
        inc3 = Incident.objects.create(
            title="CFS CPU Quota Throttling & Gateway 504 Timeouts",
            service_name="auth-service",
            environment="production",
            severity=IncidentSeverity.P2_HIGH,
            status=IncidentStatus.TRIGGERED,
            summary="Worker thread pool starvation and high latency spikes exceeding health check timeouts. 78% CFS scheduling periods throttled.",
            triggered_at=now - timedelta(minutes=15)
        )
    if not inc3.investigations.exists():
        investigator.investigate(inc3)

    # 4. P2 High: Redis Cache Timeout & DB Fallback Overload (In status INVESTIGATING)
    inc4 = Incident.objects.filter(service_name="inventory-service").first()
    if not inc4:
        inc4 = Incident.objects.create(
            title="Redis Cache Cluster Timeout & Cascading Database Overload",
            service_name="inventory-service",
            environment="production",
            severity=IncidentSeverity.P2_HIGH,
            status=IncidentStatus.INVESTIGATING,
            summary="Redis cluster timeout causing 1,200 req/sec cache miss stampede to directly hit PostgreSQL primary database.",
            triggered_at=now - timedelta(minutes=6)
        )
    if not inc4.investigations.exists():
        inv4 = Investigation.objects.create(
            incident=inc4,
            status=InvestigationStatus.RUNNING,
            agent_summary="Investigating Redis socket timeout anomalies and correlating cache miss metrics with database CPU spike.",
            started_at=now - timedelta(minutes=5)
        )
        EvidenceItem.objects.create(
            investigation=inv4,
            source_type=EvidenceSourceType.LOGS,
            title="Redis Connection Timed Out After 5000ms",
            description="RedisConnectionError: Timeout reading from socket on redis-sentinel-01:6379",
            raw_data={"error": "RedisConnectionError", "host": "redis-sentinel-01:6379"},
            confidence_impact=0.82
        )
        EvidenceItem.objects.create(
            investigation=inv4,
            source_type=EvidenceSourceType.METRICS,
            title="Postgres Read Query QPS Surge (+400%)",
            description="Read IOPS jumped from 250 to 1,250 QPS immediately following Redis timeout.",
            raw_data={"metric": "pg_stat_statements_calls", "increase": "+400%"},
            confidence_impact=0.88
        )

    # 5. P3 Moderate: Async Worker Queue Dead-Letter Buildup (In status TRIGGERED - ready for user investigation)
    inc5 = Incident.objects.filter(service_name="notification-worker").first()
    if not inc5:
        inc5 = Incident.objects.create(
            title="Async Notification Worker Dead-Letter Queue Spike",
            service_name="notification-worker",
            environment="production",
            severity=IncidentSeverity.P3_MODERATE,
            status=IncidentStatus.TRIGGERED,
            summary="Upstream SMTP rate limit 429 triggered queue backlog exceeding 10,000 pending message tasks.",
            triggered_at=now - timedelta(minutes=2)
        )

    return 5


class Command(BaseCommand):
    help = "Seeds 5 diverse, multi-factor production incidents into DevOpsAI"

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample DevOps incidents...")
        count = run_seed_cluster()
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {count} diverse production incidents!"))
