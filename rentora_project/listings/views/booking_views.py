from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Prefetch, Sum, Count, Q
from django.utils     import timezone
from django.conf      import settings
from django.urls      import reverse
from django.contrib   import messages
from django.views.decorators.csrf import csrf_exempt
from django.http      import HttpResponse
import stripe

from listings.models import Tool, Booking, ToolImage, Review, BookingStatus, DepositDispute
from listings.services.email_service import (
    send_booking_requested_emails,
    send_booking_approved_email,
    send_payment_received_emails,
    send_return_confirmation_request_email,
    send_booking_cancelled_email,
    send_dispute_opened_emails,
)
from listings.models.message import Conversation, Message
from listings.models.notification import Notification, NotificationType
from users.models    import User
from django.contrib  import messages
from listings.models.report import Report


def _save_condition_photos(booking, user, phase, files, limit=8):
    """Persist uploaded handover photos (images only, ≤8 MB). Returns count saved."""
    from listings.models import RentalConditionPhoto
    saved = 0
    for f in files[:limit]:
        if not getattr(f, "content_type", "").startswith("image/"):
            continue
        if f.size > 8 * 1024 * 1024:
            continue
        RentalConditionPhoto.objects.create(
            booking=booking, phase=phase, uploaded_by=user, image=f,
        )
        saved += 1
    return saved


def create_booking_view(request, pk):
    """
    POST-only view: validates dates, creates a Booking, redirects back.
    Requires an authenticated session.
    """
    if request.method != 'POST':
        return redirect('listings:tools:detail', pk=pk)

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('users:login')

    renter = get_object_or_404(User, pk=user_id)
    tool   = get_object_or_404(Tool, pk=pk, is_available=True)

    errors = Booking.objects.register_validator(request.POST, renter, tool)
    if errors:
        first_error = next(iter(errors.values()))
        request.session['booking_error'] = first_error
        return redirect(f'/{pk}/')

    booking = Booking.objects.create_booking(request.POST, renter, tool)

    Notification.objects.create_for(
        user=tool.owner,
        notification_type=NotificationType.BOOKING_RECEIVED,
        message=f"{renter.name} requested to rent your \"{tool.title}\" "
                f"({booking.start_date} → {booking.end_date}).",
        booking=booking,
    )
    send_booking_requested_emails(booking)

    return redirect('listings:booking_confirmation', booking_id=booking.id)

def login_required_session(view_func):
    """Custom login check using session."""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('users:login')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required_session
