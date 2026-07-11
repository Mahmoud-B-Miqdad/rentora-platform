from django.db import models
from django.conf import settings


class Report(models.Model):
    REASON_CHOICES = [
        ('scam', 'Scam / Fraud'),
        ('fake', 'Fake Listing'),
        ('no_show', 'No Show'),
        ('damage', 'Property Damage'),
        ('harassment', 'Harassment'),
        ('other', 'Other'),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports_made'
    )
    reported = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports_received'
    )
    STATUS_CHOICES = [
        ('pending',   'Pending review'),
        ('resolved',  'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    # Auto-flag threshold
    FLAGGED_AT = 3

    class Meta:
        unique_together = ('reporter', 'reported')  # each user can report one time
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reporter.name} reported {self.reported.name} - {self.reason}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Check if reported user should be flagged
        count = Report.objects.filter(reported=self.reported).count()
        if count >= self.FLAGGED_AT:
            self.reported.is_verified = False
            self.reported.save(update_fields=['is_verified'])