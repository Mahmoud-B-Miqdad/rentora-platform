from django.urls import path

from listings.views.booking_views import (
    create_booking_view, dashboard,
    approve_booking, reject_booking,
    request_return, confirm_return, dispute_return,
    booking_confirmation_view,
    payment_view, payment_success_view,
    stripe_webhook,
	report_user
)

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
    path('booking/<int:booking_id>/pay/success/', payment_success_view,     name='payment_success'),
	path('report/<int:user_id>/',                  report_user,              name='report_user'),
    path('tools/<int:pk>/book/',                  create_booking_view,       name='create_booking'),
    path('stripe/webhook/',                       stripe_webhook,            name='stripe_webhook'),
]
