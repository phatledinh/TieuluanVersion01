import os
import requests
import logging

logger = logging.getLogger(__name__)

SHIPPING_SERVICE_URL = os.environ.get('SHIPPING_SERVICE_URL', 'http://shipping-service:8006')

def initiate_shipping(order_id, token):
    headers = {'Authorization': f'Bearer {token}'}
    payload = {
        'order_id': order_id,
        'address': 'To be provided' # This should ideally be fetched from User Service or passed along
    }
    try:
        response = requests.post(f'{SHIPPING_SERVICE_URL}/shipping/create', json=payload, headers=headers, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error initiating shipping: {e}")
        return None
