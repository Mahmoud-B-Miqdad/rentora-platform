from django.utils import timezone


class LastSeenMiddleware:
    """
    Updates User.last_seen on every authenticated request.
    Throttled to one DB write per minute per session to avoid hammering the DB.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        uid = request.session.get("user_id")
        if uid:
            now = timezone.now()
            last_update = request.session.get("_ls_updated", 0)
            if now.timestamp() - last_update > 60:
                from users.models import User
                User.objects.filter(pk=uid).update(last_seen=now)
                request.session["_ls_updated"] = now.timestamp()

        return response
