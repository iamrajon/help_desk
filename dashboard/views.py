from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import customer_required
from config.logger import get_logger


logger = get_logger(__name__)

# customer dashboard
@login_required(redirect_field_name='next', login_url='login-view')
@customer_required
def customer_dashboard(request):
    """Customer dashboard - ticket management"""
    if not request.user.is_customer:
        messages.error(request, 'Access denied. Customer access required.')
        return redirect('login-view')
    context = {}
    context['user'] = request.user

    return render(request, 'dashboard/customer.html', context)
