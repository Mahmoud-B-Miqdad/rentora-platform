"""
Transactional email for the rental lifecycle.

Every send goes through _send(), which injects SITE_URL (templates build
absolute links from it) and never lets a mail failure break the request that
triggered it — a booking must still succeed if the SMTP host is down. Failures
are logged rather than silently swallowed.
"""
import logging
import threading
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _async_enabled():
    """
    Deliver off the request thread everywhere except the in-memory backend,
    which tests assert against and must stay deterministic.
    """
    return not settings.EMAIL_BACKEND.endswith("locmem.EmailBackend")


def _deliver(messages):
    """
    Actual SMTP work. Opens ONE connection for the whole batch — a TLS
    handshake to the mail host costs seconds, so per-message connections are
    what made approve/mark-returned feel slow.
    """
    try:
        connection = get_connection(fail_silently=False)
        connection.open()
        connection.send_messages(messages)
        connection.close()
    except Exception:
        logger.exception("Failed delivering %d email(s)", len(messages))


def _build(subject, template, context, recipient):
    """Render the message in the request thread (fast, no network)."""
    ctx = dict(context)
    ctx.setdefault("SITE_URL", getattr(settings, "SITE_URL", ""))
    html = render_to_string(template, ctx)
    msg = EmailMultiAlternatives(
        subject=subject,
        body="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    msg.attach_alternative(html, "text/html")
    return msg


def _dispatch(messages):
    """Hand finished messages to the mail host, off-request when possible."""
    messages = [m for m in messages if m]
    if not messages:
        return False
    if _async_enabled():
        threading.Thread(target=_deliver, args=(messages,), daemon=True).start()
    else:
        _deliver(messages)
    return True


def _send(subject, template, context, recipient):
    """Render `template` and mail it to `recipient`. Never blocks on SMTP."""
    if not recipient:
        return False
    try:
        msg = _build(subject, template, context, recipient)
    except Exception:
        logger.exception("Failed rendering %s for %s", template, recipient)
        return False
    return _dispatch([msg])


def _send_batch(items):
    """
    Render several messages and deliver them over a single SMTP connection.
    `items` is a list of (subject, template, context, recipient) tuples.
    """
    messages = []
    for subject, template, context, recipient in items:
        if not recipient:
            continue
        try:
            messages.append(_build(subject, template, context, recipient))
        except Exception:
            logger.exception("Failed rendering %s for %s", template, recipient)
    return _dispatch(messages)


# ─────────────────────────────────────────────
#  Booking lifecycle
# ─────────────────────────────────────────────

def send_booking_requested_emails(booking):
    """Booking created — receipt to the renter, action prompt to the owner."""
    shared = {
        "booking": booking,
        "renter_name": booking.renter.name,
        "tool_title": booking.tool.title,
        "owner_name": booking.tool.owner.name,
    }
    _send_batch([
        (f"Booking requested: {booking.tool.title}",
         "emails/booking_confirmation.html", shared, booking.renter.email),
        (f"New rental request: {booking.tool.title}",
         "emails/owner_rental_request.html", shared, booking.tool.owner.email),
    ])


def send_booking_approved_email(booking):
    """Owner approved — tell the renter it is time to pay."""
    _send(
        f"Approved — complete payment for {booking.tool.title}",
        "emails/booking_confirmation.html",
        {
            "booking": booking,
            "renter_name": booking.renter.name,
            "tool_title": booking.tool.title,
            "owner_name": booking.tool.owner.name,
            "awaiting_payment": True,
        },
        booking.renter.email,
    )


def send_payment_received_emails(booking):
    """Payment captured — payout summary to owner, confirmation to renter."""
    breakdown = getattr(booking, "payment_breakdown", None)

    _send_batch([
        (f"Payment received: {booking.tool.title}",
         "emails/payment_received.html",
         {"booking": booking, "breakdown": breakdown},
         booking.tool.owner.email),
        ("Payment confirmed — your rental is active",
         "emails/payment_confirmed_renter.html",
         {"booking": booking,
          "total_charged": breakdown.total_charged_to_renter if breakdown else booking.total_price},
         booking.renter.email),
    ])


def send_booking_cancelled_email(booking):
    """Renter cancelled before payment — let the owner know the dates are free."""
    _send(
        f"Booking cancelled: {booking.tool.title}",
        "emails/booking_cancelled.html",
        {
            "booking": booking,
            "owner_name": booking.tool.owner.name,
            "renter_name": booking.renter.name,
            "tool_title": booking.tool.title,
        },
        booking.tool.owner.email,
    )


# ─────────────────────────────────────────────
#  Return handshake
# ─────────────────────────────────────────────

def send_return_confirmation_request_email(booking):
    """Owner marked the tool returned — renter must confirm to stop late fees."""
    _send(
        f"Confirm the return of {booking.tool.title}",
        "emails/return_confirmation_request.html",
        {
            "booking": booking,
            "tool_title": booking.tool.title,
            "owner_name": booking.tool.owner.name,
            "confirm_return_url": f"{getattr(settings, 'SITE_URL', '')}/dashboard/?tab=my-rentals",
        },
        booking.renter.email,
    )


def send_return_reminder_email(booking):
    """Sent shortly before the agreed end date."""
    _send(
        f"Return reminder: {booking.tool.title}",
        "emails/return_reminder.html",
        {
            "booking": booking,
            "tool_title": booking.tool.title,
            "owner_name": booking.tool.owner.name,
            "end_date": booking.end_date,
        },
        booking.renter.email,
    )


def send_overdue_warning_email(booking, days_overdue=1):
    """
    Overdue notice. The charge mirrors the booking logic exactly: each late day
    costs one extra rental day at the normal daily rate (no multiplier).
    """
    rate = Decimal(str(booking.tool.daily_rate))
    _send(
        f"Overdue: {booking.tool.title}",
        "emails/overdue_warning.html",
        {
            "booking": booking,
            "tool_title": booking.tool.title,
            "owner_name": booking.tool.owner.name,
            "end_date": booking.end_date,
            "days_overdue": days_overdue,
            "daily_rate": rate,
            "overdue_charge": rate * Decimal(days_overdue),
        },
        booking.renter.email,
    )


# ─────────────────────────────────────────────
#  Disputes
# ─────────────────────────────────────────────

def send_dispute_opened_emails(dispute):
    """Renter contested the return — notify the owner and confirm to the renter."""
    booking = dispute.booking
    ctx = {
        "dispute": dispute,
        "booking": booking,
        "tool_title": booking.tool.title,
        "owner_name": booking.tool.owner.name,
        "renter_name": booking.renter.name,
    }
    _send_batch([
        (f"Return disputed: {booking.tool.title}",
         "emails/dispute_opened_owner.html", ctx, booking.tool.owner.email),
        (f"We received your dispute: {booking.tool.title}",
         "emails/dispute_opened_renter.html", ctx, booking.renter.email),
    ])


# ─────────────────────────────────────────────
#  Support
# ─────────────────────────────────────────────

def send_support_confirmation_email(contact_message):
    _send(
        f"Support ticket #{contact_message.id}: {contact_message.subject}",
        "emails/support_confirmation.html",
        {
            "name": contact_message.name,
            "subject": contact_message.subject,
            "ticket_id": contact_message.id,
            "category": contact_message.get_category_display(),
        },
        contact_message.email,
    )


def send_support_response_email(contact_message):
    _send(
        f"Response to your ticket: {contact_message.subject}",
        "emails/support_response.html",
        {
            "name": contact_message.name,
            "subject": contact_message.subject,
            "ticket_id": contact_message.id,
            "response": contact_message.staff_response,
        },
        contact_message.email,
    )


def send_dispute_resolved_emails(dispute):
    """Staff issued a decision — inform both parties with the settlement."""
    booking = dispute.booking
    ctx = {
        "dispute": dispute,
        "booking": booking,
        "tool_title": booking.tool.title,
        "decision_label": dispute.get_staff_decision_display() if dispute.staff_decision else "",
        "refund_amount": dispute.refund_amount,
        "claim_amount": dispute.claim_amount,
        "notes": dispute.staff_notes,
    }
    _send_batch([
        (f"Dispute resolved: {booking.tool.title}",
         "emails/dispute_resolved.html", dict(ctx, recipient_role="renter"),
         booking.renter.email),
        (f"Dispute resolved: {booking.tool.title}",
         "emails/dispute_resolved.html", dict(ctx, recipient_role="owner"),
         booking.tool.owner.email),
    ])
