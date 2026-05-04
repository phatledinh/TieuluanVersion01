"""
Views for Product Service — Chapter 2.3.4

API Endpoints:
    Categories:
        GET    /api/categories/                 - List categories
        POST   /api/categories/                 - Create category (admin)
        GET    /api/categories/{id}/            - Category detail
        PUT    /api/categories/{id}/            - Update category (admin)
        DELETE /api/categories/{id}/            - Delete category (admin)

    Products:
        GET    /api/products/                   - List all products (search, filter, order)
        POST   /api/products/                   - Create generic product (admin)
        GET    /api/products/{id}/              - Product detail with domain info
        PUT    /api/products/{id}/              - Update product (admin)
        DELETE /api/products/{id}/              - Delete product (admin)
        PATCH  /api/products/{id}/stock/        - Update stock (staff/admin)

    Domain-specific creation:
        POST   /api/products/books/             - Create book product (admin)
        POST   /api/products/electronics/       - Create electronics product (admin)
        POST   /api/products/fashion/           - Create fashion product (admin)

    Filtering:
        GET    /api/products/by-category/{slug}/ - Products by category
"""

import logging

from django.db.models import Prefetch
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Category, Product, Book, Electronics, Fashion
from .permissions import IsAdminOrReadOnly, IsAdminUser, IsStaffOrAdmin
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateSerializer,
    BookProductCreateSerializer,
    ElectronicsProductCreateSerializer,
    FashionProductCreateSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Category ViewSet
# ---------------------------------------------------------------------------

class CategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD for product categories.
    Public can list/retrieve, Admin can create/update/delete.
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'pk'
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']


# ---------------------------------------------------------------------------
# Product ViewSet
# ---------------------------------------------------------------------------

class ProductViewSet(viewsets.ModelViewSet):
    """
    CRUD for products — Chapter 2.3.4

    Supports:
        - Search by name, description
        - Filter by category, is_active, product price range
        - Ordering by price, name, created_at
        - Domain-specific details auto-included in detail view
    """

    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'name', 'created_at', 'stock']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Product.objects.select_related(
            'category', 'book', 'electronics', 'fashion'
        )

        # Optional price range filter
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            qs = qs.filter(price__gte=float(min_price))
        if max_price:
            qs = qs.filter(price__lte=float(max_price))

        # Optional product_type filter
        ptype = self.request.query_params.get('product_type')
        if ptype == 'book':
            qs = qs.filter(book__isnull=False)
        elif ptype == 'electronics':
            qs = qs.filter(electronics__isnull=False)
        elif ptype == 'fashion':
            qs = qs.filter(fashion__isnull=False)

        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return ProductCreateSerializer
        return ProductListSerializer

    # ------ Custom actions ------

    @action(detail=True, methods=['patch'], url_path='stock',
            permission_classes=[IsStaffOrAdmin])
    def update_stock(self, request, pk=None):
        """
        PATCH /api/products/{id}/stock/
        Staff/Admin can update product stock.
        Body: {"stock": 50}
        """
        product = self.get_object()
        new_stock = request.data.get('stock')

        if new_stock is None:
            return Response(
                {'error': 'stock field is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product.stock = int(new_stock)
            product.save(update_fields=['stock', 'updated_at'])
        except (ValueError, TypeError):
            return Response(
                {'error': 'stock must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info('Stock updated: product=%s, new_stock=%d', product.name, product.stock)
        return Response({
            'id': product.id,
            'name': product.name,
            'stock': product.stock,
        })

    @action(detail=False, methods=['get'], url_path='by-category/(?P<slug>[^/.]+)',
            permission_classes=[AllowAny])
    def by_category(self, request, slug=None):
        """
        GET /api/products/by-category/{slug}/
        List products filtered by category slug.
        """
        try:
            category = Category.objects.get(slug=slug)
        except Category.DoesNotExist:
            return Response(
                {'error': f'Category "{slug}" not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        products = self.get_queryset().filter(category=category, is_active=True)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Domain-specific creation views
# ---------------------------------------------------------------------------

class CreateBookProductView(generics.CreateAPIView):
    """
    POST /api/products/books/
    Create a product with Book domain details in one request.
    """

    serializer_class = BookProductCreateSerializer
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        logger.info('Book product created: %s', product.name)

        detail = ProductDetailSerializer(product)
        return Response(detail.data, status=status.HTTP_201_CREATED)


class CreateElectronicsProductView(generics.CreateAPIView):
    """
    POST /api/products/electronics/
    Create a product with Electronics domain details in one request.
    """

    serializer_class = ElectronicsProductCreateSerializer
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        logger.info('Electronics product created: %s', product.name)

        detail = ProductDetailSerializer(product)
        return Response(detail.data, status=status.HTTP_201_CREATED)


class CreateFashionProductView(generics.CreateAPIView):
    """
    POST /api/products/fashion/
    Create a product with Fashion domain details in one request.
    """

    serializer_class = FashionProductCreateSerializer
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        logger.info('Fashion product created: %s', product.name)

        detail = ProductDetailSerializer(product)
        return Response(detail.data, status=status.HTTP_201_CREATED)
