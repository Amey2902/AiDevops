from django.core.management.base import BaseCommand
from django.utils import timezone
from incidents.models import Incident, IncidentSeverity, IncidentStatus
from core.agent.investigator import SREInvestigator
from core.telemetry.provider import get_telemetry_provider, SimulationTelemetryProvider

class Command(BaseCommand):
    help = "Seeds demo incidents and runs AI investigation"

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample DevOps incidents...")

        # 1. Memory Leak Incident
        telemetry = get_telemetry_provider()
        if isinstance(telemetry, SimulationTelemetryProvider):
            telemetry.set_scenario("oom_memory_leak")

        inc1 = Incident.objects.create(
            title="Container Crash Loop & Exit Code 137 (OOM)",
            service_name="payment-processor",
            environment="production",
            severity=IncidentSeverity.P1_CRITICAL,
            status=IncidentStatus.TRIGGERED,
            summary="payment-processor crashed repeatedly during high transaction volume with exit code 137.",
            triggered_at=timezone.now()
        )
        self.stdout.write(f"Created incident: {inc1.title}")

        investigator = SREInvestigator()
        self.stdout.write("Running SRE Investigator for incident 1...")
        inv1 = investigator.investigate(inc1)
        self.stdout.write(f"Investigation completed: {inv1.rca_report.root_cause_title} ({int(inv1.rca_report.confidence_score * 100)}% confidence)")

        # 2. Database Connection Starvation Incident
        if isinstance(telemetry, SimulationTelemetryProvider):
            telemetry.set_scenario("db_connection_starvation")

        inc2 = Incident.objects.create(
            title="Surge in HTTP 500 Responses & Database Socket Timeouts",
            service_name="user-auth-service",
            environment="production",
            severity=IncidentSeverity.P1_CRITICAL,
            status=IncidentStatus.TRIGGERED,
            summary="User login attempts timing out after 30 seconds with internal server errors.",
            triggered_at=timezone.now()
        )
        self.stdout.write(f"Created incident: {inc2.title}")

        self.stdout.write("Running SRE Investigator for incident 2...")
        inv2 = investigator.investigate(inc2)
        self.stdout.write(f"Investigation completed: {inv2.rca_report.root_cause_title} ({int(inv2.rca_report.confidence_score * 100)}% confidence)")

        self.stdout.write(self.style.SUCCESS("Successfully seeded and investigated demo incidents!"))

