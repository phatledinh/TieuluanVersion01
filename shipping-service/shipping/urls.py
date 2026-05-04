from django.urls import path
from .views import create_shipment, shipment_status

urlpatterns = [
    path('create', create_shipment, name='create_shipment'),
    path('status', shipment_status, name='shipment_status'),
]
