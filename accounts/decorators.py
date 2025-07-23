# decorators.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps



# custom decorator for step1: email verification 
def emailverification_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('email_verification_done'):
            return redirect('signup-view')
        return view_func(request, *args, **kwargs)
    return wrapper


def customer_required(view_func):
    """Decorator for customer-only views"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_customer:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access denied. Customer access required.')
        return redirect('login-view')
    return _wrapped_view


def agent_required(view_func):
    """Decorator for agent-only views"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_agent:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access denied. Agent access required.')
        return redirect('login-view')
    return _wrapped_view


def superuser_required(view_func):
    """Decorator for superuser-only views"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser_type:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access denied. Superuser access required.')
        return redirect('login-view')
    return _wrapped_view


def staff_required(view_func):
    """Decorator for agent and superuser views"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_agent or request.user.is_superuser_type:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access denied. Staff access required.')
        return redirect('customer-dashboard')
    return _wrapped_view


def verified_agent_required(view_func):
    """Decorator for verified agents only"""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if (user.is_agent or user.is_superuser_type) and user.is_verified:
            return view_func(request, *args, **kwargs)
        
        if not user.is_verified:
            messages.error(request, 'Please verify your email first.')
        else:
            messages.error(request, 'Access denied.')
        return redirect('login-view')
    return _wrapped_view