from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from listings.models.booking      import Booking, BookingStatus
from listings.models.notification import Notification, NotificationType


class Command(BaseCommand):
    help = "Send return-reminder notifications for rentals ending in 1 or 2 days."

    def handle(self, *args, **options):
        today      = timezone.now().date()
        targets    = [today + timedelta(days=1), today + timedelta(days=2)]
        sent = 0

        active = Booking.objects.filter(
            status=BookingStatus.APPROVED,
            end_date__in=targets,
        ).select_related("renter", "tool")

        for booking in active:
            days_left = (booking.end_date - today).days

            already_sent = Notification.objects.filter(
                user=booking.renter,
                booking=booking,
                notification_type=NotificationType.RETURN_REMINDER,
                created_at__date=today,
            ).exists()

            if already_sent:
                continue

            Notification.objects.create_for(
                user=booking.renter,
                notification_type=NotificationType.RETURN_REMINDER,
                message=(
                    f"Reminder: your rental of \"{booking.tool.title}\" ends in "
                    f"{days_left} day{'s' if days_left != 1 else ''}  "
                    f"(due {booking.end_date}). Please arrange the return with the owner."
                ),
                booking=booking,
            )
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} return reminder(s)."))
