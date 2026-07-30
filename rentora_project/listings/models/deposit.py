from django.db import models
from django.utils.translation import gettext_lazy as _


class DepositDispute(models.Model):
    """Handles disputes over tool condition and deposit refunds"""

    STATUS_CHOICES = [
        ('open', _('Open')),
        ('staff_reviewing', _('Staff Reviewing')),
        ('resolved_refund', _('Resolved - Full Refund')),
        ('resolved_partial', _('Resolved - Partial Refund')),
        ('resolved_claim', _('Resolved - Damage Claim')),
    ]

    INITIATED_BY_CHOICES = [
        ('owner', _('Owner')),
        ('renter', _('Renter')),
    ]

    STAFF_DECISION_CHOICES = [
        ('refund_full', _('Full Refund to Renter')),
        ('refund_partial', _('Partial Refund to Renter')),
        ('owner_claim', _('Pay Owner for Damage')),
        ('split_50_50', _('50/50 Split')),
        ('dismiss', _('Dismiss Claim')),
    ]

    booking = models.OneToOneField(
        'Booking',
        on_delete=models.CASCADE,
        related_name='deposit_dispute'
    )

    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Original deposit amount from booking"
    )

    initiated_by = models.CharField(
        max_length=10,
        choices=INITIATED_BY_CHOICES,
        help_text="Who raised the dispute (Owner about damage, or Renter about false claim)"
    )

    reason = models.TextField(
        help_text="Why the dispute was initiated. Owner: 'Tool returned broken', Renter: 'Tool was already broken'"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open'
    )

    # Evidence (photos/videos of tool condition)
    dispute_evidence = models.FileField(
        upload_to='disputes/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Photo/video evidence of tool damage or condition"
    )

    # Responses from both parties
    owner_response = models.TextField(
        blank=True,
        help_text="Owner's response/counter-argument to the dispute"
    )

    renter_response = models.TextField(
        blank=True,
        help_text="Renter's response/counter-argument to the dispute"
    )

    # Staff decision
    staff_decision = models.CharField(
        max_length=20,
        choices=STAFF_DECISION_CHOICES,
        null=True,
        blank=True,
        help_text="Admin's resolution decision"
    )

    staff_notes = models.TextField(
        blank=True,
        help_text="Internal notes from staff investigation"
    )

    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount to be refunded to renter (if resolved_refund/partial)"
    )

    claim_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount to be paid to owner for damage (if resolved_claim)"
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the dispute was resolved"
    )

    resolved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'is_staff': True},
        related_name='disputes_resolved'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Deposit Dispute"
        verbose_name_plural = "Deposit Disputes"
        ordering = ['-created_at']

    def __str__(self):
        return f"Dispute #{self.id} | Booking {self.booking_id} | Status: {self.get_status_display()}"
