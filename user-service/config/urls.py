"""
URL configuration for user-service.
Routes:
    /admin/          - Django admin
    /api/auth/       - Authentication (register, login, refresh)
    /api/users/      - User management (CRUD)
    /api/health/     - Health check
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    """Health check endpoint for Docker / API Gateway."""
    return JsonResponse({
        'service': 'user-service',
        'status': 'healthy',
        'version': '1.0.0',
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/health/', health_check, name='health-check'),
]
