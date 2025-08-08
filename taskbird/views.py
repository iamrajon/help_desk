from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from accounts.decorators import agent_required
from taskbird.models import Ticket, TicketAttachment, Status
from taskbird.forms import TicketForm, TicketAgentForm, TicketFilterForm
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
    
    



