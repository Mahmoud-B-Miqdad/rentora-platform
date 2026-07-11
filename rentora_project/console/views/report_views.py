from collections import defaultdict
 
from django.shortcuts import render
 
from console.decorators import staff_required
from listings.models import Report
 
 
@staff_required
def reports_queue(request):
    """Pending reports grouped by the reported account —
    the moderation queue, worst offenders first."""
    pending = (Report.objects.filter(status="pending")
               .select_related("reporter", "reported")
               .order_by("-created_at"))
 
    grouped = defaultdict(list)
    for r in pending:
        grouped[r.reported].append(r)
 
    queue = sorted(
        (
            {
                "user": user,
                "count": len(reports),
                "reasons": sorted({r.get_reason_display() for r in reports}),
                "latest": reports[0].created_at,
            }
            for user, reports in grouped.items()
        ),
        key=lambda row: row["count"],
        reverse=True,
    )
 
    resolved_recent = (Report.objects.exclude(status="pending")
                       .select_related("reporter", "reported")
                       .order_by("-created_at")[:10])
 
    return render(request, "console/reports.html", {
        "active_tab": "reports",
        "queue": queue,
        "resolved_recent": resolved_recent,
    })