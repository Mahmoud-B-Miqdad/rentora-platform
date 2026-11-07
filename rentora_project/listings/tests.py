import time
from io import StringIO

from django.core import mail, signing
from django.core.cache import caches
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from listings.models import ContactMessage
from listings.models.contact import FORM_TOKEN_SALT
from listings.services.abuse_guard import client_ip
from users.models import User


def _token(age_seconds=30):
    """A valid form token that looks like it was issued `age_seconds` ago."""
    return signing.dumps(int(time.time()) - age_seconds, salt=FORM_TOKEN_SALT)


def _payload(**overrides):
    data = {
        "name": "Real Person",
        "email": "person@example.com",
        "subject": "Drill will not start",
        "category": "technical",
        "message": "The drill I rented does not power on at all.",
        "form_token": _token(),
        "website": "",
    }
    data.update(overrides)
    return data


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    TRUSTED_PROXY_COUNT=1,
)
class ContactFormAbuseTests(TestCase):
    """The public support form must not be usable as a ticket/email flood."""

    def setUp(self):
        caches["throttle"].clear()
        self.url = reverse("listings:contact")

    def tearDown(self):
        caches["throttle"].clear()

    def _post(self, ip="203.0.113.7", **overrides):
        return self.client.post(
            self.url, _payload(**overrides), HTTP_X_FORWARDED_FOR=ip)

    def test_form_carries_token_and_honeypot(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn('name="form_token"', html)
        self.assertIn('name="website"', html)

    def test_anonymous_ticket_is_stored_but_typed_address_is_never_mailed(self):
        response = self._post(email="victim@example.org")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_verified_user_gets_confirmation_at_account_email_only(self):
        user = User.objects.create_user({
            "name": "Owner", "email": "owner@example.com",
            "password": "Passw0rd123", "location": "Gaza"})
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        session = self.client.session
        session["user_id"] = user.id
        session.save()

        self._post(email="someone-else@example.org")

        ticket = ContactMessage.objects.get()
        self.assertEqual(ticket.email, "owner@example.com")
        self.assertEqual(ticket.user, user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])

    def test_unverified_user_gets_no_confirmation(self):
        user = User.objects.create_user({
            "name": "Newbie", "email": "newbie@example.com",
            "password": "Passw0rd123", "location": "Gaza"})
        session = self.client.session
        session["user_id"] = user.id
        session.save()

        self._post()

        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_without_token_is_rejected(self):
        data = _payload()
        del data["form_token"]
        self.client.post(self.url, data, HTTP_X_FORWARDED_FOR="203.0.113.8")
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_forged_token_is_rejected(self):
        self._post(form_token="not-a-real-token")
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_instant_submission_is_rejected(self):
        self._post(form_token=_token(age_seconds=0))
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_honeypot_fakes_success_but_stores_nothing(self):
        response = self._post(website="http://spam.example")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_header_injection_in_subject_is_rejected(self):
        self._post(subject="Hello\r\nBcc: victim@example.org")
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_invalid_email_and_category_rejected(self):
        self._post(email="a@b")
        self._post(email="fine@example.com", category="drop table")
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_executable_attachment_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self._post(attachment=SimpleUploadedFile("shell.php", b"<?php ?>"))
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_per_ip_hourly_limit(self):
        statuses = [
            self._post(email=f"u{i}@example.com", subject=f"Subject number {i}").status_code
            for i in range(7)
        ]
        self.assertEqual(statuses[:5], [302] * 5)
        self.assertEqual(statuses[5:], [429, 429])
        self.assertEqual(ContactMessage.objects.count(), 5)

    def test_other_ips_are_not_affected_by_one_noisy_ip(self):
        for i in range(6):
            self._post(ip="198.51.100.1", email=f"u{i}@example.com",
                       subject=f"Subject number {i}")
        response = self._post(ip="198.51.100.2")
        self.assertEqual(response.status_code, 302)

    def test_spoofed_forwarded_header_cannot_dodge_limit(self):
        # Client prepends fake addresses; our proxy appends the real one last.
        codes = [
            self.client.post(
                self.url,
                _payload(email=f"u{i}@example.com", subject=f"Subject number {i}"),
                HTTP_X_FORWARDED_FOR=f"10.0.0.{i}, 203.0.113.99",
            ).status_code
            for i in range(7)
        ]
        self.assertEqual(codes.count(429), 2)

    def test_per_email_daily_limit(self):
        codes = [
            self._post(ip=f"192.0.2.{i}", email="same@example.com",
                       subject=f"Subject number {i}").status_code
            for i in range(5)
        ]
        self.assertEqual(codes, [302, 302, 302, 429, 429])

    def test_identical_resubmission_creates_no_duplicate(self):
        self._post()
        self._post(form_token=_token())
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_global_circuit_breaker(self):
        # Fill the global counter to its cap, then the next valid ticket is refused.
        from listings.services.abuse_guard import allow
        for _ in range(100):
            allow("contact-global-hour", "all", 100, 3600)
        response = self._post(ip="198.51.100.77")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(ContactMessage.objects.count(), 0)


