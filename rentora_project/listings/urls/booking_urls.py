from django.urls import path

from listings.views.booking_views import create_booking_view
from listings.views.booking_views import (
    dashboard,
    create_booking,
    approve_booking,
    reject_booking,
)
urlpatterns = [
    path('tools/<int:pk>/book/', create_booking_view, name='create_booking'),
	path('dashboard/',                    dashboard,       name='dashboard'),
    path('book/<int:tool_id>/',           create_booking,  name='create_booking'),
    path('approve/<int:booking_id>/',     approve_booking, name='approve_booking'),
    path('reject/<int:booking_id>/',      reject_booking,  name='reject_booking'),

]
