from django.shortcuts import render
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes,APIView

from rest_framework import permissions
from django.contrib.auth.models import User

from rest_framework import mixins,generics

from .serializers import ProductSerializer,SupplierSerializer
from .permissions import IsSupplierOrReadOnly
from bazaar.models import Product
# Create your views here.

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_root(request):
    return Response(
        {
            "suppliers": reverse("users",request=request),
            "products":reverse("products",request=request)
        }
    )


# @api_view(['GET'])
# @permission_classes([permissions.AllowAny])
# def product_list(request):
#     products = Product.objects.filter(is_deleted=False,supplier = request.user)
#     serializer = ProductSerializer(products,many=True,context={'request': request})
   
#     return Response(serializer.data)




class ProductList(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsSupplierOrReadOnly]

    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user)


        
class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsSupplierOrReadOnly]

    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    
class UserList(generics.ListAPIView):

    queryset = User.objects.all()
    serializer_class = SupplierSerializer


class UserDetail(generics.RetrieveAPIView):

    queryset = User.objects.all()
    serializer_class = SupplierSerializer


    # def get(self,request):

    #     products = Product.objects.filter(is_deleted=False,supplier = request.user)
    #     serializer = ProductSerializer(products,many=True)
    
    #     return Response(serializer.data)    