from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
from django.utils.crypto import get_random_string

def send_verification_email(user):
    """Send email verification link to agent with token expiry"""
    # Generate token and set expiry (e.g., 24 hours)
    token = get_random_string(64)
    user.verification_token = token
    user.verification_token_expiry = timezone.now() + timedelta(hours=24)
    user.save()

    # Build absolute verification URL
    verification_url = f"{settings.SITE_URL.rstrip('/')}/verify-email/{token}/"

    # Email subject
    subject = 'Verify Your Help Desk Agent Account'

    # Render HTML email template (create this template later)
    context = {
        'user': user,
        'verification_url': verification_url,
        'site_name': settings.SITE_NAME,  # Add SITE_NAME to settings
    }
    html_content = render_to_string('email/verification_email.html', context)
    text_content = strip_tags(html_content)  # Fallback plain text version

    # Send email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach_alternative(html_content, "text/html")
    
    try:
        email.send(fail_silently=False)
    except Exception as e:
        # Log the error (use your preferred logging method)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        raise 

# get user dashboard based on user_type
def get_user_dashboard_url(user):
    """Get appropriate dashboard URL based on user type"""
    if user.is_customer:
        return 'customer-dashboard'
    elif user.is_agent:
        return 'agent-dashboard'
    elif user.is_superuser_type:
        return 'admin_dashboard'
    return 'login'