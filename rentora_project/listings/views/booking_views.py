from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Prefetch, Sum
from django.utils     import timezone

from listings.models import Tool, Booking, ToolImage, Review
from users.models    import User
from django.contrib  import messages


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
        return redirect('listings:tools:detail', pk=pk)

    booking = Booking.objects.create_booking(request.POST, renter, tool)
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
        tool__owner=user, status__in=['payment_pending', 'approved', 'return_pending']
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
        renter=user, status__in=['approved', 'return_pending']
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
        messages.success(request, "Booking approved. Renter has been notified to complete payment.")
    return redirect('/dashboard/?tab=booking-requests')


@login_required_session
def reject_booking(request, booking_id):
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, tool__owner=user)

    if booking.status == 'pending':
        booking.status = 'rejected'
        booking.save()
        messages.success(request, "Booking rejected.")
    return redirect('/dashboard/?tab=booking-requests')


@login_required_session
def payment_view(request, booking_id):
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, renter=user, status='payment_pending')
    return render(request, 'listings/booking/payment.html', {'booking': booking, 'user': user})


@login_required_session
def confirm_payment_view(request, booking_id):
    if request.method != 'POST':
        return redirect('listings:payment', booking_id=booking_id)

    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, renter=user, status='payment_pending')
    booking.status = 'approved'
    booking.save()
    return redirect('listings:payment_success', booking_id=booking.id)


@login_required_session
def payment_success_view(request, booking_id):
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, renter=user, status='approved')
    return render(request, 'listings/booking/payment_success.html', {'booking': booking, 'user': user})


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

    if booking.status == 'approved':
        booking.status = 'return_pending'
        booking.return_requested_at = timezone.now()
        booking.save()
        messages.success(request, "Return request sent. Waiting for renter to confirm.")
    return redirect('/dashboard/?tab=booking-requests')


@login_required_session
def confirm_return(request, booking_id):
    """Renter confirms they have returned the tool → booking completed."""
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, renter=user)

    if booking.status == 'return_pending':
        booking.status = 'completed'
        booking.return_requested_at = None
        booking.save()
        messages.success(request, "Return confirmed. Rental completed successfully!")
    return redirect('/dashboard/?tab=my-rentals')


@login_required_session
def dispute_return(request, booking_id):
    """Renter disputes the return — booking goes back to approved for review."""
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, renter=user)

    if booking.status == 'return_pending':
        booking.status = 'approved'
        booking.return_requested_at = None
        booking.save()
        messages.warning(request, "Return disputed. The owner has been notified to re-confirm.")
    return redirect('/dashboard/?tab=my-rentals')
