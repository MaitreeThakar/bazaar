from rest_framework import serializers
from bazaar.models import Product,Order
from django.contrib.auth.models import User

class ProductSerializer(serializers.HyperlinkedModelSerializer):
    supplier = serializers.ReadOnlyField(source="supplier.username")
    class Meta:
        model = Product
        fields = ['url','name','price','description','supplier']

class SupplierSerializer(serializers.HyperlinkedModelSerializer):
    products = serializers.HyperlinkedRelatedField(many=True,view_name = "product-detail",read_only = True)
    class Meta:
        model = User
        fields = ['url','id','username','products']