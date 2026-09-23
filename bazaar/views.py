from django.shortcuts import render,redirect,get_object_or_404
from .models import Account,Product,Order,OrderItem,Cart,CartItem,Coupon
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from decimal import Decimal,InvalidOperation
import random,time
import razorpay
from django.conf import settings

client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID,settings.RAZORPAY_KEY_SECRET)
)

# Create your views here.

def user_signup(request):

    if request.method == 'POST':
        username = request.POST['username'].strip()
        email = request.POST['email'].strip()
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        phone = request.POST['phone'].strip()
        role=request.POST['role'].strip()

        if not username or not email or not password or not confirm_password or not phone or not role:
            return render(request,'bazaar/signup.html',
                {  'error': "All fields are required.",
                    'username': username,
                    'email': email,
                    'phone': phone,
                    'role':role
                }
            )
        if User.objects.filter(username=username).exists():
            return render(request,'bazaar/signup.html',
                {  'error': "Username already exists.",
                    'username': username,
                    'email': email,
                    'phone': phone,
                    'role':role
                }
            )
        if password != confirm_password:
            return render(request,'bazaar/signup.html',
                            {'error':"Passwords do not match.",
                            'username':username,
                            'email':email,
                            'phone':phone,
                            'role':role})
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        Account.objects.create(
            user = user,
            phone=phone,
            role=role
        )
        return redirect("login")
    return render(request,'bazaar/signup.html')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username'].strip()
        password = request.POST['password']

        user = authenticate(
            request,
            username=username,
            password=password
        )
        if user is not None:
            login(request,user)
            return redirect("view_products")
        return render(request,'bazaar/login.html',{'error':"Invalid username or password."})
    return render(request,'bazaar/login.html')

def user_logout(request):
    logout(request)
    return redirect("login")

#PASSWORD

def forgot_password(request):
    if request.method=='POST':
        email = request.POST['email']

        if not email:
            return render(request, 'bazaar/forgot_password.html',{'error':'Email is required'})

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return render(request,'bazaar/forgot_password.html',{'error':'No account found with this email'})
        otp = random.randint(1000,9999)

        print("OTP:", otp)

        request.session['reset_email'] =email
        request.session['reset_otp'] = otp
        request.session['otp_expiry'] = time.time() +300

        request.session.set_expiry(600)




        return redirect('verify_otp')
    return render(request,'bazaar/forgot_password.html')

def verify_otp(request):
    if request.method == 'POST':
        otp = request.POST['otp']
        if not otp:
            return render(request,'bazaar/verify_otp.html',{'error':'OTP is required'})
        stored_otp = request.session.get('reset_otp')
        otp_expiry = request.session.get('otp_expiry')
        if stored_otp is None:
            return render(request,'bazaar/verify_otp.html',{'error':'Session has expired. Please request a new OTP'})

        if time.time() > otp_expiry:
            return render(
                request,
                'bazaar/verify_otp.html',
                {'error': 'OTP has expired. Please request a new OTP'}
            )


        if otp != str(stored_otp):
            return render(request,'bazaar/verify_otp.html',{'error':'Invalid OTP'})
        
        request.session['otp_verified'] = True
        return redirect('reset_password')
    return render(request,'bazaar/verify_otp.html')

def resend_otp(request):
    email = request.session.get('reset_email')    
    otp_expiry = request.session.get('otp_expiry')    

    

    if not email or not otp_expiry:
        return redirect('forgot_password')
    if time.time()<otp_expiry:
        remaining = int(otp_expiry - time.time())
        return render(request,'bazaar/verify_otp.html',{'error':f'You can request a new OTP after {remaining} seconds'})
    otp = random.randint(1000,9999)

    print("OTP:", otp)

    request.session['reset_email'] =email
    request.session['reset_otp'] = otp
    request.session['otp_expiry'] = time.time()+300
    request.session['otp_verified'] = False

    request.session.set_expiry(600)

    return redirect('verify_otp')

