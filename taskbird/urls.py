from django.urls import path
from taskbird import views


urlpatterns = [
    path('dashboard/agent/', views.agent_dashboard, name='agent-dashboard'),
    path('ticket/create/', views.create_ticket, name='create-ticket'),
]
