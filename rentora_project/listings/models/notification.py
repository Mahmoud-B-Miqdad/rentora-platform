from django.db import models


class NotificationType(models.TextChoices):
    BOOKING_RECEIVED  = "booking_received",  "New Booking Request"
    BOOKING_APPROVED  = "booking_approved",  "Booking Approved"
    BOOKING_REJECTED  = "booking_rejected",  "Booking Rejected"
    PAYMENT_RECEIVED  = "payment_received",  "Payment Received"
    RETURN_REQUESTED  = "return_requested",  "Return Requested"
    RETURN_CONFIRMED  = "return_confirmed",  "Return Confirmed"
    RETURN_REMINDER   = "return_reminder",   "Return Reminder"


# Maps each type to (fa-icon-class, css-color-token)
_TYPE_META = {
    NotificationType.BOOKING_RECEIVED : ("fa-inbox",            "notif-blue"),
    NotificationType.BOOKING_APPROVED : ("fa-circle-check",     "notif-green"),
    NotificationType.BOOKING_REJECTED : ("fa-circle-xmark",     "notif-red"),
    NotificationType.PAYMENT_RECEIVED : ("fa-credit-card",      "notif-blue"),
    NotificationType.RETURN_REQUESTED : ("fa-rotate-left",      "notif-amber"),
    NotificationType.RETURN_CONFIRMED : ("fa-flag-checkered",   "notif-green"),
    NotificationType.RETURN_REMINDER  : ("fa-clock",            "notif-amber"),
}


class NotificationManager(models.Manager):

    def create_for(self, *, user, notification_type, message, booking=None):
        return self.create(
            user=user,
            booking=booking,
            notification_type=notification_type,
            message=message,
        )

    def for_user(self, user, limit=25):
        return (
            self.filter(user=user)
            .select_related("booking", "booking__tool", "booking__tool__owner")
            .order_by("-created_at")[:limit]
        )

    def unread_count(self, user):
        return self.filter(user=user, is_read=False).count()


class Notification(models.Model):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    booking = models.ForeignKey(
        "listings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = NotificationManager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"[{self.notification_type}] → {self.user} — {self.message[:60]}"

    @property
    def icon(self):
        meta = _TYPE_META.get(self.notification_type, ("fa-bell", "notif-blue"))
        return meta[0]

    @property
    def color_class(self):
        meta = _TYPE_META.get(self.notification_type, ("fa-bell", "notif-blue"))
        return meta[1]

    @property
    def booking_url(self):
        if not self.booking_id:
            return "/dashboard/"

        T = NotificationType

        # ── Owner-only types ──────────────────────────────────────────────
        if self.notification_type == T.BOOKING_RECEIVED:
            # New request → owner reviews pending requests
            return "/dashboard/?tab=booking-requests&subtab=btab-pending"

        if self.notification_type == T.PAYMENT_RECEIVED:
            # Renter paid → booking is now active / approved
            return "/dashboard/?tab=booking-requests&subtab=btab-approved"

        # ── Renter-only types ─────────────────────────────────────────────
        if self.notification_type == T.BOOKING_APPROVED:
            # Approved → renter needs to pay (Awaiting tab)
            return "/dashboard/?tab=my-rentals&subtab=rtab-awaiting"

        if self.notification_type == T.BOOKING_REJECTED:
            # Rejected → lands in history
            return "/dashboard/?tab=my-rentals&subtab=rtab-history"

        if self.notification_type in {T.RETURN_REQUESTED, T.RETURN_REMINDER}:
            # Return pending or due soon → active rentals
            return "/dashboard/?tab=my-rentals&subtab=rtab-active"

        # ── RETURN_CONFIRMED → sent to both, route by recipient role ─────
        if self.notification_type == T.RETURN_CONFIRMED:
            try:
                if self.user_id == self.booking.tool.owner_id:
                    return "/dashboard/?tab=booking-requests&subtab=btab-completed"
            except Exception:
                pass
            return "/dashboard/?tab=my-rentals&subtab=rtab-history"

        return "/dashboard/"
