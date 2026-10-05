from django.urls import path,include
from . import views
from rest_framework.routers import DefaultRouter



router = DefaultRouter()
router.register(r"products",views.ProductViewSet)
router.register(r"suppliers",views.SupplierViewSet,basename="suppliers")
router.register(r"cart/items",views.CartItemViewSet,basename="cartitem")
router.register(r"cart",views.CartViewSet,basename="cart")


urlpatterns=[
    path('login/',views.UserLogin.as_view()),
    path('logout/',views.UserLogout.as_view()),
    path('signup/',views.UserSignup.as_view()),
    path("",include(router.urls)),

]