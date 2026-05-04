from django.db import models

class Cart(models.Model):
    user_id = models.IntegerField(unique=True, help_text="ID of the user this cart belongs to")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.id} for User {self.user_id}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product_id = models.IntegerField(help_text="ID of the product added to cart")
    quantity = models.IntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product_id')

    def __str__(self):
        return f"{self.quantity} of Product {self.product_id} in Cart {self.cart_id}"
