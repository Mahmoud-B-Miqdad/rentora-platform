"""Staff-console actions. Every mutation goes through here so that the
AdminAction audit trail is never skipped."""
 
from django.utils import timezone
 
from console.models import AdminAction
from listings.models import Tool, Report
from listings.models.notification import Notification, NotificationType
 
 
def suspend_user(target, *, staff, reason):
    """Suspend an account: block login, hide their listings,
    and resolve any pending reports against them."""
    target.is_active = False
    target.save(update_fields=["is_active"])
 
    Tool.objects.filter(owner=target).update(is_available=False)
    Report.objects.filter(reported=target, status="pending").update(status="resolved")
 
    AdminAction.objects.create(
        staff=staff, action="suspend", target_user=target, reason=reason,
    )
 
 
def reinstate_user(target, *, staff, reason):
    """Re-enable a suspended account. Their tools stay hidden until the
    owner re-enables them from My Tools."""
    target.is_active = True
    target.save(update_fields=["is_active"])
 
    AdminAction.objects.create(
        staff=staff, action="reinstate", target_user=target, reason=reason,
    )
 
 
def dismiss_reports(target, *, staff, reason):
    """Close all pending reports against a user without penalty."""
    updated = Report.objects.filter(reported=target, status="pending").update(
        status="dismissed"
    )
    AdminAction.objects.create(
        staff=staff, action="dismiss_reports", target_user=target, reason=reason,
    )
    return updated
 
 
def force_complete_booking(booking, *, staff, reason):
    """Staff resolution for a stuck return: finalize the rental as-is
    and notify both parties. Amounts are left unchanged."""
    booking.status = "completed"
    booking.actual_return_date = booking.actual_return_date or timezone.now().date()
    booking.return_requested_at = None
    booking.save()
 
    for party in (booking.renter, booking.tool.owner):
        Notification.objects.create_for(
            user=party,
            notification_type=NotificationType.RETURN_CONFIRMED,
            message=(
                f'The rental of "{booking.tool.title}" was reviewed and closed '
                f"by the Rentora team."
            ),
            booking=booking,
        )
 
    AdminAction.objects.create(
        staff=staff,
        action="force_complete",
        target_user=booking.renter,
        target_booking=booking,
        reason=reason,
    )
 