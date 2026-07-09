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

from listings.models import Tool, Booking, ToolImage, Review
from listings.models.message import Conversation, Message
from listings.models.notification import Notification, NotificationType
from users.models    import User
from django.contrib  import messages
from listings.models.report import Report


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

    booking_history = Booking.objects.filter(
        renter=user, status__in=['completed', 'rejected']
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

        messages.success(request, "Booking approved. Renter has been notified to complete payment.")
    return redirect('/dashboard/?tab=booking-requests')


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
    return redirect('/dashboard/?tab=booking-requests')


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
    """Owner marks the tool as returned — awaits renter confirmation."""
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, tool__owner=user)

    if booking.status in ('approved', 'confirmed'):
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

        messages.success(request, "Return request sent. Waiting for renter to confirm.")
    return redirect('/dashboard/?tab=booking-requests')


@login_required_session
def confirm_return(request, booking_id):
    """Renter confirms they have returned the tool → booking completed."""
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, renter=user)

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

    return redirect('/dashboard/?tab=my-rentals')


@login_required_session
def dispute_return(request, booking_id):
    """Renter disputes the return — booking goes back to approved for review."""
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, renter=user)

    if booking.status == 'return_pending':
        booking.status = 'confirmed'
        booking.return_requested_at = None
        booking.save()
        messages.warning(request, "Return disputed. The owner has been notified to re-confirm.")
    return redirect('/dashboard/?tab=my-rentals')

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