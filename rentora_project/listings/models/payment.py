from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentBreakdown(models.Model):
    """Tracks commission, fees, and payouts for each booking"""
    booking = models.OneToOneField(
        'Booking',
        on_delete=models.CASCADE,
        related_name='payment_breakdown',
        help_text="Associated booking for this payment"
    )

    # Rental amount (before fees)
    rental_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="rental_days × daily_rate"
    )

    # Platform commission
    platform_fee_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('15.00'),
        help_text="Platform commission percentage (default 15%)"
    )
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Calculated: rental_total × (platform_fee_pct / 100)"
    )

    # Insurance (optional damage protection)
    insurance_opted = models.BooleanField(default=False)
    insurance_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Optional damage protection ($10 if opted, $0 otherwise)"
    )
    insurance_platform_cut = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="30% of insurance fee goes to platform, 70% reserved for claims"
    )

    # Total charged to renter
    total_charged_to_renter = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="rental_total + insurance_fee (what Stripe charges)"
    )

    # Owner payout
    owner_payout = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="rental_total - platform_fee (owner receives after commission)"
    )

    # Stripe processing fee
    stripe_fee_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('2.90'),
        help_text="Stripe percentage (2.9% + $0.30 fixed)"
    )
    stripe_fixed_fee = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.30'),
        help_text="Stripe fixed fee per transaction"
    )
    stripe_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Calculated Stripe processing fee"
    )

    # Net platform revenue
    net_platform_revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="platform_fee + insurance_platform_cut - stripe_fee"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment Breakdown"
        verbose_name_plural = "Payment Breakdowns"

    def __str__(self):
        return f"Payment #{self.id} | Rental: ${self.rental_total} | Owner Payout: ${self.owner_payout}"
