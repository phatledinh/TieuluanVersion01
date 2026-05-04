"""
Admin configuration for Product Service.
"""

from django.contrib import admin
from .models import Category, Product, Book, Electronics, Fashion


class BookInline(admin.StackedInline):
    model = Book
    extra = 0


class ElectronicsInline(admin.StackedInline):
    model = Electronics
    extra = 0


class FashionInline(admin.StackedInline):
    model = Fashion
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock', 'product_type',
                    'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    inlines = [BookInline, ElectronicsInline, FashionInline]
    list_per_page = 25
