from django.urls import path

from listings.views.booking_views import create_booking_view

urlpatterns = [
    path('tools/<int:pk>/book/', create_booking_view, name='create_booking'),
]
