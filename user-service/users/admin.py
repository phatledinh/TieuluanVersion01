"""
Admin configuration for User Service.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model with role field."""

    list_display = [
        'username', 'email', 'role', 'first_name', 'last_name',
        'is_active', 'date_joined',
    ]
    list_filter = ['role', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']

    # Add role field to the admin form
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Role & Profile', {
            'fields': ('role', 'phone', 'address'),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Role & Profile', {
            'fields': ('role', 'email', 'phone', 'address'),
        }),
    )
