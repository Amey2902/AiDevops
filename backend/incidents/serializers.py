from rest_framework import serializers
from .models import Incident, Investigation, EvidenceItem, RCAReport

class EvidenceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceItem
        fields = [
            "id",
            "source_type",
            "title",
            "description",
            "raw_data",
            "confidence_impact",
            "timestamp",
        ]


class RCAReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = RCAReport
        fields = [
            "id",
            "root_cause_title",
            "root_cause_summary",
            "confidence_score",
            "timeline_summary",
            "recommended_immediate_actions",
            "recommended_preventative_actions",
            "cited_runbooks",
            "created_at",
        ]


class InvestigationSerializer(serializers.ModelSerializer):
    evidence_items = EvidenceItemSerializer(many=True, read_only=True)
    rca_report = RCAReportSerializer(read_only=True)

    class Meta:
        model = Investigation
        fields = [
            "id",
            "incident",
            "status",
            "agent_summary",
            "started_at",
            "completed_at",
            "evidence_items",
            "rca_report",
            "created_at",
        ]


class IncidentSerializer(serializers.ModelSerializer):
    investigations = InvestigationSerializer(many=True, read_only=True)
    active_investigation = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = [
            "id",
            "title",
            "service_name",
            "environment",
            "severity",
            "status",
            "summary",
            "triggered_at",
            "resolved_at",
            "created_at",
            "updated_at",
            "active_investigation",
            "investigations",
        ]

    def get_active_investigation(self, obj):
        latest = obj.investigations.first()
        if latest:
            return InvestigationSerializer(latest).data
        return None

