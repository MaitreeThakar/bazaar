from django.urls import path
from . import views


urlpatterns=[
    path("", views.api_root),
    # path('list/',views.product_list,name=''),
    path('list/class/',views.ProductList.as_view(),name="products"),
    path('detail/<int:pk>/',views.ProductDetail.as_view(),name = "product-detail"),
    path("users/", views.UserList.as_view(),name="users"),
    path("users/<int:pk>/", views.UserDetail.as_view(),name='user-detail'),
]