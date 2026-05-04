from django.urls import path
from .views import pay, payment_status

urlpatterns = [
    path('pay', pay, name='pay'),
    path('status', payment_status, name='payment_status'),
]
