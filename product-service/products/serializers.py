"""
Serializers for Product Service.

Handles:
    - Category CRUD
    - Product listing with domain-specific detail inlined
    - Separate creation endpoints for Book, Electronics, Fashion products
"""

from rest_framework import serializers
from .models import Category, Product, Book, Electronics, Fashion


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(
        source='products.count', read_only=True,
    )

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'is_active',
                  'product_count', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


# ---------------------------------------------------------------------------
# Domain detail serializers (nested)
# ---------------------------------------------------------------------------

class BookDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['author', 'publisher', 'isbn', 'pages', 'language']


class ElectronicsDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Electronics
        fields = ['brand', 'warranty', 'model_number', 'specifications']


class FashionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fashion
        fields = ['size', 'color', 'material', 'gender']


# ---------------------------------------------------------------------------
# Product — Read (list / detail)
# ---------------------------------------------------------------------------

class ProductListSerializer(serializers.ModelSerializer):
    """
    GET /api/products/
    Lightweight serializer for product listing.
    """

    category_name = serializers.CharField(source='category.name', read_only=True)
    product_type = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'stock', 'category', 'category_name',
                  'product_type', 'image_url', 'is_active', 'created_at']


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    GET /api/products/{id}/
    Full product detail with domain-specific info inlined.
    """

    category_name = serializers.CharField(source='category.name', read_only=True)
    product_type = serializers.CharField(read_only=True)
    book = BookDetailSerializer(read_only=True)
    electronics = ElectronicsDetailSerializer(read_only=True)
    fashion = FashionDetailSerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock',
            'category', 'category_name', 'product_type',
            'image_url', 'is_active', 'created_at', 'updated_at',
            'book', 'electronics', 'fashion',
        ]


# ---------------------------------------------------------------------------
# Product — Create / Update (per domain type)
# ---------------------------------------------------------------------------

class ProductCreateSerializer(serializers.ModelSerializer):
    """
    POST /api/products/
    Create a generic product (no domain-specific fields).
    """

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'stock',
                  'category', 'image_url', 'is_active']
        read_only_fields = ['id']


class BookProductCreateSerializer(serializers.Serializer):
    """
    POST /api/products/books/
    Create a product + book detail in one request.
    """

    # Product fields
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default='')
    price = serializers.FloatField()
    stock = serializers.IntegerField(default=0)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    image_url = serializers.URLField(required=False, default='')
    # Book fields
    author = serializers.CharField(max_length=255)
    publisher = serializers.CharField(max_length=255, required=False, default='')
    isbn = serializers.CharField(max_length=20, required=False, default='')
    pages = serializers.IntegerField(required=False, allow_null=True, default=None)
    language = serializers.CharField(max_length=50, required=False, default='Vietnamese')

    def create(self, validated_data):
        product_data = {
            k: validated_data[k]
            for k in ['name', 'description', 'price', 'stock', 'category', 'image_url']
        }
        book_data = {
            k: validated_data[k]
            for k in ['author', 'publisher', 'isbn', 'pages', 'language']
        }
        product = Product.objects.create(**product_data)
        Book.objects.create(product=product, **book_data)
        return product


class ElectronicsProductCreateSerializer(serializers.Serializer):
    """
    POST /api/products/electronics/
    Create a product + electronics detail in one request.
    """

    # Product fields
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default='')
    price = serializers.FloatField()
    stock = serializers.IntegerField(default=0)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    image_url = serializers.URLField(required=False, default='')
    # Electronics fields
    brand = serializers.CharField(max_length=100)
    warranty = serializers.IntegerField(help_text='Months')
    model_number = serializers.CharField(max_length=100, required=False, default='')
    specifications = serializers.JSONField(required=False, default=dict)

    def create(self, validated_data):
        product_data = {
            k: validated_data[k]
            for k in ['name', 'description', 'price', 'stock', 'category', 'image_url']
        }
        elec_data = {
            k: validated_data[k]
            for k in ['brand', 'warranty', 'model_number', 'specifications']
        }
        product = Product.objects.create(**product_data)
        Electronics.objects.create(product=product, **elec_data)
        return product


class FashionProductCreateSerializer(serializers.Serializer):
    """
    POST /api/products/fashion/
    Create a product + fashion detail in one request.
    """

    # Product fields
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, default='')
    price = serializers.FloatField()
    stock = serializers.IntegerField(default=0)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    image_url = serializers.URLField(required=False, default='')
    # Fashion fields
    size = serializers.CharField(max_length=10)
    color = serializers.CharField(max_length=50)
    material = serializers.CharField(max_length=100, required=False, default='')
    gender = serializers.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female'), ('U', 'Unisex')],
        default='U',
    )

    def create(self, validated_data):
        product_data = {
            k: validated_data[k]
            for k in ['name', 'description', 'price', 'stock', 'category', 'image_url']
        }
        fashion_data = {
            k: validated_data[k]
            for k in ['size', 'color', 'material', 'gender']
        }
        product = Product.objects.create(**product_data)
        Fashion.objects.create(product=product, **fashion_data)
        return product
