from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from accounts.decorators import agent_required
from taskbird.forms import TicketForm, TicketAgentForm, TicketFilterForm
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from .models import (
    Ticket, TicketSession, TicketSessionAttachment, 
    Category, Priority, Status, TicketAttachment
)
from .algorithms import process_new_ticket, PriorityScoring, ResponseTimePredictor
import json
from config.logger import get_logger



logger = get_logger(__name__)


@login_required(redirect_field_name='next', login_url='login')
@agent_required 
def agent_dashboard(request):
    """Agent dashboard - ticket resolution"""
    if not request.user.is_agent:
        messages.error(request, 'Access denied. Agent access required.')
        return redirect('login-view')
    
    return render(request, 'taskbird/agent_dashboard.html', {'user': request.user})


# ticket creation view for customer
@login_required(redirect_field_name='next', login_url='login-view')
def create_ticket(request):
    context = {}
    if request.method == 'POST':
        logger.info(f"request data: {request.POST}")
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.customer = request.user
            # ticket.status = Status.objects.get(name='Open')  # Default status
            ticket.channel = 'FORM'
            ticket.save()
            
            # Handle attachments
            # files = form.cleaned_data.get('attachments', [])
            # for file in files:
            #     TicketAttachment.objects.create(
            #         ticket=ticket,
            #         file=file,
            #         uploaded_by=request.user
            #     )
            
            messages.success(request, f"Ticket {ticket.ticket_id} created successfully!")
            if request.user.is_agent:
                return redirect('agent-ticket-list')
            return redirect('customer-dashboard')  # Adjust to your ticket list view
        else:
            messages.error(request, "Invalid credentials for Ticket!")
            return redirect("customer-dashboard")
    else:
        form = TicketForm()
        context['form'] = form
    
    return render(request, 'taskbird/create_ticket.html', context)

# ticket creation view forom agent side
@login_required(redirect_field_name='next', login_url='login-view')
@require_POST
@agent_required
def agent_create_ticket(request):
    """
    Handle ticket creation via POST request by agent only.
    Validates form data and creates ticket if valid.
    """
    if not request.user.is_authenticated and not request.user.is_agent:
        messages.error(request, 'Access denied. Agent Access required.')
        return redirect('login-view')
    
    form = TicketAgentForm(request.POST)
    try:
        if form.is_valid():
            with transaction.atomic():
                current_ticket = form.save(commit=False)
                current_ticket.agent = request.user
                current_ticket.save()

            logger.info(f"Ticket {current_ticket.ticket_id} created by agent {request.user.id}")
            messages.success(request, f"Ticket {current_ticket.ticket_id} created successfully!")

            return HttpResponseRedirect(reverse('agent-ticket-list'))
        else:
            logger.warning(f"Invalid form submission by user {request.user.id}: {form.errors}")
            
            # Get existing context for re-rendering the page
            context = _get_ticket_list_context(request)
            context['agent_ticket_form'] = form  # Pass the invalid form with errors
            
            messages.error(request, "Please correct the errors below.")
            return render(request, 'taskbird/agent_ticketlist.html', context)
    except Exception as e:
        logger.error(f"Error creating ticket for user {request.user.id}: {str(e)}")
        messages.error(request, "An error occurred while creating the ticket. Please try again.")
        return redirect('agent-ticket-list')


