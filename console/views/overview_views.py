import json
from datetime import timedelta
 
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
 
from console.decorators import staff_required
from console.models import AdminAction
from listings.models import Booking, Report, Tool
from users.models import User
 
ACTIVE_STATUSES = ("approved", "confirmed")
 
 
@staff_required
def overview(request):
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_start = today.replace(day=1)
 
    active_rentals = Booking.objects.filter(status__in=ACTIVE_STATUSES)
 
    kpis = {
        "users_total":     User.objects.count(),
        "users_new_week":  User.objects.filter(created_at__gte=week_ago).count(),
        "tools_total":     Tool.objects.count(),
        "rentals_active":  active_rentals.count(),
        "revenue_month":   Booking.objects.filter(
                               status__in=("confirmed", "return_pending", "completed"),
                               updated_at__date__gte=month_start,
                           ).aggregate(s=Sum("total_price"))["s"] or 0,
        "reports_pending": Report.objects.filter(status="pending").count(),
        "returns_waiting": Booking.objects.filter(status="return_pending").count(),
        "overdue":         active_rentals.filter(end_date__lt=today).count(),
    }
 
    # bookings per day — last 30 days
    start = today - timedelta(days=29)
    per_day = {start + timedelta(days=i): 0 for i in range(30)}
    for b in Booking.objects.filter(created_at__date__gte=start):
        per_day[b.created_at.date()] = per_day.get(b.created_at.date(), 0) + 1
    chart = {
        "labels": [d.strftime("%d %b") for d in per_day],
        "values": list(per_day.values()),
    }
 
    attention = {
        "reports": (Report.objects.filter(status="pending")
                    .select_related("reporter", "reported")[:5]),
        "returns": (Booking.objects.filter(status="return_pending")
                    .select_related("tool", "renter", "tool__owner")
                    .order_by("return_requested_at")[:5]),
        "overdue": (active_rentals.filter(end_date__lt=today)
                    .select_related("tool", "renter")
                    .order_by("end_date")[:5]),
    }
 
    return render(request, "console/overview.html", {
        "active_tab": "overview",
        "kpis": kpis,
        "chart_json": json.dumps(chart),
        "attention": attention,
        "recent_actions": AdminAction.objects.select_related(
            "staff", "target_user")[:6],
        "today": today,
    })