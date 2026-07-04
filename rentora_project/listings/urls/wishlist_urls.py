from django.urls import path
from listings.views.wishlist_views import wishlist_view

urlpatterns = [
    path('wishlist/', wishlist_view, name='wishlist'),
]