def dashboard(request):
    user = User.objects.get(id=request.session['user_id'])


    primary_img_qs  = ToolImage.objects.filter(is_primary=True)
    tool_img_pf     = Prefetch('tool__images', queryset=primary_img_qs, to_attr='primary_images')
    my_reviews_pf   = Prefetch('reviews', queryset=Review.objects.filter(reviewer=user), to_attr='my_reviews')

    # Booking Requests
    pending_requests = Booking.objects.filter(
        tool__owner=user, status='pending'
    ).select_related('tool', 'tool__category', 'renter').prefetch_related(tool_img_pf).order_by('-created_at')

    approved_requests = Booking.objects.filter(
        tool__owner=user, status__in=['payment_pending', 'approved', 'confirmed', 'return_pending']
    ).select_related('tool', 'renter').prefetch_related(tool_img_pf).order_by('-created_at')

    rejected_requests = Booking.objects.filter(
        tool__owner=user, status='rejected'
    ).select_related('tool', 'renter').prefetch_related(tool_img_pf).order_by('-created_at')

    completed_requests = Booking.objects.filter(
        tool__owner=user, status='completed'
    ).select_related('tool', 'renter').prefetch_related(tool_img_pf, my_reviews_pf).order_by('-created_at')
    completed_requests = list(completed_requests)
    for b in completed_requests:
        b.reviewed_types = {r.review_type for r in b.my_reviews}

    # My Rentals
    pending_my_rentals = Booking.objects.filter(
        renter=user, status__in=['pending', 'payment_pending']
    ).select_related('tool', 'tool__owner', 'tool__category').prefetch_related(tool_img_pf).order_by('-created_at')

    current_rentals = Booking.objects.filter(
        renter=user, status__in=['approved', 'confirmed', 'return_pending']
    ).select_related('tool', 'tool__owner').prefetch_related(tool_img_pf).order_by('start_date')

    # 'cancelled' belongs here too — without it a booking the renter cancels
    # disappears from their dashboard entirely.
    booking_history = Booking.objects.filter(
        renter=user, status__in=['completed', 'rejected', 'cancelled']
    ).select_related('tool', 'tool__owner').prefetch_related(tool_img_pf, my_reviews_pf).order_by('-created_at')
    booking_history = list(booking_history)
    for b in booking_history:
        b.reviewed_types = {r.review_type for r in b.my_reviews}

    # Stats
    my_tools_count = Tool.objects.filter(owner=user).count()
    active_rentals = current_rentals.count()
    total_earnings = Booking.objects.filter(
        tool__owner=user, status='completed'
    ).aggregate(total=Sum('total_price'))['total'] or 0

    all_tools = Tool.objects.filter(owner=user).select_related('category').prefetch_related(
        Prefetch('images', queryset=primary_img_qs, to_attr='primary_images')
    ).order_by('-id')

    recent_tools = all_tools[:3]

    # Conversations inbox
    last_msg_pf = Prefetch(
        'messages',
        queryset=Message.objects.select_related('sender').order_by('-created_at'),
        to_attr='all_messages',
    )
    conv_img_pf = Prefetch(
        'booking__tool__images',
        queryset=ToolImage.objects.filter(is_primary=True),
        to_attr='primary_images',
    )
    conversations = list(
        Conversation.objects.for_user(user)
        .prefetch_related(last_msg_pf, conv_img_pf)
        .annotate(
            unread_count=Count(
                'messages',
                filter=Q(messages__is_read=False) & ~Q(messages__sender=user),
            )
        )
    )
    for conv in conversations:
        conv.last_msg = conv.all_messages[0] if conv.all_messages else None
        conv.other    = conv.other_participant(user)

    total_unread = sum(c.unread_count for c in conversations)

    context = {
        'user'               : user,
        'pending_requests'   : pending_requests,
        'approved_requests'  : approved_requests,
        'rejected_requests'  : rejected_requests,
        'completed_requests' : completed_requests,
        'pending_my_rentals' : pending_my_rentals,
        'current_rentals'    : current_rentals,
        'booking_history'    : booking_history,
        'my_tools_count'     : my_tools_count,
        'active_rentals'     : active_rentals,
        'total_earnings'     : total_earnings,
        'all_tools'          : all_tools,
        'recent_tools'       : recent_tools,
        'conversations'      : conversations,
        'total_unread'       : total_unread,
        'active_tab'         : request.GET.get('tab', 'overview'),
        'today'              : timezone.now().date(),
    }
    return render(request, 'listings/dashboard/dashboard.html', context)


@login_required_session
def approve_booking(request, booking_id):
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, tool__owner=user)

    if booking.status == 'pending':
        booking.status = 'payment_pending'
        booking.save()

        Notification.objects.create_for(
            user=booking.renter,
            notification_type=NotificationType.BOOKING_APPROVED,
            message=f"Your booking for \"{booking.tool.title}\" was approved! "
                    f"Complete your payment to confirm the rental.",
            booking=booking,
        )
        send_booking_approved_email(booking)

        messages.success(request, "Booking approved. Renter has been notified to complete payment.")
    return redirect('/dashboard/?tab=booking-requests&subtab=btab-approved')


@login_required_session
def reject_booking(request, booking_id):
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, tool__owner=user)

    if booking.status == 'pending':
        booking.status = 'rejected'
        booking.save()

        Notification.objects.create_for(
            user=booking.renter,
            notification_type=NotificationType.BOOKING_REJECTED,
            message=f"Your booking request for \"{booking.tool.title}\" "
                    f"({booking.start_date} → {booking.end_date}) was not approved.",
            booking=booking,
        )

        messages.success(request, "Booking rejected.")
    return redirect('/dashboard/?tab=booking-requests&subtab=btab-rejected')


stripe.api_key = settings.STRIPE_SECRET_KEY


def payment_view(request, booking_id):
    """Redirect the renter to the Stripe-hosted checkout page."""
    booking = get_object_or_404(Booking, id=booking_id, status='payment_pending')

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        client_reference_id=str(booking_id),
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': booking.tool.title},
                'unit_amount': int(booking.total_price * 100),
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri(
            reverse('listings:payment_success', args=[booking.id])
        ),
        cancel_url=request.build_absolute_uri(
            reverse('listings:payment', args=[booking.id])
        ),
    )

    return redirect(session.url)

