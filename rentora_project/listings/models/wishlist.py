from django.db import models


class Wishlist(models.Model):
    """Stores a user's saved/favourite tool listings."""

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='wishlist_items',
    )
    tool = models.ForeignKey(
        'listings.Tool',
        on_delete=models.CASCADE,
        related_name='wishlist_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'tool']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} → {self.tool.title}"
