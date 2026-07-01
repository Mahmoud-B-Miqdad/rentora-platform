def wishlist_count(request):

    if not request.session.get("user_id"):
        return {"global_wishlist_count": 0}

    count = Wishlist.objects.filter(
        user_id=request.session["user_id"]
    ).count()

    return {
        "global_wishlist_count": count
    }