class ClientIpTests(TestCase):
    def _request(self, **meta):
        return RequestFactory().get("/", **meta)

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_uses_rightmost_forwarded_entry(self):
        request = self._request(HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2",
                                REMOTE_ADDR="127.0.0.1")
        self.assertEqual(client_ip(request), "2.2.2.2")

    @override_settings(TRUSTED_PROXY_COUNT=0)
    def test_ignores_forwarded_header_without_proxy(self):
        request = self._request(HTTP_X_FORWARDED_FOR="1.1.1.1",
                                REMOTE_ADDR="9.9.9.9")
        self.assertEqual(client_ip(request), "9.9.9.9")

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_falls_back_to_remote_addr(self):
        self.assertEqual(client_ip(self._request(REMOTE_ADDR="9.9.9.9")), "9.9.9.9")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailTriggerThrottleTests(TestCase):
    """Signup / password-reset mail a typed address, so they are throttled too."""

    def setUp(self):
        caches["throttle"].clear()

    def tearDown(self):
        caches["throttle"].clear()

    def test_password_reset_per_address_limit(self):
        url = reverse("users:forgot_password")
        codes = [self.client.post(url, {"email": "target@example.com"}).status_code
                 for _ in range(5)]
        self.assertEqual(codes[:3], [302, 302, 302])
        self.assertEqual(codes[3:], [429, 429])

    def test_register_per_address_limit(self):
        url = reverse("users:register")
        codes = [self.client.post(url, {"email": "target@example.com"}).status_code
                 for _ in range(5)]
        self.assertEqual(codes.count(429), 2)


class PurgeSupportSpamCommandTests(TestCase):
    def _make(self, **kwargs):
        data = dict(name="Bot", email="x@spam.test", subject="Spam spam spam",
                    category="other", message="spam spam spam spam")
        data.update(kwargs)
        return ContactMessage.objects.create(**data)

    def test_dry_run_deletes_nothing(self):
        self._make()
        call_command("purge_support_spam", stdout=StringIO())
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_apply_removes_only_unattended_anonymous_tickets(self):
        user = User.objects.create_user({
            "name": "Owner", "email": "o@example.com",
            "password": "Passw0rd123", "location": "Gaza"})
        self._make(email="a@spam.test")
        self._make(email="b@spam.test")
        keep_user = self._make(email="o@example.com", user=user)
        keep_handled = self._make(email="c@spam.test", status="resolved",
                                  staff_response="Fixed")
        call_command("purge_support_spam", "--apply", stdout=StringIO())
        self.assertEqual(
            set(ContactMessage.objects.values_list("pk", flat=True)),
            {keep_user.pk, keep_handled.pk})

    def test_domain_filter(self):
        self._make(email="a@spam.test")
        self._make(email="a@gmail.com")
        call_command("purge_support_spam", "--apply",
                     "--email-domain", "spam.test", stdout=StringIO())
        self.assertEqual(ContactMessage.objects.get().email, "a@gmail.com")
