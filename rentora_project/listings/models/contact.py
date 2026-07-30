from django.db import models
from django.utils.translation import gettext_lazy as _


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
