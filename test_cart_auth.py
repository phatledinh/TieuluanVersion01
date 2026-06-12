import urllib.request
import json
import base64

# 1. Login to get token
login_data = json.dumps({
    "username": "khachhang_001",
    "password": "123456"
}).encode('utf-8')

req = urllib.request.Request("http://localhost/users/login/", data=login_data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode())
        token = res['access']
        print("Got token:", token[:20] + "...")
        # Decode payload
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        print("Payload:", base64.b64decode(payload).decode())
except Exception as e:
    print("Login failed:", e)
    if hasattr(e, 'read'):
        print(e.read().decode())
    exit(1)

# 2. Test cart API
req = urllib.request.Request("http://localhost/carts/", headers={'Authorization': f'Bearer {token}'})
try:
    with urllib.request.urlopen(req) as response:
        print("Cart API success:", response.read().decode())
except Exception as e:
    print("Cart API failed:", getattr(e, 'code', e))
    if hasattr(e, 'read'):
        print(e.read().decode())
