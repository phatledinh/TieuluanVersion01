"""
User Model - Chapter 2.4.2

Custom User model extending AbstractUser with role-based classification:
    - Admin:    Full system access (CRUD all resources)
    - Staff:    Process orders, manage shipping & operations
    - Customer: Browse products, purchase items

Database: MySQL (Chapter 2.10.4)
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model with RBAC role field.
    Extends Django's AbstractUser for authentication compatibility.
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        STAFF = 'staff', 'Staff'
        CUSTOMER = 'customer', 'Customer'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
        help_text='User role for RBAC permissions',
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
        default='',
        help_text='Phone number',
    )

    address = models.TextField(
        blank=True,
        default='',
        help_text='Shipping address',
    )

    class Meta:
        db_table = 'user'
        ordering = ['-date_joined']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    # ---- Convenience role checks ----

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_staff_role(self):
        return self.role == self.Role.STAFF

    @property
    def is_customer_role(self):
        return self.role == self.Role.CUSTOMER
