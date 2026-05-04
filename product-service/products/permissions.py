"""
RBAC Permissions for Product Service — Chapter 2.4.3

Product Service access:
    - Admin:    Full CRUD on products and categories
    - Staff:    Can update stock/inventory
    - Customer: Read-only (browse/search products)
    - Public:   Read-only (product listing)
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminUser(BasePermission):
    """Only admin users can perform this action."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Check role claim from JWT token
        return getattr(request.user, 'role', None) == 'admin' or request.user.is_superuser


class IsAdminOrReadOnly(BasePermission):
    """
    Admin can CRUD, everyone else (including anonymous) can only read.
    Used for product listing/detail endpoints.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'role', None) == 'admin' or request.user.is_superuser


class IsStaffOrAdmin(BasePermission):
    """Staff or Admin can perform this action (e.g. update stock)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(request.user, 'role', None)
        return role in ('admin', 'staff') or request.user.is_superuser
