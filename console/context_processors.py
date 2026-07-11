def console_counts(request):
    """Sidebar badge counts — computed only inside the console."""
    if not request.path.startswith("/console/"):
        return {}
    if not getattr(request, "staff_user", None):
        return {}
 
    from listings.models import Booking, Report
 
    return {
        "nav_pending_reports": Report.objects.filter(status="pending").count(),
        "nav_returns_waiting": Booking.objects.filter(status="return_pending").count(),
    }