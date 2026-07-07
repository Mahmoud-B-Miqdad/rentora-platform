"""
users/services.py — email-related helpers for the users app.
"""
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone


def send_verification_email(request, user) -> None:
    """
    Generate a fresh verification token, persist it, then email the user.
    Any previous token for this user is replaced.
    """
    from users.models import EmailVerification       # local import avoids circular refs

    token      = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(hours=24)

    EmailVerification.objects.filter(user=user).delete()
    EmailVerification.objects.create(user=user, token=token, expires_at=expires_at)

    verify_url = request.build_absolute_uri(f"/users/verify-email/{token}/")

    html_body = render_to_string("users/emails/email_verify.html", {
        "user":       user,
        "verify_url": verify_url,
    })
    plain_body = (
        f"Hi {user.name},\n\n"
        f"Please verify your Rentora account by visiting:\n{verify_url}\n\n"
        f"This link expires in 24 hours.\n\n— The Rentora Team"
    )

    send_mail(
        subject="Verify your Rentora account",
        message=plain_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_body,
        fail_silently=False,
    )
