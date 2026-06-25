from django.shortcuts import redirect, get_object_or_404

from listings.models import Tool, Booking
from users.models    import User


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