@csrf_exempt
def stripe_webhook(request):
    payload    = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session    = event['data']['object']
        booking_id = session.get('client_reference_id')
        if booking_id:
            try:
                booking = Booking.objects.get(id=int(booking_id))
                if booking.status == 'payment_pending':
                    booking.status = 'confirmed'
                    booking.save()
                    Notification.objects.create_for(
                        user=booking.tool.owner,
                        notification_type=NotificationType.PAYMENT_RECEIVED,
                        message=f"{booking.renter.name} completed payment for \"{booking.tool.title}\".",
                        booking=booking,
                    )
                    send_payment_received_emails(booking)
            except Booking.DoesNotExist:
                pass

    return HttpResponse(status=200)


def payment_success_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Fallback in case the Stripe webhook hasn't fired yet when the user
    # lands on this page (network delay / webhook misconfiguration).
    if booking.status == 'payment_pending':
        booking.status = 'confirmed'
        booking.save()
        Notification.objects.create_for(
            user=booking.tool.owner,
            notification_type=NotificationType.PAYMENT_RECEIVED,
            message=f"{booking.renter.name} completed payment for \"{booking.tool.title}\".",
            booking=booking,
        )
        send_payment_received_emails(booking)

    user = User.objects.filter(id=request.session.get('user_id')).first()

    return render(request, "listings/booking/payment_success.html", {
        "booking": booking,
        "user":    user,
    })



@login_required_session
def booking_confirmation_view(request, booking_id):
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, renter=user)
    return render(request, 'listings/booking/booking_confirmation.html', {
        'booking': booking,
        'user':    user,
    })


@login_required_session
def request_return(request, booking_id):
    """
    Owner marks the tool as returned — awaits renter confirmation.

    GET  → a confirmation page where the owner can (optionally) attach photos of
           the tool's condition at return. These are the "after" record for a
           possible dispute.
    POST → save any photos, then transition to return_pending.
    """
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(
        Booking.objects.select_related('tool', 'renter'),
        id=booking_id, tool__owner=user,
    )

    if booking.status not in ('approved', 'confirmed'):
        messages.error(request, "This rental cannot be marked as returned.")
        return redirect('/dashboard/?tab=booking-requests&subtab=btab-approved')

    if request.method != 'POST':
        return render(request, 'listings/booking/condition_photos.html', {
            'booking': booking,
            'phase': 'return',
        })

    # Photos are mandatory — the "after" record must exist before the tool can
    # be marked returned, so both parties always have documented evidence.
    saved = _save_condition_photos(booking, user, 'return', request.FILES.getlist('photos'))
    if not saved:
        return render(request, 'listings/booking/condition_photos.html', {
            'booking': booking,
            'phase': 'return',
            'error': "Please add at least one photo of the tool's condition to mark it as returned.",
        })

    booking.status = 'return_pending'
    booking.actual_return_date  = timezone.now().date()
    booking.return_requested_at = timezone.now()
    booking.save()

    Notification.objects.create_for(
        user=booking.renter,
        notification_type=NotificationType.RETURN_REQUESTED,
        message=f"The owner marked \"{booking.tool.title}\" as returned. "
                f"Please confirm or dispute the return in your dashboard.",
        booking=booking,
    )
    send_return_confirmation_request_email(booking)

    messages.success(request, "Return request sent. Waiting for renter to confirm.")
    return redirect('/dashboard/?tab=booking-requests&subtab=btab-approved')


@login_required_session
def document_pickup(request, booking_id):
    """
    Renter documents the tool's condition when they pick it up (the "before"
    record). Available while the rental is active. Optional but encouraged.
    """
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(
        Booking.objects.select_related('tool', 'tool__owner'),
        id=booking_id, renter=user,
    )

    if booking.status not in ('approved', 'confirmed', 'return_pending'):
        messages.error(request, "You can only document condition during an active rental.")
        return redirect('/dashboard/?tab=my-rentals&subtab=rtab-active')

    if request.method != 'POST':
        return render(request, 'listings/booking/condition_photos.html', {
            'booking': booking,
            'phase': 'pickup',
        })

    n = _save_condition_photos(booking, user, 'pickup', request.FILES.getlist('photos'))
    if n:
        messages.success(request, f"Saved {n} condition photo(s). These protect you if a dispute arises.")
    else:
        messages.error(request, "Please choose at least one photo to upload.")
    return redirect('/dashboard/?tab=my-rentals&subtab=rtab-active')


