import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import models


# ─────────────────────────────────────────────
#  Choices
# ─────────────────────────────────────────────

class BookingStatus(models.TextChoices):
    PENDING         = "pending",         "Pending"
    PAYMENT_PENDING = "payment_pending", "Payment Pending"
    APPROVED        = "approved",        "Approved"
    REJECTED        = "rejected",        "Rejected"
    RETURN_PENDING  = "return_pending",  "Return Pending"
    COMPLETED       = "completed",       "Completed"
    CANCELLED       = "cancelled",       "Cancelled"


# ─────────────────────────────────────────────
#  Manager
# ─────────────────────────────────────────────

class BookingManager(models.Manager):

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_date(value, field_name, errors, label):
        """
        Coerces *value* (str ISO-8601 or datetime.date) to a date object.
        Populates errors on failure and returns None.
        """
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except (TypeError, ValueError):
            errors[field_name] = f"{label} must be a valid date (YYYY-MM-DD)."
            return None

    def _has_date_overlap(self, tool, start_date, end_date, exclude_booking_id=None):
        """
        Returns True if *tool* already has an approved or pending booking
        whose date range overlaps [start_date, end_date].

        Overlap condition (Allen's interval algebra):
            existing.start <= requested.end  AND  existing.end >= requested.start
        """
        qs = self.filter(
            tool=tool,
            status__in=[BookingStatus.PENDING, BookingStatus.APPROVED],
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        if exclude_booking_id:
            qs = qs.exclude(pk=exclude_booking_id)
        return qs.exists()

    @staticmethod
    def _calculate_total(start_date, end_date, daily_rate):
        """
        Returns total price as Decimal: rental_days × daily_rate.
        Minimum of 1 day is enforced.
        """
        rental_days = (end_date - start_date).days
        rental_days = max(rental_days, 1)
        return Decimal(str(daily_rate)) * Decimal(rental_days)

    # ── public API ────────────────────────────────────────────────────────────

    def register_validator(self, post_data, renter, tool):
        """
        Validates all incoming data for Booking creation.

        Business rules enforced:
        ─ end_date must be strictly after start_date
        ─ start_date must not be in the past
        ─ tool must be marked is_available=True
        ─ no date overlap with existing active bookings for this tool
        ─ owner cannot book their own tool

        Parameters
        ----------
        post_data : dict
            Must contain 'start_date' and 'end_date' (ISO-8601 strings or date objects).
        renter : users.User
            The authenticated user requesting the rental.
        tool : listings.Tool
            The listing being booked.

        Returns
        -------
        dict
            Field-keyed error messages. Empty dict means validation passed.
        """
        errors = {}

        # ── entity references ─────────────────────────────────────────────────
        if renter is None or not getattr(renter, "pk", None):
            errors["renter"] = "A valid authenticated renter is required."

        if tool is None or not getattr(tool, "pk", None):
            errors["tool"] = "A valid tool listing is required."
            return errors  # cannot continue without a tool

        # ── self-rental guard ─────────────────────────────────────────────────
        if getattr(renter, "pk", None) == getattr(tool.owner, "pk", None):
            errors["renter"] = "You cannot book a tool that you own."

        # ── availability flag ─────────────────────────────────────────────────
        if not tool.is_available:
            errors["tool"] = "This tool is not currently available for rental."

        # ── date parsing ───────────────────────────────────────────────────────
        start_date = self._parse_date(
            post_data.get("start_date"), "start_date", errors, "Start date"
        )
        end_date = self._parse_date(
            post_data.get("end_date"), "end_date", errors, "End date"
        )

        # ── date logic (only when both parsed successfully) ────────────────────
        if start_date and end_date:
            today = date.today()

            if start_date < today:
                errors["start_date"] = "Start date cannot be in the past."

            if end_date <= start_date:
                errors["end_date"] = (
                    "End date must be strictly after the start date."
                )

            # ── overlap check ─────────────────────────────────────────────────
            if "start_date" not in errors and "end_date" not in errors:
                if self._has_date_overlap(tool, start_date, end_date):
                    errors["start_date"] = (
                        "This tool is already booked during the selected dates. "
                        "Please choose different dates."
                    )

        return errors

    def create_booking(self, post_data, renter, tool):
        """
        Creates and persists a new Booking with auto-calculated total_price.
        Callers must run register_validator() first and guard on errors.
        """
        start_date = date.fromisoformat(str(post_data["start_date"]))
        end_date   = date.fromisoformat(str(post_data["end_date"]))
        total      = self._calculate_total(start_date, end_date, tool.daily_rate)

        return self.create(
            renter=renter,
            tool=tool,
            start_date=start_date,
            end_date=end_date,
            total_price=total,
            status=BookingStatus.PENDING,
        )

    def active_for_tool(self, tool):
        """All pending/approved bookings for a specific tool."""
        return self.filter(
            tool=tool,
            status__in=[BookingStatus.PENDING, BookingStatus.APPROVED],
        )

    def history_for_user(self, user):
        """All bookings where the user is the renter, newest first."""
        return self.filter(renter=user).order_by("-created_at")

    def pending_for_owner(self, owner):
        """
        Bookings awaiting the owner's approval across all their tools.
        """
        return self.filter(
            tool__owner=owner,
            status=BookingStatus.PENDING,
        ).select_related("tool", "renter").order_by("start_date")


# ─────────────────────────────────────────────
#  Model
# ─────────────────────────────────────────────

class Booking(models.Model):
    """
    Represents a single rental transaction between a renter and a tool owner.
    Tracks the agreed date range, auto-computed price, and lifecycle status.
    """

    renter = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="bookings",
        help_text="The platform member who requested the rental.",
    )
    tool = models.ForeignKey(
        "listings.Tool",
        on_delete=models.CASCADE,
        related_name="bookings",
        help_text="The tool listing this booking is associated with.",
    )
    start_date = models.DateField(
        help_text="First day of the rental period (inclusive).",
    )
    end_date = models.DateField(
        help_text="Last day of the rental period (inclusive).",
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Auto-calculated: rental_days × tool.daily_rate.",
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        help_text="Lifecycle state of this rental request.",
    )
    return_requested_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the owner pressed Mark as Returned.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BookingManager()

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Booking #{self.pk} — {self.tool.title} "
            f"({self.start_date} → {self.end_date}) [{self.status}]"
        )

    # ── instance-level convenience ─────────────────────────────────────────────

    @property
    def rental_days(self):
        """Number of billable rental days (minimum 1)."""
        return max((self.end_date - self.start_date).days, 1)

    @property
    def is_active(self):
        """True when the booking is in a live (pending or approved) state."""
        return self.status in {BookingStatus.PENDING, BookingStatus.APPROVED}