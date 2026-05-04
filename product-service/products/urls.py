"""
URL routing for Product Service — Chapter 2.3.4

Category endpoints:
    GET    /api/categories/                     - List categories
    POST   /api/categories/                     - Create category (admin)
    GET    /api/categories/{id}/                - Category detail
    PUT    /api/categories/{id}/                - Update category (admin)
    DELETE /api/categories/{id}/                - Delete category (admin)

Product endpoints:
    GET    /api/products/                       - List/search products
    POST   /api/products/                       - Create generic product (admin)
    GET    /api/products/{id}/                  - Product detail
    PUT    /api/products/{id}/                  - Update product (admin)
    DELETE /api/products/{id}/                  - Delete product (admin)
    PATCH  /api/products/{id}/stock/            - Update stock (staff/admin)
    GET    /api/products/by-category/{slug}/    - Products by category

Domain-specific creation:
    POST   /api/products/books/                 - Create book product
    POST   /api/products/electronics/           - Create electronics product
    POST   /api/products/fashion/               - Create fashion product
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ProductViewSet,
    CreateBookProductView,
    CreateElectronicsProductView,
    CreateFashionProductView,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    # Domain-specific product creation (before router to avoid conflict)
    path('products/books/', CreateBookProductView.as_view(), name='create-book'),
    path('products/electronics/', CreateElectronicsProductView.as_view(), name='create-electronics'),
    path('products/fashion/', CreateFashionProductView.as_view(), name='create-fashion'),
    # Router-generated URLs
    path('', include(router.urls)),
]
