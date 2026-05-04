"""
Management command to seed initial users for development/testing.

Usage:
    python manage.py seed_users
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

SEED_USERS = [
    {
        'username': 'admin',
        'email': 'admin@ecom.local',
        'password': 'admin123',
        'role': 'admin',
        'first_name': 'System',
        'last_name': 'Admin',
        'is_staff': True,
        'is_superuser': True,
    },
    {
        'username': 'staff01',
        'email': 'staff01@ecom.local',
        'password': 'staff123',
        'role': 'staff',
        'first_name': 'Nguyen',
        'last_name': 'Staff',
        'is_staff': True,
    },
    {
        'username': 'customer01',
        'email': 'customer01@ecom.local',
        'password': 'customer123',
        'role': 'customer',
        'first_name': 'Tran',
        'last_name': 'Customer',
        'phone': '0901234567',
        'address': '123 Nguyen Hue, Q1, TP.HCM',
    },
    {
        'username': 'customer02',
        'email': 'customer02@ecom.local',
        'password': 'customer123',
        'role': 'customer',
        'first_name': 'Le',
        'last_name': 'Buyer',
        'phone': '0912345678',
        'address': '456 Le Loi, Q3, TP.HCM',
    },
]


class Command(BaseCommand):
    help = 'Seed initial users (admin, staff, customers) for development'

    def handle(self, *args, **options):
        created_count = 0

        for user_data in SEED_USERS:
            username = user_data['username']

            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'  Skip: {username} (already exists)')
                )
                continue

            password = user_data.pop('password')
            is_superuser = user_data.pop('is_superuser', False)
            is_staff = user_data.pop('is_staff', False)

            user = User.objects.create_user(
                password=password,
                is_superuser=is_superuser,
                is_staff=is_staff,
                **user_data,
            )
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'  Created: {user.username} (role={user.role})'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f'\nDone! Created {created_count} user(s).')
        )
