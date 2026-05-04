"""
URL routing for User Service - Chapter 2.4.4

Auth endpoints:
    POST /api/auth/register/    - Register
    POST /api/auth/login/       - Login (JWT)
    POST /api/auth/refresh/     - Refresh token

User endpoints:
    GET    /api/users/          - List users (admin)
    POST   /api/users/          - Create user (admin)
    GET    /api/users/me/       - Current user profile
    PUT    /api/users/me/       - Update own profile
    GET    /api/users/{id}/     - User detail
    PUT    /api/users/{id}/     - Update user
    DELETE /api/users/{id}/     - Soft-delete user (admin)
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    LoginView,
    RefreshTokenView,
    RegisterView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Authentication
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/refresh/', RefreshTokenView.as_view(), name='auth-refresh'),
    # User CRUD
    path('', include(router.urls)),
]
