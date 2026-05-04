"""
Product Models — Chapter 2.3

Category → Product (base) → Domain-specific detail tables:
    - Book          (author, publisher, isbn)
    - Electronics   (brand, warranty)
    - Fashion       (size, color)

Database: PostgreSQL (Chapter 2.10.4)
  - Supports complex relations and JSON fields
  - Better full-text search for product catalog

Design:
    Product is the base table with common attributes.
    Each domain extends Product via OneToOneField (Table-per-type inheritance).
    This keeps queries efficient while allowing domain-specific attributes.
"""

from django.db import models


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class Category(models.Model):
    """
    Product category / domain classification.
    Examples: Books, Electronics, Fashion, Home & Kitchen, etc.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'category'
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Product (base)
# ---------------------------------------------------------------------------

class Product(models.Model):
    """
    Base product model — Chapter 2.3.2
    Common attributes shared across all product domains.
    """

    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default='')
    price = models.FloatField(help_text='Price in VND')
    stock = models.IntegerField(default=0, help_text='Available inventory')
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
    )
    image_url = models.URLField(max_length=500, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'product'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['price']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f'{self.name} ({self.category.name})'

    @property
    def product_type(self):
        """Return the domain-specific type if exists."""
        if hasattr(self, 'book'):
            return 'book'
        if hasattr(self, 'electronics'):
            return 'electronics'
        if hasattr(self, 'fashion'):
            return 'fashion'
        return 'general'

    @property
    def domain_detail(self):
        """Return the domain-specific detail object."""
        if hasattr(self, 'book'):
            return self.book
        if hasattr(self, 'electronics'):
            return self.electronics
        if hasattr(self, 'fashion'):
            return self.fashion
        return None


# ---------------------------------------------------------------------------
# Domain-specific detail models — Chapter 2.3.3
# ---------------------------------------------------------------------------

class Book(models.Model):
    """Book domain details — giáo trình, tiểu thuyết."""

    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name='book',
    )
    author = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255, blank=True, default='')
    isbn = models.CharField(max_length=20, unique=True, blank=True, default='')
    pages = models.IntegerField(null=True, blank=True)
    language = models.CharField(max_length=50, default='Vietnamese')

    class Meta:
        db_table = 'book'

    def __str__(self):
        return f'Book: {self.product.name} by {self.author}'


class Electronics(models.Model):
    """Electronics domain details — mobile, laptop, tủ lạnh, điều hòa."""

    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name='electronics',
    )
    brand = models.CharField(max_length=100)
    warranty = models.IntegerField(help_text='Warranty period in months')
    model_number = models.CharField(max_length=100, blank=True, default='')
    specifications = models.JSONField(
        default=dict, blank=True,
        help_text='Technical specs as JSON (e.g. {"ram": "8GB", "storage": "256GB"})',
    )

    class Meta:
        db_table = 'electronics'
        verbose_name_plural = 'Electronics'

    def __str__(self):
        return f'Electronics: {self.brand} {self.product.name}'


class Fashion(models.Model):
    """Fashion domain details — áo, quần, giày."""

    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name='fashion',
    )
    size = models.CharField(max_length=10, help_text='S, M, L, XL, XXL or shoe size')
    color = models.CharField(max_length=50)
    material = models.CharField(max_length=100, blank=True, default='')
    gender = models.CharField(
        max_length=10,
        choices=[('M', 'Male'), ('F', 'Female'), ('U', 'Unisex')],
        default='U',
    )

    class Meta:
        db_table = 'fashion'

    def __str__(self):
        return f'Fashion: {self.product.name} ({self.size}/{self.color})'
