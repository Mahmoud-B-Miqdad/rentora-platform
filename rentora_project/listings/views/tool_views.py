from django.shortcuts import render, get_object_or_404, redirect
from django.http     import JsonResponse
from django.db.models import Prefetch, Avg
from django.contrib import messages
 
 
from listings.models import Tool, ToolImage, Review, Booking, BookingStatus, Wishlist, Category
from users.models    import User
 
 
from django.core.cache import cache

import requests

from listings.models import Tool, ToolImage, Review, Booking, BookingStatus, Wishlist
from users.models    import User


def _geocode(location: str) -> tuple[float, float] | None:
    """
    Convert a location string to (lat, lon) using Nominatim (OpenStreetMap).
    Results are cached for 24 hours so Nominatim is called at most once per location.
    Returns None silently on any failure — the map is simply not shown.
    """
    if not location:
        return None
    cache_key = 'geo_' + location.lower().strip()[:120]
    cached = cache.get(cache_key)
    if cached:
        return cached
    try:
        resp = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': location, 'format': 'json', 'limit': 1},
            headers={'User-Agent': 'Rentora/1.0 (tool-rental-platform)'},
            timeout=5,
        )
        data = resp.json()
        if data:
            coords = (float(data[0]['lat']), float(data[0]['lon']))
            cache.set(cache_key, coords, 60 * 60 * 24)
            return coords
    except Exception:
        pass
    return None


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
    reviews      = Review.objects.for_tool(tool)
    review_count = reviews.count()
    avg_raw      = Review.objects.average_rating_for_tool(tool)
    avg_rating   = round(float(avg_raw), 1) if avg_raw else None
 
    # ── Owner stats ───────────────────────────────────────────────────────────
    owner_tools_count = Tool.objects.filter(
        owner=tool.owner, is_available=True
    ).count()
    owner_rentals_count = Booking.objects.filter(
        tool__owner=tool.owner,
        status=BookingStatus.COMPLETED,
    ).count()
 
    owner_avg_raw = Review.objects.filter(
        booking__tool__owner=tool.owner,
        review_type='for_owner'
    ).aggregate(Avg('rating'))['rating__avg']
 
    owner_rating = round(float(owner_avg_raw), 1) if owner_avg_raw else None
 
    # ── Wishlist state ────────────────────────────────────────────────────────
    user_id       = request.session.get('user_id')
    is_wishlisted = (
        Wishlist.objects.filter(user_id=user_id, tool=tool).exists()
        if user_id else False
    )
 

    # ── Geocode tool location for map ─────────────────────────────────────────
    coords   = _geocode(tool.location)
    tool_lat = coords[0] if coords else None
    tool_lon = coords[1] if coords else None

    # ── Pop one-time session flash messages ───────────────────────────────────
    booking_success = request.session.pop('booking_success', None)
    booking_error    = request.session.pop('booking_error', None)
 
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
        'owner_rating':         owner_rating,
        'is_wishlisted':        is_wishlisted,
        'booking_success':      booking_success,
        'booking_error':        booking_error,
        'tool_lat':             tool_lat,
        'tool_lon':             tool_lon,
    }
    return render(request, 'listings/tool/tool_detail.html', context)
 
 
def toggle_wishlist_view(request, pk):
    """AJAX POST — toggle a tool in/out of the user's wishlist."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
 
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'login_required'}, status=401)
 
    tool = get_object_or_404(Tool, pk=pk)
    user = get_object_or_404(User, pk=user_id)
 
    obj, created = Wishlist.objects.get_or_create(user=user, tool=tool)
    if not created:
        obj.delete()
        return JsonResponse({'saved': False})
    return JsonResponse({'saved': True})
 
 
# ==================================================
# Add Tool
# ==================================================
 
def add_tool_view(request):
 
    if "user_id" not in request.session:
        return redirect("users:login")
 
    if request.method == "GET":
 
        context = {
            "categories": Category.objects.all()
        }
 
        return render(
            request,
            "listings/tool/add_tool.html",
            context
        )
 
    owner = User.objects.get(
        id=request.session["user_id"]
    )
 
    errors = Tool.objects.register_validator(
        request.POST,
        owner
    )
 
    if errors:
 
        for error in errors.values():
            messages.error(
                request,
                error
            )
 
        return render(
            request,
            "listings/tool/add_tool.html",
            {
                "categories": Category.objects.all(),
                "form_data": request.POST,
            }
        )
 
    tool = Tool.objects.create_tool(
        request.POST,
        owner
    )
 
    images = request.FILES.getlist("images")
 
    for index, image in enumerate(images):
 
        ToolImage.objects.create(
            tool=tool,
            image=image,
            is_primary=(index == 0)
        )
 
    messages.success(
        request,
        "Tool listed successfully."
    )
 
    return redirect(
        "listings:tools:detail",
        pk=tool.id
    )
 
 
# ==================================================
# My Tools
# ==================================================
 
def my_tools_view(request):
 
    if "user_id" not in request.session:
        return redirect("users:login")
 
    owner = User.objects.get(
        id=request.session["user_id"]
    )
 
    tools = Tool.objects.owned_by(owner)
 
    context = {
        "tools": tools
    }
 
    return render(
        request,
        "listings/tool/my_tools.html",
        context
    )
 
 
# ==================================================
# Edit Tool
# ==================================================
 
def edit_tool_view(request, tool_id):
 
    if "user_id" not in request.session:
        return redirect("users:login")
 
    tool = get_object_or_404(
        Tool,
        id=tool_id
    )
 
    if tool.owner.id != request.session["user_id"]:
 
        messages.error(
            request,
            "You do not have permission to edit this tool."
        )
 
        return redirect(
            "listings:tools:detail",
            pk=tool.id
        )
 
    if request.method == "GET":
 
        return render(
            request,
            "listings/tool/edit_tool.html",
            {
                "tool": tool,
                "categories": Category.objects.all()
            }
        )
 
    tool.title = request.POST.get("title")
    tool.description = request.POST.get("description")
    tool.location = request.POST.get("location")
    tool.daily_rate = request.POST.get("daily_rate")
    tool.deposit = request.POST.get("deposit")
    tool.condition = request.POST.get("condition")
    tool.category_id = request.POST.get("category_id")
 
    tool.save()
 
    messages.success(
        request,
        "Tool updated successfully."
    )
 
    return redirect(
        "listings:tools:detail",
        pk=tool.id
    )
 
 
# ==================================================
# Delete Tool
# ==================================================
 
def delete_tool_view(request, tool_id):
 
    if "user_id" not in request.session:
        return redirect("users:login")
 
    tool = get_object_or_404(
        Tool,
        id=tool_id
    )
 
    if tool.owner.id != request.session["user_id"]:
 
        messages.error(
            request,
            "You do not have permission to delete this tool."
        )
 
        return redirect(
            "listings:tools:detail",
            pk=tool.id
        )
 
    tool.delete()
 
    messages.success(
        request,
        "Tool deleted successfully."
    )
 
    return redirect(
        "listings:tools:my_tools"
    )