def reset_password(request):
    if not request.session.get('otp_verified'):
        return redirect('forgot_password')

    email = request.session.get('reset_email')

    if not email:
        return redirect('forgot_password')
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return redirect('forgot_password')
    
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if not password or not confirm_password:
            return render(request,'bazaar/reset_password.html',{'error':'All fields are required'})

        if password != confirm_password:
            return render(request,'bazaar/reset_password.html',{'error':'Passwords do not match'})

        user.set_password(password)
        user.save()
        request.session.pop('reset_email', None)
        request.session.pop('reset_otp', None)
        request.session.pop('otp_verified', None)

        return redirect('login')

    return render(request, 'bazaar/reset_password.html')
        
#PRODUCT

@login_required
def view_products(request):

    if request.user.account.role == 'supplier':
        products = Product.objects.filter(
            is_deleted=False,
            supplier=request.user
        )
    else:
        products = Product.objects.filter(
            is_deleted=False
        ).exclude(
            supplier=request.user
        )

    return render(
        request,
        'bazaar/products.html',
        {'products': products}
    )

@login_required
def add_product(request):

    if request.user.account.role != 'supplier':
        return render(
            request,
            'bazaar/add_product.html',
            {'error': 'Only suppliers can add products.'}
        )

    if request.method == "POST":
        name = request.POST['name'].strip()
        description = request.POST['description'].strip()
        price = request.POST['price'].strip()
        if not name or not description or not price:
            return render(
                request,
                'bazaar/add_product.html',
                {
                    'error': "All fields are required.",
                    'name': name,
                    'description': description,
                    'price':price
                }
            )
        try:
            price = Decimal(price)

        except InvalidOperation:

            return render(
                request,
                'bazaar/add_product.html',
                {
                    'error': "price must be a valid number.",
                    'name': name,
                    'description': description,
                    'price':price
                }
            )

        if price <= 0:

            return render(
                request,
                'bazaar/add_product.html',
                {
                    'error': "price must be greater than 0.",
                    'name': name,
                    'description': description,
                    'price':price
                }
            )
        Product.objects.create(
            name = name,
            description = description,
            price=price,
            supplier = request.user
        )
        return redirect("view_products")
    return render(request,'bazaar/add_product.html')

@login_required
def update_product(request,product_id):
    if request.user.account.role != 'supplier':
        return render(
            request,
            'bazaar/update_product.html',
            {'error': 'Only suppliers can update products.'}
        )

    product = get_object_or_404(Product,id=product_id)
    if product.supplier != request.user:
        return render(request,'bazaar/update_product.html',
                      {'error':"You can not update this product.",
                       'product':product})

    if request.method == 'POST':
        name = request.POST['name'].strip()
        description = request.POST['description'].strip()
        price = request.POST['price'].strip()
        if not name or not description or not price:
            return render(request,'bazaar/update_product.html',
                {   'error': "All fields are required.",
                    'product': product
                }
            )
        try:
            price = Decimal(price)

        except InvalidOperation:

            return render(
                request,
                'bazaar/update_product.html',
                {
                    'error': "price must be a valid number.",
                    'product': product
                }
            )

        if price <= 0:

            return render(
                request,
                'bazaar/update_product.html',
                {
                    'error': "price must be greater than 0.",
                    'product': product
                }
            )

        product.name = name
        product.description = description
        product.price = price
        product.save()
        return redirect("view_products")
           
    return render(request,'bazaar/update_product.html',{'product':product})
    
@login_required
def delete_product(request,product_id):

    if request.user.account.role != 'supplier':
        return render(
            request,
            'bazaar/products.html',
            {
                'error': 'Only suppliers can delete products.',
                'products': Product.objects.filter(is_deleted=False)
            }
        )
    product = get_object_or_404(Product,id=product_id,is_deleted=False)
    if product.supplier != request.user:
        products = Product.objects.filter(is_deleted=False)
        return render(request,'bazaar/products.html',
                        {'error':"You can not delete this product.",
                        'products':products})
    if request.method == 'POST':

        product.is_deleted = True
        product.save()
        return redirect("view_products")
    return redirect("view_products")

#CART
@login_required
def view_cart(request):
    if request.user.account.role != 'customer':
        return render(
            request,
            'bazaar/view_cart.html',
            {'error': 'Only customers can access the cart.'}
        )
    cart,created = Cart.objects.get_or_create(customer=request.user)
    items = CartItem.objects.filter(cart=cart)

    total_items = items.count()
    total_quantity = sum(item.quantity for item in items)

    cart_total=0
    for item in items:
        item.item_total = item.product.price * item.quantity

        cart_total += item.item_total

    return render(
        request,
        'bazaar/view_cart.html',
        {
            'items': items,
            'total_items': total_items,
            'total_quantity': total_quantity,
            'cart_total':cart_total
        }
    )

