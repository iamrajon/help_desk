from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.decorators import agent_required
from taskbird.models import Ticket, TicketAttachment, Status
from taskbird.forms import TicketForm
from config.logger import get_logger
from django.db.models import Q


logger = get_logger(__name__)


@login_required(redirect_field_name='next', login_url='login')
@agent_required 
def agent_dashboard(request):
    """Agent dashboard - ticket resolution"""
    if not request.user.is_agent:
        messages.error(request, 'Access denied. Agent access required.')
        return redirect('login-view')
    
    return render(request, 'taskbird/agent_dashboard.html', {'user': request.user})


# ticket creation view
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


@login_required(redirect_field_name='next', login_url='login-view')
@agent_required
def agent_ticket_list(request):
    if not request.user.is_authenticated and not request.user.is_agent:
        messages.error(request, 'Access denied. Agent Access required.')
        return redirect('login-view')
    
    filters = Q()
    context = {}

    tickets = Ticket.objects.filter(filters).order_by('-created_at')
    context['tickets'] = tickets
    return render(request, 'taskbird/agent_ticketlist.html', context)

