from django.shortcuts import render
from django.db.models import Avg, Prefetch, Q

from listings.models import *
from users.models    import User


# ─────────────────────────────────────────────
#  Home View
# ─────────────────────────────────────────────

def home_view(request):
    """
    Renders the public home page.

    Pulls four pieces of real data from the DB:
      - categories    : all Category rows (for the Browse by Category grid)
      - featured_tools: 6 most-recently-created available tools
                        with their primary image pre-fetched
      - stats         : platform-level aggregates (tools, rentals, owners, rating)
    """

    # ── Categories ────────────────────────────────────────────────────────────
    categories = Category.objects.all()

    # ── Featured tools with primary image pre-fetched ─────────────────────────
    primary_img_prefetch = Prefetch(
        'images',
        queryset=ToolImage.objects.filter(is_primary=True),
        to_attr='primary_images',
    )

    featured_tools = (
        Tool.objects
        .filter(is_available=True)
        .select_related('owner', 'category')
        .prefetch_related(primary_img_prefetch)
        .annotate(
            avg_rating_computed=Avg(
                'bookings__reviews__rating',
                filter=Q(bookings__reviews__review_type='for_tool')
            )
        )
        .order_by('id')[:6]
    )

    # ── Platform stats ────────────────────────────────────────────────────────
    tools_count   = Tool.objects.filter(is_available=True).count()
    rentals_count = Booking.objects.filter(status=BookingStatus.COMPLETED).count()
    owners_count  = (
        User.objects
        .filter(tools__is_available=True)
        .distinct()
        .count()
    )
    avg_data   = Review.objects.aggregate(avg=Avg('rating'))
    avg_rating = round(float(avg_data['avg']), 1) if avg_data['avg'] else 0.0

    # ── Wishlist IDs for the logged-in user ───────────────────────────────────
    user_id = request.session.get('user_id')
    wishlist_ids = (
        set(Wishlist.objects.filter(user_id=user_id).values_list('tool_id', flat=True))
        if user_id else set()
    )

    context = {
        'categories':     categories,
        'featured_tools': featured_tools,
        'wishlist_ids':   wishlist_ids,
        'stats': {
            'tools_count':   tools_count,
            'rentals_count': rentals_count,
            'owners_count':  owners_count,
            'avg_rating':    avg_rating,
        },
    }
    return render(request, 'listings/home.html', context)