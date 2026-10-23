import random,time

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view,permission_classes,action
from rest_framework import status
from rest_framework import permissions
from rest_framework import viewsets,mixins

from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.models import User

from django.conf import settings

import logging
import razorpay
from decimal import Decimal,ROUND_HALF_UP
from django.db import transaction


from bazaar.models import Product,CartItem,Cart,Order,Coupon,OrderItem
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


from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def payment_test_page(request):
    return render(request, 'api/payment_test.html')





client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID,settings.RAZORPAY_KEY_SECRET)
)



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

# used function based view for otp and password reset flow
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def forgot_password(request):
    serializer = ForgotPasswordSerializer(data=request.data) #sending data to serializer
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

    otp = str(random.randint(1000,9999)) #generate otp of 4 digits

    print("OTP:", otp)

    request.session['reset_email'] = user.email
    request.session['reset_otp'] = otp
    request.session['otp_expiry'] = time.time() + 300  # otp valid for 5 minutes
    request.session['otp_verified'] = False            # flag set to false

    request.session.pop('password_reset_expiry', None) 

    request.session.set_expiry(600)  # session valid for 10 minutes



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
            {'error': 'Please request a new OTP.'}, # if email,otp not available then request a new otp
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

    request.session['otp_verified'] = True # flag set to true
    request.session['password_reset_expiry'] = time.time() + 600 # after flag is set, give 10 minute to 
                                                                                # reset a password.
    request.session.set_expiry(600) #session expiry timer for 10 min


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

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def product_action(self, request, pk=None):
        if request.user.account.role != 'customer':
            return Response(
                {'error': 'Only customers can buy or add products to cart.'},
                status=status.HTTP_403_FORBIDDEN
            )

        product = self.get_object() #retrieves the specific object associated with the URL

        quantity = request.data.get('quantity')
        action_type = request.data.get('action')

        # Validate quantity
        if quantity is None or str(quantity).strip() == '':
            return Response(
                {'error': 'Quantity is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Quantity must be a valid number.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity <= 0:
            return Response(
                {'error': 'Quantity must be greater than 0.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if action_type == 'cart':

            # Clear any previous Buy Now selection
            request.session.pop('buy_now_product_id', None)
            request.session.pop('buy_now_quantity', None)

            cart, _ = Cart.objects.get_or_create(customer=request.user)

            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )

            if not item_created:
                cart_item.quantity += quantity
                cart_item.save(update_fields=['quantity'])

            return Response(
                {'message': 'Product added to cart successfully.'},
                status=status.HTTP_200_OK
            )

        elif action_type == 'buy':
            request.session['buy_now_product_id'] = product.id
            request.session['buy_now_quantity'] = quantity

            return Response(
                {
                    'message': 'Product selected for purchase.',
                    'product_id': product.id,
                    'quantity': quantity
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {'error': 'Invalid action. Choose "cart" or "buy".'},
            status=status.HTTP_400_BAD_REQUEST
        )


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


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def api_checkout(request):

    # Only customers can checkout
    if request.user.account.role != 'customer':
        return Response(
            {'error': 'Only customers can checkout.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Check whether this is a Buy Now purchase
    buy_now_product_id = request.session.get('buy_now_product_id')
    buy_now_quantity = request.session.get('buy_now_quantity')

    # If both values exist, process this as a Buy Now purchase.
    if buy_now_product_id and buy_now_quantity:

        product = Product.objects.filter(
            id=buy_now_product_id,
            is_deleted=False
        ).first() # .first() returns the product if found, otherwise None.

        if product is None:
            return Response(
                {'error': 'Product not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        items = [{
            'product': product,
            'quantity': buy_now_quantity,
        }]

        receipt = f'Product {product.id}'

    else:
        # Otherwise, checkout using the cart
        cart = Cart.objects.filter(
            customer=request.user
        ).first()

        if cart is None:
            return Response(
                {'error': 'Your cart is empty.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_items = CartItem.objects.filter(
            cart=cart,
            product__is_deleted=False
        ).select_related('product')  # select_related('product') fetches related product data efficiently.

        if not cart_items.exists():
            return Response(
                {'error': 'Your cart is empty.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        items = [
            {
                'product': item.product,
                'quantity': item.quantity,
            }
            for item in cart_items
        ]

        receipt = f'Cart {cart.id}'

  

    # Calculate the subtotal before applying any coupon.
    # For every item, multiply its price by its quantity,
    # then add all the item totals together.

    total = sum(
        item['product'].price * item['quantity']
        for item in items
    )

    # Calculate coupon discount
    coupon_code = request.data.get('coupon_code')    
    coupon = None
    discount = Decimal('0')

    if coupon_code:
        coupon = Coupon.objects.filter(
            code=coupon_code,
            valid=True
        ).first()


    # If a valid coupon was found, calculate the discount.
    if coupon:
        discount = (
            total * coupon.discount_percent / Decimal('100')
        )

    # Subtract the discount from the subtotal to get the final amount.
    final_total = total - discount

    if final_total <= 0:
        return Response(
            {'error': 'The final amount must be greater than zero.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Convert rupees to paise
    amount_paise = int(final_total*100)

    # Create Razorpay order --------------------------------------
    try:
        razorpay_order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': receipt,
        })

    except Exception:
        logging.exception('Failed to create Razorpay order.')

        return Response(
            {'error': 'Unable to initiate payment. Please try again.'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    # Save the pending order and its items together.
    with transaction.atomic():

        # Create the main order.
        order = Order.objects.create(
            customer=request.user,
            coupon=coupon,
            total=total,
            discount=discount,
            final_total=final_total,
            razorpay_order_id=razorpay_order['id'],
            payment_status='pending',
        )

        # Save the products selected during checkout.
        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['product'].price,
            )
            for item in items
        ])

    # Return checkout information to the frontend
    return Response(
        {
            'message': 'Checkout initiated successfully.',
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': amount_paise,
            'currency': 'INR',
            'subtotal': str(total),
            'discount': str(discount),
            'final_total': str(final_total),
            'items': [
                {
                    'product_id': item['product'].id,
                    'product_name': item['product'].name,
                    'quantity': item['quantity'],
                    'unit_price': str(item['product'].price),
                }
                for item in items
            ],
            'django_order_id': order.id,
            'razorpay_order_id': order.razorpay_order_id,
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def payment_success(request):

    # Only customers can verify their purchases.
    if request.user.account.role != 'customer':
        return Response(
            {'error': 'Only customers can complete purchases.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get payment details returned by Razorpay.
    razorpay_order_id = request.data.get('razorpay_order_id')
    razorpay_payment_id = request.data.get('razorpay_payment_id')
    razorpay_signature = request.data.get('razorpay_signature')

    # Make sure all required details are provided.
    if not all([
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature
    ]):
        return Response(
            {'error': 'All Razorpay payment details are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Find the order belonging to this customer.
    order = Order.objects.filter(
        customer=request.user,
        razorpay_order_id=razorpay_order_id
    ).first()

    if order is None:
        return Response(
            {'error': 'Order not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Do not process an order that has already been paid.
    if order.payment_status == 'paid':
        return Response(
            {'message': 'This order has already been paid.'},
            status=status.HTTP_200_OK
        )

    # Verify that the signature was generated using Razorpay's secret.
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return Response(
            {'error': 'Payment signature verification failed.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Retrieve the payment details directly from Razorpay.
    try:
        payment = client.payment.fetch(razorpay_payment_id)
    except Exception:
        logging.exception('Failed to fetch Razorpay payment.')

        return Response(
            {'error': 'Unable to verify payment status.'},
            status=status.HTTP_502_BAD_GATEWAY
        )

    # Confirm that this payment belongs to the expected Razorpay order.
    if payment.get('order_id') != order.razorpay_order_id:
        return Response(
            {'error': 'Payment does not match this order.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Confirm that the payment amount matches the expected total.
    expected_amount = int(order.final_total * 100)

    if payment.get('amount') != expected_amount:
        return Response(
            {'error': 'Payment amount does not match the order.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # A valid signature does not necessarily mean the payment is captured.
    if payment.get('status') != 'captured':
        return Response(
            {
                'message': 'Payment has not been captured yet.',
                'payment_status': payment.get('status'),
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Mark the existing order as paid.
    with transaction.atomic():
        order = Order.objects.select_for_update().get(
            pk=order.pk,
            customer=request.user
        )

        # Recheck the status in case another request processed it.
        if order.payment_status == 'paid':
            return Response(
                {'message': 'This order has already been paid.'},
                status=status.HTTP_200_OK
            )

        order.payment_id = razorpay_payment_id
        order.payment_status = 'paid'
        order.save(update_fields=['payment_id', 'payment_status'])

        # If this was a cart checkout, remove only the purchased items.
        # Do not clear the cart for Buy Now purchases.
        buy_now_product_id = request.session.get('buy_now_product_id')

        if not buy_now_product_id:
            CartItem.objects.filter(
                cart__customer=request.user,
                product__in=order.items.values('product_id')
            ).delete()

        # Clear Buy Now session data only if it belongs to this purchase.
        if buy_now_product_id:
            request.session.pop('buy_now_product_id', None)
            request.session.pop('buy_now_quantity', None)

        # Clear coupon data after successful payment.
        request.session.pop('coupon_code', None)
        request.session.pop('discount', None)

    return Response(
        {
            'message': 'Payment verified successfully. Order placed.',
            'order_id': order.id,
            'payment_id': order.payment_id,
            'payment_status': order.payment_status,
        },
        status=status.HTTP_200_OK
    )
