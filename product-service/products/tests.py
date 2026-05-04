"""
Tests for Product Service — Chapter 2.3

Covers:
    - Category CRUD API
    - Product listing, detail, creation
    - Domain-specific product creation (Book, Electronics, Fashion)
    - Filtering, searching, pagination
    - Stock update endpoint
    - Permission enforcement
"""

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Category, Product, Book, Electronics, Fashion


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class CategoryModelTest(TestCase):
    """Test Category model behavior."""

    def test_create_category(self):
        cat = Category.objects.create(name='Books', description='Test')
        self.assertEqual(str(cat), 'Books')
        self.assertTrue(cat.slug)  # auto-generated

    def test_slug_auto_generated(self):
        cat = Category.objects.create(name='Home & Kitchen')
        self.assertEqual(cat.slug, 'home-kitchen')

    def test_unique_name(self):
        Category.objects.create(name='Electronics')
        with self.assertRaises(Exception):
            Category.objects.create(name='Electronics')


class ProductModelTest(TestCase):
    """Test Product and domain detail models."""

    def setUp(self):
        self.category = Category.objects.create(name='Books')

    def test_create_product(self):
        product = Product.objects.create(
            name='Test Book',
            price=100000,
            stock=10,
            category=self.category,
        )
        self.assertEqual(str(product), 'Test Book (Books)')
        self.assertEqual(product.product_type, 'general')

    def test_book_detail(self):
        product = Product.objects.create(
            name='Django for Beginners',
            price=350000,
            stock=20,
            category=self.category,
        )
        Book.objects.create(
            product=product,
            author='William S. Vincent',
            publisher='Leanpub',
            isbn='978-1-234-56789-0',
        )
        self.assertEqual(product.product_type, 'book')
        self.assertEqual(product.domain_detail, product.book)
        self.assertEqual(product.book.author, 'William S. Vincent')

    def test_electronics_detail(self):
        category = Category.objects.create(name='Electronics')
        product = Product.objects.create(
            name='iPhone 15',
            price=29990000,
            stock=5,
            category=category,
        )
        elec = Electronics.objects.create(
            product=product,
            brand='Apple',
            warranty=12,
            model_number='A3090',
            specifications={'ram': '6GB', 'storage': '128GB'},
        )
        self.assertEqual(product.product_type, 'electronics')
        self.assertEqual(elec.brand, 'Apple')
        self.assertEqual(elec.specifications['ram'], '6GB')

    def test_fashion_detail(self):
        category = Category.objects.create(name='Fashion')
        product = Product.objects.create(
            name='Áo Polo',
            price=250000,
            stock=50,
            category=category,
        )
        fashion = Fashion.objects.create(
            product=product,
            size='L',
            color='Navy',
            material='Cotton',
            gender='M',
        )
        self.assertEqual(product.product_type, 'fashion')
        self.assertEqual(fashion.size, 'L')
        self.assertEqual(fashion.gender, 'M')


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

class CategoryAPITest(APITestCase):
    """Test Category API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(
            name='Books',
            description='Book category',
        )

    def test_list_categories(self):
        """GET /api/categories/ — public access."""
        response = self.client.get('/api/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_category(self):
        """GET /api/categories/{id}/ — public access."""
        response = self.client.get(f'/api/categories/{self.category.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Books')


class ProductAPITest(APITestCase):
    """Test Product API endpoints — Chapter 2.3.4."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            name='Samsung Galaxy S24',
            price=25990000,
            stock=15,
            category=self.category,
        )
        Electronics.objects.create(
            product=self.product,
            brand='Samsung',
            warranty=12,
            model_number='SM-S921B',
            specifications={'ram': '8GB'},
        )

    def test_list_products(self):
        """GET /api/products/ — public, returns product list."""
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_retrieve_product_detail(self):
        """GET /api/products/{id}/ — returns full detail with domain info."""
        response = self.client.get(f'/api/products/{self.product.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Samsung Galaxy S24')
        self.assertEqual(response.data['product_type'], 'electronics')
        self.assertIn('electronics', response.data)
        self.assertEqual(response.data['electronics']['brand'], 'Samsung')

    def test_search_products(self):
        """GET /api/products/?search=Samsung — search by name."""
        response = self.client.get('/api/products/', {'search': 'Samsung'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(
            'Samsung' in p['name']
            for p in response.data['results']
        ))

    def test_filter_by_category(self):
        """GET /api/products/?category=1 — filter by category."""
        response = self.client.get('/api/products/', {'category': self.category.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_product_type(self):
        """GET /api/products/?product_type=electronics — filter by domain."""
        response = self.client.get('/api/products/', {'product_type': 'electronics'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for p in response.data['results']:
            self.assertEqual(p['product_type'], 'electronics')

    def test_filter_by_price_range(self):
        """GET /api/products/?min_price=20000000&max_price=30000000."""
        response = self.client.get('/api/products/', {
            'min_price': '20000000',
            'max_price': '30000000',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ordering(self):
        """GET /api/products/?ordering=price — order by price."""
        Product.objects.create(
            name='Cheap Item', price=10000, stock=5, category=self.category,
        )
        response = self.client.get('/api/products/', {'ordering': 'price'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prices = [p['price'] for p in response.data['results']]
        self.assertEqual(prices, sorted(prices))

    def test_product_not_found(self):
        """GET /api/products/99999/ — 404."""
        response = self.client.get('/api/products/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_product_requires_auth(self):
        """POST /api/products/ — anonymous → 401 or 403."""
        response = self.client.post('/api/products/', {
            'name': 'Test',
            'price': 10000,
            'stock': 1,
            'category': self.category.pk,
        })
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])


class ProductByCategoryAPITest(APITestCase):
    """Test /api/products/by-category/{slug}/ endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Fashion')
        Product.objects.create(
            name='Áo Thun', price=150000, stock=40, category=self.category,
        )

    def test_by_category_slug(self):
        response = self.client.get(f'/api/products/by-category/{self.category.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_by_category_slug_not_found(self):
        response = self.client.get('/api/products/by-category/nonexistent/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class HealthCheckTest(APITestCase):
    """Test health-check endpoint."""

    def test_health(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['service'], 'product-service')
        self.assertEqual(response.data['status'], 'healthy')
