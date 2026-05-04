from django.urls import path
from .views import CartView, AddToCartView, UpdateCartView, RemoveFromCartView

urlpatterns = [
    path('', CartView.as_view(), name='cart-detail'),
    path('add/', AddToCartView.as_view(), name='cart-add'),
    path('update/', UpdateCartView.as_view(), name='cart-update'),
    path('remove/', RemoveFromCartView.as_view(), name='cart-remove'),
]
