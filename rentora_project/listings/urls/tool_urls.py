from django.urls import path

from listings.views.tool_views import tool_detail_view, toggle_wishlist_view

urlpatterns = [
    path('tools/<int:pk>/',          tool_detail_view,    name='detail'),
    path('tools/<int:pk>/wishlist/', toggle_wishlist_view, name='toggle_wishlist'),
]
