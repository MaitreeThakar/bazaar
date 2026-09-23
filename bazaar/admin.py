from django.contrib import admin
from .models import Account,Product,Order,OrderItem,CartItem,Cart,Coupon
# Register your models here.

admin.site.register(Account)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Coupon)