# get_ticket_list_context func
def _get_ticket_list_context(request):
    """
    Helper function to build context for ticket list view.
    Separates filtering logic for better maintainability.
    """
    context = {}

    # initialize forms
    agent_ticket_form = TicketAgentForm()
    filter_form = TicketFilterForm(request.GET or None)

    # Build filters
    filters = Q()

    if filter_form.is_valid():
        filter_data = filter_form.cleaned_data

        # Dictionary mapping for cleaner filter building
        filter_mappings = {
            'customer': 'customer',
            'agent': 'agent',
            'priority': 'priority',
            'status': 'status',
            'category': 'category',
            'channel': 'channel',
        }

        # Apply direct field filters
        for form_field, model_field in filter_mappings.items():
            value = filter_data.get(form_field)
            if value:
                filters &= Q(**{model_field: value})

        from_date = filter_data.get('from_date')
        to_date = filter_data.get('to_date')
        
        if from_date:
            filters &= Q(created_at__date__gte=from_date)
        if to_date:
            filters &= Q(created_at__date__lte=to_date)

    # Get filtered tickets with proper ordering and optimization
    tickets = Ticket.objects.filter(filters).select_related('customer', 'agent', 'priority').order_by('-created_at')

    # pagination
    paginator = Paginator(tickets, 10) # 20 tickets per page
    page = request.GET.get('page')

    try:
        tickets_page = paginator.page(page)
    except PageNotAnInteger:
        tickets_page = paginator.page(1)
    except EmptyPage:
        tickets_page = paginator.page(paginator.num_pages)

    context.update({
        'agent_ticket_form': agent_ticket_form,
        'filter_form': filter_form,
        'tickets': tickets_page,  # Use paginated tickets
        'total_tickets': paginator.count,

    })

    return context

@login_required(redirect_field_name='next', login_url='login-view')
@require_http_methods(['GET', 'POST'])
@agent_required
def agent_ticket_list(request):
    """
    Display filtered list of tickets with forms for filtering and creating new tickets.
    """

    if not request.user.is_authenticated and not request.user.is_agent:
        messages.error(request, 'Access denied. Agent Access required.')
        return redirect('login-view')
    
    try:
        context = _get_ticket_list_context(request)
        logger.info(f"{context=}")
        return render(request, "taskbird/agent_ticketlist.html", context)
    except Exception as e:
        logger.error(f"Error loading ticket list for user {request.user.id}: {str(e)}")
        messages.error(request, "An error occurred while loading tickets.")
        return render(request, 'taskbird/agent_ticketlist.html', {
            'agent_ticket_form': TicketAgentForm(),
            'filter_form': TicketFilterForm(),
            'tickets': Ticket.objects.none(),
        })
    

# agent customer sessions
@login_required
def agent_customer_sessions(request):
    if not request.user.is_authenticated and not request.user.is_agent:
        messages.error(request, 'Access denied. Agent Access required.')
        return redirect('login-view')
    
    context = {}
    # Fetch all sessions (optimized with related objects)
    sessions = TicketSession.objects.select_related(
        'customer', 'category', 'priority', 'reviewed_by'
    ).all()

    context['sessions'] = sessions
    return render(request, "taskbird/agent_customer_sessions.html", context)



# agent customer sessions details

# @login_required
# def get_session_details(request, session_id):
#     session = get_object_or_404(TicketSession, session_id=session_id)
#     attachments = [
#         {
#             'id': attachment.id,
#             'file_url': attachment.file.url,
#             'uploaded_by': attachment.uploaded_by.username,
#             'uploaded_at': attachment.uploaded_at.strftime('%b %d, %Y %I:%M %p')
#         } for attachment in session.attachments.all()
#     ]
#     data = {
#         'session_id': str(session.session_id),
#         'title': session.title,
#         'description': session.description,
#         'customer': session.customer.username,
#         'category': session.category.name if session.category else 'None',
#         'priority': session.priority.name if session.priority else 'None',
#         'channel': session.get_channel_display(),
#         'status': session.get_session_status_display(),
#         'reviewed_by': session.reviewed_by.username if session.reviewed_by else 'None',
#         'rejection_reason': session.rejection_reason if session.rejection_reason else 'None',
#         'created_at': session.created_at.strftime('%b %d, %Y %I:%M %p'),
#         'reviewed_at': session.reviewed_at.strftime('%b %d, %Y %I:%M %p') if session.reviewed_at else 'Not reviewed',
#         'created_ticket': session.created_ticket.id if session.created_ticket else 'None',
#         'attachments': attachments,
#     }
#     return JsonResponse(data)

