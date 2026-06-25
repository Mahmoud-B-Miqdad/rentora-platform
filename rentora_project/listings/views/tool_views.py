from django.shortcuts import render, get_object_or_404
from django.db.models import Prefetch

from listings.models import Tool, ToolImage, Review, Booking, BookingStatus


def tool_detail_view(request, pk):
    """Public detail page for a single Tool listing."""

    # ── Fetch tool with images + owner + category ─────────────────────────────
    tool = get_object_or_404(
        Tool.objects
        .select_related('owner', 'category')
        .prefetch_related(
            Prefetch(
                'images',
                queryset=ToolImage.objects.order_by('-is_primary', 'id'),
                to_attr='all_images',
            )
        ),
        pk=pk,
        is_available=True,
    )

    # ── Split images ──────────────────────────────────────────────────────────
    primary_image = next((img for img in tool.all_images if img.is_primary), None)
    # Fallback: if no image is marked primary, use the first one
    if primary_image is None and tool.all_images:
        primary_image = tool.all_images[0]
    gallery = [img for img in tool.all_images if img != primary_image]

    # ── Reviews for this tool ─────────────────────────────────────────────────
    reviews    = Review.objects.for_tool(tool)
    review_count = reviews.count()
    avg_raw    = Review.objects.average_rating_for_tool(tool)
    avg_rating = round(float(avg_raw), 1) if avg_raw else None

    # ── Owner stats ───────────────────────────────────────────────────────────
    owner_tools_count = Tool.objects.filter(
        owner=tool.owner, is_available=True
    ).count()
    owner_rentals_count = Booking.objects.filter(
        tool__owner=tool.owner,
        status=BookingStatus.COMPLETED,
    ).count()

    # ── Pop one-time session flash messages ───────────────────────────────────
    booking_success = request.session.pop('booking_success', None)
    booking_error   = request.session.pop('booking_error', None)

    context = {
        'tool':                 tool,
        'primary_image':        primary_image,
        'gallery':              gallery,
        'all_images':           tool.all_images,
        'reviews':              reviews[:12],
        'review_count':         review_count,
        'avg_rating':           avg_rating,
        'owner_tools_count':    owner_tools_count,
        'owner_rentals_count':  owner_rentals_count,
        'booking_success':      booking_success,
        'booking_error':        booking_error,
    }
    return render(request, 'listings/tool_detail.html', context)
