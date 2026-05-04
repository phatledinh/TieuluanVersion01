"""
Views for User Service - Chapter 2.4.4

API Endpoints:
    POST /api/auth/register/      - Register new user
    POST /api/auth/login/         - Login (JWT token pair)
    POST /api/auth/refresh/       - Refresh JWT token
    GET  /api/users/              - List all users (admin only)
    GET  /api/users/{id}/         - Get user detail
    PUT  /api/users/{id}/         - Update user
    DELETE /api/users/{id}/       - Delete user (admin only)
    GET  /api/users/me/           - Get current user profile
    PUT  /api/users/me/           - Update current user profile
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .permissions import IsAdmin, IsAdminOrReadOnly, IsOwnerOrAdmin
from .serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserProfileSerializer,
    UserSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Authentication Views
# ---------------------------------------------------------------------------

class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/

    Register a new user account.
    Default role: customer.
    Admin users can create staff/admin accounts.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        logger.info(
            'New user registered: %s (role=%s)', user.username, user.role
        )

        return Response(
            {
                'message': 'User registered successfully.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/

    Authenticate user and return JWT access + refresh tokens.
    Response includes user profile data and role.
    """

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


class RefreshTokenView(TokenRefreshView):
    """
    POST /api/auth/refresh/

    Refresh an expired access token using a valid refresh token.
    """

    permission_classes = [AllowAny]


# ---------------------------------------------------------------------------
# User Management Views
# ---------------------------------------------------------------------------

class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for User model.

    Permissions (RBAC - Chapter 2.4.3):
        - Admin:    Full CRUD on all users
        - Staff:    Read-only access to user list
        - Customer: Can only access own profile via /me/

    Endpoints:
        GET    /api/users/          - List users
        POST   /api/users/          - Create user (admin)
        GET    /api/users/{id}/     - Get user
        PUT    /api/users/{id}/     - Update user
        DELETE /api/users/{id}/     - Delete user (admin)
        GET    /api/users/me/       - Current user profile
        PUT    /api/users/me/       - Update own profile
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ('list', 'create'):
            return [IsAdmin()]
        if self.action == 'destroy':
            return [IsAdmin()]
        if self.action in ('retrieve', 'update', 'partial_update'):
            return [IsOwnerOrAdmin()]
        if self.action in ('me', 'update_me'):
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ('me', 'update_me'):
            return UserProfileSerializer
        return UserSerializer

    # ---------- Custom actions ----------

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """GET /api/users/me/ - Get current authenticated user profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @me.mapping.put
    def update_me(self, request):
        """PUT /api/users/me/ - Update current authenticated user profile."""
        serializer = self.get_serializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info('User %s updated profile', request.user.username)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        logger.warning(
            'Admin %s deleted user %s',
            self.request.user.username,
            instance.username,
        )
        instance.is_active = False  # Soft delete
        instance.save()
