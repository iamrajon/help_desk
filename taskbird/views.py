from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.decorators import agent_required




@login_required(redirect_field_name='next', login_url='login')
@agent_required 
def agent_dashboard(request):
    """Agent dashboard - ticket resolution"""
    if not request.user.is_agent:
        messages.error(request, 'Access denied. Agent access required.')
        return redirect('login')
    
    return render(request, 'taskbird/agent.html', {'user': request.user})
