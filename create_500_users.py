import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# This script is meant to be run inside the Django shell
from django.contrib.auth.hashers import make_password
from users.models import User

def create_users():
    password = '123456'
    hashed_password = make_password(password)
    
    users_to_create = []
    
    # Get current max to avoid duplicate usernames if run multiple times
    # Or we can just use ignore_conflicts=True
    
    for i in range(1, 501):
        username = f'khachhang_{i:03d}'
        email = f'{username}@demo.local'
        user = User(
            username=username,
            email=email,
            password=hashed_password,
            first_name='Khách',
            last_name=f'Hàng {i}',
            role=User.Role.CUSTOMER,
            is_active=True,
            phone=f'0900{i:06d}',
            address=f'Địa chỉ {i}, Việt Nam'
        )
        users_to_create.append(user)

    # Bulk create users
    User.objects.bulk_create(users_to_create, ignore_conflicts=True)
    
    count = User.objects.filter(role=User.Role.CUSTOMER).count()
    print(f"Thêm thành công! Hiện tại có tổng cộng {count} khách hàng trong database.")

if __name__ == '__main__':
    create_users()
