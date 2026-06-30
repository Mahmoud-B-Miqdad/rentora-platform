from django.urls import path

from listings.views.booking_views import *
urlpatterns = [
    path('tools/<int:pk>/book/',              create_booking_view,       name='create_booking'),
    path('dashboard/',                        dashboard,                  name='dashboard'),
    path('approve/<int:booking_id>/',         approve_booking,            name='approve_booking'),
    path('reject/<int:booking_id>/',          reject_booking,             name='reject_booking'),
    path('complete/<int:booking_id>/',        complete_booking,           name='complete_booking'),
    path('booking/<int:booking_id>/confirm/', booking_confirmation_view,  name='booking_confirmation'),
    path('booking/<int:booking_id>/pay/',     payment_view,               name='payment'),
    path('booking/<int:booking_id>/pay/confirm/', confirm_payment_view,   name='confirm_payment'),
    path('booking/<int:booking_id>/pay/success/', payment_success_view,   name='payment_success'),
]
