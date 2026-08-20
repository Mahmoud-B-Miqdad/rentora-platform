"""
Payment & payout views — Lahza gateway.

  • payout_setup       : owner connects a bank account (creates a Lahza subaccount)
  • start_payment      : renter → Lahza hosted checkout (splits owner/platform)
  • payment_callback   : where Lahza returns the renter after paying
  • lahza_webhook      : server-to-server confirmation (source of truth)
"""
import json
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from listings.models import Booking, PaymentBreakdown
from listings.models.notification import Notification, NotificationType
from listings.services.payments import get_payment_provider, PaymentError, to_subunits
from listings.services.email_service import send_payment_received_emails
from users.models import User


def _login_required(view):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("user_id"):
            return redirect("users:login")
        return view(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
#  Owner payout onboarding
# ─────────────────────────────────────────────

@_login_required
def payout_setup(request):
    """Owner connects a bank account so rental earnings can be paid out."""
    user = get_object_or_404(User, id=request.session["user_id"])
    provider = get_payment_provider()

    # Banks available for settlement (for the dropdown).
    try:
        banks = provider.list_banks()
    except PaymentError:
        banks = []

    if request.method != "POST":
        return render(request, "listings/payment/payout_setup.html", {
            "user": user,
            "banks": banks,
            "connected": bool(user.lahza_subaccount_code),
            "fee_percent": settings.PLATFORM_FEE_PERCENT,
        })

    bank_code = request.POST.get("bank_code", "").strip()
    account_number = request.POST.get("account_number", "").strip()

    if not bank_code or not account_number:
        messages.error(request, "Please choose your bank and enter your account number.")
        return redirect("listings:payout_setup")

    try:
        data = provider.create_subaccount(
            business_name=user.name,
            settlement_bank=bank_code,
            account_number=account_number,
            percentage_charge=settings.PLATFORM_FEE_PERCENT,
        )
    except PaymentError as exc:
        messages.error(request, f"Could not connect your account: {exc}")
        return redirect("listings:payout_setup")

    user.lahza_subaccount_code = data.get("subaccount_code", "")
    user.payout_bank_code = bank_code
    user.payout_account_last4 = account_number[-4:]
    user.save(update_fields=[
        "lahza_subaccount_code", "payout_bank_code", "payout_account_last4",
    ])

    messages.success(request, "Payout account connected. Your rental earnings will be paid to it automatically.")
    return redirect("/dashboard/?tab=my-tools")


# ─────────────────────────────────────────────
#  Renter checkout
# ─────────────────────────────────────────────

@_login_required
def start_payment(request, booking_id):
    """Send the renter to Lahza checkout for an approved, unpaid booking."""
    user = get_object_or_404(User, id=request.session["user_id"])
    booking = get_object_or_404(
        Booking.objects.select_related("tool", "tool__owner"),
        id=booking_id, renter=user, status="payment_pending",
    )

    # Unique gateway reference we can reconcile against later.
    reference = f"RENT-{booking.id}-{uuid.uuid4().hex[:12]}"
    request.session[f"pay_ref_{booking.id}"] = reference

    owner = booking.tool.owner
    callback = request.build_absolute_uri(
        f"/booking/{booking.id}/pay/callback/"
    )

    kwargs = dict(
        amount_subunits=to_subunits(booking.total_price),
        email=user.email,
        reference=reference,
        callback_url=callback,
        metadata={"booking_id": booking.id, "renter_id": user.id},
    )
    # Split to the owner's subaccount when they've connected payouts; the
    # subaccount's percentage_charge keeps the platform commission automatically.
    if owner.lahza_subaccount_code:
        kwargs["subaccount"] = owner.lahza_subaccount_code

    try:
        data = get_payment_provider().initialize_payment(**kwargs)
    except PaymentError as exc:
        messages.error(request, f"Payment could not be started: {exc}")
        return redirect("/dashboard/?tab=my-rentals&subtab=rtab-awaiting")

    return redirect(data["authorization_url"])


# ─────────────────────────────────────────────
#  Confirmation
# ─────────────────────────────────────────────

def _confirm_paid(booking, amount_subunits, reference=""):
    """
    Idempotently mark a booking paid: flip status, record the money breakdown,
    notify + email the owner. Safe to call from both callback and webhook.
    """
    if booking.status != "payment_pending":
        return False

    booking.status = "confirmed"
    booking.save(update_fields=["status", "updated_at"])

    fee_pct = Decimal(str(settings.PLATFORM_FEE_PERCENT))
    total = booking.total_price
    platform_fee = (total * fee_pct / 100).quantize(Decimal("0.01"))
    PaymentBreakdown.objects.update_or_create(
        booking=booking,
        defaults={
            "rental_total": total,
            "platform_fee_pct": fee_pct,
            "platform_fee": platform_fee,
            "total_charged_to_renter": total,
            "owner_payout": total - platform_fee,
            "stripe_fee": Decimal("0"),
            "net_platform_revenue": platform_fee,
            "gateway_reference": reference or "",
        },
    )

    Notification.objects.create_for(
        user=booking.tool.owner,
        notification_type=NotificationType.PAYMENT_RECEIVED,
        message=f"{booking.renter.name} completed payment for \"{booking.tool.title}\".",
        booking=booking,
    )
    send_payment_received_emails(booking)
    return True


@_login_required
def payment_callback(request, booking_id):
    """
    Where Lahza returns the renter after checkout. This is UX only — we verify
    with the gateway rather than trusting the redirect, and the webhook remains
    the authoritative confirmation.
    """
    booking = get_object_or_404(Booking, id=booking_id, renter_id=request.session["user_id"])
    reference = request.GET.get("reference") or request.session.get(f"pay_ref_{booking.id}")

    if reference:
        try:
            data = get_payment_provider().verify_payment(reference)
            if data.get("status") == "success":
                _confirm_paid(booking, data.get("amount"), reference)
        except PaymentError:
            pass

    if booking.status == "confirmed":
        return render(request, "listings/booking/payment_success.html", {
            "booking": booking, "user": booking.renter,
        })

    messages.info(request, "We haven't received your payment yet. If you completed it, it will confirm shortly.")
    return redirect("/dashboard/?tab=my-rentals&subtab=rtab-awaiting")


def _booking_from_reference(reference):
    """Our references are 'RENT-<booking_id>-<uuid>'."""
    try:
        parts = reference.split("-")
        if len(parts) >= 2 and parts[0] == "RENT":
            return (Booking.objects
                    .select_related("tool", "tool__owner", "renter")
                    .filter(id=int(parts[1])).first())
    except (ValueError, IndexError):
        pass
    return None


@csrf_exempt
def lahza_webhook(request):
    """
    Server-to-server payment notification.

    Lahza does not send a signature header (at least in sandbox), so instead of
    trusting the payload we re-ask the gateway whether the referenced
    transaction really succeeded — using our secret key. This is stronger than a
    signature: a forged POST can't make verify_payment() return success.
    Always answers 200 so the gateway stops retrying.
    """
    try:
        event = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)

    data = event.get("data") or {}
    reference = data.get("reference") or ""
    if not reference:
        return HttpResponse(status=200)

    try:
        verified = get_payment_provider().verify_payment(reference)
    except PaymentError:
        return HttpResponse(status=200)  # ack; callback / next retry will confirm

    if verified.get("status") == "success":
        booking = _booking_from_reference(reference)
        if booking:
            _confirm_paid(booking, verified.get("amount"), reference)

    return HttpResponse(status=200)
