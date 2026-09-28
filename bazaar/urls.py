from django.urls import path
from . import views

urlpatterns=[
    # path('', views.user_login, name='login'),
    # path('login/', views.user_login, name='login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    # path('signup/', views.user_signup, name='signup'),
    # path('logout/', views.user_logout, name='logout'),
    # path('products/', views.view_products, name='view_products'),
    # path('add-product/', views.add_product, name='add_product'),
    # path('update-product/<int:product_id>/', views.update_product, name='update_product'),
    # path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('product-action/<int:product_id>/',views.product_action,name="product_action"),
    # path('update-cart-item/<int:item_id>/',views.update_cart_item,name="update_cart_item"),
    # path('remove-cart-item/<int:item_id>/',views.remove_cart_item,name="remove_cart_item"),
    # path('view-cart/',views.view_cart,name="view_cart"),
    path('checkout/',views.checkout,name="checkout"),
    path('create-razorpay-order/',views.create_razorpay_order,name="create_razorpay_order"),
    path('payment-success/',views.payment_success,name="payment_success"),
   # path('confirm-checkout/',views.confirm_checkout,name='confirm_checkout'),
    # path('orders/', views.view_orders, name='view_orders'),
    # path('delete-order/<int:order_id>/', views.delete_order, name='delete_order'),
    # path('supplier-orders/', views.supplier_orders, name='supplier_orders'),

    path('', views.UserLoginView.as_view(), name='login'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('signup/', views.UserSignupView.as_view(), name='signup'),



    path('products/', views.ProductListView.as_view(), name='view_products'),
    path('add-product/', views.ProductCreateView.as_view(), name='add_product'),
    path('update-product/<int:product_id>/', views.ProductUpdateView.as_view(), name='update_product'),
    path('delete-product/<int:product_id>/', views.ProductDeleteView.as_view(), name='delete_product'),

    path('orders/', views.OrderListView.as_view(), name='view_orders'),
    path('delete-order/<int:order_id>/', views.OrderDeleteView.as_view(), name='delete_order'),
    path('supplier-orders/', views.OrderSupplierView.as_view(), name='supplier_orders'),

    path('view-cart/',views.CartListView.as_view(),name="view_cart"),
    path('update-cart-item/<int:item_id>/',views.CartUpdateView.as_view(),name="update_cart_item"),
    path('remove-cart-item/<int:item_id>/',views.CartItemDeleteView.as_view(),name="remove_cart_item"),


]