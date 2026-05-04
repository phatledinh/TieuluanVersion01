import os
import requests
import logging

logger = logging.getLogger(__name__)

CART_SERVICE_URL = os.environ.get('CART_SERVICE_URL', 'http://cart-service:8003')
PAYMENT_SERVICE_URL = os.environ.get('PAYMENT_SERVICE_URL', 'http://payment-service:8005')

def get_cart_items(user_id, token):
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(f'{CART_SERVICE_URL}/cart/', headers=headers, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching cart items: {e}")
        return None

def clear_cart(token):
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.delete(f'{CART_SERVICE_URL}/cart/remove', headers=headers, timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error clearing cart: {e}")
        return False

def initiate_payment(order_id, amount, token):
    headers = {'Authorization': f'Bearer {token}'}
    payload = {
        'order_id': order_id,
        'amount': amount
    }
    try:
        response = requests.post(f'{PAYMENT_SERVICE_URL}/payment/pay', json=payload, headers=headers, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error initiating payment: {e}")
        return None
