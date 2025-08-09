from django.urls import path
from accounts.api import  views


urlpatterns = [
    path('customer/signup/', views.CustomerSignupView.as_view(), name='customer-signup'),
    
]
