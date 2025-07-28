from django.utils import timezone
from django.shortcuts import render
from config.logger import get_logger
from accounts.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.crypto import get_random_string
from django.contrib.auth.decorators import login_required
from accounts.models import User
from accounts.forms import CustomerSignupForm, AgentSignupForm, LoginForm
from accounts.decorators import emailverification_required
from accounts.utils import send_verification_email, get_user_dashboard_url


logger = get_logger(__name__) # name is accounts.views


"""
core  logic start from here
"""

def login_view(request):
    """Unified login for all user types"""
    context = {}

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=email, password=password)
            print(f"user: {user}")
            if user:
                # Check if agent needs email verification
                if (user.is_agent or user.is_superuser_type) and not (user.is_verified and user.is_active):
                    context['form'] = form
                    messages.error(request, 'Your Email is not verified!. Check your mail inbox for verification link.')
                    return render(request, 'accounts/login.html', context)
                
                # Check if account is active (for email verification and admin approval)
                # if not user.is_active:
                #     messages.error(request, 'Your account is pending admin approval.')
                #     return render(request, 'accounts/login.html', {'form': form})
                
                login(request, user)
                # messages.success(request, f'Welcome back, {user.name}!')
                return redirect(get_user_dashboard_url(user))
            else:
                context['form'] = form
                messages.error(request, 'Invalid email or password.')
                return render(request, 'accounts/login.html', context)
        else:
            context['form'] = form
            return render(request, 'accounts/login.html', context)
    else:
        form = LoginForm()
        context['form'] = form
    
    return render(request, 'accounts/login.html', context)

# signup view
def is_valid_email(email):
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False

def signup(request):
    context = {}
    if request.method == "POST":
        data = request.POST
        email = data.get('email').strip()
        is_agent = data.get('is_agent') == "on"
        email_error = ""

        if not email:
            email_error = "Email is Required."
        elif not is_valid_email(email):
            email_error = "Invalid Email Format"

        if email_error:
            messages.error(request, f"error: {email_error}")
            return redirect('signup-view')
        else:
            # store data in session
            request.session['email'] = email
            request.session['is_agent'] = is_agent
            request.session['email_verification_done'] = True
            return redirect('agent-signup-view' if is_agent else 'customer-signup-view')
    else:    
        request.session['is_agent'] = False
        is_agent = request.session.get('is_agent', False)
        context['is_agent'] = is_agent
        return render(request, "accounts/signup.html", context)

@emailverification_required
def customer_signup(request):
    """Customer registration - simple process"""
    context = {}
    email = request.session.get('email')
    if request.method == 'POST':
        print(f"request method: {request.method}")
        form = CustomerSignupForm(request.POST, email=email)
        if form.is_valid():
            print(f"form is valid: {form.is_valid()}")
            user = form.save(commit=False)
            user.user_type = User.UserType.CUSTOMER
            user.is_verified = True  # Customers don't need email verification
            user.save()
            
            login(request, user)
            messages.success(request, 'Welcome! Your account has been created successfully.')
            return redirect('customer-dashboard')
        else:
            context['form'] = form
            context['step'] = 2
            return render(request, 'accounts/customer_signup.html', context)
    else:
        # logger.info(f"request method: {request.method}")
        form = CustomerSignupForm(email=email)
        context['form'] = form
        context['step'] = 2
    return render(request, 'accounts/customer_signup.html', context)

@emailverification_required
def agent_signup(request):
    """Agent registration - requires email verification and admin approval"""
    context = {}
    if request.method == 'POST':
        form = AgentSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = User.UserType.AGENT
            user.is_active = False  
            user.is_verified = False 
            user.save()
            
            # Send verification email
            send_verification_email(user)
            
            messages.success(request, 
                'Registration submitted successfully! Please check your email for verification link and wait for admin approval.')
            return redirect('login-view')
        else:
            context['form'] = form
            context['step'] = 2
            return render(request, 'accounts/agent_signup.html', context)
    else:
        email = request.session.get('email')
        form = AgentSignupForm(email=email)
        # form = AgentSignupForm(initial={'email': email}, email=email)
        context['form'] = form
        context['step'] = 2
    
    return render(request, 'accounts/agent_signup.html', context)


@login_required(login_url="login-view")
def logout_view(request):
    """Logout user and redirect to login"""
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('login-view')


def verify_email(request, token):
    """Email verification for agents"""
    try:
        user = User.objects.get(verification_token=token)
        if user.user_type != User.UserType.AGENT:
            messages.error(request, 'Invalid verification link.')
            return redirect('login-view')
        
        # Check token expiry
        if user.verification_token_expiry and user.verification_token_expiry < timezone.now():
            messages.error(request, 'Verification link has expired.')
            user.verification_token = ''  # Clear expired token
            user.save()
            return redirect('login-view')
        
        user.is_verified = True
        user.is_active = True
        user.verification_token = ''
        user.save()
        
        if user.is_active and user.is_verified:
            messages.success(request, 'Email verified successfully! You can now login as agent.')
    except User.DoesNotExist:
        messages.error(request, 'Invalid or expired verification link.')
        return redirect("login-view")
    
    return redirect('login-view')


# @login_required
# def admin_dashboard(request):
#     """Admin dashboard - full system access"""
#     if not request.user.is_superuser_type:
#         messages.error(request, 'Access denied. Admin access required.')
#         return redirect('login')
    
#     return render(request, 'dashboard/admin.html', {'user': request.user})


# def verify_email(request, token):
#     """Email verification for agents"""
#     try:
#         user = User.objects.get(verification_token=token)
#         if user.is_agent or user.is_superuser_type:
#             user.is_verified = True
#             user.is_active = True
#             user.verification_token = ''
#             user.save()
            
#             if user.is_active and user.is_verified:
#                 messages.success(request, 'Email verified successfully! You can now login.')
#             else:
#                 messages.success(request, 'Email verified successfully! Please wait for admin approval.')
#         else:
#             messages.error(request, 'Invalid verification link.')
#     except User.DoesNotExist:
#         messages.error(request, 'Invalid or expired verification link.')
    
#     return redirect('login-view')


# def send_verification_email(user):
#     """Send email verification link to agent"""
#     token = get_random_string(64)
#     user.verification_token = token
#     user.save()
    
#     verification_url = f"{settings.SITE_URL}/verify-email/{token}/"
    
#     subject = 'Verify Your Help Desk Agent Account'
#     message = f"""
#     Hi {user.name},
    
#     Thank you for registering as an agent for our Help Desk System.
    
#     Please click the link below to verify your email address:
#     {verification_url}
    
#     After email verification, your account will be reviewed by an administrator.
#     You will be notified once your account is approved.
    
#     If you didn't create this account, please ignore this email.
    
#     Best regards,
#     Help Desk Team
#     """
    
#     send_mail(
#         subject=subject,
#         message=message,
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         recipient_list=[user.email],
#         fail_silently=False,
#     )


# Dashboard views (examples)






