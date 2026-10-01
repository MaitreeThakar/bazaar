from django.urls import path,include
from . import views
from rest_framework.routers import DefaultRouter



router = DefaultRouter()
router.register(r"products",views.ProductViewSet)
router.register(r"suppliers",views.SupplierViewSet,basename="suppliers")


urlpatterns=[
    path("",include(router.urls)),

]