# @login_required
# def accept_session(request, session_id):
#     """
#     Agent accepts the session and creates actual Ticket.
#     All 3 algorithms are applied automatically:
#     1. Priority Scoring
#     2. Auto-assignment
#     3. Response Time Prediction
#     """
#     if not request.user.is_staff:
#         return JsonResponse({'success': False, 'error': "You don't have permission to perform this action."}, status=403)
    
#     session = get_object_or_404(TicketSession, session_id=session_id)
    
#     # Check if already processed
#     if session.session_status != 'PENDING':
#         return JsonResponse({'success': False, 'error': f"This session has already been {session.session_status.lower()}."}, status=400)
    
#     if request.method == 'POST':
#         try:
#             # Use the model's method to accept and create ticket
#             ticket = session.accept_and_create_ticket(agent=request.user)
            
#             # Get algorithm results for display
#             prediction = ResponseTimePredictor.predict_resolution_time(ticket)
            
#             # Send notification email to customer
#             send_acceptance_email_to_customer(session, ticket)
            
#             # Prepare updated session data for dynamic UI update
#             attachments = [
#                 {
#                     'id': attachment.id,
#                     'file_url': attachment.file.url,
#                     'uploaded_by': attachment.uploaded_by.username,
#                     'uploaded_at': attachment.uploaded_at.strftime('%b %d, %Y %I:%M %p')
#                 } for attachment in session.attachments.all()
#             ]
#             data = {
#                 'success': True,
#                 'ticket_id': ticket.ticket_id,
#                 'message': (
#                     f"✅ Session accepted and converted to Ticket {ticket.ticket_id}! "
#                     f"<br>📊 Priority: {ticket.priority.name if ticket.priority else 'Not set'} "
#                     f"<br>👤 Assigned to: {ticket.agent.username if ticket.agent else 'Unassigned'} "
#                     f"<br>⏱️ Estimated resolution: {prediction['formatted_time']}"
#                 ),
#                 'redirect_url': f"/taskbird/tickets/{ticket.ticket_id}/",  # Adjust if ticket_detail URL is different
#                 'session': {
#                     'session_id': str(session.session_id),
#                     'title': session.title,
#                     'description': session.description,
#                     'customer': session.customer.username,
#                     'category': session.category.name if session.category else 'None',
#                     'priority': session.priority.name if session.priority else 'None',
#                     'channel': session.get_channel_display(),
#                     'status': session.get_session_status_display(),
#                     'reviewed_by': session.reviewed_by.username if session.reviewed_by else 'None',
#                     'rejection_reason': session.rejection_reason if session.rejection_reason else 'None',
#                     'created_at': session.created_at.strftime('%b %d, %Y %I:%M %p'),
#                     'reviewed_at': session.reviewed_at.strftime('%b %d, %Y %I:%M %p') if session.reviewed_at else 'Not reviewed',
#                     'created_ticket': session.created_ticket.id if session.created_ticket else 'None',
#                     'attachments': attachments,
#                 }
#             }
#             return JsonResponse(data)
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': f"Error accepting session: {str(e)}"}, status=500)
    
#     # GET request - show confirmation page
#     return render(request, 'taskbird/confirm_accept_session.html', {'session': session})

# @login_required
# def reject_session(request, session_id):
#     """
#     Agent rejects the session with a reason.
#     NO Ticket is created.
#     Customer is notified of rejection.
#     """
#     if not request.user.is_staff:
#         return JsonResponse({'success': False, 'error': "You don't have permission to perform this action."}, status=403)
    
#     session = get_object_or_404(TicketSession, session_id=session_id)
    
#     # Check if already processed
#     if session.session_status != 'PENDING':
#         return JsonResponse({'success': False, 'error': f"This session has already been {session.session_status.lower()}."}, status=400)
    
#     if request.method == 'POST':
#         data = json.loads(request.body)
#         rejection_reason = data.get('rejection_reason', '').strip()
        
#         if not rejection_reason:
#             return JsonResponse({'success': False, 'error': 'Please provide a reason for rejection.'}, status=400)
        
#         try:
#             # Use model's method to reject session
#             session.reject_session(agent=request.user, reason=rejection_reason)
            
