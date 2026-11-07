"""
Remove bot-generated support tickets.

Dry run by default — it only reports what it WOULD delete. Pass --apply to
actually delete. Only touches tickets that look unattended and anonymous:

    * not linked to a registered user,
    * still in the "new" status (no staff ever opened or answered them),
    * no staff response.

Examples:
    python manage.py purge_support_spam --since 2026-11-01
    python manage.py purge_support_spam --since 2026-11-01 --email-domain example.com --apply
"""
from collections import Counter
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from listings.models import ContactMessage


class Command(BaseCommand):
    help = "Delete anonymous, never-handled support tickets (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--since", help="Only tickets created on/after this date (YYYY-MM-DD).")
        parser.add_argument("--until", help="Only tickets created before this date (YYYY-MM-DD).")
        parser.add_argument("--email-domain", action="append", default=[],
                            help="Only tickets whose email ends with @DOMAIN (repeatable).")
        parser.add_argument("--apply", action="store_true", help="Really delete (default: dry run).")

    @staticmethod
    def _parse(value, flag):
        try:
            naive = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise CommandError(f"{flag} must look like YYYY-MM-DD")
        return timezone.make_aware(naive)

    def handle(self, *args, **opts):
        qs = ContactMessage.objects.filter(user__isnull=True, status="new", staff_response="")
        if opts["since"]:
            qs = qs.filter(created_at__gte=self._parse(opts["since"], "--since"))
        if opts["until"]:
            qs = qs.filter(created_at__lt=self._parse(opts["until"], "--until"))
        if opts["email_domain"]:
            from django.db.models import Q
            domain_q = Q()
            for domain in opts["email_domain"]:
                domain_q |= Q(email__iendswith="@" + domain.lstrip("@"))
            qs = qs.filter(domain_q)

        tickets = list(qs)
        self.stdout.write(f"Matching tickets: {len(tickets)}")
        by_domain = Counter(t.email.rsplit("@", 1)[-1].lower() for t in tickets)
        for domain, count in by_domain.most_common(15):
            self.stdout.write(f"  {count:>5}  @{domain}")

        if not opts["apply"]:
            self.stdout.write(self.style.WARNING("Dry run — nothing deleted. Re-run with --apply."))
            return

        for ticket in tickets:
            if ticket.attachment:
                ticket.attachment.delete(save=False)
        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} ticket(s)."))
