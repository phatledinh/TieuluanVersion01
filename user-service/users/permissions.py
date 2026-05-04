"""
RBAC Permissions - Chapter 2.4.3

Role-based access control:
    Admin:    CRUD toàn bộ
    Staff:    Xử lý order, shipping
    Customer: Mua hàng, xem sản phẩm
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    """Allow access only to Admin users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )


class IsStaff(BasePermission):
    """Allow access only to Staff users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ('admin', 'staff')
        )


class IsCustomer(BasePermission):
    """Allow access only to Customer users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'customer'
        )


class IsAdminOrReadOnly(BasePermission):
    """
    Admin can do anything.
    Other authenticated users can only read (GET, HEAD, OPTIONS).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role == 'admin'


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission:
    - Admin can access any user
    - Other users can only access their own profile
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        return obj.pk == request.user.pk
