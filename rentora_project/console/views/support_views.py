from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from console.decorators import staff_required
from listings.models import ContactMessage
from listings.models.notification import Notification, NotificationType
from listings.services.email_service import send_support_response_email


@staff_required
def support_queue(request):
    """Support inbox — newest messages first, filterable by status."""
    status = request.GET.get("status", "")

    msgs = ContactMessage.objects.select_related("user").order_by("-created_at")
    if status in {"new", "in_progress", "resolved", "closed"}:
        msgs = msgs.filter(status=status)

    page = Paginator(msgs, 20).get_page(request.GET.get("page"))

    return render(request, "console/support.html", {
        "active_tab": "support",
        "page": page,
        "status": status,
        "new_count": ContactMessage.objects.filter(status="new").count(),
    })


@staff_required
def support_detail(request, message_id):
    """Read a single ticket and respond."""
    ticket = get_object_or_404(
        ContactMessage.objects.select_related("user"), id=message_id
    )

    # Auto-advance a brand-new ticket to "in progress" on first open
    if ticket.status == "new":
        ticket.status = "in_progress"
        ticket.save(update_fields=["status", "updated_at"])

    return render(request, "console/support_detail.html", {
        "active_tab": "support",
        "ticket": ticket,
    })


@require_POST
@staff_required
def support_action(request, message_id):
    ticket = get_object_or_404(ContactMessage, id=message_id)
    action = request.POST.get("action")

    if action == "respond":
        response = request.POST.get("response", "").strip()
        if not response:
            messages.error(request, "Write a response before sending.")
            return redirect("console:support_detail", message_id=ticket.id)

        ticket.staff_response = response
        ticket.status = "resolved"
        ticket.assigned_to = request.staff_user
        ticket.resolved_at = timezone.now()
        ticket.save()

        # Channel 1 — email the reply to the address on the ticket
        send_support_response_email(ticket)

        # Channel 2 — in-app notification, only if the sender was logged in
        if ticket.user_id:
            Notification.objects.create_for(
                user=ticket.user,
                notification_type=NotificationType.SUPPORT_REPLY,
                message=f"Support replied to your message \"{ticket.subject}\": {response}",
            )

        messages.success(request, f"Response sent to {ticket.email}.")

    elif action == "close":
        ticket.status = "closed"
        ticket.save(update_fields=["status", "updated_at"])
        messages.success(request, "Ticket closed.")

    elif action == "reopen":
        ticket.status = "in_progress"
        ticket.resolved_at = None
        ticket.save(update_fields=["status", "resolved_at", "updated_at"])
        messages.success(request, "Ticket reopened.")

    else:
        messages.error(request, "Unknown action.")

    return redirect("console:support_detail", message_id=ticket.id)
