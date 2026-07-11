from datetime import timedelta
 
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
 
from console import services
from console.decorators import staff_required
from listings.models import Booking
 
STATUS_TABS = [
    ("", "All"),
    ("pending", "Pending"),
    ("payment_pending", "Awaiting Payment"),
    ("confirmed", "Active"),
    ("return_pending", "Return Pending"),
    ("completed", "Completed"),
    ("rejected", "Rejected"),
]
 
 
@staff_required
def bookings_monitor(request):
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
 
    bookings = (Booking.objects
                .select_related("tool", "renter", "tool__owner")
                .order_by("-created_at"))
    if status:
        bookings = bookings.filter(status=status)
    if q:
        bookings = bookings.filter(
            Q(tool__title__icontains=q) |
            Q(renter__email__icontains=q) |
            Q(renter__name__icontains=q) |
            Q(tool__owner__email__icontains=q)
        )
 
    page = Paginator(bookings, 20).get_page(request.GET.get("page"))
    stuck_cutoff = timezone.now() - timedelta(hours=1)
 
    return render(request, "console/bookings.html", {
        "active_tab": "bookings",
        "page": page,
        "q": q,
        "status": status,
        "status_tabs": STATUS_TABS,
        "stuck_cutoff": stuck_cutoff,
        "today": timezone.now().date(),
    })
 
 
@staff_required
def returns_queue(request):
    """Stuck returns (awaiting renter confirmation) and overdue rentals."""
    today = timezone.now().date()
 
    waiting = (Booking.objects.filter(status="return_pending")
               .select_related("tool", "renter", "tool__owner")
               .order_by("return_requested_at"))
    overdue = (Booking.objects.filter(
                   status__in=("approved", "confirmed"), end_date__lt=today)
               .select_related("tool", "renter", "tool__owner")
               .order_by("end_date"))
 
    return render(request, "console/returns.html", {
        "active_tab": "returns",
        "waiting": waiting,
        "overdue": overdue,
        "today": today,
    })
 
 
@require_POST
@staff_required
def booking_force_complete(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    reason = request.POST.get("reason", "").strip()
 
    if not reason:
        messages.error(request, "A reason is required to close a rental manually.")
        return redirect("console:returns")
 
    if booking.status not in ("return_pending", "approved", "confirmed"):
        messages.error(request, "This booking is not in a closable state.")
        return redirect("console:returns")
 
    services.force_complete_booking(booking, staff=request.staff_user, reason=reason)
    messages.success(
        request, f'Rental of "{booking.tool.title}" was closed and both parties notified.'
    )
    return redirect("console:returns")