from django.urls import path
from taskbird import views


urlpatterns = [
    path('dashboard/agent/', views.agent_dashboard, name='agent-dashboard'),
    path('agent/tickets/list/', views.agent_ticket_list, name='agent-ticket-list'),
    path('ticket/create/', views.create_ticket, name='create-ticket'),
    path('ticket/crate/agent/', views.agent_create_ticket, name='create-ticket-agent'),
    # path('ticket/filter/', views.ticket_filter, name='ticket-filter'),
]