@login_required
def product_action(request, product_id):

    if request.user.account.role != 'customer':
        return render(
            request,
            'bazaar/products.html',
            {
                'error': 'Only customers can buy or add products to cart.',
                'products': Product.objects.filter(is_deleted=False)
            }
        )

    product = get_object_or_404(
        Product,
        id=product_id,
        is_deleted=False
    )

    if request.method == "POST":

        quantity = request.POST['quantity'].strip()
        action = request.POST['action']

        # quantity validation
        if not quantity:
            products = Product.objects.filter(is_deleted=False)

            return render(
                request,
                'bazaar/products.html',
                {
                    'error': "Quantity is required.",
                    'products': products
                }
            )

        try:
            quantity = int(quantity)

        except ValueError:
            products = Product.objects.filter(is_deleted=False)

            return render(
                request,
                'bazaar/products.html',
                {
                    'error': "Quantity must be a valid number.",
                    'products': products
                }
            )

        if quantity <= 0:
            products = Product.objects.filter(is_deleted=False)

            return render(
                request,
                'bazaar/products.html',
                {
                    'error': "Quantity must be greater than 0.",
                    'products': products
                }
            )

        if action == "cart":

            cart, cart_created = Cart.objects.get_or_create(customer=request.user)
    
            cart_item,item_created=CartItem.objects.get_or_create(
                cart = cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not item_created:
                cart_item.quantity += quantity
                cart_item.save()
                
            return redirect("view_cart")

        elif action == "buy":

            request.session['buy_now_product_id'] = product.id
            request.session['buy_now_quantity'] = quantity

            return redirect("checkout")

        return redirect("view_orders")

    return redirect("view_products")

@login_required
def update_cart_item(request, item_id):
    if request.user.account.role != 'customer':
        return redirect("view_products")
    
    cart, created = Cart.objects.get_or_create(
        customer=request.user
    )

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart=cart
    )

    if request.method == "POST":

        quantity = request.POST['quantity'].strip()

        if not quantity:
            return render(
                request,
                'bazaar/view_cart.html',
                {
                    'error': "Quantity is required.",
                    'items': CartItem.objects.filter(cart=cart)
                }
            )

        try:
            quantity = int(quantity)

        except ValueError:
            return render(
                request,
                'bazaar/view_cart.html',
                {
                    'error': "Quantity must be a valid number.",
                    'items': CartItem.objects.filter(cart=cart)
                }
            )

        if quantity <= 0:
            return render(
                request,
                'bazaar/view_cart.html',
                {
                    'error': "Quantity must be greater than 0.",
                    'items': CartItem.objects.filter(cart=cart)
                }
            )

        item.quantity = quantity
        item.save()

        return redirect("view_cart")

    return redirect("view_cart")

@login_required
def remove_cart_item(request, item_id):
    if request.user.account.role != 'customer':
        return redirect("view_products")
    cart, created = Cart.objects.get_or_create(
        customer=request.user
    )

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart=cart
    )

    if request.method == "POST":
        item.delete()

    return redirect("view_cart")

#CHECKOUT



