from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Cart, CartItem
from .serializers import (
    CartSerializer, 
    AddToCartSerializer, 
    UpdateCartSerializer, 
    RemoveFromCartSerializer
)

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get_cart(self, user_id):
        cart, created = Cart.objects.get_or_create(user_id=user_id)
        return cart

    def get(self, request):
        """Lấy thông tin giỏ hàng của user hiện tại"""
        # JWTAuthentication decodes the token and sets request.user.id
        # In a microservice, request.user might just be a mock or dict if we customize auth
        # But SimpleJWT natively populates request.user.id from token payload if standard
        user_id = request.user.id
        cart = self.get_cart(user_id)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Thêm sản phẩm vào giỏ hàng"""
        serializer = AddToCartSerializer(data=request.data)
        if serializer.is_valid():
            user_id = request.user.id
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']

            cart, _ = Cart.objects.get_or_create(user_id=user_id)
            
            # Check if item already in cart
            try:
                cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
                cart_item.quantity += quantity
                cart_item.save()
            except CartItem.DoesNotExist:
                cart_item = CartItem.objects.create(
                    cart=cart, 
                    product_id=product_id, 
                    quantity=quantity
                )

            cart_serializer = CartSerializer(cart)
            return Response(cart_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateCartView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        """Cập nhật số lượng sản phẩm trong giỏ hàng"""
        serializer = UpdateCartSerializer(data=request.data)
        if serializer.is_valid():
            user_id = request.user.id
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data['quantity']

            try:
                cart = Cart.objects.get(user_id=user_id)
                cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
                cart_item.quantity = quantity
                cart_item.save()
                
                cart_serializer = CartSerializer(cart)
                return Response(cart_serializer.data, status=status.HTTP_200_OK)
            except (Cart.DoesNotExist, CartItem.DoesNotExist):
                return Response(
                    {"error": "Product not found in cart"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RemoveFromCartView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        """Xóa sản phẩm khỏi giỏ hàng"""
        serializer = RemoveFromCartSerializer(data=request.data)
        if serializer.is_valid():
            user_id = request.user.id
            product_id = serializer.validated_data['product_id']

            try:
                cart = Cart.objects.get(user_id=user_id)
                cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
                cart_item.delete()
                
                cart_serializer = CartSerializer(cart)
                return Response(cart_serializer.data, status=status.HTTP_200_OK)
            except (Cart.DoesNotExist, CartItem.DoesNotExist):
                return Response(
                    {"error": "Product not found in cart"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
