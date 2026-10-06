from django.shortcuts import render
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import permissions
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from rest_framework import mixins,generics
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from .serializers import ProductSerializer,SupplierSerializer,CartItemSerializer,CartSerializer,OrderSerializer,OrderItemSerializer
from .permissions import IsSupplierOrReadOnly
from bazaar.models import Product,Account,CartItem,Cart,Order,OrderItem
from bazaar.tasks import send_welcome_email



class UserSignup(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self,request):
        data = request.data
        username = data.get('username')
        email = data.get('email')
        phone = data.get('phone')
        role = data.get('role')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        if not username or not email or not password or not phone or not role:
            return Response(
                {"detail": "All fields are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if password != confirm_password:
            return Response(
                {"error": "Passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response(
                {"detail": "Username already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "Email already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if role not in ["customer", "supplier"]:
            return Response(
                {"detail": "Invalid role"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
            
        Account.objects.create(
            role=role,
            phone = phone,
            user=user
        )
        send_welcome_email.delay(user.email,user.username)

        return Response(
            {'success': "Sign up successfully",
             "username":username},
                status=status.HTTP_201_CREATED
            )

class UserLogin(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self,request):
        print("LOGIN VIEW REACHED")
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username,password=password)

        if user is None:
            return Response(
                {'detail':'Invalid username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        login(request,user)
        return Response(
            {'success':'Login successful',
            "username":username}
        )


class UserLogout(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self,request):
        logout(request)

        return Response(
            {
                "detail":"Logout successful"
            }
        )







class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,IsSupplierOrReadOnly]

   
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.filter(is_deleted=False)
    
    def perform_create(self, serializer):
        serializer.save(supplier=self.request.user)



class SupplierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = SupplierSerializer   

class CartViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer

    def get_queryset(self):
        return Cart.objects.filter(customer = self.request.user)


class CartItemViewSet(viewsets.ModelViewSet):
    permission_classes=[permissions.IsAuthenticated]
    serializer_class = CartItemSerializer

    def get_queryset(self):
        return CartItem.objects.filter(cart__customer = self.request.user)

    def perform_create(self, serializer):
        cart,created = Cart.objects.get_or_create(
            customer = self.request.user
        )
        serializer.save(cart=cart)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderSerializer
    def get_queryset(self):
        return Order.objects.filter(is_deleted=False,customer= self.request.user).prefetch_related('items')


class OrderItemViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderItemSerializer
    def get_queryset(self):
            return OrderItem.objects.filter(order__customer= self.request.user)
