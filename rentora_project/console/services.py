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
 

def resolve_dispute(dispute, *, staff, decision, notes, refund_amount=None,
                    claim_amount=None):
    """
    Settle a deposit dispute and release the rental it was blocking.

    A dispute leaves the booking parked in `confirmed` (that is what stops late
    fees accruing while we investigate), so resolving it must also finish the
    rental — otherwise it stays open forever.

    `decision` is one of DepositDispute.STAFF_DECISION_CHOICES. The money fields
    are recorded for the finance trail; no card is charged from here — refunds
    and claim payouts are executed against the payment provider separately.
    """
    from decimal import Decimal
    from listings.services.email_service import send_dispute_resolved_emails

    booking = dispute.booking
    pot = Decimal(str(dispute.deposit_amount or 0))

    def _clamp(value):
        """Never let a share fall outside the pot."""
        value = Decimal(str(value or 0))
        return min(max(value, Decimal("0")), pot)

    # Derive the settlement from the decision so the two can never disagree.
    if decision == "refund_full":
        refund, claim, status = pot, Decimal("0"), "resolved_refund"
    elif decision == "refund_partial":
        refund = _clamp(refund_amount)
        claim, status = pot - refund, "resolved_partial"
    elif decision == "owner_claim":
        claim = _clamp(claim_amount if claim_amount is not None else pot)
        refund, status = pot - claim, "resolved_claim"
    elif decision == "split_50_50":
        refund = (pot / 2).quantize(Decimal("0.01"))
        claim, status = pot - refund, "resolved_partial"
    else:  # dismiss
        refund, claim, status = pot, Decimal("0"), "resolved_refund"

    # Invariant: the two shares must add up to exactly the disputed pot —
    # staff can redistribute it, never create money.
    if refund + claim != pot:
        raise ValueError(
            f"Settlement must total ${pot} (got refund ${refund} + claim ${claim})"
        )

    dispute.staff_decision = decision
    dispute.staff_notes = notes
    dispute.refund_amount = refund
    dispute.claim_amount = claim
    dispute.status = status
    dispute.resolved_by = staff
    dispute.resolved_at = timezone.now()
    dispute.save()

    # Apply the settlement to the real balance. Owner earnings are summed from
    # booking.total_price, so the decision only becomes real once that reflects
    # the owner's share — otherwise staff "split" the money on paper while the
    # owner still banked the full amount. The original charge stays on record
    # in the PaymentBreakdown and in dispute.deposit_amount.
    booking.total_price = claim
    booking.status = "completed"
    booking.actual_return_date = booking.actual_return_date or timezone.now().date()
    booking.return_requested_at = None
    booking.save()

    breakdown = getattr(booking, "payment_breakdown", None)
    if breakdown is not None:
        breakdown.owner_payout = claim
        breakdown.save(update_fields=["owner_payout", "updated_at"])

    label = dict(dispute.STAFF_DECISION_CHOICES).get(decision, decision)
    for party in (booking.renter, booking.tool.owner):
        Notification.objects.create_for(
            user=party,
            notification_type=NotificationType.RETURN_CONFIRMED,
            message=(
                f'The dispute over "{booking.tool.title}" has been resolved by '
                f"the Rentora team: {label}."
            ),
            booking=booking,
        )

    send_dispute_resolved_emails(dispute)

    AdminAction.objects.create(
        staff=staff,
        action="resolve_dispute",
        target_user=booking.renter,
        target_booking=booking,
        reason=f"[{label}] refund=${refund} claim=${claim} — {notes}",
    )
    return dispute