@login_required_session
def confirm_return(request, booking_id):
    """Renter confirms they have returned the tool → booking completed."""
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, renter=user)

    # Pickup documentation is mandatory: a rental can't be closed unless the
    # renter recorded the tool's condition, so both sides always have evidence.
    if booking.status == 'return_pending' and not booking.condition_photos.filter(phase='pickup').exists():
        messages.error(
            request,
            "Please document the tool's condition first — this is required to confirm the return."
        )
        return redirect('listings:document_pickup', booking_id=booking.id)

    if booking.status == 'return_pending':
        actual_return = booking.actual_return_date or timezone.now().date()
        actual_days   = max((actual_return - booking.start_date).days, 1)
        new_total     = Decimal(actual_days) * Decimal(str(booking.tool.daily_rate))

        overdue_days       = max((actual_return - booking.end_date).days, 0)
        early_return_days  = max((booking.end_date - actual_return).days, 0)

        booking.total_price         = new_total
        booking.actual_return_date  = actual_return
        booking.status              = 'completed'
        booking.return_requested_at = None
        booking.save()

        if overdue_days:
            owner_msg  = (f"{booking.renter.name} returned \"{booking.tool.title}\" "
                          f"{overdue_days} day(s) late — final charge: ${new_total}.")
            renter_msg = (f"Return confirmed for \"{booking.tool.title}\". "
                          f"{overdue_days} overdue day(s) were added — final charge: ${new_total}.")
            messages.success(
                request,
                f"Return confirmed. {overdue_days} overdue day(s) added — "
                f"final total: ${new_total}."
            )
        elif early_return_days:
            owner_msg  = (f"{booking.renter.name} returned \"{booking.tool.title}\" "
                          f"{early_return_days} day(s) early — final charge: ${new_total}.")
            renter_msg = (f"Return confirmed for \"{booking.tool.title}\". "
                          f"Early return saved you {early_return_days} day(s) — final charge: ${new_total}.")
            messages.success(
                request,
                f"Return confirmed. Early return by {early_return_days} day(s) — "
                f"you were only charged for {actual_days} day(s): ${new_total}."
            )
        else:
            owner_msg  = (f"{booking.renter.name} confirmed the return of "
                          f"\"{booking.tool.title}\" — rental completed.")
            renter_msg = (f"Return confirmed for \"{booking.tool.title}\" — "
                          f"rental completed. Thank you!")
            messages.success(request, "Return confirmed. Rental completed successfully!")

        Notification.objects.create_for(
            user=booking.tool.owner,
            notification_type=NotificationType.RETURN_CONFIRMED,
            message=owner_msg,
            booking=booking,
        )
        Notification.objects.create_for(
            user=booking.renter,
            notification_type=NotificationType.RETURN_CONFIRMED,
            message=renter_msg,
            booking=booking,
        )

    return redirect('/dashboard/?tab=my-rentals&subtab=rtab-history')


