from django.urls import path

from listings.views.booking_views import (
    create_booking_view, dashboard,
    approve_booking, reject_booking,
    request_return, confirm_return, dispute_return,
    cancel_booking, document_pickup,
    booking_confirmation_view,
	report_user
)
from listings.views.payment_views import (
    payout_setup, start_payment, payment_callback, lahza_webhook,
)

urlpatterns = [
    path('tools/<int:pk>/book/',                  create_booking_view,      name='create_booking'),
    path('dashboard/',                            dashboard,                name='dashboard'),
    path('approve/<int:booking_id>/',             approve_booking,          name='approve_booking'),
    path('reject/<int:booking_id>/',              reject_booking,           name='reject_booking'),
    path('return/request/<int:booking_id>/',      request_return,           name='request_return'),
    path('return/confirm/<int:booking_id>/',      confirm_return,           name='confirm_return'),
    path('return/dispute/<int:booking_id>/',      dispute_return,           name='dispute_return'),
    path('booking/<int:booking_id>/cancel/',      cancel_booking,           name='cancel_booking'),
    path('booking/<int:booking_id>/condition/',   document_pickup,          name='document_pickup'),
    path('booking/<int:booking_id>/confirm/',     booking_confirmation_view,name='booking_confirmation'),
	path('report/<int:user_id>/',                  report_user,              name='report_user'),

    # ── Payments (Lahza) ──────────────────────────────────────────────
    path('payouts/setup/',                        payout_setup,             name='payout_setup'),
    path('booking/<int:booking_id>/pay/',         start_payment,            name='payment'),
    path('booking/<int:booking_id>/pay/callback/', payment_callback,        name='payment_callback'),
    path('payments/lahza/webhook/',               lahza_webhook,            name='lahza_webhook'),
    # Alias without the trailing slash — POST is not auto-redirected by Django,
    # so accept both spellings of the webhook URL the gateway may call.
    path('payments/lahza/webhook',                lahza_webhook),
]
