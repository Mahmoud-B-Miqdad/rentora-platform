"""
Abuse protection for public forms that can trigger outbound email or create
rows (support tickets, registration, password reset, ...).

Why this exists: an unauthenticated form that stores whatever it is given and
mails a confirmation to a typed-in address is a free spam relay — bots filed
hundreds of tickets with made-up addresses and every one produced an email
from our SMTP account. The defences are layered:

  1. Per-IP / per-address / global fixed-window counters (this module).
  2. A signed, time-stamped form token + honeypot (see ContactMessageManager).
  3. Never mailing an address nobody has proven they own (see contact view).

Counters live in the dedicated "throttle" cache (file-based, so every gunicorn
worker on the host shares the same counts; a per-process LocMemCache would
multiply every limit by the worker count).
"""
import hashlib
import logging
from functools import wraps

from django.conf import settings
from django.core.cache import caches
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def client_ip(request):
    """
    The real client address.

    Behind Nginx, REMOTE_ADDR is always the proxy (127.0.0.1), which would put
    every visitor in one shared bucket. X-Forwarded-For can't be trusted as a
    whole either — the client controls everything the proxy did not append — so
    we count TRUSTED_PROXY_COUNT hops from the RIGHT (the entries our own
    proxy wrote). Set TRUSTED_PROXY_COUNT=0 when running without a proxy.
    """
    hops = getattr(settings, "TRUSTED_PROXY_COUNT", 0)
    if hops > 0:
        forwarded = [
            part.strip()
            for part in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")
            if part.strip()
        ]
        if len(forwarded) >= hops:
            return forwarded[-hops]
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def _cache():
    return caches["throttle"] if "throttle" in settings.CACHES else caches["default"]


def _cache_key(scope, ident):
    digest = hashlib.sha256(str(ident).strip().lower().encode("utf-8")).hexdigest()[:32]
    return f"throttle:{scope}:{digest}"


def allow(scope, ident, limit, window):
    """
    Record one event for (scope, ident) and report whether it is still within
    `limit` events per `window` seconds (fixed window, starts at first event).
    An empty ident is never throttled — there is nothing to key on.
    """
    if not ident:
        return True
    cache = _cache()
    key = _cache_key(scope, ident)
    if cache.add(key, 1, window):
        return True
    try:
        count = cache.incr(key)
    except ValueError:  # key expired between add() and incr()
        cache.set(key, 1, window)
        return True
    if count > limit:
        logger.warning("Throttled %s for %s (%d/%d per %ds)", scope, ident, count, limit, window)
    return count <= limit


def too_many_requests(request=None):
    response = HttpResponse(
        "Too many requests. Please wait a while before trying again.",
        status=429,
        content_type="text/plain; charset=utf-8",
    )
    response["Retry-After"] = "600"
    return response


def throttle(scope, limit, window, key="ip"):
    """
    View decorator limiting POSTs. `key` is "ip" or "post:<field>" (the
    lower-cased value of a posted field, e.g. the email being targeted).
    Over the limit -> HTTP 429.
    """
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method == "POST":
                if key == "ip":
                    ident = client_ip(request)
                else:
                    ident = request.POST.get(key.split(":", 1)[1], "").strip()
                if not allow(scope, ident, limit, window):
                    return too_many_requests(request)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
