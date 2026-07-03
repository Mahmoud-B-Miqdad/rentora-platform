from django.urls import path

from listings.views.booking_views import *
urlpatterns = [
    path('tools/<int:pk>/book/',                  create_booking_view,      name='create_booking'),
    path('dashboard/',                            dashboard,                name='dashboard'),
    path('approve/<int:booking_id>/',             approve_booking,          name='approve_booking'),
    path('reject/<int:booking_id>/',              reject_booking,           name='reject_booking'),
    path('return/request/<int:booking_id>/',      request_return,           name='request_return'),
    path('return/confirm/<int:booking_id>/',      confirm_return,           name='confirm_return'),
    path('return/dispute/<int:booking_id>/',      dispute_return,           name='dispute_return'),
    path('booking/<int:booking_id>/confirm/',     booking_confirmation_view,name='booking_confirmation'),
    path('booking/<int:booking_id>/pay/',         payment_view,             name='payment'),
    path('booking/<int:booking_id>/pay/confirm/', confirm_payment_view,     name='confirm_payment'),
    path('booking/<int:booking_id>/pay/success/', payment_success_view,     name='payment_success'),
    path("booking/<int:booking_id>/checkout/",    create_checkout_session,  name="checkout"),
    path("stripe/webhook/",                       stripe_webhook,           name="stripe_webhook"),]
