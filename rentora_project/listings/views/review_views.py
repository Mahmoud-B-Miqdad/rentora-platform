from django.shortcuts import redirect, get_object_or_404
from django.contrib   import messages

from listings.models               import Booking, BookingStatus, Review, ReviewType
from listings.views.booking_views  import login_required_session
from users.models                  import User


@login_required_session
def submit_review_view(request, booking_id):
    """
    Handles review submission for a completed booking.
    Renters may rate the tool and the owner; owners may rate the renter.
    A single POST can carry one or both ratings depending on the caller's role.
    """
    if request.method != 'POST':
        return redirect('listings:dashboard')

    user    = User.objects.get(id=request.session['user_id'])
    booking = get_object_or_404(Booking, id=booking_id, status=BookingStatus.COMPLETED)

    is_renter = booking.renter_id == user.id
    is_owner  = booking.tool.owner_id == user.id

    if is_renter:
        submissions = [
            (ReviewType.FOR_TOOL,  request.POST.get('tool_rating'),   request.POST.get('tool_comment', '')),
            (ReviewType.FOR_OWNER, request.POST.get('owner_rating'),  request.POST.get('owner_comment', '')),
        ]
        redirect_tab = 'my-rentals'
    elif is_owner:
        submissions = [
            (ReviewType.FOR_RENTER, request.POST.get('renter_rating'), request.POST.get('renter_comment', '')),
        ]
        redirect_tab = 'booking-requests'
    else:
        return redirect('listings:dashboard')

    errors      = []
    created_any = False

    for review_type, rating, comment in submissions:
        if not rating:
            continue
        post_data    = {'rating': rating, 'review_type': review_type, 'comment': comment}
        field_errors = Review.objects.register_validator(post_data, user, booking)
        if field_errors:
            errors.append(next(iter(field_errors.values())))
            continue
        Review.objects.create_review(post_data, user, booking)
        created_any = True

    if errors:
        messages.error(request, errors[0])
    elif created_any:
        messages.success(request, "Thank you! Your review has been submitted.")
    else:
        messages.warning(request, "Please provide at least one rating.")

    return redirect(f'/dashboard/?tab={redirect_tab}')
