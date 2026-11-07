from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    IncidentViewSet, 
    SimulationTriggerView, 
    KnowledgeBaseView, 
    AlertWebhookView, 
    SystemHealthWatchdogView,
    SeedClusterView,
    TopologyGraphView
)

router = DefaultRouter()
router.register(r'incidents', IncidentViewSet, basename='incident')

urlpatterns = [
    path('', include(router.urls)),
    path('simulation/trigger/', SimulationTriggerView.as_view(), name='simulation-trigger'),
    path('simulation/seed-cluster/', SeedClusterView.as_view(), name='seed-cluster'),
    path('knowledge/', KnowledgeBaseView.as_view(), name='knowledge-base'),
    path('webhook/', AlertWebhookView.as_view(), name='alert-webhook'),
    path('incidents/webhook/', AlertWebhookView.as_view(), name='alert-webhook-incidents'),
    path('health/watchdog/', SystemHealthWatchdogView.as_view(), name='health-watchdog'),
    path('topology/', TopologyGraphView.as_view(), name='topology-graph'),
]

