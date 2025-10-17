from django.urls import path
from taskbird import views

app_name = 'taskbird'

urlpatterns = [
    path('dashboard/agent/', views.agent_dashboard, name='agent-dashboard'),
    path('agent/tickets/list/', views.agent_ticket_list, name='agent-ticket-list'),
    path('ticket/create/', views.create_ticket, name='create-ticket'),
    path('ticket/crate/agent/', views.agent_create_ticket, name='create-ticket-agent'),
    # path('ticket/filter/', views.ticket_filter, name='ticket-filter'),

    path('agent-customer/sessions/', views.agent_customer_sessions, name='agent-customer-sessions'), 
    path('agent-customer/sessions/<uuid:session_id>/', views.get_session_details, name='agent-customer-session-detail'),
    path('agent-customer/sessions/<uuid:session_id>/accept/', views.accept_session, name='accept-session'),
    path('agent-customer/sessions/<uuid:session_id>/reject/', views.reject_session, name='reject-session'),
]



# new url patterns
urlpatterns += [
    # ========================================================================
    # CUSTOMER VIEWS - Ticket Session Submission & Tracking
    # ========================================================================
    
    # Submit new ticket request (creates TicketSession)
    path('submit/ticket/createsession/', views.submit_ticket_request, name='create-session-view'),
    
    # View specific session detail (customer's own)
    path('session/<uuid:session_id>/', views.customer_session_detail, name='customer_session_detail'),
    
    # View all customer's sessions
    path('my-sessions/', views.customer_sessions_list, name='customer_sessions_list'),
    
    
    # ========================================================================
    # AGENT VIEWS - Review & Process Sessions
    # ========================================================================
    
    # Agent review queue (all pending sessions)
    path('agent/review-queue/', views.agent_review_queue, name='agent_review_queue'),
    
    # Agent views single session for review
    path('agent/session/<uuid:session_id>/review/', views.agent_session_review, name='agent_session_review'),
    
    # Agent accepts session (creates ticket with algorithms)
    path('agent/session/<uuid:session_id>/accept/', views.accept_ticket_session, name='accept_ticket_session'),
    
    # Agent rejects session (no ticket created)
    path('agent/session/<uuid:session_id>/reject/', views.reject_ticket_session, name='reject_ticket_session'),
    
    
    # ========================================================================
    # TICKET VIEWS - After Session is Accepted
    # ========================================================================
    
    # View ticket details
    path('ticket/<str:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    
    
    # ========================================================================
    # OPTIONAL: Add your existing URLs here
    # ========================================================================
    
    # Dashboard, login, etc.
    # path('dashboard/', views.dashboard, name='dashboard'),
    # path('', views.home, name='home'),
]