@login_required
def checkout(request):
    if request.user.account.role != 'customer':
        return redirect("view_products") 

    buy_now_product_id = request.session.get('buy_now_product_id')
    buy_now_quantity = request.session.get('buy_now_quantity')

    if buy_now_product_id:
        product = get_object_or_404(
            Product,
            id=buy_now_product_id,
            is_deleted=False
        )

        item_total = product.price * buy_now_quantity

        items = [{
            'product': product,
            'quantity': buy_now_quantity,
            'item_total': item_total
        }]

        cart_total = item_total
    else:
        cart, created = Cart.objects.get_or_create(
            customer=request.user
        )

        items = CartItem.objects.filter(cart=cart)

        if not items.exists():
            return redirect("view_cart")
        
        for item in items:
            item.item_total = item.product.price * item.quantity

        cart_total = sum(item.item_total for item in items) 


    coupon_code = request.session.get('coupon_code','')
    discount = Decimal('0')

    coupon = None

    if coupon_code:
        coupon = Coupon.objects.filter(
            code=coupon_code,
            valid=True
        ).first()

    if coupon:
        discount = (cart_total * coupon.discount_percent) / 100

    final_total = cart_total - discount


    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code')

        if not coupon_code:
            return render(request,'bazaar/checkout.html',{
                'items':items,
                'cart_total':cart_total,
                'coupon_code':coupon_code,
                'discount':discount,
                'final_total':final_total,
                'error':'Please enter coupon code.'})

        try:
            coupon = Coupon.objects.get(code=coupon_code,valid=True)
        except Coupon.DoesNotExist:
            request.session.pop('coupon_code', None)
            request.session.pop('discount', None)
            discount = Decimal('0')
            final_total = cart_total

            return render(request,'bazaar/checkout.html',{
                'items':items,
                'cart_total':cart_total,
                'coupon_code':coupon_code,
                'discount':discount,
                'final_total':final_total,
                'error':'Invalid Coupon code.'})

        discount = (cart_total * coupon.discount_percent) /100
        final_total = cart_total - discount

        request.session['coupon_code'] = coupon.code
        request.session['discount'] = str(discount)


    return render(
        request,
        'bazaar/checkout.html',
        {
            'items': items,
            'cart_total':cart_total,
            'coupon_code':coupon_code,
            'discount':discount,
            'final_total':final_total,
        }
    )

@login_required
def create_razorpay_order(request):
    if request.user.account.role != 'customer':
        return redirect("view_products") 
    if request.method == 'POST':
        buy_now_product_id = request.session.get('buy_now_product_id')
        buy_now_quantity = request.session.get('buy_now_quantity')

        if buy_now_product_id:

            product = get_object_or_404(
                Product,
                id=buy_now_product_id,
                is_deleted=False
            )

            items = [{
                'product': product,
                'quantity': buy_now_quantity,
                'item_total': product.price * buy_now_quantity
            }]

            total = product.price * buy_now_quantity
            receipt = f"Product {product.id}"
        else:

            cart, created = Cart.objects.get_or_create(
                customer=request.user
            )

            items = CartItem.objects.filter(cart=cart)

            if not items.exists():
                return redirect("view_cart")
            
            for item in items:
                item.item_total = item.product.price * item.quantity
                
            total = sum(item.item_total for item in items)
            receipt = f"Cart {cart.id}"

        coupon_code = request.session.get('coupon_code','')
        discount = Decimal('0')

        coupon = None

        if coupon_code:
            coupon = Coupon.objects.filter(
                code=coupon_code,
                valid=True
            ).first()

        if coupon:
            discount = (total * coupon.discount_percent) / 100

        final_total = total - discount



        amount_paise = int(final_total*100)

        razorpay_order = client.order.create({
            "amount":amount_paise,
            "currency":"INR",
            "receipt":receipt
        })
        print(razorpay_order)
        return render(request,'bazaar/checkout.html',{
            'items': items,
            'cart_total': total,
            'discount': discount,
            'coupon_code': coupon_code,
            'final_total': final_total,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_amount': amount_paise,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        })
    return redirect('checkout')

@login_required
def payment_success(request):
    if request.method != 'POST':
        return redirect('checkout')
    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_signature = request.POST.get("razorpay_signature")
    try:
        client.utility.verify_payment_signature({
            "razorpay_payment_id":razorpay_payment_id,
            "razorpay_order_id":razorpay_order_id,
            "razorpay_signature":razorpay_signature
        })
        print("PAYMENT SIGNATURE VERIFIED")

        buy_now_product_id = request.session.get('buy_now_product_id')
        buy_now_quantity = request.session.get('buy_now_quantity')

        if buy_now_product_id:

            product = get_object_or_404(
                Product,
                id=buy_now_product_id,
                is_deleted=False
            )

            items = [{
                'product': product,
                'quantity': buy_now_quantity
            }]

            total = product.price * buy_now_quantity
        else:

            cart, created = Cart.objects.get_or_create(
                customer=request.user
            )

            items = CartItem.objects.filter(cart=cart)

            if not items.exists():
                return redirect("view_cart")
            total = sum(
                        item.product.price * item.quantity
                        for item in items
                    )
        
        coupon_code = request.session.get('coupon_code')
        discount = Decimal('0')

        coupon = None

        if coupon_code:
            coupon = Coupon.objects.filter(
                code=coupon_code,
                valid=True
            ).first()

        if coupon:
            discount = (total * coupon.discount_percent) / 100
        final_total = total - discount

        with transaction.atomic():

            order = Order.objects.create(
                customer=request.user,
                coupon=coupon,
                total=total,
                discount=discount,
                final_total=final_total,
                razorpay_order_id=razorpay_order_id,
                payment_id=razorpay_payment_id,
                payment_status='paid'
            )


            if buy_now_product_id:

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=buy_now_quantity,
                    price=product.price
                )

            else:

                for item in items:

                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    )

            # Only delete CartItems for a normal cart purchase
            if not buy_now_product_id:
                items.delete()

        # Clear checkout session data
        request.session.pop('coupon_code', None)
        request.session.pop('discount', None)

        # Clear Buy Now data
        request.session.pop('buy_now_product_id', None)
        request.session.pop('buy_now_quantity', None)


    except razorpay.errors.SignatureVerificationError:
        print("PAYMENT SIGNATURE VERIFICATION FAILED")

        return redirect('checkout')
    
    print(razorpay_payment_id)
    print(razorpay_order_id)
    print(razorpay_signature)
    return redirect('view_orders')


