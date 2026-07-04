import json

from django.http      import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone

from listings.models         import Booking
from listings.models.message import Conversation, Message
from listings.models.notification import Notification, NotificationType
from users.models import User


def _get_user(request):
    uid = request.session.get("user_id")
    if not uid:
        return None
    try:
        return User.objects.get(pk=uid)
    except User.DoesNotExist:
        return None


def _assert_participant(user, conversation):
    booking = conversation.booking
    return user.pk in {booking.renter_id, booking.tool.owner_id}


def chat_view(request, booking_id):
    user = _get_user(request)
    if not user:
        return redirect("users:login")

    booking = get_object_or_404(
        Booking.objects.select_related("tool", "tool__owner", "renter"),
        pk=booking_id,
    )

    if user.pk not in {booking.renter_id, booking.tool.owner_id}:
        return redirect("listings:dashboard")

    conversation = Conversation.objects.get_or_create_for_booking(booking)

    # Mark all messages from the other person as read
    conversation.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)

    # Delete ALL accumulated NEW_MESSAGE notifications for this booking when
    # the user opens the chat — they're already reading the messages here,
    # so there's no need to keep any of them (read or unread) in the list.
    Notification.objects.filter(
        user=user,
        booking=booking,
        notification_type=NotificationType.NEW_MESSAGE,
    ).delete()

    chat_messages = conversation.messages.select_related("sender").order_by("created_at")

    other = conversation.other_participant(user)

    # Use the real last_seen field updated by LastSeenMiddleware
    other_last_seen = other.last_seen
    now = timezone.now()
    other_is_online = (
        other_last_seen is not None
        and (now - other_last_seen).total_seconds() < 300  # active within last 5 min
    )

    # Highest ID of current user's messages that the other person has already read
    last_seen_id = (
        conversation.messages
        .filter(sender=user, is_read=True)
        .order_by('-pk')
        .values_list('pk', flat=True)
        .first()
    ) or 0

    return render(request, "listings/chat/chat.html", {
        "conversation":    conversation,
        "booking":         booking,
        "chat_messages":   chat_messages,
        "other":           other,
        "other_last_seen": other_last_seen,
        "other_is_online": other_is_online,
        "last_seen_id":    last_seen_id,
        "user":            user,
        "today":           timezone.now().date(),
    })


@require_POST
def send_message_view(request, booking_id):
    user = _get_user(request)
    if not user:
        return JsonResponse({"ok": False, "error": "Not authenticated"}, status=401)

    booking = get_object_or_404(
        Booking.objects.select_related("tool", "tool__owner", "renter"),
        pk=booking_id,
    )

    if user.pk not in {booking.renter_id, booking.tool.owner_id}:
        return JsonResponse({"ok": False, "error": "Forbidden"}, status=403)

    try:
        body = json.loads(request.body)
        text = body.get("text", "").strip()
    except (json.JSONDecodeError, AttributeError):
        text = request.POST.get("text", "").strip()

    if not text:
        return JsonResponse({"ok": False, "error": "Empty message"}, status=400)

    if len(text) > 2000:
        return JsonResponse({"ok": False, "error": "Message too long"}, status=400)

    conversation = Conversation.objects.get_or_create_for_booking(booking)
    msg = Message.objects.create(
        conversation=conversation,
        sender=user,
        text=text,
    )
    # Touch updated_at on conversation for ordering
    conversation.save()

    # Keep exactly ONE NEW_MESSAGE notification per conversation:
    # delete any existing ones (read or unread), then create a fresh one.
    # This prevents stacking in the notification bell no matter how many
    # messages are exchanged.
    other = conversation.other_participant(user)
    Notification.objects.filter(
        user=other,
        booking=booking,
        notification_type=NotificationType.NEW_MESSAGE,
    ).delete()
    Notification.objects.create_for(
        user=other,
        notification_type=NotificationType.NEW_MESSAGE,
        message=f"{user.name} sent you a message about \"{booking.tool.title}\".",
        booking=booking,
    )

    return JsonResponse({
        "ok":         True,
        "message":    _serialize_message(msg, user),
    })


def poll_messages_view(request, booking_id):
    user = _get_user(request)
    if not user:
        return JsonResponse({"ok": False}, status=401)

    booking = get_object_or_404(
        Booking.objects.select_related("tool", "tool__owner", "renter"),
        pk=booking_id,
    )

    if user.pk not in {booking.renter_id, booking.tool.owner_id}:
        return JsonResponse({"ok": False}, status=403)

    after_id = request.GET.get("after", 0)
    try:
        after_id = int(after_id)
    except (TypeError, ValueError):
        after_id = 0

    conversation = Conversation.objects.get_or_create_for_booking(booking)

    new_msgs = (
        conversation.messages
        .filter(pk__gt=after_id)
        .exclude(sender=user)
        .select_related("sender")
        .order_by("created_at")
    )

    # Mark them as read
    new_msgs.update(is_read=True)

    # Delete the NEW_MESSAGE notification while the user is actively polling
    # (reading messages in the chat) so the bell stays at zero.
    Notification.objects.filter(
        user=user,
        booking=booking,
        notification_type=NotificationType.NEW_MESSAGE,
    ).delete()

    # Tell the current user which of their own messages the other person has read
    last_seen_id = (
        conversation.messages
        .filter(sender=user, is_read=True)
        .order_by('-pk')
        .values_list('pk', flat=True)
        .first()
    ) or 0

    return JsonResponse({
        "ok":           True,
        "messages":     [_serialize_message(m, user) for m in new_msgs],
        "last_seen_id": last_seen_id,
    })


# ── helpers ───────────────────────────────────────────────────────────────────

def _serialize_message(msg, current_user):
    return {
        "id":         msg.pk,
        "text":       msg.text,
        "is_mine":    msg.sender_id == current_user.pk,
        "is_read":    msg.is_read,
        "sender":     msg.sender.name,
        "avatar":     msg.sender.name[0].upper(),
        "avatar_url": msg.sender.profile_image.url if msg.sender.profile_image else "",
        "created_at": msg.created_at.isoformat(),
        "time":       msg.created_at.strftime("%H:%M"),
        "date":       msg.created_at.strftime("%b %d, %Y"),
    }
