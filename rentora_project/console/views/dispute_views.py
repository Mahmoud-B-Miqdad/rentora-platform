from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from console import services
from console.decorators import staff_required
from console.models import AdminAction
from listings.models import DepositDispute

VALID_DECISIONS = {
    "refund_full", "refund_partial", "owner_claim", "split_50_50", "dismiss",
}


@staff_required
def dispute_detail(request, dispute_id):
    """Full case file for one dispute: both sides, evidence, and the decision form."""
    dispute = get_object_or_404(
        DepositDispute.objects.select_related(
            "booking", "booking__tool", "booking__renter",
            "booking__tool__owner", "resolved_by",
        ),
        id=dispute_id,
    )
    booking = dispute.booking

    # Mark it as actively under review the first time staff open it.
    if dispute.status == "open":
        dispute.status = "staff_reviewing"
        dispute.save(update_fields=["status", "updated_at"])

    # The full conversation between the two parties — evidence for the decision.
    from listings.models import Conversation
    conversation = (Conversation.objects
                    .filter(booking=booking)
                    .prefetch_related("messages__sender")
                    .first())
    chat_messages = list(conversation.messages.all()) if conversation else []

    # Handover condition photos, split into the "before" (renter at pickup) and
    # "after" (owner at return) records staff compare to judge damage.
    photos = list(booking.condition_photos.select_related("uploaded_by").all())
    pickup_photos = [p for p in photos if p.phase == "pickup"]
    return_photos = [p for p in photos if p.phase == "return"]

    return render(request, "console/dispute_detail.html", {
        "active_tab": "returns",
        "dispute": dispute,
        "booking": booking,
        "breakdown": getattr(booking, "payment_breakdown", None),
        "chat_messages": chat_messages,
        "pickup_photos": pickup_photos,
        "return_photos": return_photos,
        "history": AdminAction.objects.filter(target_booking=booking)
                   .select_related("staff")[:10],
    })


@require_POST
@staff_required
def dispute_resolve(request, dispute_id):
    dispute = get_object_or_404(
        DepositDispute.objects.select_related("booking", "booking__tool"),
        id=dispute_id,
    )

    if dispute.resolved_at:
        messages.error(request, "This dispute has already been resolved.")
        return redirect("console:dispute_detail", dispute_id=dispute.id)

    decision = request.POST.get("decision", "")
    notes    = request.POST.get("notes", "").strip()

    if decision not in VALID_DECISIONS:
        messages.error(request, "Choose a decision before resolving.")
        return redirect("console:dispute_detail", dispute_id=dispute.id)

    if not notes:
        messages.error(request, "A written reason is required — both parties receive it.")
        return redirect("console:dispute_detail", dispute_id=dispute.id)

    def _money(field):
        raw = request.POST.get(field, "").strip()
        if not raw:
            return None
        try:
            return Decimal(raw)
        except (InvalidOperation, ValueError):
            return None

    pot    = Decimal(str(dispute.deposit_amount or 0))
    refund = _money("refund_amount")
    claim  = _money("claim_amount")

    # Staff redistribute the disputed pot — they can never hand out more than
    # the renter actually paid.
    if decision == "refund_partial":
        if refund is None:
            messages.error(request, "Enter the amount to refund the renter.")
            return redirect("console:dispute_detail", dispute_id=dispute.id)
        if refund < 0 or refund > pot:
            messages.error(
                request,
                f"The refund must be between $0 and ${pot} — the amount in dispute."
            )
            return redirect("console:dispute_detail", dispute_id=dispute.id)

    if decision == "owner_claim":
        if claim is None:
            messages.error(request, "Enter the amount to pay the owner.")
            return redirect("console:dispute_detail", dispute_id=dispute.id)
        if claim < 0 or claim > pot:
            messages.error(
                request,
                f"The payout must be between $0 and ${pot} — the amount in dispute."
            )
            return redirect("console:dispute_detail", dispute_id=dispute.id)

    # Belt-and-braces: if both boxes were filled, they must not exceed the pot.
    if refund is not None and claim is not None and refund + claim > pot:
        messages.error(
            request,
            f"Refund (${refund}) plus payout (${claim}) exceeds the ${pot} in dispute."
        )
        return redirect("console:dispute_detail", dispute_id=dispute.id)

    try:
        services.resolve_dispute(
            dispute,
            staff=request.staff_user,
            decision=decision,
            notes=notes,
            refund_amount=refund,
            claim_amount=claim,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("console:dispute_detail", dispute_id=dispute.id)

    messages.success(
        request,
        f"Dispute #{dispute.id} resolved. Both parties have been notified."
    )
    return redirect("console:returns")


@require_POST
@staff_required
def dispute_request_owner_reply(request, dispute_id):
    """Record the owner's side of the story before deciding."""
    dispute = get_object_or_404(DepositDispute, id=dispute_id)
    response = request.POST.get("owner_response", "").strip()
    if response:
        dispute.owner_response = response
        dispute.save(update_fields=["owner_response", "updated_at"])
        messages.success(request, "Owner's statement recorded.")
    return redirect("console:dispute_detail", dispute_id=dispute.id)
