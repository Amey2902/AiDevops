import uuid
from django.db import models
from django.utils import timezone

class IncidentSeverity(models.TextChoices):
    P1_CRITICAL = "P1_CRITICAL", "P1 - Critical"
    P2_HIGH = "P2_HIGH", "P2 - High"
    P3_MODERATE = "P3_MODERATE", "P3 - Moderate"
    P4_LOW = "P4_LOW", "P4 - Low"

class IncidentStatus(models.TextChoices):
    TRIGGERED = "TRIGGERED", "Triggered"
    INVESTIGATING = "INVESTIGATING", "Investigating"
    IDENTIFIED = "IDENTIFIED", "Root Cause Identified"
    MITIGATED = "MITIGATED", "Mitigated"
    RESOLVED = "RESOLVED", "Resolved"

class InvestigationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"

class EvidenceSourceType(models.TextChoices):
    LOGS = "LOGS", "Application Logs"
    METRICS = "METRICS", "Prometheus Metrics"
    CONTAINER_STATE = "CONTAINER_STATE", "Container Health State"
    RUNBOOK_MATCH = "RUNBOOK_MATCH", "Runbook Knowledge Match"
    NETWORK = "NETWORK", "Network & Ingress Telemetry"


class Incident(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    service_name = models.CharField(max_length=120)
    environment = models.CharField(max_length=64, default="production")
    severity = models.CharField(max_length=20, choices=IncidentSeverity.choices, default=IncidentSeverity.P2_HIGH)
    status = models.CharField(max_length=20, choices=IncidentStatus.choices, default=IncidentStatus.TRIGGERED)
    summary = models.TextField(blank=True, default="")
    triggered_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-triggered_at"]

    @property
    def active_investigation(self):
        return self.investigations.order_by("-started_at").first()

    def __str__(self):
        return f"[{self.severity}] {self.service_name} - {self.title}"


class Investigation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="investigations")
    status = models.CharField(max_length=20, choices=InvestigationStatus.choices, default=InvestigationStatus.PENDING)
    agent_summary = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Investigation {self.id} for {self.incident.title} ({self.status})"


class EvidenceItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE, related_name="evidence_items")
    source_type = models.CharField(max_length=32, choices=EvidenceSourceType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    raw_data = models.JSONField(default=dict, blank=True)
    confidence_impact = models.FloatField(default=0.8)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"[{self.source_type}] {self.title}"


class RCAReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.OneToOneField(Investigation, on_delete=models.CASCADE, related_name="rca_report")
    root_cause_title = models.CharField(max_length=255)
    root_cause_summary = models.TextField()
    confidence_score = models.FloatField(default=0.9)
    timeline_summary = models.JSONField(default=list, blank=True)
    recommended_immediate_actions = models.JSONField(default=list, blank=True)
    recommended_preventative_actions = models.JSONField(default=list, blank=True)
    cited_runbooks = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RCA: {self.root_cause_title} ({int(self.confidence_score * 100)}% confidence)"
