from django.shortcuts import render
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes,APIView

from rest_framework import permissions
from django.contrib.auth.models import User

from rest_framework import mixins,generics
from rest_framework import viewsets
from .serializers import ProductSerializer,SupplierSerializer
from .permissions import IsSupplierOrReadOnly
from bazaar.models import Product
# Create your views here.




class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsSupplierOrReadOnly]

    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user)



class SupplierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = SupplierSerializer   
