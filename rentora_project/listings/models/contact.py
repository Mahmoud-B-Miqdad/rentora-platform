import os
import re
import time
from datetime import timedelta

from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

FORM_TOKEN_SALT = "support-contact-form"
MIN_FILL_SECONDS = 3          # humans need longer than this to fill the form
FORM_TOKEN_MAX_AGE = 60 * 60 * 6
ALLOWED_ATTACHMENT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"}
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
# CR / LF / NUL in a single-line field is a header-injection attempt.
_CONTROL_CHARS = re.compile("[\r\n\x00]")


class ContactMessageManager(models.Manager):
    """Validation and writes for the public support form (fat model / lean view)."""

    # ── form token (proves the form was actually loaded, and when) ──────────
    def make_form_token(self):
        return signing.dumps(int(time.time()), salt=FORM_TOKEN_SALT)

    def form_token_error(self, token):
        """None if the token is valid and old enough, else an error string."""
        try:
            issued = signing.loads(token or "", salt=FORM_TOKEN_SALT, max_age=FORM_TOKEN_MAX_AGE)
        except signing.BadSignature:
            return _("This form has expired. Please reload the page and try again.")
        if time.time() - issued < MIN_FILL_SECONDS:
            return _("That was too fast. Please wait a moment and submit again.")
        return None

    # ── validation ──────────────────────────────────────────────────────────
    def submission_validator(self, post, files=None):
        """Returns an errors dict ({} when the submission is acceptable)."""
        errors = {}
        name = post.get("name", "").strip()
        email = post.get("email", "").strip()
        subject = post.get("subject", "").strip()
        message = post.get("message", "").strip()
        category = post.get("category", "")

        if len(name) < 2 or len(name) > 100 or _CONTROL_CHARS.search(name):
            errors["name"] = _("Please enter a valid name.")
        try:
            validate_email(email)
            if len(email) > 254:
                raise ValidationError("too long")
        except ValidationError:
            errors["email"] = _("Please enter a valid email address.")
        if len(subject) < 5 or len(subject) > 200 or _CONTROL_CHARS.search(subject):
            errors["subject"] = _("Subject must be at least 5 characters.")
        if len(message) < 10:
            errors["message"] = _("Message must be at least 10 characters.")
        elif len(message) > 5000:
            errors["message"] = _("Message is too long (5000 characters maximum).")
        if category not in dict(ContactMessage.CATEGORY_CHOICES):
            errors["category"] = _("Please select a category.")

        attachment = (files or {}).get("attachment")
        if attachment:
            ext = os.path.splitext(attachment.name)[1].lower()
            if attachment.size > MAX_ATTACHMENT_BYTES:
                errors["attachment"] = _("The attachment must be under 10 MB.")
            elif ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
                errors["attachment"] = _("Only images and PDF files can be attached.")
        return errors

    # ── writes ──────────────────────────────────────────────────────────────
    def create_ticket(self, post, files=None, sender=None):
        """
        Store a ticket. Returns (ticket, created). An identical message from
        the same address within 24h returns the existing ticket instead of
        piling up duplicates. A logged-in sender's account email always wins
        over the typed one, so nobody can file tickets as somebody else.
        """
        email = sender.email if sender else post.get("email", "").strip().lower()
        subject = post.get("subject", "").strip()
        message = post.get("message", "").strip()

        duplicate = self.filter(
            email__iexact=email,
            subject=subject,
            message=message,
            created_at__gte=timezone.now() - timedelta(hours=24),
        ).first()
        if duplicate:
            return duplicate, False

        ticket = self.create(
            name=post.get("name", "").strip(),
            email=email,
            subject=subject,
            category=post.get("category", "other"),
            message=message,
            attachment=(files or {}).get("attachment"),
            user=sender,
        )
        return ticket, True


class ContactMessage(models.Model):
    """User support requests and inquiries"""

    CATEGORY_CHOICES = [
        ('payment', _('Payment Issue')),
        ('booking', _('Booking Problem')),
        ('dispute', _('Report/Dispute')),
        ('feature', _('Feature Request')),
        ('technical', _('Technical Issue')),
        ('other', _('Other')),
    ]

    STATUS_CHOICES = [
        ('new', _('New')),
        ('in_progress', _('In Progress')),
        ('resolved', _('Resolved')),
        ('closed', _('Closed')),
    ]

    # Sender info
    name = models.CharField(
        max_length=100,
        help_text="Sender's full name"
    )

    email = models.EmailField(
        help_text="Sender's email for response"
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_messages',
        help_text="Associated user if logged in"
    )

    # Message details
    subject = models.CharField(
        max_length=200,
        help_text="Issue subject/title"
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        help_text="Support category for routing"
    )

    message = models.TextField(
        help_text="Full message body"
    )

    attachment = models.FileField(
        upload_to='support/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Optional evidence (photo, screenshot, document) for staff review."
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )

    # Staff response
    staff_response = models.TextField(
        blank=True,
        help_text="Staff's response/resolution"
    )

    assigned_to = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'is_staff': True},
        related_name='assigned_support_messages',
        help_text="Staff member handling this ticket"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the ticket was resolved"
    )

    objects = ContactMessageManager()

    class Meta:
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['email', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.subject} — {self.name}"
