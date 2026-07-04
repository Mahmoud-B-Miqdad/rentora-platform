import json

from django.http      import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from listings.models.notification import Notification
from users.models import User


def _get_user(request):
    uid = request.session.get("user_id")
    if not uid:
        return None
    try:
        return User.objects.get(pk=uid)
    except User.DoesNotExist:
        return None


def notifications_json(request):
    """Return the latest 25 notifications for the logged-in user as JSON."""
    user = _get_user(request)
    if not user:
        return JsonResponse({"notifications": [], "unread_count": 0})

    qs = Notification.objects.for_user(user)
    data = []
    for n in qs:
        data.append({
            "id":          n.pk,
            "type":        n.notification_type,
            "message":     n.message,
            "is_read":     n.is_read,
            "icon":        n.icon,
            "color_class": n.color_class,
            "booking_url": n.booking_url,
            "created_at":  n.created_at.isoformat(),
            "time_ago":    _time_ago(n.created_at),
        })

    unread = Notification.objects.filter(user=user, is_read=False).count()
    return JsonResponse({"notifications": data, "unread_count": unread})


@require_POST
def mark_notification_read(request, notification_id):
    user = _get_user(request)
    if not user:
        return JsonResponse({"ok": False}, status=401)

    Notification.objects.filter(pk=notification_id, user=user).update(is_read=True)
    unread = Notification.objects.filter(user=user, is_read=False).count()
    return JsonResponse({"ok": True, "unread_count": unread})


@require_POST
def mark_all_read(request):
    user = _get_user(request)
    if not user:
        return JsonResponse({"ok": False}, status=401)

    Notification.objects.filter(user=user, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True, "unread_count": 0})


def unread_count(request):
    user = _get_user(request)
    if not user:
        return JsonResponse({"unread_count": 0})

    count = Notification.objects.filter(user=user, is_read=False).count()
    return JsonResponse({"unread_count": count})


# ── helpers ───────────────────────────────────────────────────────────────────

def _time_ago(dt):
    from django.utils import timezone
    delta = timezone.now() - dt
    s = int(delta.total_seconds())
    if s < 60:
        return "just now"
    if s < 3600:
        m = s // 60
        return f"{m}m ago"
    if s < 86400:
        h = s // 3600
        return f"{h}h ago"
    d = s // 86400
    return f"{d}d ago"
