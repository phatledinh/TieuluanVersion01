from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Shipment
from .serializers import ShipmentSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_shipment(request):
    order_id = request.data.get('order_id')
    address = request.data.get('address')

    if not order_id or not address:
        return Response({'error': 'order_id and address are required'}, status=status.HTTP_400_BAD_REQUEST)

    shipment = Shipment.objects.create(
        order_id=order_id,
        address=address,
        status='Processing'
    )
    
    serializer = ShipmentSerializer(shipment)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def shipment_status(request):
    order_id = request.query_params.get('order_id')
    if not order_id:
        return Response({'error': 'order_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        shipment = Shipment.objects.get(order_id=order_id)
        serializer = ShipmentSerializer(shipment)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Shipment.DoesNotExist:
        return Response({'error': 'Shipment not found for this order'}, status=status.HTTP_404_NOT_FOUND)
