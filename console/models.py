from django.conf import settings
from django.db import models
 
 
class AdminAction(models.Model):
    """Audit trail — every staff decision is recorded with its reason."""
 
    ACTION_CHOICES = [
        ("suspend",         "Suspend user"),
        ("reinstate",       "Reinstate user"),
        ("dismiss_reports", "Dismiss reports"),
        ("force_complete",  "Force-complete booking"),
        ("category_change", "Category change"),
    ]
 
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="console_actions",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="console_actions_received",
    )
    target_booking = models.ForeignKey(
        "listings.Booking",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="console_actions",
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ["-created_at"]
 
    def __str__(self):
        return f"{self.staff} — {self.get_action_display()} ({self.created_at:%Y-%m-%d %H:%M})"