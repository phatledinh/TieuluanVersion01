from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Payment
from .serializers import PaymentSerializer
from .services import initiate_shipping

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay(request):
    order_id = request.data.get('order_id')
    amount = request.data.get('amount')

    if not order_id or not amount:
        return Response({'error': 'order_id and amount are required'}, status=status.HTTP_400_BAD_REQUEST)

    # 1. Create Payment record (Mock logic - assume it always succeeds)
    payment = Payment.objects.create(
        order_id=order_id,
        amount=amount,
        status='Success' # Mocking successful payment
    )
    
    # 2. (Removed) Shipping will be orchestrated by the frontend

    serializer = PaymentSerializer(payment)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status(request):
    order_id = request.query_params.get('order_id')
    if not order_id:
        return Response({'error': 'order_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment = Payment.objects.get(order_id=order_id)
        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found for this order'}, status=status.HTTP_404_NOT_FOUND)
