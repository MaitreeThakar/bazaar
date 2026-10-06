from rest_framework import serializers
from bazaar.models import Product,CartItem,Cart,OrderItem,Order
from django.contrib.auth.models import User

class ProductSerializer(serializers.HyperlinkedModelSerializer):
    supplier = serializers.ReadOnlyField(source= 'supplier.username')

    class Meta:
        model = Product
        fields = ['url','name','price','description','supplier']


class SupplierSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="supplier-detail"
    )
    products = serializers.HyperlinkedRelatedField(many=True,view_name = "product-detail",read_only = True)
    class Meta:
        model = User
        fields = ['url','id','username','products']

class CartItemSerializer(serializers.HyperlinkedModelSerializer):
    customer = serializers.ReadOnlyField(source= 'cart.customer.username')
    class Meta:
        model = CartItem
        fields = ['url','customer','product','quantity']

class CartSerializer(serializers.HyperlinkedModelSerializer):
    customer = serializers.ReadOnlyField(source= 'customer.username')
    items = CartItemSerializer(many=True,read_only=True)

    total_items = serializers.SerializerMethodField()
    total_quantity= serializers.SerializerMethodField()
    cart_total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['url','customer','items','total_items','total_quantity','cart_total']

    def get_total_items(self,obj):
        return obj.items.count()

    def get_total_quantity(self,obj):
        return sum(item.quantity for item in obj.items.all())

    def get_cart_total(self,obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())




class OrderItemSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = OrderItem
        fields = [ 'product','quantity','price']  

class OrderSerializer(serializers.ModelSerializer):
    customer = serializers.ReadOnlyField(source= 'customer.username')
    coupon = serializers.ReadOnlyField(source= 'coupon.code')
    items = OrderItemSerializer(many=True,read_only=True)


    class Meta:
        model = Order
        fields = [
                  'url','items',
                  'customer', 'coupon', 
                  'total', 'discount', 
                  'final_total', 
                  'payment_status']

