from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import permissions
from rest_framework import viewsets,mixins

from django.contrib.auth import authenticate,login,logout


from bazaar.models import Product,CartItem,Cart,Order
from bazaar.tasks import send_welcome_email

from .permissions import IsSupplierOrReadOnly,IsCustomerOrReadOnly

from .serializers import (SignUpSerializer,
                          ProductSerializer,
                          CartSerializer,
                          CartItemSerializer,
                          OrderSerializer)




# here normal classbased api view is implemented
class UserSignup(APIView):
    permission_classes = [permissions.AllowAny] 
    def post(self,request):
        serializers= SignUpSerializer(data=request.data) # giving data to serializer

        serializers.is_valid(raise_exception=True) # asking if serializer is valid or raise exception

        user = serializers.save() #saving serializers create methods returned value into user

        send_welcome_email.delay(user.email,user.username) # sending signal after user is created

        return Response(
            {'detail': "Sign up successfully",
             "username":user.username},
                status=status.HTTP_201_CREATED
            )

class UserLogin(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self,request): # handle post requests
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username,password=password) #authenticate user

        if user is None: 
            return Response(
                {'detail':'Invalid username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        login(request,user) # log in the authenticated user
        return Response(
            {'detail':'Login successful',
            "username":user.username},
            status=status.HTTP_200_OK
        )


class UserLogout(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self,request):
        logout(request)

        return Response(
            {
                "detail":"Logout successful"
            },
            status=status.HTTP_200_OK
        )

# here viewset is implemented and type is modelviewset - full CRUD
class ProductViewSet(viewsets.ModelViewSet):
    #authenticated and if not supplier then read only
    permission_classes = [permissions.IsAuthenticated,IsSupplierOrReadOnly] 

   
    serializer_class = ProductSerializer

    #customizing query set

    def get_queryset(self):
        user = self.request.user
        if user.account.role == 'supplier': # if role is supplier 
            return Product.objects.filter(
                        is_deleted=False,
                        supplier=user # show their products only
                    )
        return Product.objects.filter( # else show all non-deleted products
            is_deleted=False)
    
    def perform_create(self, serializer): 
        # customizing create method to have supplier=current user in data coming from serializer
        serializer.save(supplier=self.request.user)

    #customize destroy method to soft delete
    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted']) #so it just update this instead of writing all fields


# This is another type of serializer for only list and retrieve
class CartViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer

    def get_queryset(self):
        # query to get current user's cart 
        # prefetch related to avoid additional database queries when serializing the cart.
        return Cart.objects.filter(customer = self.request.user).prefetch_related("items__product")


# this is model viewset because cart item can be deleted and updated
class CartItemViewSet(viewsets.ModelViewSet):
    permission_classes=[permissions.IsAuthenticated]
    serializer_class = CartItemSerializer

    def get_queryset(self):
        # query to get current user as cart's customer
        #select related is also for preloading queries, used when one to one, direct relationship
        return CartItem.objects.filter(cart__customer = self.request.user
                                       ).select_related("cart__customer","product")

    def perform_create(self, serializer):
        cart,created = Cart.objects.get_or_create(
            customer = self.request.user
        )
        serializer.save(cart=cart) #create cart item using this cart (already exist or created)



# here mixins are used, because we want list,retrieve and delete, we do not want update for order
class OrderViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.DestroyModelMixin,
                   viewsets.GenericViewSet): #generic viewset provides generic view based behaviour
    permission_classes = [permissions.IsAuthenticated,IsCustomerOrReadOnly]
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user

        if user.account.role == 'customer':
            # when role is customer- show their own orders
            return Order.objects.filter(is_deleted=False,customer= self.request.user
                                        ).select_related("customer","coupon"
                                                         ).prefetch_related('items__product__supplier')
        # otherwise show orders to supplier where supplier = current user
        return Order.objects.filter(is_deleted=False,items__product__supplier=self.request.user
                                    ).select_related("customer","coupon"
                                                     ).prefetch_related('items__product__supplier').distinct()

    #soft delete
    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted']) #so it just update this instead of writing all fields





