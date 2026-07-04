from listings.models.wishlist      import Wishlist
from listings.models.notification  import Notification


def wishlist_count(request):
    if not request.session.get("user_id"):
        return {"global_wishlist_count": 0}

    count = Wishlist.objects.filter(
        user_id=request.session["user_id"]
    ).count()

    return {"global_wishlist_count": count}


def notification_count(request):
    if not request.session.get("user_id"):
        return {"global_unread_notifications": 0}

    count = Notification.objects.filter(
        user_id=request.session["user_id"],
        is_read=False,
    ).count()
    return {"global_unread_notifications": count}


def current_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return {"current_user": None}
    try:
        from users.models import User
        user = User.objects.get(pk=user_id)
        return {"current_user": user}
    except User.DoesNotExist:
        return {"current_user": None}
