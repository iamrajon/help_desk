from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.decorators import agent_required
from taskbird.models import Ticket, TicketAttachment, Status
from taskbird.forms import TicketForm
from config.logger import get_logger


logger = get_logger(__name__)


@login_required(redirect_field_name='next', login_url='login')
@agent_required 
def agent_dashboard(request):
    """Agent dashboard - ticket resolution"""
    if not request.user.is_agent:
        messages.error(request, 'Access denied. Agent access required.')
        return redirect('login')
    
    return render(request, 'taskbird/agent.html', {'user': request.user})


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
            return redirect('customer-dashboard')  # Adjust to your ticket list view
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = TicketForm()
        context['form'] = form
    
    return render(request, 'taskbird/create_ticket.html', context)
