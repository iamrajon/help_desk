from django.urls import path
from dashboard import views


urlpatterns = [
    path('customer/dashboard/', views.customer_dashboard, name="customer-dashboard"),
]
