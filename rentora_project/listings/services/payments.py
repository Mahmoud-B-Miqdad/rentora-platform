"""
Payment gateway abstraction.

The rest of the app talks to `get_payment_provider()` — never to a specific
gateway — so swapping Lahza for another provider later touches only this file.

Lahza (https://lahza.io) is Palestine's Paystack-compatible gateway. It supports
native marketplace splits: a transaction can route the owner's share to their
`subaccount` while the platform keeps its commission automatically.

Amounts are handled in the currency's minor unit (agorot for ILS, qirsh for JOD,
cents for USD) — Decimal major-unit amounts are converted with `to_subunits()`.
"""
import hashlib
import hmac
import logging
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Raised when the gateway rejects a request or is unreachable."""


def to_subunits(amount) -> int:
    """Decimal/str major amount (e.g. 10.50) → integer minor units (1050)."""
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_subunits(minor) -> Decimal:
    """Integer minor units (1050) → Decimal major amount (10.50)."""
    return (Decimal(int(minor)) / 100).quantize(Decimal("0.01"))


class LahzaProvider:
    """Thin, verified client over the Lahza REST API."""

    def __init__(self):
        self.base = settings.LAHZA_API_BASE.rstrip("/")
        self.secret = settings.LAHZA_SECRET_KEY
        self.currency = settings.LAHZA_CURRENCY

    # ── internals ──────────────────────────────────────────────────────────
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.secret}",
            "Content-Type": "application/json",
        }

    def _request(self, method, path, **kwargs):
        if not self.secret:
            raise PaymentError("Lahza secret key is not configured.")
        url = f"{self.base}{path}"
        try:
            resp = requests.request(method, url, headers=self._headers(), timeout=30, **kwargs)
        except requests.RequestException as exc:
            logger.exception("Lahza request failed: %s %s", method, path)
            raise PaymentError("Could not reach the payment gateway.") from exc

        try:
            body = resp.json()
        except ValueError:
            raise PaymentError(f"Unexpected gateway response ({resp.status_code}).")

        if not resp.ok or not body.get("status", False):
            msg = body.get("message", f"Gateway error ({resp.status_code}).")
            raise PaymentError(msg)
        return body.get("data", {})

    # ── checkout ───────────────────────────────────────────────────────────
    def initialize_payment(self, *, amount_subunits, email, reference,
                           callback_url, subaccount=None,
                           transaction_charge_subunits=None, bearer=None,
                           metadata=None):
        """
        Start a payment. Returns {authorization_url, access_code, reference}.

        When `subaccount` is given, Lahza splits the money: the owner's
        subaccount receives its share and the platform keeps its commission
        (defined by the subaccount's percentage_charge, or overridden per
        transaction with `transaction_charge_subunits`).
        """
        payload = {
            "email": email,
            "amount": str(int(amount_subunits)),
            "currency": self.currency,
            "reference": reference,
            "callback_url": callback_url,
        }
        if subaccount:
            payload["subaccount"] = subaccount
        if transaction_charge_subunits is not None:
            payload["transaction_charge"] = int(transaction_charge_subunits)
        if bearer:
            payload["bearer"] = bearer               # 'account' | 'subaccount'
        if metadata:
            payload["metadata"] = metadata

        return self._request("POST", "/transaction/initialize", json=payload)

    def verify_payment(self, reference):
        """
        Confirm a payment by reference. Returns the raw transaction data, incl.
        `status` ('success' when paid) and `amount` (minor units).
        """
        return self._request("GET", f"/transaction/verify/{reference}")

    def refund(self, reference, amount_subunits=None):
        """Refund a transaction — full if amount omitted, else partial."""
        payload = {"transaction": reference}
        if amount_subunits is not None:
            payload["amount"] = str(int(amount_subunits))
        return self._request("POST", "/refund", json=payload)

    # ── marketplace onboarding ─────────────────────────────────────────────
    def create_subaccount(self, *, business_name, settlement_bank,
                          account_number, percentage_charge):
        """
        Create an owner's payout subaccount. `percentage_charge` is the platform
        commission (%) kept from each transaction routed to this subaccount.
        Returns the raw data incl. `subaccount_code` (e.g. 'ACCT_xxx').
        """
        payload = {
            "business_name": business_name,
            "settlement_bank": settlement_bank,
            "account_number": account_number,
            "percentage_charge": percentage_charge,
        }
        return self._request("POST", "/subaccount", json=payload)

    def list_banks(self):
        """Banks available for subaccount settlement (code + name)."""
        return self._request("GET", "/bank")

    # ── webhook ────────────────────────────────────────────────────────────
    def _expected_signatures(self, raw_body: bytes):
        """The valid HMAC digests of the body — SHA512 (Paystack default) + SHA256."""
        key = self.secret.encode("utf-8")
        return {
            hmac.new(key, raw_body, hashlib.sha512).hexdigest(),
            hmac.new(key, raw_body, hashlib.sha256).hexdigest(),
        }

    def verify_webhook(self, raw_body: bytes, request_headers) -> bool:
        """
        Verify a webhook is genuinely from Lahza. The gateway signs the raw body
        with an HMAC of the secret key. Rather than hard-coding the header name
        (which varies), we match the computed digest against every incoming
        header value — auto-detecting both the header and the algorithm.
        """
        if not self.secret:
            return False
        expected = self._expected_signatures(raw_body)
        for value in request_headers.values():
            if value and any(hmac.compare_digest(value, e) for e in expected):
                return True
        return False


_provider = None


def get_payment_provider():
    """Return the configured payment provider (singleton)."""
    global _provider
    if _provider is None:
        _provider = LahzaProvider()
    return _provider
