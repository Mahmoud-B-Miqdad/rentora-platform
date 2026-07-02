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