@login_required_session
def dispute_return(request, booking_id):
    """
    Renter contests the owner's "Mark as Returned".

    GET  → show the dispute form (reason + optional photo/video evidence).
    POST → record a DepositDispute for staff review, hold the rental, and
           notify both sides. Late fees stop while a dispute is open because
           the booking leaves the return_pending state.
    """
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(
        Booking.objects.select_related('tool', 'tool__owner'),
        id=booking_id, renter=user,
    )

    if booking.status != 'return_pending':
        messages.error(request, "This rental is not awaiting a return confirmation.")
        return redirect('/dashboard/?tab=my-rentals&subtab=rtab-active')

    if hasattr(booking, 'deposit_dispute'):
        messages.info(request, "A dispute is already open for this rental.")
        return redirect('/dashboard/?tab=my-rentals&subtab=rtab-active')

    if request.method != 'POST':
        return render(request, 'listings/booking/dispute_form.html', {'booking': booking})

    reason = request.POST.get('reason', '').strip()
    if len(reason) < 10:
        return render(request, 'listings/booking/dispute_form.html', {
            'booking': booking,
            'error': "Please describe what happened in at least 10 characters.",
            'reason': reason,
        })

    # The pot in dispute is the money actually collected from the renter, not
    # the tool's nominal deposit — no deposit is separately held or captured,
    # so the rental payment is the only balance staff can redistribute.
    breakdown = getattr(booking, 'payment_breakdown', None)
    amount_in_dispute = (
        breakdown.total_charged_to_renter if breakdown else booking.total_price
    )

    dispute = DepositDispute.objects.create(
        booking=booking,
        deposit_amount=amount_in_dispute,
        initiated_by='renter',
        reason=reason,
        dispute_evidence=request.FILES.get('evidence'),
        status='open',
    )

    # Hold the rental: back out of return_pending so no late fees accrue
    # while staff review the case.
    booking.status = 'confirmed'
    booking.return_requested_at = None
    booking.save(update_fields=['status', 'return_requested_at', 'updated_at'])

    Notification.objects.create_for(
        user=booking.tool.owner,
        notification_type=NotificationType.RETURN_REQUESTED,
        message=f"{user.name} disputed the return of \"{booking.tool.title}\". "
                f"Rentora staff will review it.",
        booking=booking,
    )
    send_dispute_opened_emails(dispute)

    messages.warning(
        request,
        "Dispute submitted. Our staff will review it and email you the decision."
    )
    return redirect('/dashboard/?tab=my-rentals&subtab=rtab-active')

@login_required_session
def cancel_booking(request, booking_id):
    """
    Renter cancels their own booking.

    Allowed only while no money has been captured — i.e. the request is still
    awaiting the owner's decision (pending) or approved but unpaid
    (payment_pending / approved). Once a booking is `confirmed` the renter has
    paid, so cancellation has to go through support to handle the refund; we
    deliberately do not let either side cancel a paid rental unilaterally.
    """
    if request.method != 'POST':
        return redirect('/dashboard/?tab=my-rentals&subtab=rtab-awaiting')

    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, renter=user)

    cancellable = {
        BookingStatus.PENDING,
        BookingStatus.PAYMENT_PENDING,
        BookingStatus.APPROVED,
    }
    if booking.status not in cancellable:
        messages.error(
            request,
            "This booking can no longer be cancelled. Please contact support."
        )
        return redirect('/dashboard/?tab=my-rentals&subtab=rtab-awaiting')

    booking.status = BookingStatus.CANCELLED
    booking.save(update_fields=['status', 'updated_at'])

    Notification.objects.create_for(
        user=booking.tool.owner,
        notification_type=NotificationType.BOOKING_REJECTED,
        message=f"{user.name} cancelled their booking for \"{booking.tool.title}\" "
                f"({booking.start_date} → {booking.end_date}). "
                f"Those dates are free again.",
        booking=booking,
    )
    send_booking_cancelled_email(booking)

    messages.success(request, "Booking cancelled. The owner has been notified.")
    return redirect('/dashboard/?tab=my-rentals&subtab=rtab-history')


@login_required_session
def report_user(request, user_id):
    reporter = User.objects.get(id=request.session['user_id'])
    reported = get_object_or_404(User, id=user_id)

    if reporter == reported:
        messages.error(request, "You cannot report yourself.")
        return redirect('users:profile_user', user_id=user_id)

    already = Report.objects.filter(
        reporter=reporter,
        reported=reported
    ).exists()

    if request.method == 'POST':
        if already:
            messages.error(request, "You have already reported this user.")
            return redirect('users:profile_user', user_id=user_id)

        reason = request.POST.get('reason')
        details = request.POST.get('details', '')

        if reason not in dict(Report.REASON_CHOICES):
            messages.error(request, "Please select a valid reason.")
            return redirect('listings:report_user', user_id=user_id)

        Report.objects.create(
            reporter=reporter,
            reported=reported,
            reason=reason,
            details=details,
        )

        messages.success(request, "Report submitted. Our team will review it.")
        return redirect('users:profile_user', user_id=user_id)

    # GET request → اعرض صفحة الريبورت
    if already:
        messages.info(request, "You have already reported this user.")
        return redirect('users:profile_user', user_id=user_id)

    return render(request, 'listings/report/report_user.html', {
        'profile_user': reported,
    })