#ORDER
@login_required
def view_orders(request):
    if request.user.account.role != 'customer':
        return redirect("view_products")
    orders = Order.objects.filter(is_deleted=False,customer= request.user).prefetch_related('items')

    for order in orders:
        for item in order.items.all():
            item.item_total = item.price * item.quantity

    return render(request,'bazaar/orders.html',{'orders':orders})


@login_required
def supplier_orders(request):

    if request.user.account.role != 'supplier':
        return redirect("view_products")

    orders = Order.objects.filter(
        is_deleted=False,
        items__product__supplier=request.user
    ).prefetch_related('items__product').distinct()

    for order in orders:
        order.supplier_items = []

        for item in order.items.all():
            if item.product.supplier == request.user:
                item.item_total = item.price * item.quantity
                order.supplier_items.append(item)

    return render(
        request,
        'bazaar/supplier_orders.html',
        {'orders': orders}
    )

@login_required
def delete_order(request,order_id):
    if request.user.account.role != 'customer':
        return redirect("view_products")
    order = get_object_or_404(Order,id=order_id)

    if order.customer != request.user:

        orders = Order.objects.filter(is_deleted=False,customer=request.user)
        return render(request,'bazaar/orders.html',
                        {'error':"You can not delete this order.",
                        'orders':orders})
    
    if request.method == 'POST':
        order.is_deleted = True
        order.save()
        return redirect("view_orders")
    return redirect("view_orders")





# @login_required
# def confirm_checkout(request):
#     if request.user.account.role != 'customer':
#         return redirect("view_products")
    
#     if request.method != "POST":
#         return redirect("view_cart")

#     cart, created = Cart.objects.get_or_create(
#         customer=request.user
#     )

#     items = CartItem.objects.filter(cart=cart)

#     if not items.exists():
#         return redirect("view_cart")
    
#     coupon_code = request.session.get('coupon_code')
#     discount = Decimal(
#         request.session.get('discount', '0')
#     )

#     coupon = None

#     if coupon_code:
#         coupon = Coupon.objects.filter(
#             code=coupon_code,
#             valid=True
#         ).first()

#     total = sum(
#         item.product.price * item.quantity
#         for item in items
#     )

#     final_total = total - discount
#     with transaction.atomic():

#         order = Order.objects.create(
#             customer=request.user,
#             coupon=coupon,
#             total=total,
#             discount=discount,
#             final_total=final_total
#         )
#         for item in items:
#             OrderItem.objects.create(
#                 order=order,
#                 product=item.product,
#                 quantity=item.quantity,
#                 price=item.product.price,
#             )

#         items.delete()
#     request.session.pop('coupon_code', None)
#     request.session.pop('discount', None)

#     return redirect("view_orders")
