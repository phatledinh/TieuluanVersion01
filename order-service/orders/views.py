from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import Order, OrderItem
from .serializers import OrderSerializer
from .services import get_cart_items, clear_cart, initiate_payment
import requests
import os
import logging

logger = logging.getLogger(__name__)

PRODUCT_SERVICE_URL = os.environ.get('PRODUCT_SERVICE_URL', 'http://product-service:8001')

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user_id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        user_id = request.user.id
        # Extract JWT token from header to pass to other services
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        else:
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

        # 1. Fetch cart items
        cart_data = get_cart_items(user_id, token)
        if not cart_data or not cart_data.get('items'):
            return Response({'error': 'Cart is empty or could not be fetched'}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = cart_data.get('items')
        
        # 2. Calculate total price and prepare order items
        total_price = 0.0
        order_items_data = []

        for item in cart_items:
            product_id = item.get('product_id')
            quantity = item.get('quantity')
            
            # Fetch product price from Product Service
            try:
                prod_res = requests.get(f'{PRODUCT_SERVICE_URL}/api/products/{product_id}/', timeout=5)
                if prod_res.status_code == 200:
                    product_data = prod_res.json()
                    price = product_data.get('price', 0.0)
                    total_price += price * quantity
                    order_items_data.append({
                        'product_id': product_id,
                        'quantity': quantity
                    })
                else:
                    return Response({'error': f'Product {product_id} not found'}, status=status.HTTP_400_BAD_REQUEST)
            except requests.exceptions.RequestException:
                return Response({'error': 'Error connecting to Product Service'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 3. Create Order
        order = Order.objects.create(
            user_id=user_id,
            total_price=total_price,
            status='Pending'
        )

        # 4. Create Order Items
        for item_data in order_items_data:
            OrderItem.objects.create(
                order=order,
                product_id=item_data['product_id'],
                quantity=item_data['quantity']
            )

        # 5. Clear Cart
        clear_cart(token, cart_items)

        # 6. (Removed) Payment will be orchestrated by the frontend
        
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