#             # Send rejection notification to customer
#             send_rejection_email_to_customer(session)
            
#             # Prepare updated session data for dynamic UI update
#             attachments = [
#                 {
#                     'id': attachment.id,
#                     'file_url': attachment.file.url,
#                     'uploaded_by': attachment.uploaded_by.username,
#                     'uploaded_at': attachment.uploaded_at.strftime('%b %d, %Y %I:%M %p')
#                 } for attachment in session.attachments.all()
#             ]
#             data = {
#                 'success': True,
#                 'message': f"❌ Session {session.session_id} has been rejected. Customer has been notified.",
#                 'redirect_url': '/taskbird/agent-review-queue/',  # Adjust if agent_review_queue URL is different
#                 'session': {
#                     'session_id': str(session.session_id),
#                     'title': session.title,
#                     'description': session.description,
#                     'customer': session.customer.username,
#                     'category': session.category.name if session.category else 'None',
#                     'priority': session.priority.name if session.priority else 'None',
#                     'channel': session.get_channel_display(),
#                     'status': session.get_session_status_display(),
#                     'reviewed_by': session.reviewed_by.username if session.reviewed_by else 'None',
#                     'rejection_reason': session.rejection_reason if session.rejection_reason else 'None',
#                     'created_at': session.created_at.strftime('%b %d, %Y %I:%M %p'),
#                     'reviewed_at': session.reviewed_at.strftime('%b %d, %Y %I:%M %p') if session.reviewed_at else 'Not reviewed',
#                     'created_ticket': session.created_ticket.id if session.created_ticket else 'None',
#                     'attachments': attachments,
#                 }
#             }
#             return JsonResponse(data)
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': f"Error rejecting session: {str(e)}"}, status=500)
    
#     # GET request - show rejection form
#     return render(request, 'taskbird/reject_session_form.html', {'session': session})



@login_required
def get_session_details(request, session_id):
    session = get_object_or_404(TicketSession, session_id=session_id)
    attachments = [
        {
            'id': attachment.id,
            'file_url': attachment.file.url,
            'uploaded_by': attachment.uploaded_by.username,
            'uploaded_at': attachment.uploaded_at.strftime('%b %d, %Y %I:%M %p')
        } for attachment in session.attachments.all()
    ]
    data = {
        'session_id': str(session.session_id),
        'title': session.title,
        'description': session.description,
        'customer': session.customer.username,
        'category': session.category.name if session.category else 'None',
        'priority': session.priority.name if session.priority else 'None',
        'channel': session.get_channel_display(),
        'status': session.get_session_status_display(),
        'reviewed_by': session.reviewed_by.username if session.reviewed_by else 'None',
        'rejection_reason': session.rejection_reason if session.rejection_reason else 'None',
        'created_at': session.created_at.strftime('%b %d, %Y %I:%M %p'),
        'reviewed_at': session.reviewed_at.strftime('%b %d, %Y %I:%M %p') if session.reviewed_at else 'Not reviewed',
        'created_ticket': session.created_ticket.id if session.created_ticket else 'None',
        'attachments': attachments,
    }
    return JsonResponse(data)

