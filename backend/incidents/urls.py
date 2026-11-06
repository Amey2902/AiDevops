from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IncidentViewSet, SimulationTriggerView, KnowledgeBaseView

router = DefaultRouter()
router.register(r'incidents', IncidentViewSet, basename='incident')

urlpatterns = [
    path('', include(router.urls)),
    path('simulation/trigger/', SimulationTriggerView.as_view(), name='simulation-trigger'),
    path('knowledge/', KnowledgeBaseView.as_view(), name='knowledge-base'),
]

