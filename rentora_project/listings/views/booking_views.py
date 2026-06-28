from django.shortcuts import  render, redirect, get_object_or_404

from listings.models import Tool, Booking
from users.models    import User
from django.contrib import messages
from datetime import date


def create_booking_view(request, pk):
    """
    POST-only view: validates dates, creates a Booking, redirects back.
    Requires an authenticated session.
    """
    if request.method != 'POST':
        return redirect('listings:detail', pk=pk)

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('users:login')

    renter = get_object_or_404(User, pk=user_id)
    tool   = get_object_or_404(Tool, pk=pk, is_available=True)

    errors = Booking.objects.register_validator(request.POST, renter, tool)
    if errors:
        # Store first error in session so detail page can display it
        first_error = next(iter(errors.values()))
        request.session['booking_error'] = first_error
        return redirect('listings:detail', pk=pk)

    Booking.objects.create_booking(request.POST, renter, tool)
    request.session['booking_success'] = (
        f'Booking request sent for “{tool.title}”. '
        'The owner will confirm shortly.'
    )
    return redirect('listings:detail', pk=pk)
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

    # Booking Requests 
    pending_requests   = Booking.objects.filter(
        tool__owner=user, status='pending'
    ).select_related('tool', 'renter').order_by('-created_at')

    approved_requests  = Booking.objects.filter(
        tool__owner=user, status='approved'
    ).select_related('tool', 'renter').order_by('-created_at')

    rejected_requests  = Booking.objects.filter(
        tool__owner=user, status='rejected'
    ).select_related('tool', 'renter').order_by('-created_at')

    completed_requests = Booking.objects.filter(
        tool__owner=user, status='completed'
    ).select_related('tool', 'renter').order_by('-created_at')

    # My Rentals 
    current_rentals = Booking.objects.filter(
        renter=user,
        status='approved',
        end_date__gte=date.today()
    ).select_related('tool').order_by('start_date')

    booking_history = Booking.objects.filter(
        renter=user,
        status__in=['completed', 'rejected']
    ).select_related('tool').order_by('-created_at')

    # Stats
    my_tools_count   = Tool.objects.filter(owner=user).count()
    active_rentals   = current_rentals.count()

    context = {
        'user'               : user,
        'pending_requests'   : pending_requests,
        'approved_requests'  : approved_requests,
        'rejected_requests'  : rejected_requests,
        'completed_requests' : completed_requests,
        'current_rentals'    : current_rentals,
        'booking_history'    : booking_history,
        'my_tools_count'     : my_tools_count,
        'active_rentals'     : active_rentals,
        'active_tab'         : request.GET.get('tab', 'overview'),
    }
    return render(request, 'listings/dashboard/dashboard.html', context)


@login_required_session
def approve_booking(request, booking_id):
    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, tool__owner=user)

    if booking.status == 'pending':
        booking.status = 'approved'
        booking.save()
        messages.success(request, "Booking approved.")
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
def create_booking(request, tool_id):
    user = User.objects.get(id=request.session['user_id'])
    tool = get_object_or_404(Tool, id=tool_id, is_available=True)

    if tool.owner == user:
        messages.error(request, "You cannot book your own tool.")
        return redirect('tool_detail', pk=tool_id)

    if request.method == 'POST':
        start_str = request.POST.get('start_date')
        end_str   = request.POST.get('end_date')

        if not start_str or not end_str:
            messages.error(request, "Please select both dates.")
            return redirect('tool_detail', pk=tool_id)

        start_date = date.fromisoformat(start_str)
        end_date   = date.fromisoformat(end_str)

        if start_date < date.today():
            messages.error(request, "Start date cannot be in the past.")
            return redirect('tool_detail', pk=tool_id)

        if start_date >= end_date:
            messages.error(request, "End date must be after start date.")
            return redirect('tool_detail', pk=tool_id)

        conflict = Booking.objects.filter(
            tool=tool,
            status__in=['pending', 'approved'],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()

        if conflict:
            messages.error(request, "This tool is already booked for the selected dates.")
            return redirect('tool_detail', pk=tool_id)

        num_days    = (end_date - start_date).days
        total_price = num_days * tool.price_per_day

        Booking.objects.create(
            tool=tool,
            renter=user,
            start_date=start_date,
            end_date=end_date,
            total_price=total_price,
            status='pending',
        )

        messages.success(request, f"Booking request sent! Total: {total_price} ₪")
        return redirect('/dashboard/?tab=my-rentals')

    return redirect('tool_detail', pk=tool_id)



