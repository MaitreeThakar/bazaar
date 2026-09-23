from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class Account (models.Model):
    ROLE_CHOICES=(
        ('supplier' ,'Supplier'),
        ('customer', 'Customer'),
    )
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name="account")
    phone = models.CharField(max_length=15)
    role = models.CharField(max_length=10,choices=ROLE_CHOICES)

    def __str__(self):
        return self.user.username



class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=300)
    price = models.DecimalField(max_digits=10,decimal_places=2)
    supplier = models.ForeignKey(User,on_delete=models.CASCADE,related_name="products")
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return (f"{self.name} of {self.supplier.username}")

class Cart(models.Model):
    customer = models.OneToOneField(User,on_delete=models.CASCADE)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart,on_delete=models.CASCADE,related_name="items")
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity = models.IntegerField()

class Coupon(models.Model):
    code  = models.CharField(max_length=30,unique=True)
    discount_percent = models.DecimalField(max_digits=5,decimal_places=2)
    created_by = models.ForeignKey(User,on_delete=models.CASCADE)
    valid = models.BooleanField(default=True)


class Order(models.Model):
    customer = models.ForeignKey(User,on_delete=models.CASCADE,related_name="orders")
    is_deleted = models.BooleanField(default=False)
    coupon = models.ForeignKey(
        Coupon,on_delete=models.SET_NULL,null=True,blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2)
    final_total = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    razorpay_order_id = models.CharField(max_length=100,blank=True,null=True)
    payment_id = models.CharField(max_length=100,blank=True,null=True)
    payment_status = models.CharField(max_length=20,default='pending')
    
    def __str__(self):
        return (f"{self.id}  by {self.customer.username }")

class OrderItem(models.Model):
    order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name="items")
    product = models.ForeignKey(Product,on_delete=models.CASCADE,related_name="order_items")
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10,decimal_places=2)
