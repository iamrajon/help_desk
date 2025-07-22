
from django.urls import path
from accounts import views

urlpatterns = [

    # Authentication URLs
    path('login/', views.login_view, name='login-view'),
    path('logout/', views.logout_view, name='logout-view'),
    path('signup/', views.signup, name='signup-view'),
    path('signup/customer/', views.customer_signup, name='customer-signup-view'),
    path('signup/agent/', views.agent_signup, name='agent-signup-view'),
    
    # Dashboard URLs
    # path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
]