@login_required
def accept_session(request, session_id):
    """
    Agent accepts the session and creates actual Ticket.
    Applies RoundRobinAssignment, Priority Scoring, and Response Time Prediction.
    """
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': "You don't have permission to perform this action."}, status=403)
    
    session = get_object_or_404(TicketSession, session_id=session_id)
    
    if session.session_status != 'PENDING':
        return JsonResponse({'success': False, 'error': f"This session has already been {session.session_status.lower()}."}, status=400)
    
    if request.method == 'POST':
        try:
            # Create ticket and assign using RoundRobinAssignment (handled in model)
            ticket = session.accept_and_create_ticket(agent=request.user)
            
            # Get response time prediction
            try:
                prediction = ResponseTimePredictor.predict_resolution_time(ticket)
                prediction_text = f"<br>⏱️ Estimated resolution: {prediction['formatted_time']}"
            except (ImportError, AttributeError, KeyError) as e:
                prediction_text = "<br>⏱️ Estimated resolution: Not available"
            
            # Send notification email to customer
            try:
                send_acceptance_email_to_customer(session, ticket)
            except Exception as e:
                return JsonResponse({'success': False, 'error': f"Error sending acceptance email: {str(e)}"}, status=500)
            
            # Prepare updated session data for UI update
            attachments = [
                {
                    'id': attachment.id,
                    'file_url': attachment.file.url,
                    'uploaded_by': attachment.uploaded_by.username,
                    'uploaded_at': attachment.uploaded_at.strftime('%b %d, %Y %I:%M %p')
                } for attachment in session.attachments.all()
            ]
            data = {
                'success': True,
                'ticket_id': ticket.ticket_id,
                'message': (
                    f"✅ Session accepted and ticket {ticket.ticket_id} created! "
                    f"<br>📊 Priority: {ticket.priority.name if ticket.priority else 'Not set'} "
                    f"<br>👤 Assigned to: {ticket.agent.username if ticket.agent else 'Unassigned'} "
                    f"{prediction_text}"
                ),
                'redirect_url': f"/taskbird/tickets/{ticket.ticket_id}/",
                'session': {
                    'session_id': str(session.session_id),
                    'title': session.title,
                    'description': session.description,
                    'customer': session.customer.username,
                    'category': session.category.name if session.category else 'None',
                    'priority': session.priority.name if session.priority else 'None',
                    'channel': session.get_channel_display(),
                    'status': session.get_session_status_display(),
                    'reviewed_by': session.reviewed_by.username if session.reviewed_by else 'None',
                    'rejection_reason': session.rejection_reason if session.rejection_reason else 'None',
                    'created_at': session.created_at.strftime('%b %d, %Y %I:%M %p'),
                    'reviewed_at': session.reviewed_at.strftime('%b %d, %Y %I:%M %p') if session.reviewed_at else 'Not reviewed',
                    'created_ticket': session.created_ticket.id if session.created_ticket else 'None',
                    'attachments': attachments,
                }
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f"Error accepting session: {str(e)}"}, status=500)
    
    return render(request, 'taskbird/confirm_accept_session.html', {'session': session})

@login_required
def reject_session(request, session_id):
    """
    Agent rejects the session with a reason. No ticket is created.
    """
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': "You don't have permission to perform this action."}, status=403)
    
    session = get_object_or_404(TicketSession, session_id=session_id)
    
    if session.session_status != 'PENDING':
        return JsonResponse({'success': False, 'error': f"This session has already been {session.session_status.lower()}."}, status=400)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rejection_reason = data.get('rejection_reason', '').strip()
            
            if not rejection_reason:
                return JsonResponse({'success': False, 'error': 'Please provide a reason for rejection.'}, status=400)
            
            # Reject session
            session.reject_session(agent=request.user, reason=rejection_reason)
            
            # Send rejection notification
            try:
                send_rejection_email_to_customer(session)
            except Exception as e:
                return JsonResponse({'success': False, 'error': f"Error sending rejection email: {str(e)}"}, status=500)
            
            # Prepare updated session data
            attachments = [
                {
                    'id': attachment.id,
                    'file_url': attachment.file.url,
                    'uploaded_by': attachment.uploaded_by.username,
                    'uploaded_at': attachment.uploaded_at.strftime('%b %d, %Y %I:%M %p')
                } for attachment in session.attachments.all()
            ]
            data = {
                'success': True,
                'message': f"❌ Session {session.session_id} rejected. Customer notified.",
                'redirect_url': '/taskbird/agent-review-queue/',
                'session': {
                    'session_id': str(session.session_id),
                    'title': session.title,
                    'description': session.description,
                    'customer': session.customer.username,
                    'category': session.category.name if session.category else 'None',
                    'priority': session.priority.name if session.priority else 'None',
                    'channel': session.get_channel_display(),
                    'status': session.get_session_status_display(),
                    'reviewed_by': session.reviewed_by.username if session.reviewed_by else 'None',
                    'rejection_reason': session.rejection_reason if session.rejection_reason else 'None',
                    'created_at': session.created_at.strftime('%b %d, %Y %I:%M %p'),
                    'reviewed_at': session.reviewed_at.strftime('%b %d, %Y %I:%M %p') if session.reviewed_at else 'Not reviewed',
                    'created_ticket': session.created_ticket.id if session.created_ticket else 'None',
                    'attachments': attachments,
                }
            }
            return JsonResponse(data)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f"Error rejecting session: {str(e)}"}, status=500)
    
    return render(request, 'taskbird/reject_session_form.html', {'session': session})
    
    



