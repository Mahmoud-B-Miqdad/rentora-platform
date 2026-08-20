"""
Central money-formatting filters.

Single source of truth for how prices are displayed, so the site never again
shows one currency ($) while actually charging another (see LAHZA_CURRENCY /
CURRENCY_SYMBOL in settings.py).

`money` is bidi-safe: mixing digits + a currency symbol inside an RTL (Arabic)
context can make the Unicode bidi algorithm reorder the characters (observed
live in Lahza's own Arabic dashboard, e.g. "330" rendering as "033"). Wrapping
the amount in <bdi dir="ltr"> forces it to always render left-to-right,
regardless of the surrounding text direction.
"""
from decimal import Decimal, InvalidOperation

from django import template
from django.conf import settings
from django.utils.html import format_html

register = template.Library()


def _format_amount(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)

    quantized = amount.quantize(Decimal("0.01"))
    if quantized == quantized.to_integral_value():
        return f"{quantized:,.0f}"
    return f"{quantized:,.2f}"


@register.filter(name="money")
def money(value):
    """Render an amount as '20 ₪' (LTR-isolated so RTL pages can't reverse the digits)."""
    amount = _format_amount(value)
    symbol = getattr(settings, "CURRENCY_SYMBOL", "₪")
    return format_html('<bdi class="money" dir="ltr">{} {}</bdi>', amount, symbol)


@register.filter(name="money_plain")
def money_plain(value):
    """Plain-text 'amount symbol' — for emails and other non-HTML contexts."""
    amount = _format_amount(value)
    symbol = getattr(settings, "CURRENCY_SYMBOL", "₪")
    return f"{amount} {symbol}"


@register.simple_tag
def currency_symbol():
    return getattr(settings, "CURRENCY_SYMBOL", "₪")
