from django.db import models


class RentalConditionPhoto(models.Model):
    """
    A photo documenting the tool's real condition at a handover point, uploaded
    by the party who has custody at that moment:

      • pickup  → the renter, when they receive the tool (the "before" record)
      • return  → the owner, when they mark the tool returned (the "after" record)

    These are the true point-in-time references staff compare in a dispute —
    unlike the listing photos, which may be outdated.
    """
    class Phase(models.TextChoices):
        PICKUP = "pickup", "At pickup (renter)"
        RETURN = "return", "At return (owner)"

    booking = models.ForeignKey(
        "listings.Booking",
        on_delete=models.CASCADE,
        related_name="condition_photos",
    )
    phase = models.CharField(max_length=10, choices=Phase.choices)
    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="condition_photos",
    )
    image = models.ImageField(upload_to="condition/%Y/%m/%d/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Rental Condition Photo"
        verbose_name_plural = "Rental Condition Photos"

    def __str__(self):
        return f"{self.get_phase_display()} photo for booking #{self.booking_id}"