"""
new views codle
"""
# taskbird/views.py
"""
Complete Ticket Session Workflow:
1. Customer submits form → Creates TicketSession (PENDING)
2. Agent reviews session → Accept or Reject
3. If accepted → Create Ticket with algorithms applied
4. If rejected → Notify customer with reason
"""


# ============================================================================
# STEP 1: CUSTOMER SUBMITS TICKET REQUEST (Creates TicketSession)
# ============================================================================

@login_required
def submit_ticket_request(request):
    """
    Customer submits a ticket request form.
    Creates a TicketSession in PENDING status.
    Does NOT create actual Ticket yet.
    """
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        # category_id = request.POST.get('category')
        channel = request.POST.get('channel', 'FORM')
        
        # Validate required fields
        if not title or not description:
            messages.error(request, "Title and description are required!")
            return redirect('submit_ticket_request')
        
        logger.info(f"{title=}, {description=}, {channel=}")
        
        # Create TicketSession (NOT Ticket yet!)
        session = TicketSession.objects.create(
            title=title,
            description=description,
            customer=request.user,
            # category_id=category_id if category_id else None,
            channel=channel,
            session_status='PENDING'  # Waiting for agent review
        )
        
        # Handle file attachments
        files = request.FILES.getlist('attachments')
        for file in files:
            TicketSessionAttachment.objects.create(
                session=session,
                file=file,
                uploaded_by=request.user
            )
        
        # Calculate preliminary priority score (for agent reference)  # use of algorithm2
        priority_score = PriorityScoring.calculate_score(title, description)

        logger.info(f"Priority score: {priority_score}")
        
        # Suggest priority based on score
        if priority_score >= 60:
            suggested_priority = Priority.objects.filter(level=4).first()  # Critical
        elif priority_score >= 40:
            suggested_priority = Priority.objects.filter(level=3).first()  # High
        elif priority_score >= 20:
            suggested_priority = Priority.objects.filter(level=2).first()  # Medium
        else:
            suggested_priority = Priority.objects.filter(level=1).first()  # Low
        
        if suggested_priority:
            session.priority = suggested_priority
            session.save()
        
        messages.success(
            request,
            f"Your ticket request has been submitted successfully! "
            f"Session ID: {session.session_id}. "
            f"An agent will review your request shortly."
        )
        
        # Optional: Send email notification to agents
        # notify_agents_new_session(session)
        
        # return redirect('customer_session_detail', session_id=session.session_id)
        return redirect('customer-dashboard')
    
    # GET request - show form
    categories = Category.objects.all()
    context = {
        'categories': categories,
        'channel_choices': TicketSession.CHANNEL_CHOICES
    }
    return render(request, 'taskbird/submit_ticket_request.html', context)


# ============================================================================
# CUSTOMER: VIEW THEIR SESSION STATUS
# ============================================================================

@login_required
def customer_session_detail(request, session_id):
    """
    Customer views their ticket session status.
    Shows if it's pending, accepted, or rejected.
    """
    session = get_object_or_404(
        TicketSession, 
        session_id=session_id, 
        customer=request.user  # Only customer can see their session
    )
    
    context = {
        'session': session,
        'attachments': session.attachments.all()
    }
    
    # If accepted, show the created ticket
    if session.session_status == 'ACCEPTED' and session.created_ticket:
        context['ticket'] = session.created_ticket
    
    return render(request, 'taskbird/customer_session_detail.html', context)


