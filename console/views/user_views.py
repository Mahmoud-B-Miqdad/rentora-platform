from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
 
from console import services
from console.decorators import staff_required
from console.models import AdminAction
from listings.models import Booking, Report, Tool
from users.models import User
 
 
@staff_required
def users_list(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
 
    users = User.objects.annotate(
        pending_reports=Count(
            "reports_received", filter=Q(reports_received__status="pending")
        ),
        tools_count=Count("tools", distinct=True),
    ).order_by("-created_at")
 
    if q:
        users = users.filter(Q(name__icontains=q) | Q(email__icontains=q))
    if status == "active":
        users = users.filter(is_active=True)
    elif status == "suspended":
        users = users.filter(is_active=False)
    elif status == "reported":
        users = users.filter(pending_reports__gt=0)
    elif status == "staff":
        users = users.filter(is_staff=True)
 
    page = Paginator(users, 20).get_page(request.GET.get("page"))
 
    return render(request, "console/users.html", {
        "active_tab": "users",
        "page": page,
        "q": q,
        "status": status,
    })
 
 
@staff_required
def user_detail(request, user_id):
    """The moderation screen: full context + decision actions."""
    target = get_object_or_404(User, id=user_id)
 
    reports = (Report.objects.filter(reported=target)
               .select_related("reporter").order_by("-created_at"))
    pending_reports = [r for r in reports if r.status == "pending"]
 
    stats = {
        "tools":            Tool.objects.filter(owner=target).count(),
        "rentals_as_renter": Booking.objects.filter(renter=target).count(),
        "rentals_as_owner": Booking.objects.filter(tool__owner=target).count(),
        "completed":        Booking.objects.filter(
                                renter=target, status="completed").count(),
        "reports_made":     Report.objects.filter(reporter=target).count(),
    }
 
    return render(request, "console/user_detail.html", {
        "active_tab": "users",
        "target": target,
        "reports": reports,
        "pending_count": len(pending_reports),
        "stats": stats,
        "tools": Tool.objects.filter(owner=target).select_related("category")[:8],
        "history": AdminAction.objects.filter(target_user=target)
                   .select_related("staff")[:10],
    })
 
 
@require_POST
@staff_required
def user_action(request, user_id):
    target = get_object_or_404(User, id=user_id)
    action = request.POST.get("action")
    reason = request.POST.get("reason", "").strip()
 
    if target.is_staff and action == "suspend":
        messages.error(request, "Staff accounts cannot be suspended from the console.")
        return redirect("console:user_detail", user_id=target.id)
 
    if action == "suspend":
        if not reason:
            messages.error(request, "A reason is required to suspend an account.")
            return redirect("console:user_detail", user_id=target.id)
        services.suspend_user(target, staff=request.staff_user, reason=reason)
        messages.success(request, f"{target.name} has been suspended.")
 
    elif action == "reinstate":
        services.reinstate_user(target, staff=request.staff_user, reason=reason)
        messages.success(request, f"{target.name} has been reinstated.")
 
    elif action == "dismiss_reports":
        n = services.dismiss_reports(target, staff=request.staff_user, reason=reason)
        messages.success(request, f"{n} report(s) dismissed.")
 
    else:
        messages.error(request, "Unknown action.")
 
    return redirect("console:user_detail", user_id=target.id)