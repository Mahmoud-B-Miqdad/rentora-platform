import re

from django.db import models


# ─────────────────────────────────────────────
#  Choices
# ─────────────────────────────────────────────

class ReviewType(models.TextChoices):
    FOR_TOOL   = "for_tool",   "For Tool"
    FOR_OWNER  = "for_owner",  "For Owner"
    FOR_RENTER = "for_renter", "For Renter"


# ─────────────────────────────────────────────
#  Manager
# ─────────────────────────────────────────────

class ReviewManager(models.Manager):

    _VALID_REVIEW_TYPES = {rt.value for rt in ReviewType}

    # ── public API ────────────────────────────────────────────────────────────

    def register_validator(self, post_data, reviewer, booking):
        """
        Validates all incoming data for Review creation.

        Business rules enforced:
        ─ rating must be an integer in the closed range [1, 5]
        ─ review_type must be one of the allowed choices
        ─ booking must have status='completed'
        ─ reviewer must be a party to the booking (renter or tool owner)
        ─ duplicate reviews for the same booking / reviewer / type are rejected

        Parameters
        ----------
        post_data : dict
            Expected keys: 'rating' (int 1-5), 'review_type' (str), 'comment' (str, optional).
        reviewer : users.User
            The authenticated user submitting this review.
        booking : listings.Booking
            The completed booking this review references.

        Returns
        -------
        dict
            Field-keyed error messages. Empty dict means validation passed.
        """
        errors = {}

        rating      = post_data.get("rating")
        review_type = post_data.get("review_type", "").strip()
        comment     = post_data.get("comment", "").strip()

        # ── entity references ─────────────────────────────────────────────────
        if reviewer is None or not getattr(reviewer, "pk", None):
            errors["reviewer"] = "A valid authenticated reviewer is required."

        if booking is None or not getattr(booking, "pk", None):
            errors["booking"] = "A valid booking reference is required."
            return errors  # cannot run booking-dependent checks without it

        # ── booking must be completed ─────────────────────────────────────────
        from listings.models.booking import BookingStatus
        if booking.status != BookingStatus.COMPLETED:
            errors["booking"] = (
                "Reviews can only be submitted after a booking is completed."
            )

        # ── reviewer must be a party to the booking ───────────────────────────
        reviewer_pk  = getattr(reviewer, "pk", None)
        renter_pk    = getattr(booking.renter, "pk", None)
        owner_pk     = getattr(booking.tool.owner, "pk", None)

        if reviewer_pk not in {renter_pk, owner_pk}:
            errors["reviewer"] = (
                "You can only review bookings that you participated in."
            )

        # ── review_type ───────────────────────────────────────────────────────
        if not review_type:
            errors["review_type"] = "Review type is required."
        elif review_type not in self._VALID_REVIEW_TYPES:
            errors["review_type"] = (
                f"Review type must be one of: "
                f"{', '.join(self._VALID_REVIEW_TYPES)}."
            )
        else:
            # ── type/author coherence ─────────────────────────────────────────
            # Only the renter may review the tool or the owner.
            # Only the owner may review the renter.
            if review_type in {ReviewType.FOR_TOOL, ReviewType.FOR_OWNER}:
                if reviewer_pk != renter_pk:
                    errors["review_type"] = (
                        "Only the renter can leave a review for the tool or owner."
                    )
            elif review_type == ReviewType.FOR_RENTER:
                if reviewer_pk != owner_pk:
                    errors["review_type"] = (
                        "Only the tool owner can leave a review for the renter."
                    )

            # ── duplicate guard ───────────────────────────────────────────────
            if (
                "review_type" not in errors
                and "reviewer" not in errors
                and self.filter(
                    booking=booking,
                    reviewer=reviewer,
                    review_type=review_type,
                ).exists()
            ):
                errors["review_type"] = (
                    "You have already submitted this type of review "
                    "for this booking."
                )

        # ── rating ────────────────────────────────────────────────────────────
        if rating is None or str(rating).strip() == "":
            errors["rating"] = "Rating is required."
        else:
            try:
                rating_int = int(rating)
            except (TypeError, ValueError):
                errors["rating"] = "Rating must be a whole number."
                rating_int = None

            if rating_int is not None and not (1 <= rating_int <= 5):
                errors["rating"] = "Rating must be between 1 and 5."

        # ── comment (optional but bounded when provided) ───────────────────────
        if comment and len(comment) > 1000:
            errors["comment"] = "Comment must not exceed 1000 characters."

        return errors

    def create_review(self, post_data, reviewer, booking):
        """
        Persists a new Review record.
        Callers must run register_validator() first and guard on errors.
        """
        return self.create(
            booking=booking,
            reviewer=reviewer,
            rating=int(post_data["rating"]),
            review_type=post_data["review_type"].strip(),
            comment=post_data.get("comment", "").strip() or None,
        )

    def for_tool(self, tool):
        """All FOR_TOOL reviews for a specific listing, newest first."""
        return (
            self.filter(review_type=ReviewType.FOR_TOOL, booking__tool=tool)
            .select_related("reviewer")
            .order_by("-created_at")
        )

    def for_user(self, user):
        """All reviews ever written *about* a specific user (as owner or renter)."""
        return self.filter(
            models.Q(
                review_type=ReviewType.FOR_OWNER,
                booking__tool__owner=user,
            )
            | models.Q(
                review_type=ReviewType.FOR_RENTER,
                booking__renter=user,
            )
        ).order_by("-created_at")

    def average_rating_for_tool(self, tool):
        """
        Returns the average FOR_TOOL rating as a float, or None if no reviews.
        """
        result = (
            self.filter(review_type=ReviewType.FOR_TOOL, booking__tool=tool)
            .aggregate(avg=models.Avg("rating"))
        )
        return result["avg"]


# ─────────────────────────────────────────────
#  Model
# ─────────────────────────────────────────────

class Review(models.Model):
    """
    Captures a single piece of feedback submitted after a completed booking.

    Three distinct review types exist per booking:
    ─ FOR_TOOL    (renter → tool quality)
    ─ FOR_OWNER   (renter → owner communication)
    ─ FOR_RENTER  (owner  → renter reliability)
    """

    booking = models.ForeignKey(
        "listings.Booking",
        on_delete=models.CASCADE,
        related_name="reviews",
        help_text="The completed booking this review is attached to.",
    )
    reviewer = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="reviews_given",
        help_text="The platform member who authored this review.",
    )
    rating = models.PositiveSmallIntegerField(
        help_text="Numeric score from 1 (Poor) to 5 (Excellent).",
    )
    comment = models.TextField(
        null=True,
        blank=True,
        help_text="Optional written feedback (max 1000 characters).",
    )
    review_type = models.CharField(
        max_length=20,
        choices=ReviewType.choices,
        help_text="Indicates the target of this review.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ReviewManager()

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ["-created_at"]
        # Enforce uniqueness: one review per booking / reviewer / type combination.
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "reviewer", "review_type"],
                name="unique_review_per_booking_reviewer_type",
            )
        ]

    def __str__(self):
        return (
            f"Review by {self.reviewer} "
            f"({self.get_review_type_display()}) — "
            f"{'★' * self.rating}{'☆' * (5 - self.rating)}"
        )