# ============================================================================
# CUSTOMER: VIEW ALL THEIR SESSIONS
# ============================================================================

@login_required
def customer_sessions_list(request):
    """Customer views all their ticket sessions"""
    sessions = TicketSession.objects.filter(
        customer=request.user
    ).order_by('-created_at')
    
    context = {
        'sessions': sessions,
        'pending_count': sessions.filter(session_status='PENDING').count(),
        'accepted_count': sessions.filter(session_status='ACCEPTED').count(),
        'rejected_count': sessions.filter(session_status='REJECTED').count(),
    }
    return render(request, 'taskbird/customer_sessions_list.html', context)


# ============================================================================
# STEP 2: AGENT VIEWS PENDING SESSIONS (Review Queue)
# ============================================================================

@login_required
def agent_review_queue(request):
    """
    Agent dashboard showing all pending ticket sessions.
    Only staff/agents can access this.
    """
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get all pending sessions
    pending_sessions = TicketSession.objects.filter(
        session_status='PENDING'
    ).order_by('-created_at')
    
    # Get statistics
    total_pending = pending_sessions.count()
    today_pending = pending_sessions.filter(
        created_at__date=timezone.now().date()
    ).count()
    
    context = {
        'pending_sessions': pending_sessions,
        'total_pending': total_pending,
        'today_pending': today_pending,
    }
    return render(request, 'taskbird/agent_review_queue.html', context)


# ============================================================================
# AGENT: VIEW SINGLE SESSION DETAIL (For Review)
# ============================================================================

@login_required
def agent_session_review(request, session_id):
    """
    Agent views a single pending session in detail.
    Can accept or reject from this page.
    """
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    session = get_object_or_404(TicketSession, session_id=session_id)
    
    # Calculate priority score for agent reference
    priority_score = PriorityScoring.calculate_score(
        session.title, 
        session.description
    )
    
    context = {
        'session': session,
        'attachments': session.attachments.all(),
        'priority_score': priority_score,
        'suggested_priority': session.priority,
    }
    return render(request, 'taskbird/agent_session_review.html', context)


# ============================================================================
# STEP 3A: AGENT ACCEPTS SESSION (Creates Ticket with Algorithms)
# ============================================================================

@login_required
def accept_ticket_session(request, session_id):
    """
    Agent accepts the session and creates actual Ticket.
    All 3 algorithms are applied automatically:
    1. Priority Scoring
    2. Auto-assignment
    3. Response Time Prediction
    """
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    session = get_object_or_404(TicketSession, session_id=session_id)
    
    # Check if already processed
    if session.session_status != 'PENDING':
        messages.warning(
            request, 
            f"This session has already been {session.session_status.lower()}."
        )
        return redirect('agent_review_queue')
    
    if request.method == 'POST':
        try:
            # Use the model's method to accept and create ticket
            # This method is already updated in your models.py to call algorithms
            ticket = session.accept_and_create_ticket(agent=request.user)
            
            # Get algorithm results for display
            from .algorithms import ResponseTimePredictor
            prediction = ResponseTimePredictor.predict_resolution_time(ticket)
            
            # Send notification email to customer
            send_acceptance_email_to_customer(session, ticket)
            
            messages.success(
                request,
                f"✅ Session accepted and converted to Ticket {ticket.ticket_id}! "
                f"<br>📊 Priority: {ticket.priority.name if ticket.priority else 'Not set'} "
                f"<br>👤 Assigned to: {ticket.agent.username if ticket.agent else 'Unassigned'} "
                f"<br>⏱️ Estimated resolution: {prediction['formatted_time']}"
            )
            
            return redirect('ticket_detail', ticket_id=ticket.ticket_id)
            
        except Exception as e:
            messages.error(
                request, 
                f"Error accepting session: {str(e)}"
            )
            return redirect('agent_session_review', session_id=session_id)
    
    # GET request - show confirmation page
    return render(request, 'taskbird/confirm_accept_session.html', {'session': session})


# ============================================================================
# STEP 3B: AGENT REJECTS SESSION (Does NOT create Ticket)
# ============================================================================

