import random,time

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view,permission_classes
from rest_framework import status
from rest_framework import permissions
from rest_framework import viewsets,mixins

from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.models import User



from bazaar.models import Product,CartItem,Cart,Order
from bazaar.tasks import send_welcome_email

from .permissions import IsSupplierOrReadOnly,IsCustomerOrReadOnly

from .serializers import (SignUpSerializer,
                          ForgotPasswordSerializer,
                          VerifyOTPSerializer,
                          ResendOTPSerializer,
                          ResetPasswordSerializer,
                          ProductSerializer,
                          CartSerializer,
                          CartItemSerializer,
                          OrderSerializer)




# here normal classbased api view is implemented
class UserSignup(APIView):
    permission_classes = [permissions.AllowAny] 
    def post(self,request):
        serializer= SignUpSerializer(data=request.data) # giving data to serializer

        serializer.is_valid(raise_exception=True) # asking if serializer is valid or raise exception

        user = serializer.save() #saving serializers create methods returned value into user

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

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def forgot_password(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']

    user = User.objects.filter(email__iexact=email).first()

    # Use the same response whether or not the email exists.
    response_data = {
        'message': 'If an account exists with this email, '
                    'an OTP will be sent.'
    }

    if user is None:
        return Response(response_data, status=status.HTTP_200_OK)

    otp = str(random.randint(1000,9999))

    print("OTP:", otp)

    request.session['reset_email'] = user.email
    request.session['reset_otp'] = otp
    request.session['otp_expiry'] = time.time() + 300
    request.session['otp_verified'] = False

    request.session.pop('password_reset_expiry', None)

    request.session.set_expiry(600)



    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_otp(request):

    serializer = VerifyOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    otp = serializer.validated_data['otp']

    session_email = request.session.get('reset_email')
    session_otp = request.session.get('reset_otp')
    otp_expiry = request.session.get('otp_expiry')

    if not session_email or not session_otp or not otp_expiry:
        return Response(
            {'error': 'Please request a new OTP.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if email.lower() != session_email.lower():
        return Response(
            {'error': 'Invalid password-reset session.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if time.time() >= otp_expiry:
        return Response(
            {'error': 'OTP has expired. Please request a new one.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if otp != session_otp:
        return Response(
            {'error': 'Invalid OTP.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    request.session['otp_verified'] = True
    request.session['password_reset_expiry'] = time.time() + 600
    request.session.set_expiry(600)


    return Response(
        {'message': 'OTP verified successfully. You can reset your password within 10 minutes.'},
        status=status.HTTP_200_OK
    )
        
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def resend_otp(request):
    serializer = ResendOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']

    session_email = request.session.get('reset_email')
    otp_expiry = request.session.get('otp_expiry')

    # Check whether the password-reset session belongs to this email.
    if not session_email or not otp_expiry or email.lower() != session_email.lower():
        return Response(
            {'error': 'Please start the password-reset process again.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Prevent requesting a new OTP while the current one is still valid.
    if time.time() < otp_expiry:
        remaining = int(otp_expiry - time.time())

        return Response(
            {
                'error': (
                    f'You can request a new OTP after '
                    f'{remaining} seconds.'
                )
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generate a new OTP after the existing OTP expires.
    otp = str(random.randint(1000, 9999))

    print("New OTP:", otp)

    request.session['reset_otp'] = otp
    request.session['otp_expiry'] = time.time() + 300
    request.session['otp_verified'] = False

    request.session.pop('password_reset_expiry', None)


    request.session.set_expiry(600)

    return Response(
        {'message': 'A new OTP has been generated.'},
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def reset_password(request):

    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data['email']
    new_password = serializer.validated_data['new_password']

    session_email = request.session.get('reset_email')
    reset_expiry = request.session.get('password_reset_expiry')

    if not request.session.get('otp_verified'):
        return Response(
            {'error': 'Please verify your OTP first.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not session_email or email.lower() != session_email.lower():
        return Response(
            {'error': 'Invalid password-reset session.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check the separate password-reset authorization expiry.
    if not reset_expiry or time.time() >= reset_expiry:
        return Response(
            {'error': 'Password-reset authorization has expired. Please start again.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.filter(email__iexact=session_email).first()

    if user is None:
        return Response(
            {'error': 'Unable to process the request.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.set_password(new_password)
    user.save(update_fields=['password'])

    # Clear password-reset data after a successful reset.
    for key in (
        'reset_email',
        'reset_otp',
        'otp_expiry',
        'otp_verified',
        'password_reset_expiry',
    ):
        request.session.pop(key, None)

    request.session.modified = True

    return Response(
        {'message': 'Password reset successfully.'},
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





