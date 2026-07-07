import urllib.parse

from django.shortcuts import render
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Prefetch, Q
from django.urls import reverse

from listings.models import Category, Tool, ToolImage, Booking, Review, BookingStatus, ReviewType, Wishlist
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
        .order_by('-id')[:6]
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

    # ── Featured reviews (FOR_TOOL, ≥4 stars, with comment) ─────────────────
    featured_reviews = (
        Review.objects
        .filter(
            review_type=ReviewType.FOR_TOOL,
            comment__isnull=False,
            rating__gte=4,
        )
        .exclude(comment='')
        .select_related('reviewer', 'booking__tool')
        .order_by('-rating', '-created_at')[:3]
    )

    # ── Wishlist IDs for the logged-in user ───────────────────────────────────
    user_id = request.session.get('user_id')
    wishlist_ids = (
        set(Wishlist.objects.filter(user_id=user_id).values_list('tool_id', flat=True))
        if user_id else set()
    )

    context = {
        'categories':       categories,
        'featured_tools':   featured_tools,
        'featured_reviews': featured_reviews,
        'wishlist_ids':     wishlist_ids,
        'stats': {
            'tools_count':   tools_count,
            'rentals_count': rentals_count,
            'owners_count':  owners_count,
            'avg_rating':    avg_rating,
        },
    }
    return render(request, 'listings/pages/home.html', context)


# ─────────────────────────────────────────────
#  Browse View
# ─────────────────────────────────────────────

def browse_view(request):
    """Filterable, sortable, paginated tool listing page."""

    primary_img_prefetch = Prefetch(
        'images',
        queryset=ToolImage.objects.filter(is_primary=True),
        to_attr='primary_images',
    )

    tools_qs = (
        Tool.objects
        .filter(is_available=True)
        .select_related('owner', 'category')
        .prefetch_related(primary_img_prefetch)
        .annotate(
            avg_rating=Avg(
                'bookings__reviews__rating',
                filter=Q(bookings__reviews__review_type='for_tool')
            ),
            review_count=Count(
                'bookings__reviews',
                filter=Q(bookings__reviews__review_type='for_tool'),
                distinct=True,
            ),
        )
    )

    # ── Read GET params ───────────────────────────────────────────────────────
    q            = request.GET.get('q', '').strip()
    category_id  = request.GET.get('category', '').strip()
    try:
        max_price = float(request.GET.get('max_price', 200))
    except ValueError:
        max_price = 200
    availability = request.GET.get('availability', '')
    location     = request.GET.get('location', '').strip()
    sort         = request.GET.get('sort', 'newest')

    # ── Apply filters ─────────────────────────────────────────────────────────
    if q:
        tools_qs = tools_qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )
    if category_id:
        tools_qs = tools_qs.filter(category_id=category_id)
    if max_price:
        tools_qs = tools_qs.filter(daily_rate__lte=max_price)
    if availability == '1':
        tools_qs = tools_qs.filter(is_available=True)
    if location:
        tools_qs = tools_qs.filter(location__icontains=location)

    # ── Sort ──────────────────────────────────────────────────────────────────
    if sort == 'price_asc':
        tools_qs = tools_qs.order_by('daily_rate', 'id')
    elif sort == 'price_desc':
        tools_qs = tools_qs.order_by('-daily_rate', 'id')
    elif sort == 'top_rated':
        tools_qs = tools_qs.order_by('-avg_rating', '-id')
    else:
        tools_qs = tools_qs.order_by('-created_at')

    # ── Paginate (6 per page) ─────────────────────────────────────────────────
    paginator  = Paginator(tools_qs, 6)
    page_obj   = paginator.get_page(request.GET.get('page', 1))

    # ── Filter helpers ────────────────────────────────────────────────────────
    categories = Category.objects.all()
    locations  = (
        Tool.objects
        .values_list('location', flat=True)
        .exclude(location='')
        .distinct()
        .order_by('location')
    )

    # ── Wishlist IDs ──────────────────────────────────────────────────────────
    user_id = request.session.get('user_id')
    wishlist_ids = (
        set(Wishlist.objects.filter(user_id=user_id).values_list('tool_id', flat=True))
        if user_id else set()
    )

    context = {
        'page_obj':     page_obj,
        'total_count':  paginator.count,
        'categories':   categories,
        'locations':    locations,
        'wishlist_ids': wishlist_ids,
        'filters': {
            'q':           q,
            'category':    category_id,
            'max_price':   int(max_price),
            'availability': availability,
            'location':    location,
            'sort':        sort,
        },
    }

    # Return partial HTML fragment for real-time search AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.template.loader import render_to_string
        html = render_to_string(
            'listings/partials/_tools_grid.html', context, request=request
        )
        return JsonResponse({'html': html, 'count': paginator.count})

    return render(request, 'listings/pages/browse.html', context)


# ─────────────────────────────────────────────
#  About View
# ─────────────────────────────────────────────

def about_view(request):
    """Static about page with live platform stats."""
    tools_count   = Tool.objects.filter(is_available=True).count()
    rentals_count = Booking.objects.filter(status=BookingStatus.COMPLETED).count()
    owners_count  = User.objects.filter(tools__is_available=True).distinct().count()
    avg_data      = Review.objects.aggregate(avg=Avg('rating'))
    avg_rating    = round(float(avg_data['avg']), 1) if avg_data['avg'] else 0.0

    context = {
        'stats': {
            'tools_count':   tools_count,
            'rentals_count': rentals_count,
            'owners_count':  owners_count,
            'avg_rating':    avg_rating,
        }
    }
    return render(request, 'listings/pages/about.html', context)


# ─────────────────────────────────────────────
#  AI Smart Search View
# ─────────────────────────────────────────────

def smart_search_view(request):
    """
    AJAX endpoint: receives a natural-language query, calls Gemini Flash
    to extract English tool keywords, and returns a browse redirect URL.

    Falls back to the raw query if AI is unavailable or fails.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    query = request.POST.get('q', '').strip()
    if not query:
        return JsonResponse({'keywords': '', 'redirect': reverse('listings:browse')})

    from listings.services.ai_search_service import extract_search_keywords
    keywords = extract_search_keywords(query)

    search_term  = keywords if keywords else query
    redirect_url = reverse('listings:browse') + '?q=' + urllib.parse.quote(search_term)

    return JsonResponse({
        'keywords': search_term,
        'ai_used':  keywords is not None,
        'redirect': redirect_url,
    })