@login_required
def reject_ticket_session(request, session_id):
    """
    Agent rejects the session with a reason.
    NO Ticket is created.
    Customer is notified of rejection.
    """
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to perform this action.")
        return redirect('dashboard')
    
    session = get_object_or_404(TicketSession, session_id=session_id)
    
    # Check if already processed
    if session.session_status != 'PENDING':
        messages.warning(
            request, 
            f"This session has already been {session.session_status.lower()}."
        )
        return redirect('agent_review_queue')
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            messages.error(request, "Please provide a reason for rejection.")
            return redirect('reject_ticket_session', session_id=session_id)
        
        try:
            # Use model's method to reject session
            session.reject_session(agent=request.user, reason=rejection_reason)
            
            # Send rejection notification to customer
            send_rejection_email_to_customer(session)
            
            messages.success(
                request,
                f"❌ Session {session.session_id} has been rejected. "
                f"Customer has been notified."
            )
            
            return redirect('agent_review_queue')
            
        except Exception as e:
            messages.error(
                request, 
                f"Error rejecting session: {str(e)}"
            )
            return redirect('agent_session_review', session_id=session_id)
    
    # GET request - show rejection form
    return render(request, 'taskbird/reject_session_form.html', {'session': session})


# ============================================================================
# VIEW TICKET DETAIL (After Creation)
# ============================================================================

@login_required
def ticket_detail(request, ticket_id):
    """
    View details of a created ticket.
    Shows algorithm results and predictions.
    """
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
    
    # Check permissions
    is_agent = request.user.is_staff
    is_customer = ticket.customer == request.user
    
    if not (is_agent or is_customer):
        messages.error(request, "You don't have permission to view this ticket.")
        return redirect('dashboard')
    
    # Get prediction info
    from .algorithms import ResponseTimePredictor
    prediction = ResponseTimePredictor.predict_resolution_time(ticket)
    
    context = {
        'ticket': ticket,
        'comments': ticket.comments.all(),
        'attachments': ticket.attachments.all(),
        'prediction': prediction,
        'is_agent': is_agent,
        'is_customer': is_customer,
    }
    
    # Show source session if exists
    if hasattr(ticket, 'source_session'):
        context['source_session'] = ticket.source_session
    
    return render(request, 'taskbird/ticket_detail.html', context)


# ============================================================================
# HELPER FUNCTIONS: EMAIL NOTIFICATIONS
# ============================================================================

def send_acceptance_email_to_customer(session, ticket):
    """Send email to customer when session is accepted"""
    subject = f"Your Ticket Request Has Been Accepted - {ticket.ticket_id}"
    message = f"""
    Dear {session.customer.get_full_name() or session.customer.username},
    
    Good news! Your ticket request has been accepted and a ticket has been created.
    
    Ticket Details:
    - Ticket ID: {ticket.ticket_id}
    - Title: {ticket.title}
    - Priority: {ticket.priority.name if ticket.priority else 'Not set'}
    - Assigned Agent: {ticket.agent.get_full_name() if ticket.agent else 'To be assigned'}
    - Status: {ticket.status.name if ticket.status else 'Open'}
    
    You can track your ticket status in your dashboard.
    
    Thank you for contacting our support team!
    
    Best regards,
    Support Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [session.customer.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending acceptance email: {e}")


def send_rejection_email_to_customer(session):
    """Send email to customer when session is rejected"""
    subject = f"Your Ticket Request - Session {session.session_id}"
    message = f"""
    Dear {session.customer.get_full_name() or session.customer.username},
    
    Thank you for submitting your ticket request. After review, we are unable to process 
    your request for the following reason:
    
    Reason for Rejection:
    {session.rejection_reason}
    
    If you believe this is an error or would like to submit a new request with additional 
    information, please feel free to create a new ticket request.
    
    We apologize for any inconvenience.
    
    Best regards,
    Support Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [session.customer.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error sending rejection email: {e}")


# Import timezone at the top if not already imported
from django.utils import timezone
