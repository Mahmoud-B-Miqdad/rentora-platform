import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from listings.models import ContactMessage
from listings.services.abuse_guard import allow, client_ip
from listings.services.email_service import send_support_confirmation_email

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def terms_of_service(request):
    """Terms of Service page (static)"""
    return render(request, 'listings/legal/terms_of_service.html')


@require_http_methods(["GET"])
def privacy_policy(request):
    """Privacy Policy page (static)"""
    return render(request, 'listings/legal/privacy_policy.html')


@require_http_methods(["GET"])
def faq(request):
    """FAQ page with expandable sections"""
    return render(request, 'listings/legal/faq.html')


def _contact_form(request, status=200, **context):
    """Render the form with a fresh signed token (proof it was loaded, and when)."""
    context["form_token"] = ContactMessage.objects.make_form_token()
    return render(request, 'listings/legal/contact.html', context, status=status)


@require_http_methods(["GET", "POST"])
def contact(request):
    """Support/Contact form (public — hardened against bots, see abuse_guard)."""

    if request.method == "GET":
        return _contact_form(request)

    ip = client_ip(request)
    sender = None
    session_user_id = request.session.get("user_id")
    if session_user_id:
        from users.models import User
        sender = User.objects.filter(pk=session_user_id).first()

    # Gate 1 — every POST attempt counts, valid or not, so a script can't
    # hammer the form for free.
    if not allow("contact-attempt", ip, 20, 3600):
        return _contact_form(request, status=429, errors={
            'form': _('Too many requests. Please try again later.')})

    # Gate 2 — honeypot: invisible to people, tempting to bots. Pretend it
    # worked so the bot learns nothing, but store nothing and send nothing.
    if request.POST.get('website', ''):
        logger.warning("Support honeypot tripped from %s", ip)
        messages.success(request, _('Thank you! We received your message. We\'ll respond within 24 hours.'))
        return redirect('listings:contact')

    # Gate 3 — signed, time-stamped token from the GET (no token = never loaded the form).
    token_error = ContactMessage.objects.form_token_error(request.POST.get('form_token'))
    if token_error:
        return _contact_form(request, errors={'form': token_error}, form_data=request.POST)

    errors = ContactMessage.objects.submission_validator(request.POST, request.FILES)
    if errors:
        return _contact_form(request, errors=errors, form_data=request.POST)

    # Gate 4 — volume caps on actual tickets: per IP (hour + day), per address,
    # per account, and a global circuit-breaker so a distributed flood can't
    # fill the inbox either. Checked in order; the global cap only counts
    # traffic that already passed the personal ones.
    email = sender.email if sender else request.POST.get('email', '').strip().lower()
    within_limits = (
        allow("contact-ip-hour", ip, 5, 3600)
        and allow("contact-ip-day", ip, 15, 86400)
        and allow("contact-email-day", email, 3, 86400)
        and (sender is None or allow("contact-user-day", sender.pk, 10, 86400))
        and allow("contact-global-hour", "all", 100, 3600)
    )
    if not within_limits:
        return _contact_form(request, status=429, errors={
            'form': _('Too many requests. Please try again later.')},
            form_data=request.POST)

    ticket, created = ContactMessage.objects.create_ticket(
        request.POST, request.FILES, sender=sender)
    logger.info("Support ticket #%s (created=%s) from ip=%s user=%s",
                ticket.pk, created, ip, getattr(sender, "pk", None))

    # Only ever email an address the account holder has proven they own. A
    # typed-in address on an anonymous ticket is NOT mailed: that is exactly
    # how the form was used to spam third parties from our SMTP account.
    if created and sender and sender.is_verified:
        send_support_confirmation_email(ticket)

    messages.success(request, _('Thank you! We received your message. We\'ll respond within 24 hours.'))
    return redirect('listings:contact')


@require_http_methods(["GET"])
def my_messages(request):
    """Logged-in user's own support tickets and the staff replies."""
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("users:login")

    from users.models import User
    user = get_object_or_404(User, pk=user_id)
    tickets = ContactMessage.objects.filter(user=user).order_by("-created_at")
    return render(request, "listings/legal/my_messages.html", {"tickets": tickets})
