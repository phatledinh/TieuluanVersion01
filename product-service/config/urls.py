"""
URL configuration for product-service.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static


def health_check(request):
    """Health check endpoint for Docker / API Gateway."""
    return JsonResponse({
        'service': 'product-service',
        'status': 'healthy',
        'version': '1.0.0',
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('products.urls')),
    path('api/health/', health_check, name='health-check'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
