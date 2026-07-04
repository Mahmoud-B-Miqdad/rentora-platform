from django.db import models


class ConversationManager(models.Manager):
    def get_or_create_for_booking(self, booking):
        obj, _ = self.get_or_create(booking=booking)
        return obj

    def for_user(self, user):
        return (
            self.filter(
                models.Q(booking__renter=user) | models.Q(booking__tool__owner=user)
            )
            .select_related("booking", "booking__tool", "booking__renter", "booking__tool__owner")
            .order_by("-updated_at")
        )


class Conversation(models.Model):
    booking    = models.OneToOneField(
        "listings.Booking",
        on_delete=models.CASCADE,
        related_name="conversation",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ConversationManager()

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Conversation for Booking #{self.booking_id}"

    def unread_count_for(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()

    def other_participant(self, user):
        booking = self.booking
        if user.pk == booking.renter_id:
            return booking.tool.owner
        return booking.renter


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender     = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    text       = models.TextField()
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.sender}] {self.text[:60]}"
